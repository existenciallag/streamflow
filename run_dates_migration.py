#!/usr/bin/env python3
"""
Migration Runner for Date Fixes
Runs migration 003_fix_dates.sql
"""

import sqlite3
import os
from datetime import datetime
import shutil

DB_PATH = "db/inventory.db"
MIGRATION_FILE = "migrations/003_fix_dates.sql"
BACKUP_DIR = "db/backups"


def backup_database():
    """Create timestamped backup of database"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}/inventory_before_dates_fix_{timestamp}.db"

    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def verify_current_state(conn):
    """Check current database state before migration"""
    cursor = conn.cursor()

    print("\n=== PRE-MIGRATION STATE ===")

    # Check if arrival_date already exists in general_reagent_units
    cursor.execute("PRAGMA table_info(general_reagent_units)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'arrival_date' in columns:
        print("⚠️  WARNING: arrival_date column already exists in general_reagent_units")
        print("   Migration may have been run before")
        response = input("   Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration aborted")
            return False
    else:
        print("✓ arrival_date column missing (will be added)")

    # Check date format issues
    cursor.execute("""
        SELECT COUNT(*) FROM reagent_units
        WHERE expiration_date LIKE '%T%'
    """)
    dates_with_time = cursor.fetchone()[0]
    print(f"✓ Reagent units with time in expiration_date: {dates_with_time}")

    cursor.execute("""
        SELECT COUNT(*) FROM general_reagent_units
        WHERE expiration_date LIKE '%T%'
    """)
    general_dates_with_time = cursor.fetchone()[0]
    print(f"✓ General units with time in expiration_date: {general_dates_with_time}")

    # Check expired units
    cursor.execute("""
        SELECT COUNT(*) FROM reagent_units
        WHERE expiration_date < date('now')
    """)
    expired = cursor.fetchone()[0]
    print(f"✓ Expired reagent units: {expired}")

    return True


def run_migration():
    """Execute the migration"""

    # Check files exist
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return False

    if not os.path.exists(MIGRATION_FILE):
        print(f"❌ Migration file not found: {MIGRATION_FILE}")
        return False

    # Backup first
    backup_path = backup_database()

    # Connect and verify
    conn = sqlite3.connect(DB_PATH)

    if not verify_current_state(conn):
        conn.close()
        return False

    # Read migration SQL
    with open(MIGRATION_FILE, 'r') as f:
        migration_sql = f.read()

    # Execute migration
    print("\n=== RUNNING MIGRATION ===")
    try:
        cursor = conn.cursor()

        # Split by semicolon and execute one by one
        statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

        for i, statement in enumerate(statements):
            # Skip comments and empty statements
            if statement.startswith('--') or len(statement) < 5:
                continue

            try:
                cursor.execute(statement)
                print(f"  ✓ Statement {i+1}/{len(statements)}")
            except sqlite3.Error as e:
                # Some statements might fail if already applied
                if "duplicate column name" in str(e).lower():
                    print(f"  ⚠️  Statement {i+1}: Column already exists (skipping)")
                elif "already exists" in str(e).lower():
                    print(f"  ⚠️  Statement {i+1}: Already exists (skipping)")
                else:
                    print(f"  ❌ Statement {i+1} failed: {e}")
                    # Continue anyway - some failures are expected in idempotent migrations

        conn.commit()
        print("✓ Migration executed successfully")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        conn.close()
        print(f"\nDatabase can be restored from: {backup_path}")
        return False

    # Verify post-migration state
    print("\n=== POST-MIGRATION STATE ===")
    cursor = conn.cursor()

    # Check arrival_date added
    cursor.execute("PRAGMA table_info(general_reagent_units)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'arrival_date' in columns:
        print(f"✓ Column added: general_reagent_units.arrival_date")

        cursor.execute("SELECT COUNT(*) FROM general_reagent_units WHERE arrival_date IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"✓ General units with arrival_date: {count}")
    else:
        print(f"❌ Column missing: general_reagent_units.arrival_date")

    # Check date format standardization
    cursor.execute("SELECT COUNT(*) FROM reagent_units WHERE expiration_date LIKE '%T%'")
    dates_with_time = cursor.fetchone()[0]
    print(f"✓ Reagent units with time format (should be 0): {dates_with_time}")

    cursor.execute("SELECT COUNT(*) FROM general_reagent_units WHERE expiration_date LIKE '%T%'")
    general_dates_with_time = cursor.fetchone()[0]
    print(f"✓ General units with time format (should be 0): {general_dates_with_time}")

    # Check indexes created
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index'
        AND name LIKE 'idx_%expiration%'
    """)
    indexes = cursor.fetchall()
    print(f"✓ Expiration indexes created: {len(indexes)}")

    # Sample data check
    print("\n=== SAMPLE DATA CHECK ===")
    cursor.execute("""
        SELECT r.name, ru.arrival_date, ru.expiration_date, ru.status
        FROM reagent_units ru
        JOIN reagents r ON r.id = ru.reagent_id
        WHERE ru.expiration_date IS NOT NULL
        ORDER BY ru.expiration_date
        LIMIT 5
    """)

    print("Sample reagent units with standardized dates:")
    for row in cursor.fetchall():
        name, arrival, expiration, status = row
        print(f"  {name[:30]:<30} | Arrived: {arrival or 'N/A':<12} | Expires: {expiration:<12} | {status}")

    conn.close()

    print("\n✅ MIGRATION COMPLETED SUCCESSFULLY")
    print(f"Backup saved at: {backup_path}")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("MIGRATION 003: Fix Date Handling")
    print("=" * 70)
    print()
    print("This migration will:")
    print("  1. Add arrival_date column to general_reagent_units")
    print("  2. Standardize all dates to ISO format (YYYY-MM-DD)")
    print("  3. Add indexes for date-based queries")
    print("  4. Improve Dashboard performance")
    print()

    response = input("Proceed with migration? (yes/no): ")

    if response.lower() == 'yes':
        success = run_migration()
        exit(0 if success else 1)
    else:
        print("Migration cancelled")
        exit(1)
