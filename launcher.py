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
    """Create db/inventory.db from schema.sql if it does not exist yet."""
    import sqlite3

    db_dir = os.path.join(DATA_DIR, "db")
    db_path = os.path.join(db_dir, "inventory.db")
    schema_path = os.path.join(APP_DIR, "schema.sql")

    os.makedirs(db_dir, exist_ok=True)

    if not os.path.exists(db_path):
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn = sqlite3.connect(db_path)
            conn.executescript(schema_sql)
            conn.commit()
            conn.close()
        else:
            # schema.sql not found — create an empty file so the app can start
            # and will report "no such table" for individual queries.
            open(db_path, "w").close()


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
