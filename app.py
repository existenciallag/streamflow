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

# -----------------------------
# Configuración página
# -----------------------------
st.set_page_config(
    page_title="Cytometry Manager",
    layout="wide"
)

# -----------------------------
# Sidebar navegación
# -----------------------------
page = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Paneles", "Panel Builder", "CRUD", "Base de datos", "Inventario Avanzado",]
)

st.title("Inventario de Citometría")

# -----------------------------
# Base de datos viewer
# -----------------------------
if page == "Base de datos":
    show_db_viewer()
    st.stop()

# -----------------------------
# Cargar datos
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
# CRUD
# -----------------------------
if page == "CRUD":
    run_crud()
    st.stop()

# -----------------------------
# PANELES — SOLO VISUALIZACION
# -----------------------------
if page == "Paneles":
    show_panels(data)
    st.stop()

# -----------------------------
# PANEL BUILDER — CREACION
# -----------------------------
if page == "Panel Builder":
    create_panel()
    st.stop()

# -----------------------------
# Inventario avanzado
# -----------------------------
if page == "Inventario Avanzado":
    advanced_inventory_view(inventory)
    st.stop()

# -----------------------------
# DASHBOARD
# -----------------------------
if page == "Dashboard":

    # 🔍 Búsqueda rápida
    query = st.text_input(
        "Buscar en inventario...",
        placeholder="cd3, b220, pb, biolegend..."
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

    # Antibody metrics
    df_ab_all = inv[inv["item_type"] == "antibody"]
    n_ab_total = len(df_ab_all)
    n_ab_open = (df_ab_all["status"].str.lower().isin(["stored", "in use"])).sum()
    n_ab_closed = (df_ab_all["status"].str.lower() == "closed").sum()

    # General reagent metrics
    n_gen = (inv["item_type"] == "general_reagent").sum()

    col1.metric("Total Antibodies", n_ab_total)
    col2.metric("Open Vials", n_ab_open, help="Antibody vials available (Stored + In Use)")
    col3.metric("Closed Vials", n_ab_closed)
    col4.metric("General Reagents", n_gen)

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
