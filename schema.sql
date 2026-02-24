PRAGMA foreign_keys = ON;

-- =============================================================================
-- StreamFlow - Complete Database Schema
-- This file is the single source of truth for a fresh installation.
-- It incorporates the base schema plus all migrations (001-004).
-- =============================================================================

-- schema_migrations: tracks which migrations have been applied
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

-- brands
CREATE TABLE IF NOT EXISTS brands (
    id TEXT PRIMARY KEY,
    name TEXT,
    team_id TEXT
);

-- cytometers (+ migration 001 columns)
CREATE TABLE IF NOT EXISTS cytometers (
    id TEXT PRIMARY KEY,
    name TEXT,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    created_at TEXT,
    team_id TEXT,
    -- migration 001
    is_default INTEGER DEFAULT 0,
    laser_configuration TEXT,
    detector_count INTEGER,
    status TEXT DEFAULT 'active',
    installation_date TEXT,
    last_maintenance_date TEXT,
    next_maintenance_due TEXT
);

-- optical_channels
CREATE TABLE IF NOT EXISTS optical_channels (
    id TEXT PRIMARY KEY,
    name TEXT,
    min_range INTEGER,
    max_range INTEGER,
    team_id TEXT
);

-- fluorochromes
CREATE TABLE IF NOT EXISTS fluorochromes (
    id TEXT PRIMARY KEY,
    name TEXT
);

-- reagents (+ migration 001 + migration 002 columns)
CREATE TABLE IF NOT EXISTS reagents (
    id TEXT PRIMARY KEY,
    name TEXT,
    fluorochrome TEXT,
    brand_id TEXT,
    catalog_number TEXT,
    clone TEXT,
    price REAL,
    team_id TEXT,
    user_id TEXT,
    -- migration 001
    target_antigen TEXT,
    -- migration 002
    catalog_price REAL,
    catalog_volume REAL
);

-- general_reagents
CREATE TABLE IF NOT EXISTS general_reagents (
    id TEXT PRIMARY KEY,
    name TEXT,
    brand_id TEXT,
    type TEXT,
    concentration TEXT,
    preparation_date TEXT,
    notes TEXT,
    created_at TEXT,
    arrival_date TEXT,
    expiration_date TEXT,
    price REAL,
    team_id TEXT,
    user_id TEXT
);

-- reagent_units (+ migration 001 + migration 002 columns)
CREATE TABLE IF NOT EXISTS reagent_units (
    id TEXT PRIMARY KEY,
    reagent_id TEXT,
    initial_volume REAL,
    arrival_date TEXT,
    expiration_date TEXT,
    status TEXT,
    lot TEXT,
    team_id TEXT,
    -- migration 001
    current_volume REAL,
    opened_date TEXT,
    closed_date TEXT,
    qc_status TEXT DEFAULT 'pending',
    qc_date TEXT,
    qc_notes TEXT,
    storage_location TEXT,
    -- migration 002
    purchase_price REAL,
    purchase_date TEXT,
    supplier_id TEXT,
    cost_per_ul REAL
);

-- general_reagent_units (+ migration 003: arrival_date)
CREATE TABLE IF NOT EXISTS general_reagent_units (
    id TEXT PRIMARY KEY,
    general_reagent_id TEXT,
    lot_number TEXT,
    expiration_date TEXT,
    location TEXT,
    status TEXT,
    volume REAL,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT,
    team_id TEXT,
    -- migration 003
    arrival_date TEXT
);

-- panels (+ migration 001 columns)
CREATE TABLE IF NOT EXISTS panels (
    id TEXT PRIMARY KEY,
    name TEXT,
    category_id TEXT,
    description TEXT,
    sample_volume REAL,
    created_at TEXT,
    status TEXT,
    cytometer_id TEXT,
    washed_sample INTEGER,
    acquisition_protocol_status TEXT,
    acquisition_protocol_name TEXT,
    acquisition_protocol_code TEXT,
    compensation_status TEXT,
    compensation_name TEXT,
    compensation_code TEXT,
    analysis_protocol_status TEXT,
    analysis_protocol_name TEXT,
    analysis_protocol_code TEXT,
    team_id TEXT,
    user_id TEXT,
    -- migration 001
    version TEXT DEFAULT '1.0.0',
    parent_panel_id TEXT,
    version_notes TEXT,
    validated_at TEXT,
    validated_by TEXT,
    clinical_indication TEXT,
    sample_type TEXT,
    estimated_cost_per_test REAL,
    estimated_time_minutes INTEGER,
    updated_at TEXT,
    created_by TEXT
);

-- panel_reagents (+ migration 001 columns)
CREATE TABLE IF NOT EXISTS panel_reagents (
    id TEXT PRIMARY KEY,
    panel_id TEXT,
    reagent_id TEXT,
    optical_channel_id TEXT,
    volume_used REAL,
    assigned_at TEXT,
    is_intracellular INTEGER,
    display_name TEXT,
    team_id TEXT,
    -- migration 001
    preferred_reagent_unit_id TEXT,
    channel_display_name TEXT,
    is_surface INTEGER DEFAULT 1,
    staining_step INTEGER DEFAULT 1,
    display_order INTEGER,
    unit_cost REAL,
    cost_per_test REAL,
    added_by TEXT
);

-- panel_general_reagents (+ migration 001 columns)
CREATE TABLE IF NOT EXISTS panel_general_reagents (
    id TEXT PRIMARY KEY,
    panel_id TEXT,
    general_reagent_id TEXT,
    volume_used REAL,
    notes TEXT,
    added_at TEXT,
    team_id TEXT,
    -- migration 001
    preferred_unit_id TEXT,
    usage_type TEXT,
    application_step INTEGER DEFAULT 1,
    is_required INTEGER DEFAULT 1,
    display_name TEXT,
    cost_per_test REAL
);

-- purchase_orders
CREATE TABLE IF NOT EXISTS purchase_orders (
    id TEXT PRIMARY KEY,
    supplier TEXT,
    total_price REAL,
    status TEXT,
    created_at TEXT,
    updated_at TEXT,
    team_id TEXT,
    user_id TEXT
);

-- purchase_order_items
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id TEXT PRIMARY KEY,
    purchase_order_id TEXT,
    reagent_id TEXT,
    quantity INTEGER,
    unit_price REAL,
    total_price REAL,
    status TEXT,
    received_quantity INTEGER,
    team_id TEXT
);

-- cytometer_optical_channels (+ migration 001 columns)
CREATE TABLE IF NOT EXISTS cytometer_optical_channels (
    id TEXT PRIMARY KEY,
    cytometer_id TEXT,
    optical_channel_id TEXT,
    associated_fluorochrome TEXT,
    team_id TEXT,
    -- migration 001
    primary_fluorochrome TEXT,
    display_order INTEGER,
    is_scatter INTEGER DEFAULT 0,
    detector_type TEXT,
    laser_wavelength INTEGER
);

-- =============================================================================
-- Migration 001: Protocol tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS acquisition_protocols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cytometer_id TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    version TEXT DEFAULT '1.0.0',
    notes TEXT,
    validated_at TEXT,
    validated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    team_id TEXT,
    FOREIGN KEY (cytometer_id) REFERENCES cytometers(id)
);

CREATE TABLE IF NOT EXISTS compensation_protocols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cytometer_id TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    version TEXT DEFAULT '1.0.0',
    notes TEXT,
    validated_at TEXT,
    validated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    team_id TEXT,
    FOREIGN KEY (cytometer_id) REFERENCES cytometers(id)
);

CREATE TABLE IF NOT EXISTS analysis_protocols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    version TEXT DEFAULT '1.0.0',
    notes TEXT,
    validated_at TEXT,
    validated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    team_id TEXT
);

-- =============================================================================
-- Migration 004: Panel categories, versioning, clinical & economic infrastructure
-- =============================================================================

-- Clinical areas (Immunology, Oncohematology, Fertility, etc.)
CREATE TABLE IF NOT EXISTS panel_areas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    code TEXT UNIQUE,
    display_order INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Disease categories
CREATE TABLE IF NOT EXISTS panel_disease_categories (
    id TEXT PRIMARY KEY,
    area_id TEXT,
    name TEXT NOT NULL,
    description TEXT,
    icd_code TEXT,
    requires_patient_tracking INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (area_id) REFERENCES panel_areas(id)
);

-- Panel ↔ area/disease classification
CREATE TABLE IF NOT EXISTS panel_classifications (
    id TEXT PRIMARY KEY,
    panel_id TEXT NOT NULL,
    area_id TEXT,
    disease_category_id TEXT,
    is_primary INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE,
    FOREIGN KEY (area_id) REFERENCES panel_areas(id),
    FOREIGN KEY (disease_category_id) REFERENCES panel_disease_categories(id)
);

-- Panel version history
CREATE TABLE IF NOT EXISTS panel_versions (
    id TEXT PRIMARY KEY,
    panel_id TEXT NOT NULL,
    version TEXT NOT NULL,
    previous_version TEXT,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    created_by TEXT,
    validation_notes TEXT,
    changes_summary TEXT,
    snapshot_json TEXT,
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE
);

-- Panel status transition log
CREATE TABLE IF NOT EXISTS panel_status_history (
    id TEXT PRIMARY KEY,
    panel_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_at TEXT DEFAULT (datetime('now')),
    changed_by TEXT,
    reason TEXT,
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE
);

-- Patient registry
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    medical_record_number TEXT UNIQUE NOT NULL,
    national_id TEXT,
    initials TEXT NOT NULL,
    date_of_birth DATE,
    age_at_registration INTEGER,
    sex TEXT CHECK(sex IN ('M', 'F', 'Other', 'Unknown')),
    referring_physician TEXT,
    referring_institution TEXT,
    registration_date TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    created_by TEXT,
    updated_at TEXT
);

-- Clinical cases
CREATE TABLE IF NOT EXISTS clinical_cases (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    case_number TEXT UNIQUE NOT NULL,
    clinical_suspicion TEXT,
    sample_date DATE NOT NULL,
    sample_type TEXT,
    referring_physician TEXT,
    disease_category_id TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'routine',
    received_at TEXT DEFAULT (datetime('now')),
    reported_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_category_id) REFERENCES panel_disease_categories(id)
);

-- Panels assigned to cases
CREATE TABLE IF NOT EXISTS case_panels (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    panel_id TEXT NOT NULL,
    run_date DATE,
    run_number TEXT,
    cytometer_id TEXT,
    operator TEXT,
    events_acquired INTEGER,
    viability_percent REAL,
    quality_flags TEXT,
    immunophenotype TEXT,
    interpretation TEXT,
    status TEXT DEFAULT 'pending',
    reagent_lots_used TEXT,
    actual_cost REAL,
    cost_calculation_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (case_id) REFERENCES clinical_cases(id) ON DELETE CASCADE,
    FOREIGN KEY (panel_id) REFERENCES panels(id),
    FOREIGN KEY (cytometer_id) REFERENCES cytometers(id)
);

-- Final diagnosis
CREATE TABLE IF NOT EXISTS case_diagnoses (
    id TEXT PRIMARY KEY,
    case_id TEXT UNIQUE NOT NULL,
    final_diagnosis TEXT NOT NULL,
    icd_code TEXT,
    disease_category_id TEXT,
    who_classification TEXT,
    fab_classification TEXT,
    correlates_with_morphology INTEGER,
    correlates_with_cytogenetics INTEGER,
    additional_findings TEXT,
    reported_by TEXT,
    reviewed_by TEXT,
    report_date DATE,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (case_id) REFERENCES clinical_cases(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_category_id) REFERENCES panel_disease_categories(id)
);

-- Panel usage log (economic tracking)
CREATE TABLE IF NOT EXISTS panel_usage_log (
    id TEXT PRIMARY KEY,
    panel_id TEXT NOT NULL,
    panel_version TEXT,
    execution_date DATE NOT NULL,
    area_id TEXT,
    case_panel_id TEXT,
    is_patient_tracked INTEGER DEFAULT 0,
    tests_count INTEGER DEFAULT 1,
    cost_per_test REAL,
    total_cost REAL,
    cost_calculation_json TEXT,
    operator TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (panel_id) REFERENCES panels(id),
    FOREIGN KEY (area_id) REFERENCES panel_areas(id),
    FOREIGN KEY (case_panel_id) REFERENCES case_panels(id)
);

-- Reagent consumption log
CREATE TABLE IF NOT EXISTS reagent_consumption_log (
    id TEXT PRIMARY KEY,
    reagent_unit_id TEXT NOT NULL,
    reagent_id TEXT NOT NULL,
    consumption_date DATE NOT NULL,
    panel_usage_log_id TEXT,
    case_panel_id TEXT,
    volume_used REAL NOT NULL,
    cost_per_ul REAL,
    total_cost REAL,
    operator TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (reagent_unit_id) REFERENCES reagent_units(id),
    FOREIGN KEY (reagent_id) REFERENCES reagents(id),
    FOREIGN KEY (panel_usage_log_id) REFERENCES panel_usage_log(id),
    FOREIGN KEY (case_panel_id) REFERENCES case_panels(id)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_panels_version ON panels(name, version);
CREATE INDEX IF NOT EXISTS idx_panels_status ON panels(status);
CREATE INDEX IF NOT EXISTS idx_panel_reagents_panel ON panel_reagents(panel_id);
CREATE INDEX IF NOT EXISTS idx_panel_reagents_channel ON panel_reagents(optical_channel_id);
CREATE INDEX IF NOT EXISTS idx_reagent_units_lot ON reagent_units(lot);
CREATE INDEX IF NOT EXISTS idx_reagent_units_expiration ON reagent_units(expiration_date);
CREATE INDEX IF NOT EXISTS idx_reagent_units_cost ON reagent_units(reagent_id, cost_per_ul, status);
CREATE INDEX IF NOT EXISTS idx_acquisition_protocol_status ON acquisition_protocols(status);
CREATE INDEX IF NOT EXISTS idx_acquisition_protocol_cytometer ON acquisition_protocols(cytometer_id);
CREATE INDEX IF NOT EXISTS idx_compensation_protocol_status ON compensation_protocols(status);
CREATE INDEX IF NOT EXISTS idx_compensation_protocol_cytometer ON compensation_protocols(cytometer_id);
CREATE INDEX IF NOT EXISTS idx_analysis_protocol_status ON analysis_protocols(status);
CREATE INDEX IF NOT EXISTS idx_panel_classifications_panel ON panel_classifications(panel_id);
CREATE INDEX IF NOT EXISTS idx_panel_classifications_area ON panel_classifications(area_id);
CREATE INDEX IF NOT EXISTS idx_panel_versions_panel ON panel_versions(panel_id);
CREATE INDEX IF NOT EXISTS idx_panel_status_history_panel ON panel_status_history(panel_id);
CREATE INDEX IF NOT EXISTS idx_clinical_cases_patient ON clinical_cases(patient_id);
CREATE INDEX IF NOT EXISTS idx_case_panels_case ON case_panels(case_id);
CREATE INDEX IF NOT EXISTS idx_case_panels_panel ON case_panels(panel_id);
CREATE INDEX IF NOT EXISTS idx_panel_usage_log_panel ON panel_usage_log(panel_id);
CREATE INDEX IF NOT EXISTS idx_panel_usage_log_date ON panel_usage_log(execution_date);
CREATE INDEX IF NOT EXISTS idx_reagent_consumption_log_date ON reagent_consumption_log(consumption_date);
CREATE INDEX IF NOT EXISTS idx_reagent_units_arrival ON reagent_units(arrival_date);
CREATE INDEX IF NOT EXISTS idx_general_units_expiration ON general_reagent_units(expiration_date);
CREATE INDEX IF NOT EXISTS idx_general_units_arrival ON general_reagent_units(arrival_date);

-- =============================================================================
-- SEED DATA: Default clinical areas and disease categories
-- =============================================================================

INSERT OR IGNORE INTO panel_areas (id, name, code, description, display_order) VALUES
    ('area-oncohem',   'Oncohematology', 'ONCOHEM', 'Hematological malignancies and disorders',        1),
    ('area-immuno',    'Immunology',     'IMMUNO',  'Immunological disorders and autoimmune diseases', 2),
    ('area-fertility', 'Fertility',      'FERT',    'Reproductive health and fertility assessment',    3),
    ('area-transplant','Transplant',     'TXPLNT',  'Pre and post-transplant monitoring',              4),
    ('area-research',  'Research',       'RSCH',    'Research and experimental protocols',             5);

INSERT OR IGNORE INTO panel_disease_categories (id, area_id, name, description, icd_code, requires_patient_tracking) VALUES
    ('disease-aml',      'area-oncohem', 'Acute Myeloid Leukemia',         'AML and related precursor neoplasms',    'C92.0', 1),
    ('disease-all',      'area-oncohem', 'Acute Lymphoblastic Leukemia',   'B-ALL and T-ALL',                        'C91.0', 1),
    ('disease-cll',      'area-oncohem', 'Chronic Lymphocytic Leukemia',   'CLL and related B-cell disorders',       'C91.1', 1),
    ('disease-myeloma',  'area-oncohem', 'Multiple Myeloma',               'Plasma cell neoplasms',                  'C90.0', 1),
    ('disease-lymphoma', 'area-oncohem', 'Lymphoma',                       'Hodgkin and Non-Hodgkin lymphomas',      'C85',   1),
    ('disease-mds',      'area-oncohem', 'Myelodysplastic Syndrome',       'MDS and related disorders',              'D46',   1);

INSERT OR IGNORE INTO panel_disease_categories (id, area_id, name, description, requires_patient_tracking) VALUES
    ('disease-autoimmune',       'area-immuno', 'Autoimmune Disorders',  'General autoimmune disease screening',          0),
    ('disease-immunodeficiency', 'area-immuno', 'Immunodeficiency',      'Primary and secondary immunodeficiencies',      0);
