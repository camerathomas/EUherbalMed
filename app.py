import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="EMA Herbal Medicines – overzicht",
    page_icon="🌿",
    layout="wide",
)

DATA_FILE = Path(__file__).parent / "ema_herbal_medicines.json"


# ---------------------------------------------------------------------------
# Data laden
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
# Zijbalk met filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

zoekterm = st.sidebar.text_input(
    "Zoek op naam",
    placeholder="Latijns, Nederlands, Engels of botanisch…",
)

statussen = sorted([s for s in df["ema_status"].dropna().unique() if s])
gekozen_status = st.sidebar.multiselect("EMA-status", options=statussen, default=statussen)

resultaten = sorted([o for o in df["ema_outcome"].dropna().unique() if o])
gekozen_resultaat = st.sidebar.multiselect("Beoordelingsresultaat", options=resultaten, default=resultaten)

alle_gebieden = sorted({
    gebied
    for gebieden in df["therapeutic_area"]
    if isinstance(gebieden, list)
    for gebied in gebieden
})
gekozen_gebieden = st.sidebar.multiselect("Therapeutisch gebied", options=alle_gebieden, default=[])

# ---------------------------------------------------------------------------
# Filteren
# ---------------------------------------------------------------------------
filtered = df.copy()

if zoekterm:
    q = zoekterm.lower()
    mask = (
        filtered["latin_name"].fillna("").str.lower().str.contains(q, regex=False)
        | filtered["dutch_common_name"].fillna("").str.lower().str.contains(q, regex=False)
        | filtered["english_common_name"].fillna("").str.lower().str.contains(q, regex=False)
        | filtered["botanical_name"].fillna("").str.lower().str.contains(q, regex=False)
    )
    filtered = filtered[mask]

if gekozen_status:
    filtered = filtered[filtered["ema_status"].isin(gekozen_status)]

if gekozen_resultaat:
    filtered = filtered[filtered["ema_outcome"].isin(gekozen_resultaat)]

if gekozen_gebieden:
    filtered = filtered[
        filtered["therapeutic_area"].apply(
            lambda x: isinstance(x, list) and any(g in x for g in gekozen_gebieden)
        )
    ]

# ---------------------------------------------------------------------------
# Weergave
# ---------------------------------------------------------------------------
st.title("🌿 EMA Herbal Medicines – overzicht")
st.caption(
    f"Bron: EMA herbal medicines JSON · {len(filtered)} van {len(df)} records zichtbaar"
)

toon_kolommen = [
    "latin_name",
    "dutch_common_name",
    "english_common_name",
    "ema_status",
    "ema_outcome",
    "therapeutic_area_str",
]

kolomnamen = {
    "latin_name": "Latijnse naam",
    "dutch_common_name": "Nederlandse naam",
    "english_common_name": "Engelse naam",
    "ema_status": "EMA-status",
    "ema_outcome": "Resultaat",
    "therapeutic_area_str": "Therapeutisch gebied",
}

weergave = filtered[toon_kolommen].rename(columns=kolomnamen)

# Reset index zodat we de geselecteerde rij kunnen terugvinden
weergave = weergave.reset_index(drop=True)

# ---------------------------------------------------------------------------
# Tabel met rij-selectie
# ---------------------------------------------------------------------------
st.subheader("Klik op een rij om de details te zien")

try:
    selectie = st.dataframe(
        weergave,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "EMA-status": st.column_config.TextColumn("EMA-status", width="medium"),
            "Resultaat": st.column_config.TextColumn("Resultaat", width="medium"),
        },
    )
    geselecteerde_rijen = selectie.selection.rows if hasattr(selectie, "selection") else []
except TypeError:
    # Fallback voor oudere Streamlit-versies zonder on_select
    st.dataframe(
        weergave,
        use_container_width=True,
        hide_index=True,
        column_config={
            "EMA-status": st.column_config.TextColumn("EMA-status", width="medium"),
            "Resultaat": st.column_config.TextColumn("Resultaat", width="medium"),
        },
    )
    geselecteerde_rijen = []

# ---------------------------------------------------------------------------
# Detailweergave
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Details")

record = None

if geselecteerde_rijen:
    # Gebruiker klikte op een rij in de tabel
    idx = geselecteerde_rijen[0]
    record = filtered.iloc[idx].to_dict()
elif not filtered.empty:
    # Fallback: selectbox onderaan
    opties = filtered.apply(
        lambda r: f"{r['latin_name']} — {r['dutch_common_name'] or r['english_common_name'] or ''}",
        axis=1,
    ).tolist()
    keuze = st.selectbox("Of kies een plant uit de lijst", opties)
    index = opties.index(keuze)
    record = filtered.iloc[index].to_dict()

if record:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Botanische gegevens**")
        st.write(f"Latijns: *{record.get('latin_name', '')}*")
        st.write(f"Nederlands: {record.get('dutch_common_name', '')}")
        st.write(f"Engels: {record.get('english_common_name', '')}")
        st.write(f"Botanisch: {record.get('botanical_name', '')}")
        gebieden = record.get("therapeutic_area") or []
        st.write(f"Therapeutisch gebied: {', '.join(gebieden) if isinstance(gebieden, list) else gebieden}")

    with col2:
        st.markdown("**EMA-gegevens**")
        st.write(f"Status: {record.get('ema_status', '') or '—'}")
        st.write(f"Resultaat: {record.get('ema_outcome', '') or '—'}")
        url = record.get("ema_url", "")
        if url:
            st.markdown(f"[🔗 Open EMA-pagina]({url})")
        else:
            st.write("Geen EMA-link beschikbaar")

    st.markdown("**Nederlandse situatie (nog in te vullen)**")
    st.json({
        "nl_registered": record.get("nl_registered"),
        "nl_product_name": record.get("nl_product_name"),
        "nl_price_eur": record.get("nl_price_eur"),
        "de_price_eur": record.get("de_price_eur"),
        "price_difference_pct": record.get("price_difference_pct"),
        "notes": record.get("notes"),
    })
else:
    st.info("Geen records gevonden met de huidige filters.")

# Zet de paginaconfiguratie
st.set_page_config(page_title="Plantaardige geneesmiddelen", layout="wide")

# Functie om de tekst uit de markdown-file te lezen
def laad_waarom_tekst():
    pad = Path(__file__).parent / "waarom_deze_app.md"
    if pad.exists():
        return pad.read_text(encoding="utf-8")
    else:
        return "De tekst 'waarom_deze_app.md' kon niet worden gevonden."

# Sessie-state om bij te houden of de tekst zichtbaar is
if "toon_waarom" not in st.session_state:
    st.session_state.toon_waarom = False

# Titel
st.title("Plantaardige geneesmiddelen")

# Knop om de tekst te openen/sluiten
if st.button("Waarom deze app?"):
    st.session_state.toon_waarom = not st.session_state.toon_waarom

# Toon de tekst als de knop is ingedrukt
if st.session_state.toon_waarom:
    st.markdown(laad_waarom_tekst())

# Hier komen later de andere onderdelen van de app (per plant, etc.)
st.divider()
st.caption("Inhoud volgt: per plant de Duitse marktstatus, de EMA-status en de aanvraagstatus.")
