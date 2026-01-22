# ui/search.py
import streamlit as st
import pandas as pd

def global_search(inventory):
    st.subheader("🔎 Búsqueda Global")

    query = st.text_input("Buscar en todo el inventario...")

    if not query:
        return inventory

    q = query.lower()

    mask = (
        inventory["name"].str.lower().str.contains(q, na=False) |
        inventory["clone"].astype(str).str.lower().str.contains(q, na=False) |
        inventory["name_brand"].astype(str).str.lower().str.contains(q, na=False) |
        inventory["name_fluor"].astype(str).str.lower().str.contains(q, na=False) |
        inventory["item_type"].str.lower().str.contains(q, na=False)
    )

    results = inventory[mask]

    st.write(f"Resultados encontrados: **{len(results)}**")
    return results
