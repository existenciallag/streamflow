# ui/panel_builder.py
import streamlit as st
import uuid
from datetime import datetime
import pandas as pd
from ui.crud_panels import query_panels

def create_panel():

    st.title("🧬 Panel Builder")

    # ============================================================
    # STATE
    # ============================================================
    if "panel_reagents_draft" not in st.session_state:
        st.session_state["panel_reagents_draft"] = []

    # ============================================================
    # METADATA DEL PANEL
    # ============================================================
    st.subheader("Datos del panel")

    name = st.text_input("Nombre del panel")
    description = st.text_area("Descripción", height=80)

    c1, c2, c3 = st.columns(3)

    sample_volume = c1.number_input("Volumen muestra (µL)", min_value=0.0, step=1.0)
    washed_sample = c2.checkbox("Muestra lavada")

    # ---- CITÓMETROS ----
    cytometers = query_panels("SELECT id, name FROM cytometers")
    if cytometers.empty:
        st.error("No hay citómetros configurados")
        return

    cyt_map = dict(zip(cytometers["name"], cytometers["id"]))
    cyt_name = c3.selectbox("Citómetro", ["—"] + list(cyt_map.keys()))
    cytometer_id = cyt_map.get(cyt_name)

    # ============================================================
    # BUSCADOR DE ANTICUERPOS
    # ============================================================
    st.markdown("---")
    st.subheader("🔍 Agregar anticuerpos")

    if cyt_name == "—":
        st.info("Seleccioná un citómetro para continuar")
        st.stop()

    search = st.text_input("Buscar por nombre o clon")

    reagents_df = query_panels("""
        SELECT r.id, r.name, r.clone, f.name AS fluorochrome
        FROM reagents r
        JOIN fluorochromes f ON f.id = r.fluorochrome
        ORDER BY r.name
    """)

    if search:
        reagents_df = reagents_df[
            reagents_df["name"].str.contains(search, case=False, na=False) |
            reagents_df["clone"].str.contains(search, case=False, na=False)
        ]

    # ============================================================
    # LISTADO DE ANTICUERPOS
    # ============================================================
    for _, ab in reagents_df.head(20).iterrows():
        with st.expander(f"{ab['name']} ({ab['clone']}) — {ab['fluorochrome']}"):

            # ---- ASIGNACIÓN DE CANAL ----
            channel_df = query_panels("""
                SELECT oc.id, oc.name
                FROM cytometer_optical_channels coc
                JOIN optical_channels oc ON oc.id = coc.optical_channel_id
                WHERE coc.cytometer_id = ? AND coc.associated_fluorochrome = ?
            """, (cytometer_id, ab["fluorochrome"]))

            if not channel_df.empty:
                channel_id = channel_df.iloc[0]["id"]
                channel_name = channel_df.iloc[0]["name"]
                st.success(f"Canal automático: {channel_name}")
            else:
                all_channels = query_panels("""
                    SELECT oc.id, oc.name
                    FROM cytometer_optical_channels coc
                    JOIN optical_channels oc ON oc.id = coc.optical_channel_id
                    WHERE coc.cytometer_id = ?
                """, (cytometer_id,))
                channel_map = dict(zip(all_channels["name"], all_channels["id"]))
                channel_name = st.selectbox("Canal", list(channel_map.keys()), key=f"ch_{ab['id']}")
                channel_id = channel_map[channel_name]

            # ---- PARÁMETROS ----
            c1, c2, c3 = st.columns(3)
            volume = c1.number_input("Volumen (µL)", min_value=0.0, step=0.5, key=f"vol_{ab['id']}")
            intra = c2.checkbox("Intracelular", key=f"intra_{ab['id']}")
            display_name = c3.text_input("Nombre en panel", value=f"{ab['name']} {ab['fluorochrome']}", key=f"disp_{ab['id']}")

            if st.button("➕ Agregar", key=f"add_{ab['id']}"):
                st.session_state["panel_reagents_draft"].append({
                    "reagent_id": ab["id"],
                    "optical_channel_id": channel_id,
                    "volume_used": volume,
                    "is_intracellular": 1 if intra else 0,
                    "display_name": display_name
                })
                st.success("Agregado al panel")

    # ============================================================
    # PREVIEW DEL PANEL
    # ============================================================
    st.markdown("---")
    st.subheader("📋 Panel actual")
    if st.session_state["panel_reagents_draft"]:
        preview = pd.DataFrame(st.session_state["panel_reagents_draft"])
        st.dataframe(preview, use_container_width=True)
    else:
        st.info("Todavía no hay anticuerpos agregados")

    # ============================================================
    # GUARDADO DEL PANEL — SIN PERDER DRAFT
    # ============================================================
    st.markdown("---")
    guardar = st.button("💾 Guardar panel", type="primary")

    if guardar:
        st.info("🚀 Intentando guardar panel...")
        st.write("📦 Draft actual:", st.session_state["panel_reagents_draft"])
        st.write("🧾 Nombre:", name)
        st.write("🧪 Cytometer ID:", cytometer_id)

        if not name.strip():
            st.error("El panel debe tener nombre")
            return

        if not st.session_state["panel_reagents_draft"]:
            st.error("Agregá al menos un anticuerpo")
            return

        try:
            panel_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            # INSERT PANEL
            query_panels("""
                INSERT INTO panels (
                    id, name, description,
                    sample_volume, washed_sample,
                    created_at, status, cytometer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                panel_id,
                name.strip(),
                description or None,
                sample_volume or None,
                1 if washed_sample else 0,
                now,
                "draft",
                cytometer_id
            ), commit=True)

            # INSERT ANTICUERPOS
            for ab in st.session_state["panel_reagents_draft"]:
                query_panels("""
                    INSERT INTO panel_reagents (
                        id, panel_id, reagent_id,
                        optical_channel_id, volume_used,
                        assigned_at, is_intracellular,
                        display_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    panel_id,
                    ab["reagent_id"],
                    ab["optical_channel_id"],
                    ab["volume_used"],
                    now,
                    ab["is_intracellular"],
                    ab["display_name"]
                ), commit=True)

            st.success("✅ Panel creado correctamente")

            # 🔒 Solo limpiar draft si todo salió OK
            st.session_state["panel_reagents_draft"] = []

        except Exception as e:
            st.error("💥 ERROR guardando panel:")
            st.exception(e)
