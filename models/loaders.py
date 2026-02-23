# models/loaders.py
import os
import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

# Resolve DB path robustly:
# - When packaged (launcher.py sets STREAMFLOW_BASE_DIR), use that directory.
# - Otherwise fall back to the classic relative path (dev environment).
_base = os.environ.get("STREAMFLOW_BASE_DIR", "")
if _base:
    DB_PATH = Path(_base) / "db" / "inventory.db"
else:
    DB_PATH = Path("db/inventory.db")

@st.cache_data
def load_table(table_name: str) -> pd.DataFrame:
    """Carga una tabla específica desde SQLite"""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df

@st.cache_data
def load_all():
    """Carga todas las tablas relevantes para la app"""
    tables = [
        "brands",
        "reagents",
        "general_reagents",
        "fluorochromes",
        "reagent_units",
        "general_reagent_units",
        "panels",
        "panel_reagents",
        "cytometers",
        "cytometer_optical_channels",
        "optical_channels"
    ]
    return {tbl: load_table(tbl) for tbl in tables}
