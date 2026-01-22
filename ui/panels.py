import streamlit as st
import pandas as pd
from ui.crud_panels import query_panels

def show_panels(panels_df=None):

    st.subheader("🔬 Panels")

    # ============================
    # Estado
    # ============================
    if "panel_mode" not in st.session_state:
        st.session_state["panel_mode"] = "view"

    # ============================
    # Resolver input
    # ============================
    if panels_df is None:
        panels = query_panels("SELECT * FROM panels")
    elif isinstance(panels_df, dict):
        panels = panels_df.get("panels")
    elif isinstance(panels_df, pd.DataFrame):
        panels = panels_df.copy()
    else:
        panels = None

    if panels is None or panels.empty:
        st.info("No hay panels cargados.")
        return

    col_list, col_detail = st.columns([1, 3])

    # ============================
    # PANEL IZQUIERDO — LISTA
    # ============================
    with col_list:

        search = st.text_input("Buscar panel")

        df = panels.copy()
        if search:
            df = df[
                df["name"]
                .astype(str)
                .str.lower()
                .str.contains(search.lower(), na=False)
            ]

        selected = st.dataframe(
            df[["name", "category_id", "status"]],
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun",
            height=500
        )

    # ============================
    # PANEL DERECHO — DETALLE
    # ============================
    with col_detail:

        panel_id = None
        if selected and selected.get("selection", {}).get("rows"):
            panel_id = df.iloc[selected["selection"]["rows"][0]]["id"]

        if not panel_id:
            st.info("Seleccioná un panel para ver el detalle.")
            return

        panel = panels[panels["id"] == panel_id].iloc[0]

        # ============================
        # HEADER
        # ============================
        st.markdown(f"## {panel['name']}")
        st.caption(
            f"Categoría: {panel.get('category_id') or '—'} · Estado: {panel['status']}"
        )

        if panel.get("description"):
            st.write(panel["description"])

        # ============================
        # METADATA
        # ============================
        st.markdown("### ⚙️ Metadata")

        cytometer_name = "—"
        if panel.get("cytometer_id"):
            cyt = query_panels(
                "SELECT name FROM cytometers WHERE id = ?",
                (panel["cytometer_id"],)
            )
            if not cyt.empty:
                cytometer_name = cyt.iloc[0]["name"]

        m1, m2, m3 = st.columns(3)
        m1.metric("Volumen muestra (µL)", panel.get("sample_volume") or "—")
        m2.metric("Lavado", "Sí" if panel.get("washed_sample") else "No")
        m3.metric("Citómetro", cytometer_name)

        st.markdown("#### 📑 Protocolos")
        p1, p2, p3 = st.columns(3)
        p1.metric("Acquisition", panel.get("acquisition_protocol_status") or "—")
        p2.metric("Compensation", panel.get("compensation_status") or "—")
        p3.metric("Analysis", panel.get("analysis_protocol_status") or "—")

        # ============================
        # ANTICUERPOS
        # ============================
        st.markdown("---")
        st.markdown("### 🧬 Anticuerpos del panel")

        panel_abs = query_panels("""
        SELECT
            r.name            AS antibody,
            r.clone,
            f.name            AS fluorochrome,
            b.name            AS brand,
            oc.name           AS channel,
            pr.volume_used,
            pr.is_intracellular,
            r.price           AS vial_price,
            ru.vial_volume
        FROM panel_reagents pr
        JOIN reagents r ON r.id = pr.reagent_id
        LEFT JOIN (
            SELECT reagent_id, AVG(initial_volume) AS vial_volume
            FROM reagent_units
            GROUP BY reagent_id
        ) ru ON ru.reagent_id = r.id
        LEFT JOIN fluorochromes f ON f.id = r.fluorochrome
        LEFT JOIN brands b ON b.id = r.brand_id
        LEFT JOIN optical_channels oc ON oc.id = pr.optical_channel_id
        WHERE pr.panel_id = ?
        ORDER BY r.name
        """, (panel_id,))

        if panel_abs.empty:
            st.info("Este panel no tiene anticuerpos asignados.")
            return

        df_show = panel_abs.copy()

        def compute_cost(row):
            if pd.isna(row["vial_price"]) or pd.isna(row["vial_volume"]) or row["vial_volume"] == 0:
                return 0.0
            return (row["vial_price"] / row["vial_volume"]) * row["volume_used"]

        df_show["Costo estimado"] = df_show.apply(compute_cost, axis=1)
        df_show["Intracelular"] = df_show["is_intracellular"].apply(lambda x: "Sí" if x else "No")

        total_cost = df_show["Costo estimado"].sum()

        st.dataframe(
            df_show[[
                "antibody", "clone", "fluorochrome", "brand",
                "channel", "volume_used", "Intracelular", "Costo estimado"
            ]].rename(columns={
                "antibody": "Anticuerpo",
                "clone": "Clon",
                "fluorochrome": "Fluorocromo",
                "brand": "Marca",
                "channel": "Canal",
                "volume_used": "Volumen (µL)"
            }),
            use_container_width=True
        )

        st.markdown(f"### 💰 Costo total estimado del panel: **${total_cost:.2f}**")
