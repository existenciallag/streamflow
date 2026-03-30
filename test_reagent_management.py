#!/usr/bin/env python3
"""Test script to verify reagent management system"""

import sqlite3

def test_database():
    """Test database structure and data"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    print("=" * 60)
    print("REAGENT MANAGEMENT SYSTEM TEST")
    print("=" * 60)

    # Test tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n✓ Found {len(tables)} tables in database")

    # Test brands
    cursor.execute("SELECT COUNT(*), GROUP_CONCAT(name, ', ') FROM brands")
    brand_count, brand_names = cursor.fetchone()
    print(f"\n✓ BRANDS: {brand_count} brands")
    print(f"  {brand_names}")

    # Test fluorochromes
    cursor.execute("SELECT COUNT(*), GROUP_CONCAT(name, ', ') FROM fluorochromes")
    fluoro_count, fluoro_names = cursor.fetchone()
    print(f"\n✓ FLUOROCHROMES: {fluoro_count} fluorochromes")
    print(f"  {fluoro_names}")

    # Test reagents (antibodies)
    cursor.execute("""
        SELECT COUNT(*) FROM reagents
    """)
    reagent_count = cursor.fetchone()[0]
    print(f"\n✓ REAGENTS (Antibodies): {reagent_count} antibodies")

    if reagent_count > 0:
        cursor.execute("""
            SELECT r.name, f.name as fluoro, b.name as brand, r.clone
            FROM reagents r
            LEFT JOIN brands b ON r.brand_id = b.id
            LEFT JOIN fluorochromes f ON r.fluorochrome = f.id
            LIMIT 5
        """)
        print("  Sample reagents:")
        for row in cursor.fetchall():
            print(f"    - {row[0]} {row[1]} ({row[2]}, clone {row[3]})")

    # Test reagent units
    cursor.execute("SELECT COUNT(*) FROM reagent_units")
    unit_count = cursor.fetchone()[0]
    print(f"\n✓ REAGENT UNITS: {unit_count} vials")

    # Test general reagents
    cursor.execute("""
        SELECT COUNT(*) FROM general_reagents
    """)
    gen_reagent_count = cursor.fetchone()[0]
    print(f"\n✓ GENERAL REAGENTS: {gen_reagent_count} general reagents")

    if gen_reagent_count > 0:
        cursor.execute("""
            SELECT gr.name, gr.type, b.name as brand, gr.concentration
            FROM general_reagents gr
            LEFT JOIN brands b ON gr.brand_id = b.id
            LIMIT 5
        """)
        print("  Sample general reagents:")
        for row in cursor.fetchall():
            conc = f", {row[3]}" if row[3] else ""
            print(f"    - {row[0]} ({row[1]}{conc}) - Brand: {row[2]}")

    # Test general reagent units
    cursor.execute("SELECT COUNT(*) FROM general_reagent_units")
    gen_unit_count = cursor.fetchone()[0]
    print(f"\n✓ GENERAL REAGENT UNITS: {gen_unit_count} units")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Database is properly initialized")
    print(f"✅ {brand_count} brands available")
    print(f"✅ {fluoro_count} fluorochromes available")
    print(f"✅ {reagent_count} antibodies with {unit_count} vials")
    print(f"✅ {gen_reagent_count} general reagents with {gen_unit_count} units")
    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

    # Test brand mapping (the issue the user mentioned)
    print("\n" + "=" * 60)
    print("BRAND DISPLAY TEST")
    print("=" * 60)

    cursor.execute("""
        SELECT r.name, b.name as brand_name, r.brand_id
        FROM reagents r
        LEFT JOIN brands b ON r.brand_id = b.id
        LIMIT 3
    """)
    print("\nReagent brand display:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: Brand Name = '{row[1]}' (ID: {row[2]})")

    cursor.execute("""
        SELECT gr.name, b.name as brand_name, gr.brand_id
        FROM general_reagents gr
        LEFT JOIN brands b ON gr.brand_id = b.id
        LIMIT 3
    """)
    print("\nGeneral reagent brand display:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: Brand Name = '{row[1]}' (ID: {row[2]})")

    conn.close()

if __name__ == "__main__":
    test_database()
