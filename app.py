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
    # 📊 Stock Health Metrics
    # -----------------------------
    st.markdown("### 📊 Stock Health")

    health = get_stock_health_metrics()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Unique Reagents",
            health['unique_reagents'],
            help="Number of different reagent types in stock"
        )

    with col2:
        st.metric(
            "Value at Risk",
            f"${health['total_value_at_risk']:.0f}",
            help="Dollar value expiring in next 30 days"
        )

    with col3:
        st.metric(
            "Low Stock Alerts",
            health['low_stock_count'],
            help="Reagents with < 2 available units",
            delta="⚠️" if health['low_stock_count'] > 0 else None
        )

    with col4:
        st.metric(
            "Expired Units",
            health['expired_units'],
            help="Units past expiration date",
            delta="❌" if health['expired_units'] > 0 else None
        )

    st.markdown("---")

    # -----------------------------
    # 🚨 CRITICAL: Expired Inventory
    # -----------------------------
    if health['expired_units'] > 0:
        st.markdown("### 🚨 Expired Inventory - Requires Immediate Disposal")

        expired_inv = get_expired_inventory(limit=10)

        if not expired_inv.empty:
            # Format for display
            expired_display = expired_inv.copy()
            expired_display['purchase_price'] = expired_display['purchase_price'].apply(
                lambda x: f"${x:.2f}" if pd.notna(x) else "—"
            )
            expired_display['initial_volume'] = expired_display['initial_volume'].apply(
                lambda x: f"{x:.0f}µL" if pd.notna(x) else "—"
            )

            expired_display = expired_display[[
                'reagent_name', 'lot', 'expiration_date', 'days_expired',
                'purchase_price', 'initial_volume', 'status'
            ]].rename(columns={
                'reagent_name': 'Reagent',
                'lot': 'Lot',
                'expiration_date': 'Expired On',
                'days_expired': 'Days Ago',
                'purchase_price': 'Value',
                'initial_volume': 'Volume',
                'status': 'Status'
            })

            st.dataframe(
                expired_display,
                use_container_width=True,
                hide_index=True
            )

            total_expired_value = expired_inv['purchase_price'].sum()
            st.warning(f"⚠️ Total expired value: **${total_expired_value:.2f}** - These units should be marked as 'Closed' or disposed.")

        st.markdown("---")

    # -----------------------------
    # ⏰ Expiring Soon - High Priority
    # -----------------------------
    st.markdown("### ⏰ Expiring in Next 30 Days")

    expiring_inv = get_expiring_inventory(days=30, limit=10)

    if expiring_inv.empty:
        st.success("✅ No reagents expiring in the next 30 days")
    else:
        # Format for display
        expiring_display = expiring_inv.copy()
        expiring_display['purchase_price'] = expiring_display['purchase_price'].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "—"
        )
        expiring_display['initial_volume'] = expiring_display['initial_volume'].apply(
            lambda x: f"{x:.0f}µL" if pd.notna(x) else "—"
        )

        expiring_display = expiring_display[[
            'reagent_name', 'lot', 'expiration_date', 'days_until_expiration',
            'purchase_price', 'initial_volume'
        ]].rename(columns={
            'reagent_name': 'Reagent',
            'lot': 'Lot',
            'expiration_date': 'Expires',
            'days_until_expiration': 'Days Left',
            'purchase_price': 'Value',
            'initial_volume': 'Volume'
        })

        # Color code by urgency
        def highlight_urgency(row):
            if row['Days Left'] <= 7:
                return ['background-color: rgba(139,0,0,0.3)'] * len(row)  # Red
            elif row['Days Left'] <= 14:
                return ['background-color: rgba(255,140,0,0.3)'] * len(row)  # Orange
            else:
                return ['background-color: rgba(255,255,0,0.2)'] * len(row)  # Yellow

        styled = expiring_display.style.apply(highlight_urgency, axis=1)

        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True
        )

        total_at_risk = expiring_inv['purchase_price'].sum()
        st.info(f"💰 Total value at risk: **${total_at_risk:.2f}** - Consider using these reagents soon.")

    st.markdown("---")

    # =============================
    # 🧪 General Reagents Status (Enhanced with Volumes)
    # =============================
    st.markdown("### 🧪 General Reagents Status")

    summary_enhanced = get_general_reagents_enhanced(
        data["general_reagents"],
        data["general_reagent_units"]
    )

    if summary_enhanced.empty:
        st.info("No general reagent units found.")
    else:
        # Format for display
        display_summary = summary_enhanced.copy()
        display_summary['Total Volume'] = display_summary['Total Volume'].apply(
            lambda x: f"{x:.0f}µL" if pd.notna(x) else "—"
        )
        display_summary['Next Expiration'] = display_summary['Next Expiration'].apply(
            lambda x: x if pd.notna(x) else "—"
        )
        display_summary['Usage %'] = (display_summary['Ratio'] * 100).round(1)

        # Select columns for display
        display_cols = display_summary[[
            'Reactivo', 'In Use', 'Stored', 'Total Volume', 'Usage %', 'Next Expiration'
        ]]

        # Style based on usage ratio
        def highlight_usage(row):
            ratio = row['Usage %'] / 100
            if ratio >= 0.8:  # 80% or more in use
                return ['background-color: rgba(255,0,0,0.2)'] * len(row)  # Red - critical
            elif ratio >= 0.5:  # 50-79% in use
                return ['background-color: rgba(255,165,0,0.2)'] * len(row)  # Orange - warning
            else:
                return [''] * len(row)  # Normal

        styled = display_cols.style.apply(highlight_usage, axis=1)

        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True
        )

        st.caption("🔴 Red = >80% in use (reorder soon) | 🟠 Orange = 50-80% in use (monitor)")

    st.markdown("---")

    # =============================
    # 🎯 Panel Readiness Status
    # =============================
    st.markdown("### 🎯 Panel Readiness")

    panel_status = get_panel_readiness_status()

    if panel_status.empty:
        st.info("No panels defined yet. Create panels in Panel Builder.")
    else:
        # Add status column
        panel_status['Status'] = panel_status.apply(
            lambda row: "✅ Ready" if row['is_complete']
            else f"⚠️ Incomplete ({row['available_reagents']}/{row['total_reagents']})",
            axis=1
        )

        # Format next expiration
        panel_status['Next Exp'] = panel_status['next_expiration'].apply(
            lambda x: x if pd.notna(x) else "—"
        )

        # Display
        display_panels = panel_status[[
            'panel_name', 'Status', 'total_reagents', 'available_reagents', 'Next Exp'
        ]].rename(columns={
            'panel_name': 'Panel',
            'total_reagents': 'Total',
            'available_reagents': 'Available'
        })

        st.dataframe(
            display_panels,
            use_container_width=True,
            hide_index=True
        )

        ready_count = panel_status['is_complete'].sum()
        total_panels = len(panel_status)
        st.info(f"✅ **{ready_count} of {total_panels}** panels are ready to run right now")

    st.markdown("---")

    # =============================
    # 💰 Cost Insights
    # =============================
    st.markdown("### 💰 Cost Insights")

    cost_data = get_cost_insights()

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**Top 5 Most Valuable Reagents**")
        if cost_data['top_expensive_reagents']:
            for name, value in cost_data['top_expensive_reagents']:
                st.write(f"• {name}: **${value:.0f}**")
        else:
            st.write("No data available")

    with col_b:
        st.metric(
            "Expired Value This Month",
            f"${cost_data['expired_value_this_month']:.0f}",
            help="Dollar value of reagents that expired this month"
        )

    with col_c:
        st.metric(
            "Avg Stock Age",
            f"{cost_data['avg_reagent_age']:.0f} days",
            help="Average days since arrival for stored reagents"
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
