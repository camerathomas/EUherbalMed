import streamlit as st
import json
import pandas as pd
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
PLANTEN_JSON = BASE_DIR / "planten_indicaties.json"
WAAROM_MD = BASE_DIR / "waarom_deze_app.md"


# ---------------------------------------------------------------------------
# Data laden
# ---------------------------------------------------------------------------
@st.cache_data
def laad_planten() -> pd.DataFrame:
    if not PLANTEN_JSON.exists():
        st.error(f"Het bestand '{PLANTEN_JSON.name}' kon niet worden gevonden.")
        return pd.DataFrame()

    with open(PLANTEN_JSON, encoding="utf-8") as f:
        payload = json.load(f)

    # Ondersteun zowel een lijst als een dict met "data"
    if isinstance(payload, dict) and "data" in payload:
        records = payload["data"]
    else:
        records = payload

    return pd.DataFrame(records)


@st.cache_data
def laad_waarom_tekst() -> str:
    if WAAROM_MD.exists():
        return WAAROM_MD.read_text(encoding="utf-8")
    return "De tekst 'waarom_deze_app.md' kon niet worden gevonden."


df = laad_planten()
waarom_tekst = laad_waarom_tekst()

# Zorg dat de verwachte kolommen bestaan (ook als ze in de JSON ontbreken)
verwachte_kolommen = [
    "Duitse_naam",
    "Nederlandse_naam",
    "Categorie",
    "Wirkstoff",
    "Indicatie",
    "EMA_status",
    "Quelle",
]
for kolom in verwachte_kolommen:
    if kolom not in df.columns:
        df[kolom] = None


# ---------------------------------------------------------------------------
# UI: header en "Waarom deze app?"
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
        st.markdown(waarom_tekst)

st.divider()


# ---------------------------------------------------------------------------
# UI: filters
# ---------------------------------------------------------------------------
st.subheader("Overzicht")

col1, col2, col3 = st.columns(3)

with col1:
    categorieen = ["Alle"] + sorted(
        df["Categorie"].dropna().unique().tolist()
    ) if "Categorie" in df.columns else ["Alle"]
    keuze_categorie = st.selectbox("Filter op categorie", categorieen)

with col2:
    ema_opties = ["Alle"] + sorted(
        df["EMA_status"].dropna().unique().tolist()
    ) if "EMA_status" in df.columns else ["Alle"]
    keuze_ema = st.selectbox("Filter op EMA-status", ema_opties)

with col3:
    zoekterm = st.text_input("Zoek op naam (Duits of Nederlands)")

# Filter toepassen
df_filtered = df.copy()

if keuze_categorie != "Alle" and "Categorie" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Categorie"] == keuze_categorie]

if keuze_ema != "Alle" and "EMA_status" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["EMA_status"] == keuze_ema]

if zoekterm:
    mask = pd.Series(False, index=df_filtered.index)
    for kolom in ["Duitse_naam", "Nederlandse_naam"]:
        if kolom in df_filtered.columns:
            mask |= df_filtered[kolom].astype(str).str.contains(
                zoekterm, case=False, na=False
            )
    df_filtered = df_filtered[mask]


# ---------------------------------------------------------------------------
# UI: tabel
# ---------------------------------------------------------------------------
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

st.caption(f"{len(df_filtered)} van {len(df)} planten getoond.")


# ---------------------------------------------------------------------------
# UI: appendix (alleen Duitse planten zonder EMA-monografie)
# ---------------------------------------------------------------------------
if "EMA_status" in df.columns:
    df_appendix = df[
        df["EMA_status"].isna() | (df["EMA_status"] != "Ja")
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
