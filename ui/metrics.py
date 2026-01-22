import streamlit as st
import pandas as pd

def show_metrics(inventory, brands, fluoros, days_alert):

    st.subheader("📊 Métricas del Inventario")
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Reactivos únicos", inventory["id"].nunique())
    col2.metric("Marcas", brands["id"].nunique())
    col3.metric("Fluorocromos", fluoros["id"].nunique())
    col4.metric("Viales en inventario", inventory.shape[0])

    if "initial_volume" in inventory.columns:
        total_volume = inventory["initial_volume"].fillna(0).astype(float).sum()
    else:
        total_volume = 0

    col5.metric("Volumen total (µL)", round(total_volume, 2))

    soon = inventory[inventory["expiration_date"] <= pd.Timestamp.today() + pd.Timedelta(days=days_alert)]
    st.markdown(f"**⚠️ {soon.shape[0]} viales próximos a vencer (< {days_alert} días)**")
