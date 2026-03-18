import streamlit as st
import pandas as pd

def status_style(val):
    """Mapea estado a color de celda con transparencia según estilo pedido"""
    if pd.isna(val):
        return ""
    val_lower = str(val).lower()
    if val_lower == "in use":
        return "background-color: rgba(85,107,47,0.3); color: black"
    elif val_lower == "stored":
        return "background-color: rgba(25,25,112,0.3); color: white"
    elif val_lower == "empty":
        return "background-color: rgba(105,105,105,0.3); color: white"
    else:
        return "background-color: rgba(105,105,105,0.3); color: white"

def show_inventory_table(df, days_alert):
    if df.empty:
        st.info("No hay elementos para mostrar.")
        return

    table = df.copy()
    exp_limit = pd.Timestamp.today() + pd.Timedelta(days=days_alert)

    # Normalizar fechas
    for col in ["expiration_date", "arrival_date"]:
        if col in table.columns:
            table[col] = pd.to_datetime(table[col], errors="coerce").dt.date

    # Columnas a mostrar según tipo
    cols = []
    if "item_type" in table.columns and table["item_type"].iloc[0] == "antibody":
        cols = ["name", "name_brand", "clone", "name_fluor",
                "status", "initial_volume", "arrival_date", "expiration_date", "lot"]
    else:
        cols = ["name", "name_brand", "type",
                "status", "volume", "arrival_date", "expiration_date", "lot"]

    rename_map = {
        "name": "Reagente",
        "name_brand": "Marca",
        "clone": "Clon",
        "name_fluor": "Fluorocromo",
        "status": "Estado",
        "initial_volume": "Volumen (µL)",
        "volume": "Volumen (µL)",
        "arrival_date": "Llegada",
        "expiration_date": "Vence",
        "type": "Tipo",
        "lot": "Lote"
    }
    display_cols = [c for c in cols if c in table.columns]
    table = table[display_cols].rename(columns=rename_map)

    # Highlight para vencimientos
    def highlight_expiring(row):
        if "Vence" in row and pd.notna(row["Vence"]):
            if row["Vence"] < pd.Timestamp.today().date():
                return ["background-color: rgba(139,0,0,0.2)"] * len(row)  # vencido
            elif row["Vence"] <= exp_limit.date():
                return ["background-color: rgba(255,140,0,0.2)"] * len(row)  # próximo a vencer
        return [""] * len(row)

    styled = table.style.apply(highlight_expiring, axis=1)

    # Colorear Estado
    if "Estado" in table.columns:
        styled = styled.applymap(status_style, subset=["Estado"])

    st.subheader("📦 Inventario filtrado")
    st.markdown(f"**{df.shape[0]} viales coinciden con los filtros aplicados**")
    st.dataframe(styled, use_container_width=True, hide_index=True)
