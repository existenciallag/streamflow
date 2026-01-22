import streamlit as st
import pandas as pd
from models.loaders import load_table

def show_db_viewer():
    st.header("📂 Explorador de Base de Datos")

    tables = [
        "brands",
        "reagents",
        "general_reagents",
        "fluorochromes",
        "reagent_units",
        "general_reagent_units",
        "panels",
        "panel_reagents",
        "panel_general_reagents",
        "cytometers",
        "cytometer_optical_channels",
        "optical_channels",
        "purchase_orders",
        "purchase_order_items"
    ]

    st.subheader("Seleccioná una tabla")
    table_name = st.selectbox("Tabla", tables)

    df = load_table(table_name)

    st.markdown(f"### 🔎 Vista previa de **{table_name}** ({len(df)} filas)")

    st.dataframe(df, use_container_width=True)

    st.markdown("### 🧬 Columnas")
    st.write(pd.DataFrame({
        "columna": df.columns,
        "dtype": df.dtypes.astype(str)
    }))
