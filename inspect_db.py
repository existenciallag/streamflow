import sqlite3
from pathlib import Path

DB = Path("db/inventory.db")

with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()

    print("\n=== TABLAS EN LA BASE ===")
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    for (table,) in tables:
        print(f"\n--- {table} ---")
        cols = cursor.execute(f"PRAGMA table_info({table})").fetchall()
        for col in cols:
            cid, name, ctype, notnull, default, pk = col
            print(f"  {name}  ({ctype})")
