import streamlit as st

def apply_filters(inventory, brands, fluoros, panels, days_default=30):

    st.sidebar.header("Filtros avanzados")

    f_brand = st.sidebar.multiselect("Marca", brands["name"].dropna().unique())
    f_fluor = st.sidebar.multiselect("Fluorocromo", fluoros["name"].dropna().unique())
    f_status = st.sidebar.multiselect("Estado del vial", inventory["status"].dropna().unique())

    if "type" in inventory.columns:
        f_type = st.sidebar.multiselect("Tipo de reactivo", inventory["type"].dropna().unique())
    else:
        f_type = []

    days_alert = st.sidebar.slider("Alertas de vencimiento (días)", 0, 365, days_default)

    df = inventory.copy()

    if f_brand:
        df = df[df["name_brand"].isin(f_brand)]
    if f_fluor:
        df = df[df["name_fluor"].isin(f_fluor)]
    if f_status:
        df = df[df["status"].isin(f_status)]
    if f_type:
        df = df[df["type"].isin(f_type)]

    return df, days_alert
