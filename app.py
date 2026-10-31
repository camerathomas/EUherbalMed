import streamlit as st
import pandas as pd
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paginaconfiguratie
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Plantaardige geneesmiddelen",
    page_icon="🌿",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Bestandspaden
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
PLANTEN_CSV = BASE_DIR / "planten_data.csv"
INDICATIES_JSON = BASE_DIR / "planten_indicaties.json"
WAAROM_MD = BASE_DIR / "waarom_deze_app.md"


# ---------------------------------------------------------------------------
# Data laden
# ---------------------------------------------------------------------------
@st.cache_data
def laad_planten_data() -> pd.DataFrame:
    if PLANTEN_CSV.exists():
        return pd.read_csv(PLANTEN_CSV)
    st.error(f"Het bestand '{PLANTEN_CSV.name}' kon niet worden gevonden.")
    return pd.DataFrame()


@st.cache_data
def laad_indicaties() -> pd.DataFrame:
    if INDICATIES_JSON.exists():
        with open(INDICATIES_JSON, encoding="utf-8") as f:
            return pd.DataFrame(json.load(f))
    st.warning(f"Het bestand '{INDICATIES_JSON.name}' kon niet worden gevonden.")
    return pd.DataFrame()


@st.cache_data
def laad_waarom_tekst() -> str:
    if WAAROM_MD.exists():
        return WAAROM_MD.read_text(encoding="utf-8")
    return "De tekst 'waarom_deze_app.md' kon niet worden gevonden."


df_planten = laad_planten_data()
df_indicaties = laad_indicaties()
waarom_tekst = laad_waarom_tekst()


# ---------------------------------------------------------------------------
# Samenvoegen
# ---------------------------------------------------------------------------
if not df_planten.empty and not df_indicaties.empty:
    df_compleet = pd.merge(
        df_planten,
        df_indicaties,
        on="Duitse_naam",
        how="left",
    )
else:
    df_compleet = df_planten.copy()

# Zorg dat de nieuwe kolommen altijd bestaan
for kolom in ["Indicatie", "EMA_status"]:
    if kolom not in df_compleet.columns:
        df_compleet[kolom] = None


# ---------------------------------------------------------------------------
# UI: header en "Waarom deze app?"
# ---------------------------------------------------------------------------
st.title("🌿 Plantaardige geneesmiddelen")
st.caption("Een overzicht van in Duitsland toegelaten plantaardige geneesmiddelen, met EMA-status en indicaties.")

if "toon_waarom" not in st.session_state:
    st.session_state.toon_waarom = False

if st.button("Waarom deze app?"):
    st.session_state.toon_waarom = not st.session_state.toon_waarom

if st.session_state.toon_waarom:
    with st.container(border=True):
        st.markdown(waarom_tekst)

st.divider()


# ---------------------------------------------------------------------------
# UI: filters
# ---------------------------------------------------------------------------
st.subheader("Overzicht")

col1, col2, col3 = st.columns(3)

with col1:
    categorieen = ["Alle"] + sorted(
        df_compleet["Categorie"].dropna().unique().tolist()
    ) if "Categorie" in df_compleet.columns else ["Alle"]
    keuze_categorie = st.selectbox("Filter op categorie", categorieen)

with col2:
    ema_opties = ["Alle"] + sorted(
        df_compleet["EMA_status"].dropna().unique().tolist()
    ) if "EMA_status" in df_compleet.columns else ["Alle"]
    keuze_ema = st.selectbox("Filter op EMA-status", ema_opties)

with col3:
    zoekterm = st.text_input("Zoek op naam (Duits of Nederlands)")

# Filter toepassen
df_filtered = df_compleet.copy()

if keuze_categorie != "Alle" and "Categorie" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Categorie"] == keuze_categorie]

if keuze_ema != "Alle" and "EMA_status" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["EMA_status"] == keuze_ema]

if zoekterm:
    mask = pd.Series(False, index=df_filtered.index)
    for kolom in ["Duitse_naam", "Nederlandse_naam"]:
        if kolom in df_filtered.columns:
            mask |= df_filtered[kolom].astype(str).str.contains(zoekterm, case=False, na=False)
    df_filtered = df_filtered[mask]


# ---------------------------------------------------------------------------
# UI: tabel
# ---------------------------------------------------------------------------
# Kies een zinvolle kolomvolgorde (alleen kolommen die bestaan)
gewenste_kolommen = [
    "Duitse_naam",
    "Nederlandse_naam",
    "Categorie",
    "Wirkstoff",
    "Indicatie",
    "EMA_status",
    "Quelle",
]
kolommen = [k for k in gewenste_kolommen if k in df_filtered.columns]

st.dataframe(
    df_filtered[kolommen] if kolommen else df_filtered,
    use_container_width=True,
    hide_index=True,
)

st.caption(f"{len(df_filtered)} van {len(df_compleet)} planten getoond.")


# ---------------------------------------------------------------------------
# UI: appendix (alleen Duitse planten zonder EMA-monografie)
# ---------------------------------------------------------------------------
if "EMA_status" in df_compleet.columns:
    df_appendix = df_compleet[
        df_compleet["EMA_status"].isna() | (df_compleet["EMA_status"] != "Ja")
    ]

    if not df_appendix.empty:
        with st.expander("Appendix: planten zonder EMA-monografie (alleen Duits)"):
            appendix_kolommen = [
                k for k in ["Duitse_naam", "Nederlandse_naam", "Categorie", "Wirkstoff"]
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
