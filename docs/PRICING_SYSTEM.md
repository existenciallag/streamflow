# Dynamic Pricing System

## Overview

The streamflow laboratory management system now uses a **dynamic pricing system** that calculates panel costs in real-time from current reagent stock prices. This replaces the old fixed-cost approach where prices were stored in the database and became stale when reagent prices changed.

## Design Philosophy

### Core Principles

1. **Source of Truth**: Actual purchase prices stored at the lot (reagent_unit) level
2. **Dynamic Calculation**: Panel costs calculated on-demand from current stock
3. **No Fixed Costs**: Panels store only what reagents are needed and how much
4. **Full Traceability**: Know exactly which lot was used and what it cost

### Why This Matters for Clinical Labs

- **Real Pricing**: Different lots purchased at different times have different costs
- **Accurate Budgeting**: Cost calculations reflect your actual current inventory
- **Procurement Decisions**: Compare costs across suppliers and lots
- **Test Profitability**: Know the real cost-per-test based on what's actually in stock

## Database Schema

### Three-Tier Pricing Architecture

#### Tier 1: Catalog Reference (reagents table)
```sql
ALTER TABLE reagents ADD COLUMN catalog_price REAL;
ALTER TABLE reagents ADD COLUMN catalog_volume REAL;
```

- **Purpose**: Manufacturer's list price for reference
- **Not Used For**: Actual cost calculations
- **Example**: BD catalog lists CD34-PE at $500 for 100µL

#### Tier 2: Actual Purchase Price (reagent_units table)
```sql
ALTER TABLE reagent_units ADD COLUMN purchase_price REAL;
ALTER TABLE reagent_units ADD COLUMN purchase_date TEXT;
ALTER TABLE reagent_units ADD COLUMN supplier_id TEXT;
ALTER TABLE reagent_units ADD COLUMN cost_per_ul REAL;
```

- **Purpose**: What you actually paid for each specific vial/lot
- **This is the Source of Truth** for all cost calculations
- **Example**:
  - Lot A: Purchased from Supplier X for $450 (200µL) = $2.25/µL
  - Lot B: Purchased from Supplier Y for $380 (200µL) = $1.90/µL
  - Same reagent, different costs tracked accurately

#### Tier 3: Panel Design (panels + panel_reagents tables)
```sql
-- panels table: NO estimated_cost_per_test column used
-- panel_reagents table: NO cost_per_test or unit_cost columns used

-- Only volume requirement stored:
panel_reagents (
    volume_used REAL  -- How many µL of this reagent per test
)
```

- **Purpose**: Define the recipe (what reagents, how much)
- **No Costs Stored**: All costs calculated dynamically
- **Example**: "Use 10µL of CD34-PE per test" (cost depends on available stock)

## Cost Calculation

### Current Cost Calculation

Function: `calculate_panel_cost_current(panel_id, strategy='cheapest')`

**How it works:**

1. Get panel reagents with volume requirements from `panel_reagents`
2. For each reagent, find available units (lots) from `reagent_units`
3. Select best unit based on strategy:
   - **cheapest**: Lowest cost-per-µL (default)
   - **average**: Average cost across available lots
   - **fifo**: First-in-first-out (oldest lot first)
   - **fefo**: First-expired-first-out (use soonest-to-expire)
4. Calculate: `total_cost = Σ(volume_needed × cost_per_ul)`

**Example:**

Panel: MDS Panel v2.0
- CD34-PE: 10µL needed
- CD45-FITC: 5µL needed
- CD117-APC: 20µL needed

Available stock:
- CD34-PE Lot A: $2.25/µL (200µL available)
- CD45-FITC Lot B: $1.80/µL (500µL available)
- CD117-APC Lot C: $0.50/µL (300µL available)

Calculation (cheapest strategy):
```
CD34-PE:   10µL × $2.25/µL = $22.50
CD45-FITC:  5µL × $1.80/µL = $ 9.00
CD117-APC: 20µL × $0.50/µL = $10.00
                             -------
Total Cost:                  $41.50
```

**If stock changes** (e.g., cheaper CD34-PE lot arrives):
- New Lot D: $1.95/µL
- Panel cost automatically recalculates to $34.00

### Draft Panel Calculation

Function: `calculate_draft_panel_cost(reagent_list, strategy='cheapest')`

- Used in Panel Builder UI before panel is saved
- Same logic as `calculate_panel_cost_current` but works on in-memory reagent list
- Allows real-time cost feedback while designing panels

## User Interface

### Panel Builder

**Before (Fixed Costs):**
- Calculated cost when adding reagent
- Stored cost in database
- Never updated

**After (Dynamic Costs):**
- Shows "Est. Cost/Test: $41.50" in real-time
- Tooltip: "Calculated dynamically from current cheapest stock"
- Updates automatically when stock prices change
- No cost data saved to database

### Panels Viewer

**Before:**
- Displayed `estimated_cost_per_test` from database
- Could be months/years out of date

**After:**
- Calculates cost on page load: `$41.50 ✅`
- Warning if incomplete: `$35.00 ⚠️` (some reagents out of stock)
- Caption: "Calculated from current cheapest stock. Cost updates when reagent prices change."

## Migration

### Migration 002: Dynamic Pricing

File: `migrations/002_dynamic_pricing.sql`

**What it does:**

1. Adds price columns to `reagent_units`
2. Migrates existing `reagents.price` to all reagent units as `purchase_price`
3. Calculates `cost_per_ul` for each unit
4. Adds `catalog_price` to reagents for reference
5. Nulls out deprecated fixed cost columns

**Running the migration:**

```bash
python3 run_pricing_migration.py
```

**Safety:**
- Creates automatic backup before running
- Idempotent (can run multiple times safely)
- Validates results after migration

## API Reference

### Core Functions

#### `calculate_panel_cost_current(panel_id, strategy='cheapest')`

Calculate current panel cost from database.

**Parameters:**
- `panel_id` (str): UUID of the panel
- `strategy` (str): 'cheapest', 'average', 'fifo', 'fefo'

**Returns:**
```python
{
    'panel_id': str,
    'panel_name': str,
    'total_cost': float,
    'breakdown': [
        {
            'reagent': str,
            'volume_needed': float,
            'using_lot': str,
            'cost_per_ul': float,
            'reagent_cost': float,
            'status': 'available' | 'out_of_stock'
        },
        ...
    ],
    'warnings': [str, ...],
    'is_complete': bool,
    'calculated_at': str (ISO datetime)
}
```

#### `calculate_draft_panel_cost(reagent_list, strategy='cheapest')`

Calculate cost for unsaved panel.

**Parameters:**
- `reagent_list` (list): List of dicts with keys:
  - `reagent_id`: UUID
  - `reagent_name`: Display name
  - `volume_per_test`: µL needed
- `strategy` (str): Cost selection strategy

**Returns:** Same structure as `calculate_panel_cost_current`

#### `get_panel_cost_summary(panel_id, strategy='cheapest')`

Get formatted text summary.

**Returns:** String like:
```
✅ MDS Panel v2.0
Total Cost: $41.50 (cheapest strategy)
Status: Complete (3/3 reagents available)
```

#### `get_panel_cost_breakdown(panel_id, strategy='cheapest')`

Get detailed formatted breakdown.

**Returns:** Multi-line string with per-reagent details.

## Future: Historical Pricing (Assay Tracking)

### Phase 5: When to Implement

When adding patient/sample tracking and assay execution.

### Design: Assay-Based Snapshots

```sql
CREATE TABLE assays (
    id TEXT PRIMARY KEY,
    patient_id TEXT,
    panel_id TEXT,
    performed_at TIMESTAMP,
    technician TEXT
);

CREATE TABLE assay_reagents_used (
    id TEXT PRIMARY KEY,
    assay_id TEXT,
    reagent_unit_id TEXT,
    volume_used REAL,
    cost_per_ul_at_time REAL,  -- SNAPSHOT
    total_cost REAL,            -- SNAPSHOT
    lot_number TEXT,            -- Denormalized for audit
    FOREIGN KEY(assay_id) REFERENCES assays(id),
    FOREIGN KEY(reagent_unit_id) REFERENCES reagent_units(id)
);
```

### Why Snapshots?

- **Immutable record** of what test actually cost when performed
- **Billing accuracy**: Charge patient based on actual costs
- **Audit trail**: Know exact cost even if vial later deleted
- **Trend analysis**: See how costs changed over time

### Usage Example

```python
# When performing assay
def perform_assay(panel_id, patient_id):
    # Get current cost
    cost_calc = calculate_panel_cost_current(panel_id, 'fifo')

    # Create assay record
    assay_id = create_assay(patient_id, panel_id)

    # SNAPSHOT: Save what was actually used
    for item in cost_calc['breakdown']:
        save_assay_reagent(
            assay_id=assay_id,
            reagent_unit_id=item['reagent_unit_id'],
            volume_used=item['volume_needed'],
            cost_per_ul_at_time=item['cost_per_ul'],  # Historical snapshot
            total_cost=item['reagent_cost']
        )

    return assay_id

# Later: Get what test actually cost
def get_assay_actual_cost(assay_id):
    return query("""
        SELECT SUM(total_cost)
        FROM assay_reagents_used
        WHERE assay_id = ?
    """, assay_id)[0]
```

## Best Practices

### For Laboratory Managers

1. **Update Purchase Prices**: When receiving new lots, enter actual purchase price
2. **Supplier Comparison**: Track which supplier provides better pricing
3. **Cost Trends**: Review panel costs monthly to track budget impact
4. **Stock Strategy**: Use 'cheapest' for cost optimization, 'fefo' for expiration management

### For System Administrators

1. **Backup Before Migration**: Run `run_pricing_migration.py` creates automatic backups
2. **Verify Migration**: Check sample data after migration
3. **Monitor Calculations**: Dynamic calculations are fast but cached in UI session
4. **Future-Proof**: Design supports assay tracking when ready

### For Developers

1. **Never Store Costs**: Always calculate dynamically
2. **Use Existing Functions**: Import from `utils.pricing`
3. **Handle Missing Data**: Check `is_complete` flag in results
4. **Display Warnings**: Show user when reagents are unavailable

## Troubleshooting

### "Panel cost shows $0.00"

**Cause:** No purchase prices set for reagent units

**Fix:**
```sql
-- Check which reagents lack prices
SELECT r.name, COUNT(ru.id) as units,
       SUM(CASE WHEN ru.purchase_price IS NULL THEN 1 ELSE 0 END) as no_price
FROM reagents r
JOIN reagent_units ru ON ru.reagent_id = r.id
GROUP BY r.id
HAVING no_price > 0;

-- Update prices from catalog
UPDATE reagent_units
SET purchase_price = (SELECT catalog_price FROM reagents WHERE id = reagent_units.reagent_id)
WHERE purchase_price IS NULL;
```

### "Panel shows ⚠️ warning"

**Cause:** Some reagents unavailable or out of stock

**Debug:**
```python
result = calculate_panel_cost_current(panel_id)
print(result['warnings'])  # See which reagents are missing
```

### "Cost calculation seems slow"

**Cause:** Calculating for many panels in a loop

**Fix:** Cache results in session or use database query batching

## Summary

The dynamic pricing system provides:

✅ **Accurate costs** based on real purchase prices
✅ **Always current** - updates when stock prices change
✅ **Full traceability** - know which lot, what cost
✅ **Strategic flexibility** - choose cheapest, FIFO, FEFO
✅ **Future-ready** - supports assay-based historical tracking

No more stale pricing data. Every cost calculation reflects your actual current inventory.
