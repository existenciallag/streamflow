import sqlite3
import pandas as pd
from models.loaders import DB_PATH


def query_panels(sql, params=None, commit=False):
    """
    Ejecuta queries sobre la base de paneles.

    - Si commit=True → hace INSERT/UPDATE/DELETE y devuelve None
    - Si es SELECT → devuelve DataFrame
    """

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if params is None:
        params = ()

    cur.execute(sql, params)

    if commit:
        conn.commit()
        conn.close()
        return None

    rows = cur.fetchall()

    # Si no es SELECT
    if cur.description is None:
        conn.close()
        return pd.DataFrame()

    columns = [desc[0] for desc in cur.description]
    conn.close()

    return pd.DataFrame(rows, columns=columns)
