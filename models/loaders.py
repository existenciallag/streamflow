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


def _get_db_mtime():
    """Get database modification time for cache invalidation."""
    try:
        return os.path.getmtime(DB_PATH)
    except FileNotFoundError:
        return 0


@st.cache_data(ttl=None, show_spinner=False)
def load_table(table_name: str, _db_mtime: float = None) -> pd.DataFrame:
    """Carga una tabla específica desde SQLite

    Cache is invalidated when database file is modified.
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df


def load_all():
    """Carga todas las tablas relevantes para la app

    Cache is invalidated when database file is modified.
    """
    db_mtime = _get_db_mtime()
    return _load_all_cached(db_mtime)


@st.cache_data(ttl=None, show_spinner=False)
def _load_all_cached(_db_mtime: float):
    """Internal cached loader - cache key includes db modification time."""
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
    return {tbl: load_table(tbl, _db_mtime) for tbl in tables}
