#!/usr/bin/env python3
"""
Migration Runner for Panel Builder v2
Safely applies schema changes to the database with backup
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import uuid

DB_PATH = "db/inventory.db"
MIGRATION_FILE = "migrations/001_panel_builder_v2.sql"
BACKUP_DIR = "db/backups"


def backup_database():
    """Create a backup of the database before migration"""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}/inventory_backup_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path


def run_migration():
    """Run the migration SQL script"""
    print("\n" + "="*60)
    print("PANEL BUILDER V2 MIGRATION")
    print("="*60)

    # Check if migration already applied
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT migration_name FROM schema_migrations WHERE migration_name = ?",
                      ('001_panel_builder_v2',))
        if cursor.fetchone():
            print("\n⚠️  Migration '001_panel_builder_v2' already applied!")
            choice = input("Apply again anyway? (yes/no): ")
            if choice.lower() != 'yes':
                print("Migration cancelled.")
                conn.close()
                return False
    except sqlite3.OperationalError:
        # schema_migrations table doesn't exist yet
        pass

    conn.close()

    # Backup
    print("\n📦 Creating backup...")
    backup_path = backup_database()

    # Read migration file
    print(f"\n📄 Reading migration: {MIGRATION_FILE}")
    with open(MIGRATION_FILE, 'r') as f:
        migration_sql = f.read()

    # Apply migration
    print("\n🚀 Applying migration...")
    conn = sqlite3.connect(DB_PATH)

    try:
        # Use executescript - it handles multiple statements automatically
        # Note: executescript commits automatically, so no explicit commit needed
        conn.executescript(migration_sql)
        print("✅ Migration applied successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"\n📦 Restore from backup: {backup_path}")
        conn.close()
        return False

    conn.close()
    return True


def set_cytoflex_as_default():
    """Set CytoFLEX as the default cytometer"""
    print("\n🔧 Setting CytoFLEX as default cytometer...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # First, unset all defaults
        cursor.execute("UPDATE cytometers SET is_default = 0")

        # Set CytoFLEX as default (by name)
        cursor.execute("""
            UPDATE cytometers
            SET is_default = 1,
                laser_configuration = '3-laser (405nm, 488nm, 638nm)',
                detector_count = 13,
                status = 'active'
            WHERE name = 'Cytoflex'
        """)

        if cursor.rowcount > 0:
            print("✅ CytoFLEX set as default cytometer")
        else:
            print("⚠️  CytoFLEX not found in database")

        conn.commit()

    except Exception as e:
        print(f"❌ Error setting default cytometer: {e}")
        conn.rollback()

    conn.close()


def populate_channel_display_names():
    """Populate channel_display_name in existing panel_reagents from optical_channels"""
    print("\n🔧 Populating channel display names for existing panel reagents...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Update panel_reagents with channel names
        cursor.execute("""
            UPDATE panel_reagents
            SET channel_display_name = (
                SELECT oc.name
                FROM optical_channels oc
                WHERE oc.id = panel_reagents.optical_channel_id
            )
            WHERE channel_display_name IS NULL
        """)

        print(f"✅ Updated {cursor.rowcount} panel reagent records with channel names")
        conn.commit()

    except Exception as e:
        print(f"❌ Error populating channel names: {e}")
        conn.rollback()

    conn.close()


def create_sample_protocols():
    """Create sample acquisition, compensation, and analysis protocols"""
    print("\n🔧 Creating sample protocols...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get CytoFLEX ID
        cursor.execute("SELECT id FROM cytometers WHERE name = 'Cytoflex'")
        result = cursor.fetchone()
        if not result:
            print("⚠️  CytoFLEX not found, skipping protocol creation")
            conn.close()
            return

        cytoflex_id = result[0]
        now = datetime.utcnow().isoformat()

        # Create sample acquisition protocol
        acq_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO acquisition_protocols
            (id, name, cytometer_id, status, version, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            acq_id,
            "Standard Acquisition CytoFLEX",
            cytoflex_id,
            "validated",
            "1.0.0",
            "Standard acquisition settings: Medium flow rate, 100k events, FSC threshold 5000",
            now
        ))

        # Create sample compensation protocol
        comp_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO compensation_protocols
            (id, name, cytometer_id, status, version, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            comp_id,
            "Standard Compensation Matrix",
            cytoflex_id,
            "validated",
            "1.0.0",
            "Compensation matrix calculated using single-stain controls",
            now
        ))

        # Create sample analysis protocol
        analysis_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO analysis_protocols
            (id, name, status, version, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            analysis_id,
            "Standard Lymphocyte Gating",
            "validated",
            "1.0.0",
            "Standard gating strategy: FSC/SSC lymphocyte gate → CD45+ → subpopulations",
            now
        ))

        conn.commit()
        print("✅ Created 3 sample protocols (acquisition, compensation, analysis)")

    except Exception as e:
        print(f"❌ Error creating protocols: {e}")
        conn.rollback()

    conn.close()


def verify_migration():
    """Verify that migration was successful"""
    print("\n🔍 Verifying migration...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    checks = [
        ("acquisition_protocols table exists",
         "SELECT name FROM sqlite_master WHERE type='table' AND name='acquisition_protocols'"),
        ("compensation_protocols table exists",
         "SELECT name FROM sqlite_master WHERE type='table' AND name='compensation_protocols'"),
        ("analysis_protocols table exists",
         "SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_protocols'"),
        ("panels.version column exists",
         "SELECT version FROM panels LIMIT 1"),
        ("cytometers.is_default column exists",
         "SELECT is_default FROM cytometers LIMIT 1"),
        ("reagent_units.current_volume column exists",
         "SELECT current_volume FROM reagent_units LIMIT 1"),
    ]

    all_passed = True
    for check_name, query in checks:
        try:
            cursor.execute(query)
            print(f"   ✅ {check_name}")
        except sqlite3.OperationalError as e:
            print(f"   ❌ {check_name}: {e}")
            all_passed = False

    conn.close()

    if all_passed:
        print("\n✅ All verification checks passed!")
    else:
        print("\n⚠️  Some checks failed. Migration may be incomplete.")

    return all_passed


def main():
    """Run migration and setup"""
    if run_migration():
        set_cytoflex_as_default()
        populate_channel_display_names()
        create_sample_protocols()
        verify_migration()

        print("\n" + "="*60)
        print("MIGRATION COMPLETE!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Test the panel builder: streamlit run app.py")
        print("  2. Create a new panel to test the new features")
        print("  3. Check that channel names display correctly (not IDs)")
        print("="*60 + "\n")
    else:
        print("\n❌ Migration failed. Database unchanged.")


if __name__ == "__main__":
    main()
