-- Migration: Panel Builder v2 - Clinical Grade Traceability
-- Date: 2026-01-23
-- Description: Adds versioning, protocol management, cost tracking, and lot traceability

PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. CREATE NEW PROTOCOL TABLES (SIMPLIFIED)
-- ============================================================

-- Acquisition Protocols: stores instrument acquisition settings by name only
CREATE TABLE IF NOT EXISTS acquisition_protocols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cytometer_id TEXT NOT NULL,

    -- Status & Versioning
    status TEXT DEFAULT 'draft',              -- draft | validated | archived
    version TEXT DEFAULT '1.0.0',

    -- Documentation
    notes TEXT,                                -- Free text description of settings

    -- Validation
    validated_at TEXT,
    validated_by TEXT,

    -- Audit
    created_at TEXT NOT NULL,
    updated_at TEXT,
    team_id TEXT,

    FOREIGN KEY (cytometer_id) REFERENCES cytometers(id)
);

CREATE INDEX idx_acquisition_protocol_status ON acquisition_protocols(status);
CREATE INDEX idx_acquisition_protocol_cytometer ON acquisition_protocols(cytometer_id);

-- Compensation Protocols: stores compensation matrix by name only
CREATE TABLE IF NOT EXISTS compensation_protocols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cytometer_id TEXT NOT NULL,

    -- Status & Versioning
    status TEXT DEFAULT 'draft',
    version TEXT DEFAULT '1.0.0',

    -- Documentation
    notes TEXT,                                -- Description of controls used, method, etc.

    -- Validation
    validated_at TEXT,
    validated_by TEXT,

    -- Audit
    created_at TEXT NOT NULL,
    updated_at TEXT,
    team_id TEXT,

    FOREIGN KEY (cytometer_id) REFERENCES cytometers(id)
);

CREATE INDEX idx_compensation_protocol_status ON compensation_protocols(status);
CREATE INDEX idx_compensation_protocol_cytometer ON compensation_protocols(cytometer_id);

-- Analysis Protocols: stores gating/analysis strategy by name only
CREATE TABLE IF NOT EXISTS analysis_protocols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,

    -- Status & Versioning
    status TEXT DEFAULT 'draft',
    version TEXT DEFAULT '1.0.0',

    -- Documentation
    notes TEXT,                                -- Description of gating strategy, populations, etc.

    -- Validation
    validated_at TEXT,
    validated_by TEXT,

    -- Audit
    created_at TEXT NOT NULL,
    updated_at TEXT,
    team_id TEXT
);

CREATE INDEX idx_analysis_protocol_status ON analysis_protocols(status);


-- ============================================================
-- 2. ALTER EXISTING TABLES - PANELS
-- ============================================================

-- Add versioning columns to panels
ALTER TABLE panels ADD COLUMN version TEXT DEFAULT '1.0.0';
ALTER TABLE panels ADD COLUMN parent_panel_id TEXT;  -- Points to previous version
ALTER TABLE panels ADD COLUMN version_notes TEXT;     -- "Added CD69, removed CD38"

-- Add validation columns
ALTER TABLE panels ADD COLUMN validated_at TEXT;
ALTER TABLE panels ADD COLUMN validated_by TEXT;

-- Add clinical metadata
ALTER TABLE panels ADD COLUMN clinical_indication TEXT;  -- "Lymphocyte subset analysis"
ALTER TABLE panels ADD COLUMN sample_type TEXT;          -- "Whole Blood", "Bone Marrow"

-- Add cost tracking
ALTER TABLE panels ADD COLUMN estimated_cost_per_test REAL;  -- Auto-calculated
ALTER TABLE panels ADD COLUMN estimated_time_minutes INTEGER;

-- Add audit columns
ALTER TABLE panels ADD COLUMN updated_at TEXT;
ALTER TABLE panels ADD COLUMN created_by TEXT;

-- Add foreign key for parent panel (SQLite doesn't support ALTER TABLE ADD CONSTRAINT,
-- so this will be enforced in application logic)


-- ============================================================
-- 3. ALTER EXISTING TABLES - PANEL_REAGENTS
-- ============================================================

-- Link to specific reagent lot
ALTER TABLE panel_reagents ADD COLUMN preferred_reagent_unit_id TEXT;  -- FK to reagent_units

-- Semantic channel name for display
ALTER TABLE panel_reagents ADD COLUMN channel_display_name TEXT;  -- "PE", "V450", "B585/42"

-- Multi-step staining support
ALTER TABLE panel_reagents ADD COLUMN is_surface INTEGER DEFAULT 1;
ALTER TABLE panel_reagents ADD COLUMN staining_step INTEGER DEFAULT 1;

-- Display customization
ALTER TABLE panel_reagents ADD COLUMN display_order INTEGER;

-- Cost tracking
ALTER TABLE panel_reagents ADD COLUMN unit_cost REAL;           -- Cost per µL
ALTER TABLE panel_reagents ADD COLUMN cost_per_test REAL;       -- volume_used × unit_cost

-- Audit
ALTER TABLE panel_reagents ADD COLUMN added_by TEXT;


-- ============================================================
-- 4. ALTER EXISTING TABLES - PANEL_GENERAL_REAGENTS
-- ============================================================

ALTER TABLE panel_general_reagents ADD COLUMN preferred_unit_id TEXT;  -- FK to general_reagent_units
ALTER TABLE panel_general_reagents ADD COLUMN usage_type TEXT;         -- "fixation", "lysis", "wash"
ALTER TABLE panel_general_reagents ADD COLUMN application_step INTEGER DEFAULT 1;
ALTER TABLE panel_general_reagents ADD COLUMN is_required INTEGER DEFAULT 1;
ALTER TABLE panel_general_reagents ADD COLUMN display_name TEXT;
ALTER TABLE panel_general_reagents ADD COLUMN cost_per_test REAL;


-- ============================================================
-- 5. ALTER EXISTING TABLES - CYTOMETERS
-- ============================================================

ALTER TABLE cytometers ADD COLUMN is_default INTEGER DEFAULT 0;
ALTER TABLE cytometers ADD COLUMN laser_configuration TEXT;
ALTER TABLE cytometers ADD COLUMN detector_count INTEGER;
ALTER TABLE cytometers ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE cytometers ADD COLUMN installation_date TEXT;
ALTER TABLE cytometers ADD COLUMN last_maintenance_date TEXT;
ALTER TABLE cytometers ADD COLUMN next_maintenance_due TEXT;


-- ============================================================
-- 6. ALTER EXISTING TABLES - REAGENTS
-- ============================================================

ALTER TABLE reagents ADD COLUMN target_antigen TEXT;  -- "CD3", "CD4" (separate from fluorochrome)


-- ============================================================
-- 7. ALTER EXISTING TABLES - REAGENT_UNITS
-- ============================================================

ALTER TABLE reagent_units ADD COLUMN current_volume REAL;        -- Remaining volume
ALTER TABLE reagent_units ADD COLUMN opened_date TEXT;
ALTER TABLE reagent_units ADD COLUMN closed_date TEXT;
ALTER TABLE reagent_units ADD COLUMN qc_status TEXT DEFAULT 'pending';
ALTER TABLE reagent_units ADD COLUMN qc_date TEXT;
ALTER TABLE reagent_units ADD COLUMN qc_notes TEXT;
ALTER TABLE reagent_units ADD COLUMN storage_location TEXT;


-- ============================================================
-- 8. ALTER EXISTING TABLES - CYTOMETER_OPTICAL_CHANNELS
-- ============================================================

ALTER TABLE cytometer_optical_channels ADD COLUMN primary_fluorochrome TEXT;
ALTER TABLE cytometer_optical_channels ADD COLUMN display_order INTEGER;
ALTER TABLE cytometer_optical_channels ADD COLUMN is_scatter INTEGER DEFAULT 0;
ALTER TABLE cytometer_optical_channels ADD COLUMN detector_type TEXT;
ALTER TABLE cytometer_optical_channels ADD COLUMN laser_wavelength INTEGER;


-- ============================================================
-- 9. CREATE INDEXES FOR PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_panels_version ON panels(name, version);
CREATE INDEX IF NOT EXISTS idx_panels_status ON panels(status);
CREATE INDEX IF NOT EXISTS idx_panel_reagents_panel ON panel_reagents(panel_id);
CREATE INDEX IF NOT EXISTS idx_panel_reagents_channel ON panel_reagents(optical_channel_id);
CREATE INDEX IF NOT EXISTS idx_reagent_units_lot ON reagent_units(lot);
CREATE INDEX IF NOT EXISTS idx_reagent_units_expiration ON reagent_units(expiration_date);


-- ============================================================
-- 10. UPDATE EXISTING DATA - SET DEFAULT VALUES
-- ============================================================

-- Set current_volume = initial_volume for existing reagent units
UPDATE reagent_units
SET current_volume = initial_volume
WHERE current_volume IS NULL;

-- Set default version for existing panels
UPDATE panels
SET version = '1.0.0'
WHERE version IS NULL OR version = '';

-- Extract target antigen from reagent name (heuristic: first word before space)
UPDATE reagents
SET target_antigen = CASE
    WHEN name LIKE '% %' THEN SUBSTR(name, 1, INSTR(name, ' ') - 1)
    ELSE name
END
WHERE target_antigen IS NULL;


-- ============================================================
-- 11. MIGRATION COMPLETE
-- ============================================================

-- Log migration completion
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

INSERT INTO schema_migrations (migration_name, applied_at)
VALUES ('001_panel_builder_v2', datetime('now'));
