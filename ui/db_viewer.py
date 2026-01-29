import streamlit as st
import pandas as pd
from models.loaders import load_table
from utils.translations import get_lang_dict

def show_db_viewer():
    # Get language from session state
    lang = st.session_state.get('language', 'en')
    t = get_lang_dict('database', lang)

    st.header(f"📂 {t['header']}")

    tables = [
        "brands",
        "reagents",
        "general_reagents",
        "fluorochromes",
        "reagent_units",
        "general_reagent_units",
        "panels",
        "panel_reagents",
        "panel_general_reagents",
        "cytometers",
        "cytometer_optical_channels",
        "optical_channels",
        "purchase_orders",
        "purchase_order_items"
    ]

    st.subheader(t['select_table_subheader'])
    table_name = st.selectbox(t['table_label'], tables)

    df = load_table(table_name)

    st.markdown(f"### 🔎 {t['preview_header']} **{table_name}** ({len(df)} {t['rows_label']})")

    st.dataframe(df, use_container_width=True)

    st.markdown(f"### 🧬 {t['columns_header']}")
    st.write(pd.DataFrame({
        t['column_label']: df.columns,
        t['dtype_label']: df.dtypes.astype(str)
    }))
