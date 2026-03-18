import streamlit as st
import pandas as pd
from uuid import uuid4
import sqlite3
from models.loaders import DB_PATH


# ============================================================
#                        DB HELPERS
# ============================================================

STATUS_VALUES = ["Stored", "In Use", "Empty"]


def generate_id():
    return str(uuid4())


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def query(sql, params=()):
    with connect_db() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def exec_db(sql, params=()):
    with connect_db() as conn:
        conn.execute(sql, params)
        conn.commit()


def insert_db(table, data):
    if "id" not in data:
        data["id"] = generate_id()

    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))

    exec_db(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
        list(data.values())
    )


def update_db(table, data, id_):
    sets = ", ".join([f"{k}=?" for k in data])
    exec_db(
        f"UPDATE {table} SET {sets} WHERE id=?",
        list(data.values()) + [id_]
    )


def delete_db(table, id_):
    exec_db(f"DELETE FROM {table} WHERE id=?", (id_,))


# ============================================================
#                      HISTORIAL
# ============================================================

def log_change(unit_id, field, old, new, note=""):
    """
    Log a change to a reagent unit in the history table.
    Includes all required fields to match the reagent_unit_history schema.
    """
    insert_db("reagent_unit_history", {
        "reagent_unit_id": unit_id,
        "field": field,
        "old_value": str(old) if old is not None else "",
        "new_value": str(new) if new is not None else "",
        "changed_at": pd.Timestamp.now().isoformat(),
        "changed_by": None,  # Can be populated if user tracking is added
        "team_id": None,     # Can be populated if multi-tenancy is added
        "note": note if note else ""
    })


# ============================================================
#                        UI PRINCIPAL
# ============================================================

def run_crud():

    reagents = query("SELECT * FROM reagents")
    units = query("SELECT * FROM reagent_units")
    brands = query("SELECT * FROM brands")
    fluoros = query("SELECT * FROM fluorochromes")

    brand_map = dict(zip(brands["id"], brands["name"]))
    fluoro_map = dict(zip(fluoros["id"], fluoros["name"]))

    reagents["Marca"] = reagents["brand_id"].map(brand_map)
    reagents["Fluorocromo"] = reagents["fluorochrome"].map(fluoro_map)

    left, right = st.columns([1.2, 2])

    # ========================================================
    #                    LISTA DE ANTICUERPOS
    # ========================================================

    with left:

        st.markdown("### 📋 Lista de Anticuerpos")
        st.markdown("")  # Spacing

        search = st.text_input("🔍 Buscar", placeholder="CD3, PE, Biolegend...").lower()

        df = reagents.copy()

        if search:
            df = df[
                df.astype(str)
                .apply(lambda x: x.str.lower().str.contains(search))
                .any(axis=1)
            ]

        table = df[[
            "name", "Fluorocromo", "Marca", "clone"
        ]].rename(columns={
            "name": "CD",
            "clone": "Clon"
        })

        selected = st.dataframe(
            table,
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun",
            hide_index=True
        )

        # ---------- NUEVO ANTICUERPO ----------

        st.markdown("")  # Spacing
        st.markdown("---")
        st.markdown("")  # Spacing

        with st.expander("➕ Crear Nuevo Anticuerpo", expanded=False):
            with st.form("new_reagent"):

                st.markdown("**Información del reactivo**")
                name = st.text_input("CD *", placeholder="Ej: CD3")
                clone = st.text_input("Clon", placeholder="Ej: UCHT1")
                catalog = st.text_input("Catálogo", placeholder="Ej: 300459")

                st.markdown("")  # Spacing
                st.markdown("**Proveedor y fluorocromo**")

                col1, col2 = st.columns(2)
                with col1:
                    fluorochrome = st.selectbox(
                        "Fluorocromo *",
                        fluoros["id"],
                        format_func=lambda x: fluoro_map.get(x, x)
                    )

                with col2:
                    brand_id = st.selectbox(
                        "Marca *",
                        brands["id"],
                        format_func=lambda x: brand_map.get(x, x)
                    )

                st.markdown("")  # Spacing
                price = st.number_input("Precio referencia ($)", 0.0, step=10.0)

                st.markdown("")  # Spacing
                if st.form_submit_button("✓ Crear Anticuerpo", use_container_width=True):

                    if not name:
                        st.error("El campo CD es obligatorio")
                    else:
                        insert_db("reagents", {
                            "name": name,
                            "clone": clone,
                            "catalog_number": catalog,
                            "fluorochrome": fluorochrome,
                            "brand_id": brand_id,
                            "price": price
                        })

                        st.rerun()

    # ========================================================
    #                  DETALLE DEL ANTICUERPO
    # ========================================================

    with right:

        if not selected or not selected["selection"]["rows"]:
            st.info("👈 Seleccione un anticuerpo de la lista para ver detalles y gestionar viales")
            return

        r = df.iloc[selected["selection"]["rows"][0]]

        # ---------- HEADER ----------
        st.markdown(f"### 🔬 {r['name']} – {r['Fluorocromo']}")
        st.markdown(f"**Marca:** {r['Marca']} | **Clon:** {r['clone']}")
        st.markdown("")  # Spacing

        # ---------- EDITAR ANTICUERPO ----------

        with st.expander("✏️ Editar Información del Anticuerpo", expanded=False):
            with st.form("edit_reagent"):

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**Identificación**")
                    name = st.text_input("CD", r["name"])
                    clone = st.text_input("Clon", r["clone"])
                    catalog = st.text_input("Catálogo", r["catalog_number"])

                with c2:
                    st.markdown("**Proveedor y especificaciones**")
                    fluorochrome = st.selectbox(
                        "Fluorocromo",
                        fluoros["id"],
                        index=list(fluoros["id"]).index(r["fluorochrome"]),
                        format_func=lambda x: fluoro_map.get(x, x)
                    )

                    brand_id = st.selectbox(
                        "Marca",
                        brands["id"],
                        index=list(brands["id"]).index(r["brand_id"]),
                        format_func=lambda x: brand_map.get(x, x)
                    )

                    price = st.number_input(
                        "Precio referencia ($)",
                        value=float(r["price"] or 0),
                        step=10.0
                    )

                st.markdown("")  # Spacing
                if st.form_submit_button("✓ Guardar Cambios", use_container_width=True):

                    update_db("reagents", {
                        "name": name,
                        "clone": clone,
                        "catalog_number": catalog,
                        "fluorochrome": fluorochrome,
                        "brand_id": brand_id,
                        "price": price
                    }, r["id"])

                    st.rerun()

        st.markdown("")  # Spacing

        # ====================================================
        #                  GESTIÓN DE VIALES
        # ====================================================

        st.markdown("---")
        st.markdown("### 🧪 Gestión de Viales")
        st.markdown("")  # Spacing

        r_units = units[units["reagent_id"] == r["id"]]

        if not r_units.empty:

            st.markdown(f"**{len(r_units)} viales registrados**")

            display = r_units[[
                "lot", "expiration_date",
                "initial_volume", "status"
            ]].rename(columns={
                "lot": "Lote",
                "expiration_date": "Vence",
                "initial_volume": "Vol (µL)",
                "status": "Estado"
            })

            sel_u = st.dataframe(
                display,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun",
                hide_index=True
            )

            st.markdown("")  # Spacing

            if sel_u and sel_u["selection"]["rows"]:

                u = r_units.iloc[sel_u["selection"]["rows"][0]]

                st.markdown(f"**Editando vial:** Lote {u['lot']}")

                # -------- NORMALIZAR ESTADO (FIX BUG) --------

                current_status = str(u["status"] or "").strip().title()

                if current_status not in STATUS_VALUES:
                    current_status = "Stored"

                # -------- FORM EDICION --------

                with st.form("edit_unit"):

                    c1, c2 = st.columns(2)

                    with c1:
                        st.markdown("**Volumen y fechas**")
                        vol = st.number_input(
                            "Volumen inicial (µL)",
                            value=float(u["initial_volume"]),
                            step=10.0
                        )

                        arrival = st.date_input(
                            "Fecha de llegada",
                            value=pd.to_datetime(u["arrival_date"]).date()
                        )

                    with c2:
                        st.markdown("**Estado y lote**")
                        expiration = st.date_input(
                            "Fecha de vencimiento",
                            value=pd.to_datetime(u["expiration_date"]).date()
                        )

                        status = st.selectbox(
                            "Estado actual",
                            STATUS_VALUES,
                            index=STATUS_VALUES.index(current_status),
                            help="Stored: almacenado | In Use: en uso | Closed: terminado"
                        )

                        lot = st.text_input("Número de lote", u["lot"])

                    st.markdown("")  # Spacing
                    if st.form_submit_button("✓ Actualizar Vial", use_container_width=True):

                        # ----- HISTORIAL -----

                        if float(u["initial_volume"]) != vol:
                            log_change(u["id"], "volume",
                                       u["initial_volume"], vol)

                        if str(u["expiration_date"]) != str(expiration):
                            log_change(u["id"], "expiration",
                                       u["expiration_date"], expiration)

                        if str(u["status"]).strip() != status:
                            log_change(u["id"], "status",
                                       u["status"], status)

                        if str(u["lot"]) != lot:
                            log_change(u["id"], "lot",
                                       u["lot"], lot)

                        # ----- UPDATE REAL -----

                        update_db("reagent_units", {
                            "initial_volume": vol,
                            "arrival_date": str(arrival),
                            "expiration_date": str(expiration),
                            "status": status,
                            "lot": lot
                        }, u["id"])

                        st.rerun()

                st.markdown("")  # Spacing

                # -------- HISTORIAL --------

                hist = query("""
                    SELECT field, old_value, new_value, changed_at
                    FROM reagent_unit_history
                    WHERE reagent_unit_id = ?
                    ORDER BY changed_at DESC
                """, (u["id"],))

                if not hist.empty:
                    with st.expander(f"📜 Historial de Cambios ({len(hist)} registros)", expanded=False):
                        hist_display = hist.rename(columns={
                            "field": "Campo",
                            "old_value": "Valor anterior",
                            "new_value": "Valor nuevo",
                            "changed_at": "Fecha"
                        })
                        st.dataframe(hist_display, use_container_width=True, hide_index=True)
        else:
            st.info("No hay viales registrados para este anticuerpo")

        # ---------- NUEVO VIAL ----------

        st.markdown("")  # Spacing
        st.markdown("---")
        st.markdown("")  # Spacing

        with st.expander("➕ Agregar Nuevo Vial", expanded=False):
            with st.form("new_unit"):

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**Volumen y fechas**")
                    vol = st.number_input("Volumen inicial (µL) *", 0.0, step=10.0)
                    arrival = st.date_input("Fecha de llegada")

                with c2:
                    st.markdown("**Estado y lote**")
                    expiration = st.date_input("Fecha de vencimiento")
                    status = st.selectbox(
                        "Estado inicial",
                        STATUS_VALUES,
                        help="Stored: almacenado | In Use: en uso | Closed: terminado"
                    )
                    lot = st.text_input("Número de lote *", placeholder="Ej: B123456")

                st.markdown("")  # Spacing
                if st.form_submit_button("✓ Crear Vial", use_container_width=True):

                    if vol <= 0:
                        st.error("El volumen debe ser mayor a 0")
                    elif not lot:
                        st.error("El número de lote es obligatorio")
                    else:
                        insert_db("reagent_units", {
                            "reagent_id": r["id"],
                            "initial_volume": vol,
                            "arrival_date": str(arrival),
                            "expiration_date": str(expiration),
                            "status": status,
                            "lot": lot
                        })

                        st.rerun()
