import streamlit as st
import pandas as pd
from uuid import uuid4
import sqlite3
from models.loaders import DB_PATH


# ============================================================
#                        DB HELPERS
# ============================================================

STATUS_VALUES = ["Stored", "In Use", "Closed"]


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
    insert_db("reagent_unit_history", {
        "reagent_unit_id": unit_id,
        "field": field,
        "old_value": str(old),
        "new_value": str(new),
        "changed_at": pd.Timestamp.now().isoformat(),
        "note": note
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
    #                       LISTA
    # ========================================================

    with left:

        st.subheader("Anticuerpos")

        search = st.text_input("Buscar").lower()

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
            on_select="rerun"
        )

        # ---------- NUEVO REACTIVO ----------

        st.markdown("---")
        st.subheader("Nuevo anticuerpo")

        with st.form("new_reagent"):

            name = st.text_input("CD")
            clone = st.text_input("Clon")
            catalog = st.text_input("Catálogo")

            fluorochrome = st.selectbox(
                "Fluorocromo",
                fluoros["id"],
                format_func=lambda x: fluoro_map.get(x, x)
            )

            brand_id = st.selectbox(
                "Marca",
                brands["id"],
                format_func=lambda x: brand_map.get(x, x)
            )

            price = st.number_input("Precio referencia", 0.0)

            if st.form_submit_button("Crear"):

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
    #                       DETALLE
    # ========================================================

    with right:

        if not selected or not selected["selection"]["rows"]:
            st.info("Seleccione un anticuerpo")
            return

        r = df.iloc[selected["selection"]["rows"][0]]

        st.subheader(
            f"{r['name']} – {r['Fluorocromo']} – {r['Marca']} – clon {r['clone']}"
        )

        # ---------- EDITAR REAGENT ----------

        with st.form("edit_reagent"):

            c1, c2 = st.columns(2)

            name = c1.text_input("CD", r["name"])
            clone = c1.text_input("Clon", r["clone"])
            catalog = c1.text_input("Catálogo", r["catalog_number"])

            fluorochrome = c2.selectbox(
                "Fluorocromo",
                fluoros["id"],
                index=list(fluoros["id"]).index(r["fluorochrome"]),
                format_func=lambda x: fluoro_map.get(x, x)
            )

            brand_id = c2.selectbox(
                "Marca",
                brands["id"],
                index=list(brands["id"]).index(r["brand_id"]),
                format_func=lambda x: brand_map.get(x, x)
            )

            price = c2.number_input(
                "Precio",
                value=float(r["price"] or 0)
            )

            if st.form_submit_button("Guardar cambios"):

                update_db("reagents", {
                    "name": name,
                    "clone": clone,
                    "catalog_number": catalog,
                    "fluorochrome": fluorochrome,
                    "brand_id": brand_id,
                    "price": price
                }, r["id"])

                st.rerun()

        # ====================================================
        #                       VIALES
        # ====================================================

        st.markdown("## Viales")

        r_units = units[units["reagent_id"] == r["id"]]

        if not r_units.empty:

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
                on_select="rerun"
            )

            if sel_u and sel_u["selection"]["rows"]:

                u = r_units.iloc[sel_u["selection"]["rows"][0]]

                # -------- NORMALIZAR ESTADO (FIX BUG) --------

                current_status = str(u["status"] or "").strip().title()

                if current_status not in STATUS_VALUES:
                    current_status = "Stored"

                # -------- FORM EDICION --------

                with st.form("edit_unit"):

                    c1, c2 = st.columns(2)

                    vol = c1.number_input(
                        "Volumen",
                        value=float(u["initial_volume"])
                    )

                    arrival = c1.date_input(
                        "Llegada",
                        value=pd.to_datetime(u["arrival_date"]).date()
                    )

                    expiration = c2.date_input(
                        "Vencimiento",
                        value=pd.to_datetime(u["expiration_date"]).date()
                    )

                    status = c2.selectbox(
                        "Estado",
                        STATUS_VALUES,
                        index=STATUS_VALUES.index(current_status)
                    )

                    lot = c2.text_input("Lote", u["lot"])

                    if st.form_submit_button("Guardar vial"):

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

                # -------- HISTORIAL --------

                hist = query("""
                    SELECT field, old_value, new_value, changed_at
                    FROM reagent_unit_history
                    WHERE reagent_unit_id = ?
                    ORDER BY changed_at DESC
                """, (u["id"],))

                if not hist.empty:
                    st.markdown("### Historial")
                    st.dataframe(hist, use_container_width=True)

        # ---------- NUEVO VIAL ----------

        st.markdown("### Nuevo vial")

        with st.form("new_unit"):

            c1, c2 = st.columns(2)

            vol = c1.number_input("Volumen (µL)", 0.0)
            arrival = c1.date_input("Llegada")
            expiration = c2.date_input("Vencimiento")
            status = c2.selectbox("Estado", STATUS_VALUES)
            lot = c2.text_input("Lote")

            if st.form_submit_button("Crear vial"):

                insert_db("reagent_units", {
                    "reagent_id": r["id"],
                    "initial_volume": vol,
                    "arrival_date": str(arrival),
                    "expiration_date": str(expiration),
                    "status": status,
                    "lot": lot
                })

                st.rerun()
