"""
Panel Categories Utilities
Functions for managing panel areas, disease categories, and classifications
"""

import pandas as pd
from ui.crud_panels import query_panels
import uuid


def get_all_areas():
    """Get all clinical areas"""
    return query_panels("""
        SELECT id, name, code, description, display_order
        FROM panel_areas
        ORDER BY display_order, name
    """)


def get_all_disease_categories(area_id=None):
    """Get all disease categories, optionally filtered by area"""
    if area_id:
        return query_panels("""
            SELECT id, name, description, icd_code, requires_patient_tracking
            FROM panel_disease_categories
            WHERE area_id = ?
            ORDER BY name
        """, (area_id,))
    else:
        return query_panels("""
            SELECT
                pdc.id,
                pdc.name,
                pdc.description,
                pdc.icd_code,
                pdc.requires_patient_tracking,
                pa.name as area_name
            FROM panel_disease_categories pdc
            LEFT JOIN panel_areas pa ON pa.id = pdc.area_id
            ORDER BY pa.name, pdc.name
        """)


def get_panel_classifications(panel_id):
    """Get all classifications for a panel"""
    return query_panels("""
        SELECT
            pc.id,
            pc.area_id,
            pc.disease_category_id,
            pc.is_primary,
            pa.name as area_name,
            pdc.name as disease_category_name
        FROM panel_classifications pc
        LEFT JOIN panel_areas pa ON pa.id = pc.area_id
        LEFT JOIN panel_disease_categories pdc ON pdc.id = pc.disease_category_id
        WHERE pc.panel_id = ?
        ORDER BY pc.is_primary DESC, pa.name
    """, (panel_id,))


def get_primary_area(panel_id):
    """Get the primary clinical area for a panel"""
    result = query_panels("""
        SELECT pa.id, pa.name
        FROM panel_classifications pc
        JOIN panel_areas pa ON pa.id = pc.area_id
        WHERE pc.panel_id = ? AND pc.is_primary = 1
        LIMIT 1
    """, (panel_id,))

    if result is None or result.empty:
        return None, None
    return result.iloc[0]['id'], result.iloc[0]['name']


def get_primary_disease_category(panel_id):
    """Get the primary disease category for a panel"""
    result = query_panels("""
        SELECT pdc.id, pdc.name
        FROM panel_classifications pc
        JOIN panel_disease_categories pdc ON pdc.id = pc.disease_category_id
        WHERE pc.panel_id = ? AND pc.is_primary = 1
        LIMIT 1
    """, (panel_id,))

    if result is None or result.empty:
        return None, None
    return result.iloc[0]['id'], result.iloc[0]['name']


def set_panel_classification(panel_id, area_id, disease_category_id=None, is_primary=True):
    """Set or update panel classification"""
    classification_id = str(uuid.uuid4())

    # If setting as primary, clear other primary classifications
    if is_primary:
        query_panels("""
            UPDATE panel_classifications
            SET is_primary = 0
            WHERE panel_id = ?
        """, (panel_id,), commit=True)

    # Check if classification already exists
    existing = query_panels("""
        SELECT id FROM panel_classifications
        WHERE panel_id = ? AND area_id = ?
          AND (disease_category_id = ? OR (disease_category_id IS NULL AND ? IS NULL))
    """, (panel_id, area_id, disease_category_id, disease_category_id))

    if existing is not None and not existing.empty:
        # Update existing
        query_panels("""
            UPDATE panel_classifications
            SET is_primary = ?
            WHERE id = ?
        """, (1 if is_primary else 0, existing.iloc[0]['id']), commit=True)
    else:
        # Insert new
        query_panels("""
            INSERT INTO panel_classifications (id, panel_id, area_id, disease_category_id, is_primary)
            VALUES (?, ?, ?, ?, ?)
        """, (classification_id, panel_id, area_id, disease_category_id, 1 if is_primary else 0), commit=True)

    return classification_id


def add_area(name, code, description=""):
    """Add a new clinical area"""
    area_id = str(uuid.uuid4())

    # Get max display order
    result = query_panels("SELECT MAX(display_order) as max_order FROM panel_areas")
    max_order = 0
    if result is not None and not result.empty and result.iloc[0]['max_order'] is not None:
        max_order = int(result.iloc[0]['max_order'])

    query_panels("""
        INSERT INTO panel_areas (id, name, code, description, display_order)
        VALUES (?, ?, ?, ?, ?)
    """, (area_id, name, code, description, max_order + 1), commit=True)

    return area_id


def add_disease_category(name, area_id=None, description="", icd_code="", requires_patient_tracking=False):
    """Add a new disease category"""
    category_id = str(uuid.uuid4())

    query_panels("""
        INSERT INTO panel_disease_categories (id, area_id, name, description, icd_code, requires_patient_tracking)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (category_id, area_id, name, description, icd_code, 1 if requires_patient_tracking else 0), commit=True)

    return category_id


def requires_patient_tracking(area_id=None, disease_category_id=None):
    """Check if patient tracking is required for an area or disease category"""
    if disease_category_id:
        result = query_panels("""
            SELECT requires_patient_tracking
            FROM panel_disease_categories
            WHERE id = ?
        """, (disease_category_id,))

        if result is not None and not result.empty:
            return bool(result.iloc[0]['requires_patient_tracking'])

    # Check if area is Oncohematology (always requires tracking)
    if area_id:
        result = query_panels("""
            SELECT code FROM panel_areas WHERE id = ?
        """, (area_id,))

        if result is not None and not result.empty:
            return result.iloc[0]['code'] == 'ONCOHEM'

    return False
