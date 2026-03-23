import streamlit as st
import pandas as pd

# -----------------------------
# Modelos y utilidades
# -----------------------------
from models.loaders import load_all
from models.merges import build_inventory
from ui.filters import apply_filters
from ui.tables import show_inventory_table
from ui.inventory_advanced import advanced_inventory_view
from ui.db_viewer import show_db_viewer
from ui.crud import run_crud

# Widget dashboard
from ui.dashboard_widgets import general_reagents_quick_status
from utils.dashboard_metrics import (
    get_stock_health_metrics,
    get_expiring_inventory,
    get_expired_inventory,
    get_panel_readiness_status,
    get_general_reagents_enhanced,
    get_cost_insights
)

# 👉 NUEVO: paneles
from ui.panels import show_panels
from ui.panel_builder import create_panel  # <-- Panel Builder

# 👉 NEW: Economic section
from ui.economic import run_economic
from ui.settings import run_settings
from ui.general_reagents import run_general_reagents_crud

# -----------------------------
# Configuración página
# -----------------------------
st.set_page_config(
    page_title="Cytometry Manager",
    layout="wide"
)

# -----------------------------
# Language support
# -----------------------------
from utils.translations import NAV, DASHBOARD, PANELS, SETTINGS, COMMON

if 'language' not in st.session_state:
    st.session_state['language'] = 'en'  # Default to English

lang = st.session_state['language']

# Get translated labels
labels = NAV[lang]
dashboard_labels = DASHBOARD[lang]
panels_labels = PANELS[lang]
settings_labels = SETTINGS[lang]
common_labels = COMMON[lang]

# -----------------------------
# Sidebar navegación
# -----------------------------
st.sidebar.markdown("### " + ("Navigation" if lang == 'en' else "Navegación"))

# Initialize current page in session state
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = None

# Define sections
operational_pages = [
    labels['dashboard'],
    labels['panels'],
    labels['panel_builder'],
    labels['economic'],
    labels['reagents'],
    labels['general_reagents']
]

technical_pages = [
    labels['database'],
    labels['advanced_inventory'],
    labels['settings']
]

# OPERATIONAL SECTION
st.sidebar.markdown("---")
st.sidebar.markdown("#### " + ("🔬 OPERATIONAL" if lang == 'en' else "🔬 OPERACIONAL"))

for page_name in operational_pages:
    if st.sidebar.button(
        page_name,
        key=f"nav_{page_name}",
        use_container_width=True,
        type="primary" if st.session_state['current_page'] == page_name else "secondary"
    ):
        st.session_state['current_page'] = page_name
        st.rerun()

# TECHNICAL SECTION
st.sidebar.markdown("---")
st.sidebar.markdown("#### " + ("⚙️ TECHNICAL" if lang == 'en' else "⚙️ TÉCNICO"))

for page_name in technical_pages:
    if st.sidebar.button(
        page_name,
        key=f"nav_{page_name}",
        use_container_width=True,
        type="primary" if st.session_state['current_page'] == page_name else "secondary"
    ):
        st.session_state['current_page'] = page_name
        st.rerun()

# Set default page if none selected
if st.session_state['current_page'] is None:
    st.session_state['current_page'] = labels['dashboard']

page = st.session_state['current_page']

st.title(dashboard_labels['title'])

# -----------------------------
# Settings
# -----------------------------
if page == labels['settings']:
    run_settings()
    st.stop()

# -----------------------------
# Database viewer
# -----------------------------
if page == labels['database']:
    show_db_viewer()
    st.stop()

# -----------------------------
# Load data (for pages that need it)
# -----------------------------
data = load_all()

inventory = build_inventory(
    data["reagents"],
    data["general_reagents"],
    data["brands"],
    data["fluorochromes"],
    data["reagent_units"],
    data["general_reagent_units"]
)

# -----------------------------
# Reagents (CRUD)
# -----------------------------
if page == labels['reagents']:
    run_crud()
    st.stop()

# -----------------------------
# General Reagents (CRUD)
# -----------------------------
if page == labels['general_reagents']:
    run_general_reagents_crud()
    st.stop()

# -----------------------------
# Panels (View/Edit)
# -----------------------------
if page == labels['panels']:
    show_panels(data)
    st.stop()

# -----------------------------
# Panel Builder
# -----------------------------
if page == labels['panel_builder']:
    create_panel()
    st.stop()

# -----------------------------
# Economic Section
# -----------------------------
if page == labels['economic']:
    run_economic()
    st.stop()

# -----------------------------
# Advanced Inventory
# -----------------------------
if page == labels['advanced_inventory']:
    advanced_inventory_view(inventory)
    st.stop()

# -----------------------------
# DASHBOARD
# -----------------------------
if page == labels['dashboard']:

    # Quick search
    query = st.text_input(
        dashboard_labels['search_placeholder'].split('...')[0] + '...',
        placeholder=dashboard_labels['search_placeholder'].split('...')[1] if '...' in dashboard_labels['search_placeholder'] else ''
    )

    # 🎛 Filtros
    df_filtered, days_alert = apply_filters(
        inventory,
        data["brands"],
        data["fluorochromes"],
        data["panels"]
    )

    inv = df_filtered.copy()

    if query:
        q = query.lower()
        inv = inv[
            inv["name"].str.lower().str.contains(q, na=False)
            | inv.get("clone", "").astype(str).str.lower().str.contains(q, na=False)
            | inv["name_brand"].astype(str).str.lower().str.contains(q, na=False)
            | inv["name_fluor"].astype(str).str.lower().str.contains(q, na=False)
        ]

    # -----------------------------
    # 📊 Quick Metrics - Operational Overview
    # -----------------------------
    col1, col2, col3, col4 = st.columns(4)

    # Antibody metrics with corrected terminology
    df_ab_all = inv[inv["item_type"] == "antibody"]
    n_ab_total = len(df_ab_all)
    n_ab_in_use = (df_ab_all["status"].str.lower() == "in use").sum()  # Currently being used
    n_ab_stored = (df_ab_all["status"].str.lower() == "stored").sum()  # Not in active use
    n_ab_empty = (df_ab_all["status"].str.lower() == "empty").sum()  # Finished/empty

    # General reagent metrics
    n_gen = (inv["item_type"] == "general_reagent").sum()

    col1.metric(dashboard_labels['total_antibodies'], n_ab_total)
    col2.metric(dashboard_labels['in_use'], n_ab_in_use, help=dashboard_labels['in_use_help'])
    col3.metric(dashboard_labels['stored'], n_ab_stored, help=dashboard_labels['stored_help'])
    col4.metric(dashboard_labels['empty'], n_ab_empty, help=dashboard_labels['empty_help'])

    st.markdown("---")

    # -----------------------------
    # 🚨 Expired Reagents Alert (Compact)
    # -----------------------------
    n_expired = inv["expiration_date"].lt(pd.Timestamp.today()).sum()
    if n_expired > 0:
        with st.expander(f"⚠️ {n_expired} expired units found - Click to view", expanded=False):
            expired_inv = get_expired_inventory(limit=10)
            if not expired_inv.empty:
                expired_display = expired_inv[['reagent_name', 'lot', 'expiration_date', 'days_expired']].rename(columns={
                    'reagent_name': 'Reagent',
                    'lot': 'Lot',
                    'expiration_date': 'Expired',
                    'days_expired': 'Days Ago'
                })
                st.dataframe(expired_display, use_container_width=True, hide_index=True)
                st.caption("Note: Expired reagents may still be usable depending on storage and validation")

    st.markdown("---")

    # =============================
    # 🧪 Consumables Quick Status (Compact Cards)
    # =============================
    st.markdown("## Resumen consumibles")

    summary = general_reagents_quick_status(
        data["general_reagents"],
        data["general_reagent_units"]
    )

    if summary.empty:
        st.info("No hay unidades de reactivos generales.")
    else:
        cols_per_row = 4
        rows = [
            summary.iloc[i:i + cols_per_row]
            for i in range(0, len(summary), cols_per_row)
        ]

        for row in rows:
            cols = st.columns(len(row))
            for col, (_, r) in zip(cols, row.iterrows()):
                with col:
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid #e0e0e0;
                            border-radius: 8px;
                            padding: 10px;
                            font-size: 0.9rem;
                        ">
                            <strong>{r['Reactivo']}</strong><br>
                            En uso: {int(r['In Use'])}<br>
                            Stock: {int(r['Stored'])}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    st.markdown("---")

    # =============================
    # 🧬 TABLA — ANTICUERPOS
    # =============================
    st.markdown("## Anticuerpos")

    df_ab = inv[inv["item_type"] == "antibody"]

    if df_ab.empty:
        st.info("No hay anticuerpos para mostrar.")
    else:
        show_inventory_table(df_ab, days_alert)

    st.markdown("---")

    # =============================
    # ⚗️ TABLA — REACTIVOS GENERALES
    # =============================
    st.markdown("## Consumibles")

    df_gen = inv[inv["item_type"] == "general_reagent"]

    if df_gen.empty:
        st.info("No hay reactivos generales para mostrar.")
    else:
        show_inventory_table(df_gen, days_alert)

    st.stop()
