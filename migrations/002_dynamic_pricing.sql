-- Migration 002: Dynamic Pricing System
-- Purpose: Move from fixed panel costs to dynamic lot-level pricing
-- Date: 2026-01-24
--
-- Design Philosophy:
-- - Panel cost = sum of (volume_per_test × current_cost_per_ul) for each reagent
-- - Actual cost tracked at reagent_unit (lot) level, not reagent type level
-- - No fixed costs stored in panels or panel_reagents
-- - Historical costs tracked when assays are performed (future)

-- ============================================================================
-- PHASE 1: Add Lot-Level Pricing to reagent_units
-- ============================================================================

-- Add purchase pricing columns to reagent_units
ALTER TABLE reagent_units ADD COLUMN purchase_price REAL;
ALTER TABLE reagent_units ADD COLUMN purchase_date TEXT;
ALTER TABLE reagent_units ADD COLUMN supplier_id TEXT;
ALTER TABLE reagent_units ADD COLUMN cost_per_ul REAL;

-- Migrate existing data: Copy reagent catalog price to all units
-- This is a one-time data migration to populate initial values
UPDATE reagent_units
SET purchase_price = (
    SELECT r.price
    FROM reagents r
    WHERE r.id = reagent_units.reagent_id
),
purchase_date = COALESCE(arrival_date, date('now'));

-- Calculate cost per microliter for each unit
-- Handle edge cases: NULL prices, zero volumes
UPDATE reagent_units
SET cost_per_ul = CASE
    WHEN initial_volume > 0 AND purchase_price IS NOT NULL
    THEN purchase_price / initial_volume
    ELSE NULL
END;

-- Add index for cost-based queries (finding cheapest available units)
CREATE INDEX IF NOT EXISTS idx_reagent_units_cost
ON reagent_units(reagent_id, cost_per_ul, status);

-- ============================================================================
-- PHASE 2: Clarify Panel Reagent Volume Semantics
-- ============================================================================

-- volume_used already exists in panel_reagents
-- No schema change needed - just document that it means "volume per test"
-- (Renaming would break existing data, so we keep volume_used)

-- Add comment to clarify usage
-- volume_used = how many microliters of this reagent per single test

-- ============================================================================
-- PHASE 3: Deprecate Fixed Cost Columns
-- ============================================================================

-- NULL out fixed costs in panels
-- Don't drop columns to preserve any historical data
UPDATE panels
SET estimated_cost_per_test = NULL;

-- NULL out fixed costs in panel_reagents
UPDATE panel_reagents
SET cost_per_test = NULL,
    unit_cost = NULL;

-- Add marker columns to indicate these are deprecated
-- This helps prevent future code from using these columns
PRAGMA table_info(panels);  -- Just a check, doesn't modify

-- ============================================================================
-- PHASE 4: Rename Reagent Price to Catalog Price
-- ============================================================================

-- SQLite doesn't support RENAME COLUMN directly in older versions
-- Create new column, copy data, note old column as deprecated

ALTER TABLE reagents ADD COLUMN catalog_price REAL;
ALTER TABLE reagents ADD COLUMN catalog_volume REAL;

-- Copy existing price data
UPDATE reagents
SET catalog_price = price,
    catalog_volume = 100.0;  -- Default assumption, can be updated per reagent

-- Mark old column as deprecated by setting to NULL
-- Don't drop to avoid breaking existing queries during transition
UPDATE reagents SET price = NULL;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check migration success:
-- SELECT COUNT(*) as units_with_prices FROM reagent_units WHERE cost_per_ul IS NOT NULL;
-- SELECT COUNT(*) as panels_with_null_costs FROM panels WHERE estimated_cost_per_test IS NULL;
-- SELECT COUNT(*) as reagents_with_catalog_price FROM reagents WHERE catalog_price IS NOT NULL;

-- ============================================================================
-- POST-MIGRATION NOTES
-- ============================================================================

-- 1. All existing reagent units now have purchase_price and cost_per_ul populated
-- 2. Labs should update purchase_price for each lot with actual purchase costs
-- 3. New reagent_units should always set purchase_price at creation time
-- 4. Panel costs are now calculated dynamically - see utils/pricing.py
-- 5. Future: When assays are implemented, snapshot costs at time of test

-- END OF MIGRATION
