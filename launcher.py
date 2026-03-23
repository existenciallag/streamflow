"""
StreamFlow Launcher
-------------------
Entry point for the packaged Windows application.
- Creates the database on first run using schema.sql
- Finds a free port
- Starts the Streamlit server programmatically (no terminal window)
- Opens the browser automatically once the server is ready
"""

import os
import sys
import socket
import sqlite3
import threading
import time
import webbrowser
import csv
import shutil
from pathlib import Path


# ── Resolve the installation directory ────────────────────────────────────────
# When frozen by PyInstaller this is the folder that contains StreamFlow.exe.
# When running from source this is the directory that contains launcher.py.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    # sys._MEIPASS contains the bundled app files (app.py, ui/, utils/, …)
    APP_DIR = sys._MEIPASS
    # On Windows the exe lives in Program Files (read-only for regular users).
    # Store the database in %LOCALAPPDATA%\StreamFlow so any user can write it.
    DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "StreamFlow",
    )
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BASE_DIR
    DATA_DIR = BASE_DIR  # dev: keep db/ next to the source files

# Change CWD to BASE_DIR so every relative path resolves to the install dir.
os.chdir(BASE_DIR)

# Tell the app where to find the database (loaders.py reads this).
os.environ["STREAMFLOW_BASE_DIR"] = DATA_DIR


# ── Database bootstrap ─────────────────────────────────────────────────────────
def ensure_database():
    """Create or upgrade db/inventory.db.

    - Fresh install (Windows): copies bundled template database with all data.
    - Dev mode (Codespaces): uses existing db/inventory.db directly.
    - Fallback: creates from schema.sql + imports CSVs.
    """
    db_dir = os.path.join(DATA_DIR, "db")
    db_path = os.path.join(db_dir, "inventory.db")
    schema_path = os.path.join(APP_DIR, "schema.sql")
    template_db = os.path.join(APP_DIR, "db_template", "inventory.db")

    os.makedirs(db_dir, exist_ok=True)

    # FIRST RUN: Copy bundled template database (Windows installer)
    if not os.path.exists(db_path):
        if os.path.exists(template_db):
            print(f"[StreamFlow] First run detected - copying template database...")
            print(f"[StreamFlow] Template: {template_db}")
            print(f"[StreamFlow] Template size: {os.path.getsize(template_db) / 1024:.1f} KB")
            print(f"[StreamFlow] Target: {db_path}")

            try:
                shutil.copy2(template_db, db_path)
                print(f"[StreamFlow] File copied. Verifying...")

                # Verify the copy was successful and has data
                conn = sqlite3.connect(db_path)
                try:
                    cur = conn.cursor()

                    # Check if tables exist
                    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    print(f"[StreamFlow] Database has {len(tables)} tables")

                    reagent_count = cur.execute("SELECT COUNT(*) FROM reagents").fetchone()[0]
                    unit_count = cur.execute("SELECT COUNT(*) FROM reagent_units").fetchone()[0]
                    print(f"[StreamFlow] ✅ Database copied successfully!")
                    print(f"[StreamFlow]    - {reagent_count} reagents")
                    print(f"[StreamFlow]    - {unit_count} units")

                    _normalize_status_values(conn)
                    conn.commit()
                finally:
                    conn.close()
                return
            except Exception as e:
                print(f"[StreamFlow] ❌ Error copying template: {e}")
                print(f"[StreamFlow] Falling back to CSV import...")
                # Remove failed DB and continue to fallback
                if os.path.exists(db_path):
                    os.remove(db_path)
        else:
            print(f"[StreamFlow] Template database not found at: {template_db}")
            print(f"[StreamFlow] Checking bundled files...")
            print(f"[StreamFlow] APP_DIR: {APP_DIR}")
            if os.path.exists(APP_DIR):
                print(f"[StreamFlow] APP_DIR contents:")
                for item in os.listdir(APP_DIR):
                    print(f"[StreamFlow]   - {item}")
            print(f"[StreamFlow] Falling back to CSV import...")

    # FALLBACK: Create from schema.sql if no template and no existing DB
    if not os.path.exists(db_path):
        print(f"[StreamFlow] Database not found at: {db_path}")
        print(f"[StreamFlow] Template DB exists: {os.path.exists(template_db)}")
        print(f"[StreamFlow] Falling back to schema.sql + CSV import...")

        if not os.path.exists(schema_path):
            print(f"[StreamFlow] WARNING: schema.sql not found, creating empty database")
            open(db_path, "w").close()
            return

    conn = sqlite3.connect(db_path)
    try:
        # For existing databases: add columns that were added in migrations.
        # Ignore errors (column already exists = success).
        _apply_column_migrations(conn)

        # Now apply the full schema (tables, indexes, seed data).
        # CREATE TABLE IF NOT EXISTS and INSERT OR IGNORE make this safe.
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        # Import seed data from CSV files (if tables are empty - first run).
        _import_seed_data(conn)

        # Normalize legacy status values → three canonical statuses.
        _normalize_status_values(conn)

        # Verify database has data
        try:
            cur = conn.cursor()
            reagent_count = cur.execute("SELECT COUNT(*) FROM reagents").fetchone()[0]
            unit_count = cur.execute("SELECT COUNT(*) FROM reagent_units").fetchone()[0]
            print(f"[StreamFlow] Database initialized: {reagent_count} reagents, {unit_count} units")
        except Exception:
            pass  # Tables may not exist yet

        conn.commit()
    finally:
        conn.close()


def _normalize_status_values(conn):
    """Convert legacy status values to the canonical three: Stored, In Use, Empty.

    Discarded, Closed, closed, discarded → Empty
    In Use / Stored are kept as-is (case-normalised to title case).
    """
    for table in ("reagent_units", "general_reagent_units"):
        try:
            conn.execute(f"""
                UPDATE {table}
                SET status = CASE
                    WHEN LOWER(status) IN ('closed', 'discarded', 'expired', 'wasted') THEN 'Empty'
                    WHEN LOWER(status) = 'in use'  THEN 'In Use'
                    WHEN LOWER(status) = 'stored'  THEN 'Stored'
                    ELSE 'Empty'
                END
                WHERE LOWER(status) NOT IN ('in use', 'stored', 'empty')
            """)
        except Exception:
            pass  # Table may not exist yet on first run


def _import_seed_data(conn):
    """Import seed data from CSV files on first run (if tables are empty).

    CSV files are bundled in the data/ directory by PyInstaller.
    """
    print(f"[StreamFlow] Checking for CSV seed data...")

    # CSV files to import (in dependency order)
    # Format: (table_name, csv_filename, expected_columns)
    csv_imports = [
        ("brands", "brands.csv"),
        ("fluorochromes", "fluorochromes.csv"),
        ("cytometers", "cytometers.csv"),
        ("optical_channels", "optical_channels.csv"),
        ("cytometer_optical_channels", "cytometer_optical_channels.csv"),
        ("general_reagents", "general_reagents.csv"),
        ("reagents", "reagents.csv"),
        ("general_reagent_units", "general_reagents_units.csv"),  # Note: CSV has _s
        ("reagent_units", "reagents_units.csv"),                  # Note: CSV has _s
        ("panels", "panels.csv"),
        ("panel_reagents", "panel_reagents.csv"),
        ("panel_general_reagents", "panel_general_reagents.csv"),
    ]

    data_dir = Path(APP_DIR) / "data"
    if not data_dir.exists():
        print(f"[StreamFlow] No data/ directory found at: {data_dir}")
        return  # No CSV files bundled (dev mode without data/ dir)

    print(f"[StreamFlow] Found data directory: {data_dir}")
    cursor = conn.cursor()

    for table_name, csv_filename in csv_imports:
        # Check if table already has data
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"[StreamFlow]   {table_name}: skipping (already has {count} rows)")
                continue  # Skip - table already populated
        except sqlite3.OperationalError:
            print(f"[StreamFlow]   {table_name}: table doesn't exist yet, skipping")
            continue  # Table doesn't exist yet

        # Import from CSV
        csv_path = data_dir / csv_filename
        if not csv_path.exists():
            print(f"[StreamFlow]   {table_name}: CSV not found ({csv_filename})")
            continue

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                if not rows:
                    print(f"[StreamFlow]   {table_name}: CSV is empty")
                    continue

                # Get columns from CSV header
                csv_cols = list(rows[0].keys())

                # Get valid table columns
                table_cols = _get_table_columns(cursor, table_name)

                # Only use columns that exist in both CSV and table
                valid_cols = [col for col in csv_cols if col in table_cols]

                if not valid_cols:
                    print(f"[StreamFlow]   {table_name}: no matching columns between CSV and table")
                    continue

                # Build INSERT statement
                placeholders = ", ".join(["?" for _ in valid_cols])
                insert_sql = f"INSERT OR IGNORE INTO {table_name} ({', '.join(valid_cols)}) VALUES ({placeholders})"

                # Insert all rows
                inserted = 0
                for row in rows:
                    values = [row.get(col, None) for col in valid_cols]
                    cursor.execute(insert_sql, values)
                    if cursor.rowcount > 0:
                        inserted += 1

                print(f"[StreamFlow]   {table_name}: ✅ imported {inserted}/{len(rows)} rows")

        except Exception as e:
            # Skip errors and continue with other tables
            print(f"[StreamFlow]   {table_name}: ❌ error importing - {e}")
            pass


def _get_table_columns(cursor, table_name):
    """Get list of column names for a table."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    except Exception:
        return []


def _apply_column_migrations(conn):
    """Add columns from migrations 001-004 to existing tables.

    Silently ignores errors (column already exists).
    """
    migrations = [
        # Migration 001: cytometers
        "ALTER TABLE cytometers ADD COLUMN is_default INTEGER DEFAULT 0",
        "ALTER TABLE cytometers ADD COLUMN laser_configuration TEXT",
        "ALTER TABLE cytometers ADD COLUMN detector_count INTEGER",
        "ALTER TABLE cytometers ADD COLUMN status TEXT DEFAULT 'active'",
        "ALTER TABLE cytometers ADD COLUMN installation_date TEXT",
        "ALTER TABLE cytometers ADD COLUMN last_maintenance_date TEXT",
        "ALTER TABLE cytometers ADD COLUMN next_maintenance_due TEXT",

        # Migration 001: reagents
        "ALTER TABLE reagents ADD COLUMN target_antigen TEXT",

        # Migration 001: reagent_units
        "ALTER TABLE reagent_units ADD COLUMN current_volume REAL",
        "ALTER TABLE reagent_units ADD COLUMN opened_date TEXT",
        "ALTER TABLE reagent_units ADD COLUMN closed_date TEXT",
        "ALTER TABLE reagent_units ADD COLUMN qc_status TEXT DEFAULT 'pending'",
        "ALTER TABLE reagent_units ADD COLUMN qc_date TEXT",
        "ALTER TABLE reagent_units ADD COLUMN qc_notes TEXT",
        "ALTER TABLE reagent_units ADD COLUMN storage_location TEXT",

        # Migration 001: panels
        "ALTER TABLE panels ADD COLUMN version TEXT DEFAULT '1.0.0'",
        "ALTER TABLE panels ADD COLUMN parent_panel_id TEXT",
        "ALTER TABLE panels ADD COLUMN version_notes TEXT",
        "ALTER TABLE panels ADD COLUMN validated_at TEXT",
        "ALTER TABLE panels ADD COLUMN validated_by TEXT",
        "ALTER TABLE panels ADD COLUMN clinical_indication TEXT",
        "ALTER TABLE panels ADD COLUMN sample_type TEXT",
        "ALTER TABLE panels ADD COLUMN estimated_cost_per_test REAL",
        "ALTER TABLE panels ADD COLUMN estimated_time_minutes INTEGER",
        "ALTER TABLE panels ADD COLUMN updated_at TEXT",
        "ALTER TABLE panels ADD COLUMN created_by TEXT",

        # Migration 001: panel_reagents
        "ALTER TABLE panel_reagents ADD COLUMN preferred_reagent_unit_id TEXT",
        "ALTER TABLE panel_reagents ADD COLUMN channel_display_name TEXT",
        "ALTER TABLE panel_reagents ADD COLUMN is_surface INTEGER DEFAULT 1",
        "ALTER TABLE panel_reagents ADD COLUMN staining_step INTEGER DEFAULT 1",
        "ALTER TABLE panel_reagents ADD COLUMN display_order INTEGER",
        "ALTER TABLE panel_reagents ADD COLUMN unit_cost REAL",
        "ALTER TABLE panel_reagents ADD COLUMN cost_per_test REAL",
        "ALTER TABLE panel_reagents ADD COLUMN added_by TEXT",

        # Migration 001: panel_general_reagents
        "ALTER TABLE panel_general_reagents ADD COLUMN preferred_unit_id TEXT",
        "ALTER TABLE panel_general_reagents ADD COLUMN usage_type TEXT",
        "ALTER TABLE panel_general_reagents ADD COLUMN application_step INTEGER DEFAULT 1",
        "ALTER TABLE panel_general_reagents ADD COLUMN is_required INTEGER DEFAULT 1",
        "ALTER TABLE panel_general_reagents ADD COLUMN display_name TEXT",
        "ALTER TABLE panel_general_reagents ADD COLUMN cost_per_test REAL",

        # Migration 001: cytometer_optical_channels
        "ALTER TABLE cytometer_optical_channels ADD COLUMN primary_fluorochrome TEXT",
        "ALTER TABLE cytometer_optical_channels ADD COLUMN display_order INTEGER",
        "ALTER TABLE cytometer_optical_channels ADD COLUMN is_scatter INTEGER DEFAULT 0",
        "ALTER TABLE cytometer_optical_channels ADD COLUMN detector_type TEXT",
        "ALTER TABLE cytometer_optical_channels ADD COLUMN laser_wavelength INTEGER",

        # Migration 002: reagent_units
        "ALTER TABLE reagent_units ADD COLUMN purchase_price REAL",
        "ALTER TABLE reagent_units ADD COLUMN purchase_date TEXT",
        "ALTER TABLE reagent_units ADD COLUMN supplier_id TEXT",
        "ALTER TABLE reagent_units ADD COLUMN cost_per_ul REAL",

        # Migration 002: reagents
        "ALTER TABLE reagents ADD COLUMN catalog_price REAL",
        "ALTER TABLE reagents ADD COLUMN catalog_volume REAL",

        # Migration 003: general_reagent_units
        "ALTER TABLE general_reagent_units ADD COLUMN arrival_date TEXT",
    ]

    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            # Column already exists or table doesn't exist yet - both OK
            pass


# ── Port selection ─────────────────────────────────────────────────────────────
def find_free_port(start: int = 8501) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start


# ── Browser opener ─────────────────────────────────────────────────────────────
def open_browser_when_ready(port: int):
    """Poll Streamlit's health endpoint; open the browser as soon as it answers."""
    import urllib.request

    url = f"http://localhost:{port}"
    health_url = f"{url}/_stcore/health"

    for _ in range(60):          # wait up to 30 seconds
        try:
            urllib.request.urlopen(health_url, timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)

    # Fallback: open even if health check timed out
    webbrowser.open(url)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ensure_database()

    port = find_free_port()

    # Start browser opener in a daemon thread so it doesn't block Streamlit
    browser_thread = threading.Thread(
        target=open_browser_when_ready, args=(port,), daemon=True
    )
    browser_thread.start()

    # Point Streamlit at app.py inside the bundle (APP_DIR) or source tree
    app_path = os.path.join(APP_DIR, "app.py")

    # Build the argv that Streamlit's CLI parser expects
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--client.showErrorDetails=true",
        "--global.developmentMode=false",
    ]

    from streamlit.web import cli as stcli
    stcli.main()


if __name__ == "__main__":
    main()
