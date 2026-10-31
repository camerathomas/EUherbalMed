import streamlit as st
import pandas as pd
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Plantaardige geneesmiddelen",
    page_icon="🌿",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "planten_data.json"          # jouw originele JSON
INDICATIES_JSON = BASE_DIR / "planten_indicaties.json"
WAAROM_MD = BASE_DIR / "waarom_deze_app.md"


# ---------------------------------------------------------------------------
# Data laden (bestaande structuur)
# ---------------------------------------------------------------------------
@st.cache_data
def load_records() -> list[dict]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


records = load_records()
df = pd.DataFrame(records)

verwachte_kolommen = [
    "latin_name",
    "dutch_common_name",
    "english_common_name",
    "botanical_name",
    "therapeutic_area",
    "ema_status",
    "ema_outcome",
    "ema_url",
    "nl_registered",
    "nl_product_name",
    "nl_price_eur",
    "de_price_eur",
    "price_difference_pct",
    "notes",
]
for kolom in verwachte_kolommen:
    if kolom not in df.columns:
        df[kolom] = None

df["therapeutic_area_str"] = df["therapeutic_area"].apply(
    lambda x: ", ".join(x) if isinstance(x, list) else (x or "")
)


# ---------------------------------------------------------------------------
# Aanvulling: indicaties en EMA-status uit aparte JSON
# ---------------------------------------------------------------------------
@st.cache_data
def laad_indicaties() -> pd.DataFrame:
    if not INDICATIES_JSON.exists():
        st.warning(f"Het bestand '{INDICATIES_JSON.name}' kon niet worden gevonden.")
        return pd.DataFrame()
    with open(INDICATIES_JSON, encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


df_indicaties = laad_indicaties()

if not df.empty and not df_indicaties.empty:
    df = df.merge(
        df_indicaties,
        left_on="botanical_name",
        right_on="botanical_name",
        how="left",
        suffixes=("", "_aanvulling"),
    )
    # Als ema_status al bestond, vul aan waar leeg
    if "ema_status_aanvulling" in df.columns:
        df["ema_status"] = df["ema_status"].fillna(df["ema_status_aanvulling"])
        df = df.drop(columns=["ema_status_aanvulling"])

# Zorg dat de nieuwe kolommen altijd bestaan
for kolom in ["Indicatie", "EMA_status"]:
    if kolom not in df.columns:
        df[kolom] = None


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("🌿 Plantaardige geneesmiddelen")
st.caption(
    "Een overzicht van in Duitsland toegelaten plantaardige geneesmiddelen, "
    "met EMA-status en indicaties."
)

if "toon_waarom" not in st.session_state:
    st.session_state.toon_waarom = False

if st.button("Waarom deze app?"):
    st.session_state.toon_waarom = not st.session_state.toon_waarom

if st.session_state.toon_waarom:
    with st.container(border=True):
        if WAAROM_MD.exists():
            st.markdown(WAAROM_MD.read_text(encoding="utf-8"))
        else:
            st.info("De tekst 'waarom_deze_app.md' kon niet worden gevonden.")

st.divider()


# ---------------------------------------------------------------------------
# Filters (op de bestaande kolommen)
# ---------------------------------------------------------------------------
st.subheader("Overzicht")

col1, col2, col3 = st.columns(3)

with col1:
    ema_opties = ["Alle"] + sorted(
        df["ema_status"].dropna().unique().tolist()
    ) if "ema_status" in df.columns else ["Alle"]
    keuze_ema = st.selectbox("Filter op EMA-status", ema_opties)

with col2:
    therapeutische_opties = ["Alle"] + sorted(
        df["therapeutic_area_str"].dropna().unique().tolist()
    ) if "therapeutic_area_str" in df.columns else ["Alle"]
    keuze_therapeutisch = st.selectbox("Filter op therapeutisch gebied", therapeutische_opties)

with col3:
    zoekterm = st.text_input("Zoek op Latijnse of Nederlandse naam")

# Filter toepassen
df_filtered = df.copy()

if keuze_ema != "Alle" and "ema_status" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["ema_status"] == keuze_ema]

if keuze_therapeutisch != "Alle" and "therapeutic_area_str" in df_filtered.columns:
    df_filtered = df_filtered[
        df_filtered["therapeutic_area_str"] == keuze_therapeutisch
    ]

if zoekterm:
    mask = pd.Series(False, index=df_filtered.index)
    for kolom in ["latin_name", "dutch_common_name", "botanical_name"]:
        if kolom in df_filtered.columns:
            mask |= df_filtered[kolom].astype(str).str.contains(
                zoekterm, case=False, na=False
            )
    df_filtered = df_filtered[mask]


# ---------------------------------------------------------------------------
# Tabel (jouw originele kolommen + de nieuwe)
# ---------------------------------------------------------------------------
gewenste_kolommen = [
    "latin_name",
    "dutch_common_name",
    "english_common_name",
    "botanical_name",
    "therapeutic_area_str",
    "ema_status",
    "ema_outcome",
    "nl_registered",
    "nl_product_name",
    "nl_price_eur",
    "de_price_eur",
    "price_difference_pct",
    "Indicatie",
    "EMA_status",
    "notes",
]
kolommen = [k for k in gewenste_kolommen if k in df_filtered.columns]

st.dataframe(
    df_filtered[kolommen] if kolommen else df_filtered,
    use_container_width=True,
    hide_index=True,
)

st.caption(f"{len(df_filtered)} van {len(df)} planten getoond.")


# ---------------------------------------------------------------------------
# Appendix (alleen Duitse planten zonder EMA-monografie)
# ---------------------------------------------------------------------------
if "EMA_status" in df.columns:
    df_appendix = df[
        df["EMA_status"].isna() | (df["EMA_status"] != "Ja")
    ]

    if not df_appendix.empty:
        with st.expander("Appendix: planten zonder EMA-monografie (alleen Duits)"):
            appendix_kolommen = [
                k for k in [
                    "latin_name",
                    "dutch_common_name",
                    "therapeutic_area_str",
                    "ema_status",
                ]
                if k in df_appendix.columns
            ]
            st.dataframe(
                df_appendix[appendix_kolommen],
                use_container_width=True,
                hide_index=True,
            )


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "Deze app is informatief en vervangt geen medisch advies. "
    "Raadpleeg bij klachten altijd een arts of apotheker. "
    "Sommige plantaardige middelen kunnen interacties geven met andere geneesmiddelen."
)
