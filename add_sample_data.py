#!/usr/bin/env python3
"""Add sample reagents and general reagents to the database"""

import sqlite3
from uuid import uuid4
from datetime import datetime, timedelta

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Get brand and fluorochrome IDs
cursor.execute("SELECT id, name FROM brands")
brands = {name: id for id, name in cursor.fetchall()}

cursor.execute("SELECT id, name FROM fluorochromes")
fluoros = {name: id for id, name in cursor.fetchall()}

# Add sample reagents (antibodies)
sample_reagents = [
    ("CD3", "UCHT1", fluoros.get("FITC"), brands.get("BD Biosciences"), "300459", 350.0),
    ("CD4", "RPA-T4", fluoros.get("PE"), brands.get("BioLegend"), "300508", 325.0),
    ("CD8", "SK1", fluoros.get("APC"), brands.get("BD Biosciences"), "344722", 375.0),
    ("CD19", "HIB19", fluoros.get("PE-Cy7"), brands.get("BioLegend"), "302216", 400.0),
    ("CD45", "HI30", fluoros.get("BV421"), brands.get("BioLegend"), "304032", 450.0),
]

for name, clone, fluoro_id, brand_id, catalog, price in sample_reagents:
    reagent_id = str(uuid4())
    cursor.execute("""
        INSERT INTO reagents (id, name, clone, fluorochrome, brand_id, catalog_number, price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (reagent_id, name, clone, fluoro_id, brand_id, catalog, price))

    # Add 2 vials for each reagent
    for i in range(2):
        cursor.execute("""
            INSERT INTO reagent_units (id, reagent_id, initial_volume, arrival_date,
                                     expiration_date, status, lot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            reagent_id,
            100.0,  # 100µL
            (datetime.now() - timedelta(days=30)).isoformat(),
            (datetime.now() + timedelta(days=365)).isoformat(),
            "Stored",
            f"LOT{i+1}{name[:2]}"
        ))

# Add sample general reagents
sample_general_reagents = [
    ("PBS 1X", "Buffer", "1X", brands.get("Thermo Fisher"), 45.0, 500.0, None),
    ("Lysing Buffer", "Lysis Solution", "10X", brands.get("BD Biosciences"), 180.0, 100.0, None),
    ("EDTA", "Chelating Agent", "0.5M", brands.get("Thermo Fisher"), 35.0, 250.0, None),
    ("Fetal Bovine Serum", "Serum", "100%", brands.get("Thermo Fisher"), 350.0, 500.0, None),
    ("FACS Tubes", "Consumable", None, brands.get("BD Biosciences"), 120.0, None, 500.0),
]

for name, type_, conc, brand_id, price, std_vol, std_units in sample_general_reagents:
    reagent_id = str(uuid4())
    cursor.execute("""
        INSERT INTO general_reagents (id, name, type, concentration, brand_id, price, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (reagent_id, name, type_, conc, brand_id, price, datetime.now().isoformat()))

    # Add 1-2 units for each general reagent
    num_units = 2 if std_vol else 1  # More units for liquids
    for i in range(num_units):
        volume = std_vol if std_vol else None
        cursor.execute("""
            INSERT INTO general_reagent_units (id, general_reagent_id, lot_number,
                                              expiration_date, location, status, volume,
                                              arrival_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            reagent_id,
            f"BATCH{i+1}{name[:3].upper()}",
            (datetime.now() + timedelta(days=180)).isoformat(),
            f"Refrigerador A, Estante {i+1}",
            "Stored",
            volume,
            (datetime.now() - timedelta(days=15)).isoformat(),
            datetime.now().isoformat()
        ))

conn.commit()
conn.close()

print("✅ Sample data added successfully!")
print(f"Added {len(sample_reagents)} reagents with 2 vials each")
print(f"Added {len(sample_general_reagents)} general reagents with units")
