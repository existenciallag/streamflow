# ui/inventory_advanced.py
import streamlit as st
import pandas as pd

def advanced_inventory_view(df):
    st.subheader("📊 Inventario Avanzado")

    cols = st.multiselect("Mostrar columnas", df.columns, default=df.columns)

    group_by = st.selectbox("Agrupar por...", ["Ninguno"] + list(df.columns))

    if group_by != "Ninguno":
        grouped = df.groupby(group_by).size().reset_index(name="count")
        st.dataframe(grouped, use_container_width=True)
    else:
        st.dataframe(df[cols], use_container_width=True)

    if st.button("Exportar a CSV"):
        st.download_button(
            "Descargar CSV",
            df.to_csv(index=False),
            file_name="inventario.csv"
        )
