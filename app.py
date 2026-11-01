import streamlit as st
import pandas as pd
import json
import re
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
DATA_FILE = BASE_DIR / "ema_herbal_medicines.json"
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
    "notes",
]
for kolom in verwachte_kolommen:
    if kolom not in df.columns:
        df[kolom] = None

df = df[verwachte_kolommen].copy()

# Lijst met therapeutische gebieden -> leesbare tekst (ook voor zoeken)
df["therapeutic_area"] = df["therapeutic_area"].apply(
    lambda x: ", ".join(x) if isinstance(x, list) else x
)
df["therapeutic_area_str"] = df["therapeutic_area"].fillna("").astype(str)


# --- Duitse data erbij laden ---
@st.cache_data
def load_duitse_data() -> list[dict]:
    with open(INDICATIES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def soort_sleutel(naam) -> str:
    """Genus + soort (kleine letters), bv. 'Betula pendula Roth; ...' -> 'betula pendula'."""
    if naam is None or (isinstance(naam, float) and pd.isna(naam)):
        return ""
    eerste = re.split(r"[;(\[]| and ", str(naam))[0]
    woorden = re.findall(r"[A-Za-z\-]+", eerste)
    return " ".join(w.lower() for w in woorden[:2])


duits_map = {}
if INDICATIES_JSON.exists():
    for rij in load_duitse_data():
        sleutel = soort_sleutel(rij.get("botanical_name"))
        if sleutel:
            duits_map[sleutel] = rij
else:
    st.warning(f"Het bestand '{INDICATIES_JSON.name}' kon niet worden gevonden.")


def zoek_duits(botanisch, veld):
    rij = duits_map.get(soort_sleutel(botanisch))
    return rij.get(veld) if rij else None


df["Gebruik in Duitsland"] = df["botanical_name"].apply(lambda x: zoek_duits(x, "Indicatie"))
df["Status in Duitsland"] = df["botanical_name"].apply(lambda x: zoek_duits(x, "EMA_status"))

# ---------------------------------------------------------------------------
# Zijbalk: zoekfunctie
# ---------------------------------------------------------------------------
st.sidebar.header("Zoeken")

zoekterm = st.sidebar.text_input(
    "Zoek op naam, indicatie of werkstof",
    placeholder="bijv. Ginkgo biloba, dementie, silymarine …",
    help="Typ een deel van de Latijnse naam, de Nederlandse naam, de indicatie of de werkstof.",
)

if zoekterm:
    mask = pd.Series(False, index=df.index)
    for kolom in [
        "latin_name",
        "dutch_common_name",
        "english_common_name",
        "botanical_name",
        "therapeutic_area_str",
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
# Complete tabel met checkbox-kolom
# ---------------------------------------------------------------------------
st.subheader("Complete tabel")

# Tijdelijke kolom voor de selectie
df_tabel = df.copy()
df_tabel.insert(0, "Selecteer", False)

# Data editor met checkbox
edited_df = st.data_editor(
    df_tabel,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Selecteer": st.column_config.CheckboxColumn(
            "Selecteer",
            help="Vink één plant aan om de monografie te tonen",
            default=False,
        )
    },
    disabled=[k for k in df_tabel.columns if k != "Selecteer"],
)

# Bepaal de geselecteerde plant (alleen de eerste, als er meerdere zijn aangevinkt)
geselecteerd = edited_df[edited_df["Selecteer"] == True]

st.caption(f"{len(df)} planten getoond.")


# ---------------------------------------------------------------------------
# Monografie (één plant)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Monografie")

if geselecteerd.empty:
    st.info("Vink één plant aan in de tabel om de monografie te tonen.")
else:
    if len(geselecteerd) > 1:
        st.warning("Je hebt meerdere planten aangevinkt. Alleen de eerste wordt getoond.")

    rij = geselecteerd.iloc[0]
    st.markdown(f"### {rij.get('latin_name', 'Onbekend')}")

    for kolom in df.columns:
        waarde = rij[kolom]

        if waarde is None:
            continue
        if isinstance(waarde, float) and pd.isna(waarde):
            continue
        if isinstance(waarde, str) and waarde.strip() == "":
            continue

        if isinstance(waarde, list):
            waarde = ", ".join(str(w) for w in waarde)

        st.markdown(f"**{kolom}:** {waarde}")

# ---------------------------------------------------------------------------
# Monografie
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

            # Sla lege waarden over
            if waarde is None:
                continue
            if isinstance(waarde, float) and pd.isna(waarde):
                continue
            if isinstance(waarde, str) and waarde.strip() == "":
                continue

            # Lijsten netjes weergeven
            if isinstance(waarde, list):
                waarde = ", ".join(str(w) for w in waarde)

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
