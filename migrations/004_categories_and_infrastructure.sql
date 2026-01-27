-- Migration 004: Categories, Versioning, and Clinical/Economic Infrastructure
-- This migration creates the foundation for:
-- 1. Panel categories (areas + disease categories)
-- 2. Panel version history and status management
-- 3. Clinical section (patients, cases, results)
-- 4. Economic section (usage tracking, cost analysis)

-- =============================================================================
-- PANEL CATEGORIES & CLASSIFICATION
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

-- Disease categories (custom, manageable)
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

-- Link panels to both areas and diseases
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

-- =============================================================================
-- PANEL VERSIONING & STATUS MANAGEMENT
-- =============================================================================

-- Version history tracking
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

-- Status transition log
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

-- =============================================================================
-- CLINICAL SECTION - ONCOHEMATOLOGY PATIENTS
-- =============================================================================

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

-- =============================================================================
-- ECONOMIC SECTION - USAGE TRACKING
-- =============================================================================

-- Panel usage tracking
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

-- Reagent consumption tracking
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
-- INDEXES FOR PERFORMANCE
-- =============================================================================

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

-- =============================================================================
-- SEED DATA: DEFAULT AREAS AND CATEGORIES
-- =============================================================================

-- Insert default clinical areas
INSERT OR IGNORE INTO panel_areas (id, name, code, description, display_order) VALUES
('area-oncohem', 'Oncohematology', 'ONCOHEM', 'Hematological malignancies and disorders', 1),
('area-immuno', 'Immunology', 'IMMUNO', 'Immunological disorders and autoimmune diseases', 2),
('area-fertility', 'Fertility', 'FERT', 'Reproductive health and fertility assessment', 3),
('area-transplant', 'Transplant', 'TXPLNT', 'Pre and post-transplant monitoring', 4),
('area-research', 'Research', 'RSCH', 'Research and experimental protocols', 5);

-- Insert default disease categories for Oncohematology
INSERT OR IGNORE INTO panel_disease_categories (id, area_id, name, description, icd_code, requires_patient_tracking) VALUES
('disease-aml', 'area-oncohem', 'Acute Myeloid Leukemia', 'AML and related precursor neoplasms', 'C92.0', 1),
('disease-all', 'area-oncohem', 'Acute Lymphoblastic Leukemia', 'B-ALL and T-ALL', 'C91.0', 1),
('disease-cll', 'area-oncohem', 'Chronic Lymphocytic Leukemia', 'CLL and related B-cell disorders', 'C91.1', 1),
('disease-myeloma', 'area-oncohem', 'Multiple Myeloma', 'Plasma cell neoplasms', 'C90.0', 1),
('disease-lymphoma', 'area-oncohem', 'Lymphoma', 'Hodgkin and Non-Hodgkin lymphomas', 'C85', 1),
('disease-mds', 'area-oncohem', 'Myelodysplastic Syndrome', 'MDS and related disorders', 'D46', 1);

-- Insert immunology categories
INSERT OR IGNORE INTO panel_disease_categories (id, area_id, name, description, requires_patient_tracking) VALUES
('disease-autoimmune', 'area-immuno', 'Autoimmune Disorders', 'General autoimmune disease screening', 0),
('disease-immunodeficiency', 'area-immuno', 'Immunodeficiency', 'Primary and secondary immunodeficiencies', 0);

-- =============================================================================
-- FIX EXISTING DATA: Standardize panel status values
-- =============================================================================

-- Update existing panels with wrong status vocabulary
UPDATE panels SET status = 'draft' WHERE status IS NULL OR status = '';
UPDATE panels SET status = 'active' WHERE LOWER(status) = 'active' AND status != 'active';
UPDATE panels SET status = 'validated' WHERE LOWER(status) = 'validated';
UPDATE panels SET status = 'archived' WHERE LOWER(status) IN ('archived', 'deprecated');

-- Create initial version records for existing panels
INSERT INTO panel_versions (id, panel_id, version, status, created_at, changes_summary)
SELECT
    'ver-' || p.id || '-initial',
    p.id,
    COALESCE(p.version, '1.0.0'),
    COALESCE(p.status, 'draft'),
    COALESCE(p.created_at, datetime('now')),
    'Initial version from migration'
FROM panels p
WHERE NOT EXISTS (SELECT 1 FROM panel_versions WHERE panel_id = p.id);

-- Create initial status history for existing panels
INSERT INTO panel_status_history (id, panel_id, from_status, to_status, changed_at, reason)
SELECT
    'status-' || p.id || '-initial',
    p.id,
    NULL,
    COALESCE(p.status, 'draft'),
    COALESCE(p.created_at, datetime('now')),
    'Initial status from migration'
FROM panels p
WHERE NOT EXISTS (SELECT 1 FROM panel_status_history WHERE panel_id = p.id);
