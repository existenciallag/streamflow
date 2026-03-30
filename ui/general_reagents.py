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
    insert_db("general_reagent_unit_history", {
        "general_reagent_unit_id": unit_id,
        "field": field,
        "old_value": str(old),
        "new_value": str(new),
        "changed_at": pd.Timestamp.now().isoformat(),
        "note": note
    })


# ============================================================
#                        UI PRINCIPAL
# ============================================================

def run_general_reagents_crud():

    reagents = query("SELECT * FROM general_reagents")
    units = query("SELECT * FROM general_reagent_units")
    brands = query("SELECT * FROM brands")

    brand_map = dict(zip(brands["id"], brands["name"]))

    reagents["Marca"] = reagents["brand_id"].map(brand_map)

    left, right = st.columns([1.2, 2])

    # ========================================================
    #                    LISTA DE REACTIVOS GENERALES
    # ========================================================

    with left:

        st.markdown("### 📋 Lista de Reactivos Generales")
        st.markdown("")  # Spacing

        search = st.text_input("🔍 Buscar", placeholder="PBS, EDTA, Lysing Buffer...").lower()

        df = reagents.copy()

        if search:
            df = df[
                df.astype(str)
                .apply(lambda x: x.str.lower().str.contains(search))
                .any(axis=1)
            ]

        table = df[[
            "name", "type", "Marca", "concentration"
        ]].rename(columns={
            "name": "Nombre",
            "type": "Tipo",
            "concentration": "Concentración"
        })

        selected = st.dataframe(
            table,
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun",
            hide_index=True
        )

        # ---------- NUEVO REACTIVO GENERAL ----------

        st.markdown("")  # Spacing
        st.markdown("---")
        st.markdown("")  # Spacing

        with st.expander("➕ Crear Nuevo Reactivo General", expanded=False):
            with st.form("new_general_reagent"):

                st.markdown("**Información del reactivo**")
                name = st.text_input("Nombre *", placeholder="Ej: PBS 1X")
                reagent_type = st.text_input("Tipo", placeholder="Ej: Buffer, Solución, Lisante")
                concentration = st.text_input("Concentración", placeholder="Ej: 1X, 10mM")

                st.markdown("")  # Spacing
                st.markdown("**Proveedor y precio**")

                col1, col2 = st.columns(2)
                with col1:
                    brand_id = st.selectbox(
                        "Marca *",
                        brands["id"],
                        format_func=lambda x: brand_map.get(x, x)
                    )

                with col2:
                    price = st.number_input("Precio referencia ($)", 0.0, step=10.0)

                st.markdown("")  # Spacing
                notes = st.text_area("Notas", placeholder="Notas adicionales sobre este reactivo")

                st.markdown("")  # Spacing
                if st.form_submit_button("✓ Crear Reactivo General", use_container_width=True):

                    if not name:
                        st.error("El campo Nombre es obligatorio")
                    else:
                        insert_db("general_reagents", {
                            "name": name,
                            "type": reagent_type,
                            "concentration": concentration,
                            "brand_id": brand_id,
                            "price": price,
                            "notes": notes,
                            "created_at": pd.Timestamp.now().isoformat()
                        })

                        st.rerun()

    # ========================================================
    #                  DETALLE DEL REACTIVO GENERAL
    # ========================================================

    with right:

        if not selected or not selected["selection"]["rows"]:
            st.info("👈 Seleccione un reactivo general de la lista para ver detalles y gestionar unidades")
            return

        r = df.iloc[selected["selection"]["rows"][0]]

        # ---------- HEADER ----------
        st.markdown(f"### 🧪 {r['name']}")
        st.markdown(f"**Marca:** {r['Marca']} | **Tipo:** {r['type'] or 'N/A'}")
        if r['concentration']:
            st.markdown(f"**Concentración:** {r['concentration']}")
        st.markdown("")  # Spacing

        # ---------- EDITAR REACTIVO GENERAL ----------

        col_edit, col_del = st.columns([4, 1])

        with col_edit:
            with st.expander("✏️ Editar Información del Reactivo", expanded=False):
                with st.form("edit_general_reagent"):

                    c1, c2 = st.columns(2)

                    with c1:
                        st.markdown("**Identificación**")
                        name = st.text_input("Nombre", r["name"])
                        reagent_type = st.text_input("Tipo", r["type"] or "")
                        concentration = st.text_input("Concentración", r["concentration"] or "")

                    with c2:
                        st.markdown("**Proveedor y precio**")
                        brand_id = st.selectbox(
                            "Marca",
                            brands["id"],
                            index=list(brands["id"]).index(r["brand_id"]) if r["brand_id"] in list(brands["id"]) else 0,
                            format_func=lambda x: brand_map.get(x, x)
                        )

                        price = st.number_input(
                            "Precio referencia ($)",
                            value=float(r["price"] or 0),
                            step=10.0
                        )

                    notes = st.text_area("Notas", r["notes"] or "")

                    st.markdown("")  # Spacing
                    if st.form_submit_button("✓ Guardar Cambios", use_container_width=True):

                        update_db("general_reagents", {
                            "name": name,
                            "type": reagent_type,
                            "concentration": concentration,
                            "brand_id": brand_id,
                            "price": price,
                            "notes": notes
                        }, r["id"])

                        st.rerun()

        with col_del:
            with st.expander("🗑️ Eliminar", expanded=False):
                st.warning("⚠️ Esto eliminará el reactivo y todas sus unidades")
                if st.button("Confirmar Eliminación", type="primary", use_container_width=True):
                    # Delete all units first
                    for unit_id in r_units["id"]:
                        delete_db("general_reagent_units", unit_id)
                    # Delete the reagent
                    delete_db("general_reagents", r["id"])
                    st.success("Reactivo eliminado")
                    st.rerun()

        st.markdown("")  # Spacing

        # ====================================================
        #                  GESTIÓN DE UNIDADES
        # ====================================================

        st.markdown("---")
        st.markdown("### 📦 Gestión de Unidades")
        st.markdown("")  # Spacing

        r_units = units[units["general_reagent_id"] == r["id"]]

        if not r_units.empty:

            st.markdown(f"**{len(r_units)} unidades registradas**")

            display = r_units[[
                "lot_number", "expiration_date",
                "volume", "status", "location"
            ]].rename(columns={
                "lot_number": "Lote",
                "expiration_date": "Vence",
                "volume": "Volumen (mL)",
                "status": "Estado",
                "location": "Ubicación"
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

                st.markdown(f"**Editando unidad:** Lote {u['lot_number']}")

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
                            "Volumen (mL)",
                            value=float(u["volume"] or 0),
                            step=10.0
                        )

                        arrival = st.date_input(
                            "Fecha de llegada",
                            value=pd.to_datetime(u["arrival_date"]).date() if u["arrival_date"] else pd.Timestamp.now().date()
                        )

                    with c2:
                        st.markdown("**Estado y ubicación**")
                        expiration = st.date_input(
                            "Fecha de vencimiento",
                            value=pd.to_datetime(u["expiration_date"]).date() if u["expiration_date"] else pd.Timestamp.now().date()
                        )

                        status = st.selectbox(
                            "Estado actual",
                            STATUS_VALUES,
                            index=STATUS_VALUES.index(current_status),
                            help="Stored: almacenado | In Use: en uso | Closed: terminado"
                        )

                    lot = st.text_input("Número de lote", u["lot_number"] or "")
                    location = st.text_input("Ubicación", u["location"] or "")
                    unit_notes = st.text_area("Notas", u["notes"] or "")

                    st.markdown("")  # Spacing
                    if st.form_submit_button("✓ Actualizar Unidad", use_container_width=True):

                        # ----- HISTORIAL -----

                        if float(u["volume"] or 0) != vol:
                            log_change(u["id"], "volume",
                                       u["volume"], vol)

                        if str(u["expiration_date"]) != str(expiration):
                            log_change(u["id"], "expiration",
                                       u["expiration_date"], expiration)

                        if str(u["status"]).strip() != status:
                            log_change(u["id"], "status",
                                       u["status"], status)

                        if str(u["lot_number"]) != lot:
                            log_change(u["id"], "lot",
                                       u["lot_number"], lot)

                        if str(u["location"]) != location:
                            log_change(u["id"], "location",
                                       u["location"], location)

                        # ----- UPDATE REAL -----

                        update_db("general_reagent_units", {
                            "volume": vol,
                            "arrival_date": str(arrival),
                            "expiration_date": str(expiration),
                            "status": status,
                            "lot_number": lot,
                            "location": location,
                            "notes": unit_notes,
                            "updated_at": pd.Timestamp.now().isoformat()
                        }, u["id"])

                        st.rerun()

                st.markdown("")  # Spacing

                # -------- ELIMINAR UNIDAD --------

                if st.button("🗑️ Eliminar Unidad", type="secondary", use_container_width=True):
                    delete_db("general_reagent_units", u["id"])
                    st.success("Unidad eliminada")
                    st.rerun()

                st.markdown("")  # Spacing

                # -------- HISTORIAL --------

                hist = query("""
                    SELECT field, old_value, new_value, changed_at
                    FROM general_reagent_unit_history
                    WHERE general_reagent_unit_id = ?
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
            st.info("No hay unidades registradas para este reactivo")

        # ---------- NUEVA UNIDAD ----------

        st.markdown("")  # Spacing
        st.markdown("---")
        st.markdown("")  # Spacing

        with st.expander("➕ Agregar Nueva Unidad", expanded=False):
            with st.form("new_unit"):

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**Volumen y fechas**")
                    vol = st.number_input("Volumen (mL) *", 0.0, step=10.0)
                    arrival = st.date_input("Fecha de llegada")

                with c2:
                    st.markdown("**Estado y ubicación**")
                    expiration = st.date_input("Fecha de vencimiento")
                    status = st.selectbox(
                        "Estado inicial",
                        STATUS_VALUES,
                        help="Stored: almacenado | In Use: en uso | Closed: terminado"
                    )

                lot = st.text_input("Número de lote *", placeholder="Ej: B123456")
                location = st.text_input("Ubicación", placeholder="Ej: Refrigerador A, Estante 2")
                unit_notes = st.text_area("Notas", placeholder="Notas sobre esta unidad específica")

                st.markdown("")  # Spacing
                if st.form_submit_button("✓ Crear Unidad", use_container_width=True):

                    if vol <= 0:
                        st.error("El volumen debe ser mayor a 0")
                    elif not lot:
                        st.error("El número de lote es obligatorio")
                    else:
                        insert_db("general_reagent_units", {
                            "general_reagent_id": r["id"],
                            "volume": vol,
                            "arrival_date": str(arrival),
                            "expiration_date": str(expiration),
                            "status": status,
                            "lot_number": lot,
                            "location": location,
                            "notes": unit_notes,
                            "created_at": pd.Timestamp.now().isoformat()
                        })

                        st.rerun()
