# create_db.py
import os
import sqlite3
import json
from pathlib import Path
import pandas as pd
from datetime import datetime

ROOT = Path(".")
DATA_DIR = Path("data") if Path("data").exists() else ROOT
DB_FILE = ROOT / "inventory.db"
SCHEMA_FILE = ROOT / "schema.sql"

# Expected columns mapping for each table (lowercase)
EXPECTED_COLUMNS = {
    "brands": ["id","name","team_id"],
    "cytometers": ["id","name","manufacturer","model","serial_number","created_at","team_id"],
    "optical_channels": ["id","name","min_range","max_range","team_id"],
    "fluorochromes": ["id","name"],
    "reagents": ["id","name","fluorochrome","brand_id","catalog_number","clone","price","team_id","user_id"],
    "general_reagents": ["id","name","brand_id","type","concentration","preparation_date","notes","created_at","arrival_date","expiration_date","price","team_id","user_id"],
    "reagent_units": ["id","reagent_id","initial_volume","arrival_date","expiration_date","status","lot","team_id"],
    "general_reagent_units": ["id","general_reagent_id","lot_number","expiration_date","location","status","volume","notes","created_at","updated_at","team_id"],
    "panels": ["id","name","category_id","description","sample_volume","created_at","status","cytometer_id","washed_sample","acquisition_protocol_status","acquisition_protocol_name","acquisition_protocol_code","compensation_status","compensation_name","compensation_code","analysis_protocol_status","analysis_protocol_name","analysis_protocol_code","team_id","user_id"],
    "panel_reagents": ["id","panel_id","reagent_id","optical_channel_id","volume_used","assigned_at","is_intracellular","display_name","team_id"],
    "panel_general_reagents": ["id","panel_id","general_reagent_id","volume_used","notes","added_at","team_id"],
    "purchase_orders": ["id","supplier","total_price","status","created_at","updated_at","team_id","user_id"],
    "purchase_order_items": ["id","purchase_order_id","reagent_id","quantity","unit_price","total_price","status","received_quantity","team_id"],
    "cytometer_optical_channels": ["id","cytometer_id","optical_channel_id","associated_fluorochrome","team_id"]
}

# helper: normalize dataframe columns and types
def normalize_df(df):
    # strip BOM / whitespace and set lowercase
    df.columns = [str(c).strip().replace("\ufeff","") for c in df.columns]
    df.columns = [c.lower() for c in df.columns]

    # boolean-ish to 0/1
    bool_cols = [c for c in df.columns if c.startswith("is_") or c in ("washed_sample",)]
    for c in bool_cols:
        df[c] = df[c].map({True:1, False:0, "true":1, "false":0, "True":1, "False":0}).fillna(df[c])
        try:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
        except:
            pass

    # dates: columns that likely are dates
    date_like = [c for c in df.columns if "date" in c or c.endswith("_at") or c in ("created_at","updated_at","arrival_date","expiration_date","preparation_date")]
    for c in date_like:
        if c in df.columns:
            # try parse; store ISO string or None
            df[c] = pd.to_datetime(df[c], errors="coerce")
            df[c] = df[c].dt.strftime("%Y-%m-%dT%H:%M:%S")
            df[c] = df[c].where(df[c].notna(), None)

    # arrays -> json text (very simple heuristics)
    arr_guess = [c for c in df.columns if "associated_fluor" in c or c.endswith("tags")]
    for c in arr_guess:
        def to_json_cell(v):
            if pd.isna(v):
                return None
            s = str(v)
            if s.startswith("{") and s.endswith("}"):
                inner = s[1:-1]
                items = [x.strip().strip('"').strip("'") for x in inner.split(",") if x!='']
                return json.dumps(items)
            if s.startswith("[") and s.endswith("]"):
                try:
                    return json.dumps(json.loads(s))
                except:
                    return json.dumps([s])
            return json.dumps([s])
        df[c] = df[c].apply(to_json_cell)

    # strip whitespace from object/string columns
    for c in df.select_dtypes(include=["object"]).columns:
        df[c] = df[c].apply(lambda x: x.strip() if isinstance(x, str) else x)

    return df

# create DB from schema.sql
def create_db_from_schema():
    if SCHEMA_FILE.exists():
        schema_sql = SCHEMA_FILE.read_text()
    else:
        raise FileNotFoundError("schema.sql not found in current directory.")

    if DB_FILE.exists():
        print(f"Removing existing DB: {DB_FILE}")
        DB_FILE.unlink()

    conn = sqlite3.connect(str(DB_FILE))
    conn.executescript("PRAGMA foreign_keys = ON;")
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print("Created DB and applied schema.")

def insert_csv_to_table(csv_path, table_name, engine):
    fname = csv_path.name
    print(f"  -> Reading {fname}")
    # try common separators automatically
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        try:
            df = pd.read_csv(csv_path, sep=";")
        except Exception:
            df = pd.read_csv(csv_path, sep="\t")

    df = normalize_df(df)
    exp_cols = EXPECTED_COLUMNS.get(table_name, None)
    if exp_cols is None:
        # fallback: insert whatever, lowercased cols
        df.columns = [c.lower() for c in df.columns]
        df.to_sql(table_name, con=engine, if_exists="append", index=False)
        print(f"    Inserted {len(df)} rows into {table_name} (fallback)")
        return {"inserted": len(df), "warnings": []}

    # ensure all expected columns exist in df (fill with None)
    for c in exp_cols:
        if c not in df.columns:
            df[c] = None

    # keep only expected columns in that order
    df_out = df[exp_cols].copy()

    # convert numeric-ish columns
    for c in df_out.columns:
        if c in ("min_range","max_range","quantity","received_quantity"):
            df_out[c] = pd.to_numeric(df_out[c], errors="coerce").astype("Int64")
        if c in ("initial_volume","volume","price","total_price","unit_price","sample_volume","volume_used"):
            df_out[c] = pd.to_numeric(df_out[c], errors="coerce")

    # write to SQL
    try:
        df_out.to_sql(table_name, con=engine, if_exists="append", index=False)
        return {"inserted": len(df_out), "warnings": []}
    except Exception as e:
        # try safer cast to strings
        try:
            df2 = df_out.astype(str).where(~df_out.isna(), None)
            df2.to_sql(table_name, con=engine, if_exists="append", index=False)
            return {"inserted": len(df2), "warnings": [f"fallback-string-insert: {e}"]}
        except Exception as e2:
            return {"inserted": 0, "warnings": [f"failed: {e2}"]}

def main():
    print("DATA DIR:", DATA_DIR)
    csv_files = [p for p in DATA_DIR.iterdir() if p.suffix.lower() == ".csv"]
    if not csv_files:
        print("No CSV files found in data directory.")
        return

    # create DB schema
    create_db_from_schema()

    # connect engine via sqlite3 for pandas
    import sqlalchemy
    engine = sqlalchemy.create_engine(f"sqlite:///{DB_FILE}", future=True)

    # insertion order chosen to satisfy FKs
    ordered_tables = [
        "brands", "cytometers", "optical_channels", "fluorochromes",
        "reagents", "general_reagents",
        "reagent_units", "general_reagent_units",
        "panels", "panel_reagents", "panel_general_reagents",
        "purchase_orders", "purchase_order_items", "cytometer_optical_channels"
    ]

    # map filenames -> Path objects
    fname_map = {p.name.lower(): p for p in csv_files}

    report = {}
    # insert in ordered_tables if file exists
    for tbl in ordered_tables:
        # find candidate filename
        candidate = None
        for fname, path in fname_map.items():
            if fname.replace(".csv","") == tbl or fname.replace(".csv","") == tbl + "s":
                candidate = path
                break
        # some files have slightly different names in your dump: map specials
        if candidate is None:
            # special mapping rules
            for fname, path in fname_map.items():
                if tbl == "reagent_units" and "reagents_units" in fname:
                    candidate = path
                    break
                if tbl == "general_reagent_units" and "general_reagents_units" in fname:
                    candidate = path
                    break
                if tbl == "cytometer_optical_channels" and "cytometer_optical_channels" in fname:
                    candidate = path
                    break
        if candidate:
            res = insert_csv_to_table(candidate, tbl, engine)
            report[tbl] = res
            print(f"    Inserted {res['inserted']} rows into {tbl}. Warnings: {res['warnings']}")
        else:
            print(f"    No CSV found for table {tbl} — skipping.")
            report[tbl] = {"inserted": 0, "warnings": ["missing file"]}

    # any CSVs not in the ordered list? insert them by filename->table conversion
    inserted_files = set([p.name for p in csv_files if p.name.replace(".csv","") in ordered_tables])
    for p in csv_files:
        if p.name in inserted_files:
            continue
        tbl_guess = p.name.lower().replace(".csv","")
        print(f"Inserting remaining file {p.name} as table {tbl_guess}")
        res = insert_csv_to_table(p, tbl_guess, engine)
        report[tbl_guess] = res
        print(f"    Inserted {res['inserted']} rows into {tbl_guess}. Warnings: {res['warnings']}")

    print("\n=== INSERTION REPORT ===")
    for k,v in report.items():
        print(f"{k}: inserted={v['inserted']} warnings={v['warnings']}")

    print("\nDB created at:", DB_FILE)

if __name__ == "__main__":
    main()
