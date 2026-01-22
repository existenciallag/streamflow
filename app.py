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
    # 📊 Métricas principales
    # -----------------------------
    col1, col2, col3, col4 = st.columns(4)

    n_ab = (inv["item_type"] == "antibody").sum()
    n_gen = (inv["item_type"] == "general_reagent").sum()
    n_expired = inv["expiration_date"].lt(pd.Timestamp.today()).sum()
    n_alert = inv["expiration_date"].between(
        pd.Timestamp.today(),
        pd.Timestamp.today() + pd.Timedelta(days=days_alert)
    ).sum()

    col1.metric("Anticuerpos", n_ab)
    col2.metric("Reactivos generales", n_gen)
    col3.metric("Vencidos", n_expired)
    col4.metric(f"Vencen en {days_alert} días", n_alert)

    st.markdown("---")

    # =============================
    # 🧪 DASHBOARD RÁPIDO REACTIVOS
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
