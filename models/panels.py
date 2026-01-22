import streamlit as st
import pandas as pd
from ui.crud import query
from ui.panel_builder import create_panel, assign_reagents


def show_panels(panels_df=None):

    st.subheader("🔬 Panels")

    if "panel_mode" not in st.session_state:
        st.session_state["panel_mode"] = "view"

    if panels_df is None:
        panels = query("SELECT * FROM panels ORDER BY created_at DESC")
    else:
        panels = panels_df.copy()

    col_list, col_detail = st.columns([1, 3])

    # ============================
    # LISTA
    # ============================
    with col_list:

        if st.button("➕ Nuevo panel"):
            st.session_state["panel_mode"] = "create"
            st.rerun()

        if panels is None or panels.empty:
            st.info("No hay panels")
            return

        selected = st.dataframe(
            panels[["name", "status"]],
            selection_mode="single-row",
            on_select="rerun",
            height=500,
            use_container_width=True
        )

    # ============================
    # CONTENIDO
    # ============================
    with col_detail:

        if st.session_state["panel_mode"] == "create":
            create_panel()
            return

        if st.session_state["panel_mode"] == "assign_reagents":
            assign_reagents(st.session_state["panel_selected"])
            return

        if not selected or not selected.get("selection", {}).get("rows"):
            st.info("Seleccioná un panel")
            return

        panel_id = panels.iloc[selected["selection"]["rows"][0]]["id"]
        panel = panels[panels["id"] == panel_id].iloc[0]

        st.markdown(f"## {panel['name']}")
        st.caption(f"Estado: {panel['status']}")

        if panel.get("description"):
            st.write(panel["description"])
