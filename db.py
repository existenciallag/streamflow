# db.py
import pandas as pd
from sqlalchemy import create_engine

ENGINE = create_engine("sqlite:///inventory.db", echo=False, future=True)

def query(sql, params=None):
    return pd.read_sql(sql, ENGINE, params=params)
