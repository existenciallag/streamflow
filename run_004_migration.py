#!/usr/bin/env python3
"""
Run Migration 004: Categories and Infrastructure
Creates tables for panel categories, versioning, clinical section, and economic tracking
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = "db/inventory.db"
MIGRATION_FILE = "migrations/004_categories_and_infrastructure.sql"


def backup_database():
    """Create a backup of the database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"db/backups/inventory_before_migration_004_{timestamp}.db"

    # Ensure backups directory exists
    Path("db/backups").mkdir(parents=True, exist_ok=True)

    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def verify_current_state(conn):
    """Verify database state before migration"""
    cursor = conn.cursor()

    # Check if migration already applied
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='panel_areas'
    """)

    if cursor.fetchone():
        print("⚠ Migration 004 appears to already be applied (panel_areas table exists)")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            return False

    # Check panels table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='panels'
    """)

    if not cursor.fetchone():
        print("✗ Error: panels table does not exist. Run previous migrations first.")
        return False

    print("✓ Database state verified")
    return True


def run_migration():
    """Execute the migration"""
    print("=" * 70)
    print("MIGRATION 004: Categories and Infrastructure")
    print("=" * 70)

    # Backup
    backup_path = backup_database()

    # Connect
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Verify
    if not verify_current_state(conn):
        conn.close()
        return False

    # Read migration file
    with open(MIGRATION_FILE, 'r') as f:
        migration_sql = f.read()

    # Execute migration
    print("\nExecuting migration...")
    cursor = conn.cursor()

    try:
        # Execute all statements
        cursor.executescript(migration_sql)
        conn.commit()
        print("✓ Migration executed successfully")

        # Verify results
        print("\nVerifying migration results...")

        # Check new tables
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN (
                'panel_areas',
                'panel_disease_categories',
                'panel_classifications',
                'panel_versions',
                'panel_status_history',
                'patients',
                'clinical_cases',
                'case_panels',
                'case_diagnoses',
                'panel_usage_log',
                'reagent_consumption_log'
            )
            ORDER BY name
        """)
        tables = cursor.fetchall()
        print(f"✓ Created {len(tables)} new tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # Check seed data
        cursor.execute("SELECT COUNT(*) FROM panel_areas")
        areas_count = cursor.fetchone()[0]
        print(f"\n✓ Seeded {areas_count} clinical areas")

        cursor.execute("SELECT COUNT(*) FROM panel_disease_categories")
        categories_count = cursor.fetchone()[0]
        print(f"✓ Seeded {categories_count} disease categories")

        # Check status updates
        cursor.execute("SELECT status, COUNT(*) FROM panels GROUP BY status")
        status_distribution = cursor.fetchall()
        print(f"\n✓ Panel status distribution:")
        for status, count in status_distribution:
            print(f"  - {status}: {count}")

        # Check version records
        cursor.execute("SELECT COUNT(*) FROM panel_versions")
        versions_count = cursor.fetchone()[0]
        print(f"\n✓ Created {versions_count} initial version records")

        conn.close()

        print("\n" + "=" * 70)
        print("MIGRATION 004 COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nBackup saved at: {backup_path}")
        print("\nNew features enabled:")
        print("  ✓ Panel categories (areas + disease categories)")
        print("  ✓ Panel version history tracking")
        print("  ✓ Panel status workflow")
        print("  ✓ Clinical section infrastructure (patients, cases)")
        print("  ✓ Economic tracking infrastructure (usage, costs)")

        return True

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        conn.rollback()
        conn.close()
        print(f"\nDatabase has been rolled back. Original backup available at: {backup_path}")
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
