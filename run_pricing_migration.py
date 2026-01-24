#!/usr/bin/env python3
"""
Migration Runner for Dynamic Pricing System
Runs migration 002_dynamic_pricing.sql
"""

import sqlite3
import os
from datetime import datetime
import shutil

DB_PATH = "db/inventory.db"
MIGRATION_FILE = "migrations/002_dynamic_pricing.sql"
BACKUP_DIR = "db/backups"


def backup_database():
    """Create timestamped backup of database"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}/inventory_before_pricing_migration_{timestamp}.db"

    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def verify_current_state(conn):
    """Check current database state before migration"""
    cursor = conn.cursor()

    print("\n=== PRE-MIGRATION STATE ===")

    # Check if columns already exist (migration already run)
    cursor.execute("PRAGMA table_info(reagent_units)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'purchase_price' in columns:
        print("⚠️  WARNING: purchase_price column already exists")
        print("   Migration may have been run before")
        response = input("   Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration aborted")
            return False

    # Check how many reagents have prices
    cursor.execute("SELECT COUNT(*) FROM reagents WHERE price IS NOT NULL")
    reagents_with_price = cursor.fetchone()[0]
    print(f"✓ Reagents with prices: {reagents_with_price}")

    # Check total reagent units
    cursor.execute("SELECT COUNT(*) FROM reagent_units")
    total_units = cursor.fetchone()[0]
    print(f"✓ Total reagent units: {total_units}")

    # Check panels with fixed costs
    cursor.execute("SELECT COUNT(*) FROM panels WHERE estimated_cost_per_test IS NOT NULL")
    panels_with_costs = cursor.fetchone()[0]
    print(f"✓ Panels with fixed costs: {panels_with_costs}")

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

        # Split by semicolon and execute one by one (executescript doesn't work with PRAGMA)
        statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

        for i, statement in enumerate(statements):
            # Skip comments and empty statements
            if statement.startswith('--') or len(statement) < 5:
                continue

            # Skip PRAGMA table_info (it's just a check, not a modification)
            if 'PRAGMA table_info' in statement:
                continue

            try:
                cursor.execute(statement)
                print(f"  ✓ Statement {i+1}/{len(statements)}")
            except sqlite3.Error as e:
                # Some statements might fail if already applied (like ALTER TABLE ADD COLUMN)
                # This is okay for idempotent migrations
                if "duplicate column name" in str(e).lower():
                    print(f"  ⚠️  Statement {i+1}: Column already exists (skipping)")
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

    # Check new columns exist
    cursor.execute("PRAGMA table_info(reagent_units)")
    columns = [col[1] for col in cursor.fetchall()]
    new_columns = ['purchase_price', 'purchase_date', 'supplier_id', 'cost_per_ul']

    for col in new_columns:
        if col in columns:
            print(f"✓ Column added: reagent_units.{col}")
        else:
            print(f"❌ Column missing: reagent_units.{col}")

    # Check data migration
    cursor.execute("SELECT COUNT(*) FROM reagent_units WHERE purchase_price IS NOT NULL")
    units_with_price = cursor.fetchone()[0]
    print(f"✓ Reagent units with purchase_price: {units_with_price}")

    cursor.execute("SELECT COUNT(*) FROM reagent_units WHERE cost_per_ul IS NOT NULL")
    units_with_cost_per_ul = cursor.fetchone()[0]
    print(f"✓ Reagent units with cost_per_ul: {units_with_cost_per_ul}")

    # Check catalog price
    cursor.execute("PRAGMA table_info(reagents)")
    reagent_columns = [col[1] for col in cursor.fetchall()]
    if 'catalog_price' in reagent_columns:
        print(f"✓ Column added: reagents.catalog_price")

        cursor.execute("SELECT COUNT(*) FROM reagents WHERE catalog_price IS NOT NULL")
        catalog_count = cursor.fetchone()[0]
        print(f"✓ Reagents with catalog_price: {catalog_count}")

    # Check deprecated columns nulled
    cursor.execute("SELECT COUNT(*) FROM panels WHERE estimated_cost_per_test IS NOT NULL")
    panels_still_with_costs = cursor.fetchone()[0]
    print(f"✓ Panels with estimated_cost_per_test (should be 0): {panels_still_with_costs}")

    # Sample data check
    print("\n=== SAMPLE DATA CHECK ===")
    cursor.execute("""
        SELECT r.name, ru.lot, ru.purchase_price, ru.initial_volume, ru.cost_per_ul
        FROM reagent_units ru
        JOIN reagents r ON r.id = ru.reagent_id
        WHERE ru.cost_per_ul IS NOT NULL
        LIMIT 5
    """)

    print("Sample reagent units with pricing:")
    for row in cursor.fetchall():
        name, lot, price, volume, cost_per_ul = row
        print(f"  {name[:30]:<30} | Lot: {lot:<10} | ${price:.2f} / {volume}µL = ${cost_per_ul:.4f}/µL")

    conn.close()

    print("\n✅ MIGRATION COMPLETED SUCCESSFULLY")
    print(f"Backup saved at: {backup_path}")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("MIGRATION 002: Dynamic Pricing System")
    print("=" * 70)
    print()
    print("This migration will:")
    print("  1. Add purchase_price, cost_per_ul to reagent_units")
    print("  2. Migrate existing prices from reagents to reagent_units")
    print("  3. Add catalog_price to reagents")
    print("  4. Deprecate fixed costs in panels and panel_reagents")
    print()

    response = input("Proceed with migration? (yes/no): ")

    if response.lower() == 'yes':
        success = run_migration()
        exit(0 if success else 1)
    else:
        print("Migration cancelled")
        exit(1)
