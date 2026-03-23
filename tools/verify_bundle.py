"""
Verify that the template database is bundled correctly.
Run this INSIDE the built installer to check.
"""
import os
import sys
import sqlite3

print("=" * 60)
print("StreamFlow Bundle Verification")
print("=" * 60)

if getattr(sys, "frozen", False):
    print("✅ Running as FROZEN executable")
    APP_DIR = sys._MEIPASS
    print(f"   Bundle directory: {APP_DIR}")
else:
    print("⚠️  Running as PYTHON SCRIPT (not frozen)")
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"   Script directory: {APP_DIR}")

print()
print("Checking bundled files...")
print("-" * 60)

# Check for schema.sql
schema_path = os.path.join(APP_DIR, "schema.sql")
if os.path.exists(schema_path):
    print(f"✅ schema.sql found ({os.path.getsize(schema_path)} bytes)")
else:
    print(f"❌ schema.sql NOT FOUND at {schema_path}")

# Check for template database
template_db = os.path.join(APP_DIR, "db_template", "inventory.db")
if os.path.exists(template_db):
    size = os.path.getsize(template_db)
    print(f"✅ Template database found ({size:,} bytes)")

    # Try to open and check contents
    try:
        conn = sqlite3.connect(template_db)
        cur = conn.cursor()

        # Check tables
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"   Database has {len(tables)} tables")

        # Check reagents
        try:
            reagent_count = cur.execute("SELECT COUNT(*) FROM reagents").fetchone()[0]
            print(f"   ✅ Reagents: {reagent_count} rows")
        except Exception as e:
            print(f"   ❌ Reagents table: {e}")

        # Check reagent_units
        try:
            unit_count = cur.execute("SELECT COUNT(*) FROM reagent_units").fetchone()[0]
            print(f"   ✅ Reagent units: {unit_count} rows")
        except Exception as e:
            print(f"   ❌ Reagent_units table: {e}")

        conn.close()
    except Exception as e:
        print(f"   ❌ Error opening database: {e}")
else:
    print(f"❌ Template database NOT FOUND at {template_db}")

# Check data/ folder
data_dir = os.path.join(APP_DIR, "data")
if os.path.exists(data_dir):
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    print(f"✅ data/ folder found with {len(csv_files)} CSV files")
else:
    print(f"❌ data/ folder NOT FOUND at {data_dir}")

print("=" * 60)
input("Press Enter to close...")
