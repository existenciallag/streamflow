# ui/inventory_advanced.py
import streamlit as st
import pandas as pd
from utils.translations import get_lang_dict

def advanced_inventory_view(df):
    # Get language from session state
    lang = st.session_state.get('language', 'en')
    t = get_lang_dict('inventory', lang)

    st.subheader(f"📊 {t['subheader']}")

    cols = st.multiselect(t['show_columns_label'], df.columns, default=df.columns)

    group_by = st.selectbox(t['group_by_label'], [t['group_by_none']] + list(df.columns))

    if group_by != t['group_by_none']:
        grouped = df.groupby(group_by).size().reset_index(name="count")
        st.dataframe(grouped, use_container_width=True)
    else:
        st.dataframe(df[cols], use_container_width=True)

    if st.button(t['export_button']):
        st.download_button(
            t['download_button_label'],
            df.to_csv(index=False),
            file_name=t['filename']
        )
