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
DATA_FILE = BASE_DIR / "planten_data.json"
INDICATIES_JSON = BASE_DIR / "planten_indicaties.json"
WAAROM_MD = BASE_DIR / "waarom_deze_app.md"


# ---------------------------------------------------------------------------
# Data laden (bestaand)
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
# Aanvulling: indicaties en EMA-status uit aparte JSON (alleen toevoegen)
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
    if "ema_status_aanvulling" in df.columns:
        df["ema_status"] = df["ema_status"].fillna(df["ema_status_aanvulling"])
        df = df.drop(columns=["ema_status_aanvulling"])

for kolom in ["Indicatie", "EMA_status"]:
    if kolom not in df.columns:
        df[kolom] = None


# ---------------------------------------------------------------------------
# Zijbalk: zoekfunctie
# ---------------------------------------------------------------------------
st.sidebar.header("Zoeken")

zoekterm = st.sidebar.text_input("Zoek op naam, indicatie of werkstof")

if zoekterm:
    mask = pd.Series(False, index=df.index)
    for kolom in [
        "latin_name",
        "dutch_common_name",
        "english_common_name",
        "botanical_name",
        "therapeutic_area_str",
        "Indicatie",
        "notes",
    ]:
        if kolom in df.columns:
            mask |= df[kolom].astype(str).str.contains(zoekterm, case=False, na=False)
    df = df[mask]


# ---------------------------------------------------------------------------
# Hoofdweergave
# ---------------------------------------------------------------------------
st.title("🌿 Plantaardige geneesmiddelen")

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
# Complete tabel
# ---------------------------------------------------------------------------
st.subheader("Complete tabel")

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)

st.caption(f"{len(df)} planten getoond.")


# ---------------------------------------------------------------------------
# Monografie (per plant, als je die al had)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Monografie")

if "latin_name" in df.columns:
    keuze = st.selectbox(
        "Kies een plant voor de monografie",
        df["latin_name"].dropna().unique().tolist(),
    )
    if keuze:
        rij = df[df["latin_name"] == keuze].iloc[0]
        for kolom in df.columns:
            waarde = rij[kolom]
            if pd.notna(waarde) and waarde != "":
                st.markdown(f"**{kolom}:** {waarde}")
else:
    st.info("Geen monografie-gegevens beschikbaar.")


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "Deze app is informatief en vervangt geen medisch advies. "
    "Raadpleeg bij klachten altijd een arts of apotheker."
)
