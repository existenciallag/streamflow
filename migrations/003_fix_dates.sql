-- Migration 003: Fix Date Handling and Add arrival_date
-- Purpose: Add missing arrival_date column to general_reagent_units and standardize date formats
-- Date: 2026-01-24
--
-- Issues Fixed:
-- 1. general_reagent_units missing arrival_date column (causes NULL displays in Dashboard)
-- 2. Date format inconsistency (some YYYY-MM-DD, some YYYY-MM-DDTHH:MM:SS)
-- 3. No validation of date ranges

-- ============================================================================
-- PHASE 1: Add missing arrival_date to general_reagent_units
-- ============================================================================

-- Add arrival_date column
ALTER TABLE general_reagent_units ADD COLUMN arrival_date TEXT;

-- Populate with created_at as fallback (best available approximation)
UPDATE general_reagent_units
SET arrival_date = COALESCE(created_at, date('now'))
WHERE arrival_date IS NULL;

-- ============================================================================
-- PHASE 2: Standardize date format to ISO 8601 (YYYY-MM-DD)
-- ============================================================================

-- Note: SQLite doesn't have native date type, stores as TEXT
-- We'll ensure all dates are in ISO format for consistent parsing

-- Function to clean dates: remove time component if present, keep date only
-- This makes display consistent and easier to work with

-- For reagent_units
UPDATE reagent_units
SET expiration_date = date(expiration_date)
WHERE expiration_date IS NOT NULL
  AND expiration_date LIKE '%T%';  -- Has time component

UPDATE reagent_units
SET arrival_date = date(arrival_date)
WHERE arrival_date IS NOT NULL
  AND arrival_date LIKE '%T%';

UPDATE reagent_units
SET opened_date = date(opened_date)
WHERE opened_date IS NOT NULL
  AND opened_date LIKE '%T%';

UPDATE reagent_units
SET closed_date = date(closed_date)
WHERE closed_date IS NOT NULL
  AND closed_date LIKE '%T%';

UPDATE reagent_units
SET purchase_date = date(purchase_date)
WHERE purchase_date IS NOT NULL
  AND purchase_date LIKE '%T%';

-- For general_reagent_units
UPDATE general_reagent_units
SET expiration_date = date(expiration_date)
WHERE expiration_date IS NOT NULL
  AND expiration_date LIKE '%T%';

UPDATE general_reagent_units
SET arrival_date = date(arrival_date)
WHERE arrival_date IS NOT NULL
  AND arrival_date LIKE '%T%';

-- ============================================================================
-- PHASE 3: Add indexes for date-based queries (performance)
-- ============================================================================

-- Dashboard queries frequently filter by expiration_date
CREATE INDEX IF NOT EXISTS idx_reagent_units_expiration
ON reagent_units(expiration_date)
WHERE expiration_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_general_units_expiration
ON general_reagent_units(expiration_date)
WHERE expiration_date IS NOT NULL;

-- Arrival date for stock age calculations
CREATE INDEX IF NOT EXISTS idx_reagent_units_arrival
ON reagent_units(arrival_date)
WHERE arrival_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_general_units_arrival
ON general_reagent_units(arrival_date)
WHERE arrival_date IS NOT NULL;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check date format consistency:
-- SELECT COUNT(*) FROM reagent_units WHERE expiration_date LIKE '%T%';
-- Should return 0

-- Check arrival_date populated:
-- SELECT COUNT(*) FROM general_reagent_units WHERE arrival_date IS NULL;
-- Should be 0 or very low

-- Check expired units:
-- SELECT COUNT(*) FROM reagent_units WHERE expiration_date < date('now');

-- ============================================================================
-- POST-MIGRATION NOTES
-- ============================================================================

-- 1. All dates now in YYYY-MM-DD format (no time component)
-- 2. general_reagent_units now has arrival_date populated
-- 3. Indexes added for better query performance
-- 4. Dashboard should now display dates correctly

-- Future improvements:
-- - Add CHECK constraints to validate date formats on INSERT
-- - Add triggers to auto-update status when expiration_date < now
-- - Add default value for arrival_date on new inserts

-- END OF MIGRATION
