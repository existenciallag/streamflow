import streamlit as st
import pandas as pd
from .tables import status_badge


def show_details(inventory):

    st.subheader("Detalle del reactivo")

    # --- selector ---
    chosen = st.selectbox(
        "Seleccioná un reactivo",
        sorted(inventory["name"].dropna().unique())
    )

    df = inventory[inventory["name"] == chosen].copy()

    # Normalizar fechas
    for col in df.columns:
        if "date" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    # Estado como chip
    if "status" in df.columns:
        df["status"] = df["status"].apply(status_badge)

    # ocultar columnas internas
    hidden = ["id", "team_id", "user_id"]
    cols = [c for c in df.columns if c not in hidden]

    st.write(df[cols].sort_values("expiration_date").to_html(escape=False, index=False),
             unsafe_allow_html=True)
