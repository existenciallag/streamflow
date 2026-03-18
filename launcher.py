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
    """Create or upgrade db/inventory.db from schema.sql.

    - Fresh install: creates the database with all tables and seed data.
    - Existing install: applies missing columns/tables then runs full schema.
    """
    db_dir = os.path.join(DATA_DIR, "db")
    db_path = os.path.join(db_dir, "inventory.db")
    schema_path = os.path.join(APP_DIR, "schema.sql")

    os.makedirs(db_dir, exist_ok=True)

    if not os.path.exists(schema_path):
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

        # Normalize legacy status values → three canonical statuses.
        _normalize_status_values(conn)

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
