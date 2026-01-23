# Panel Builder v2.0 - Clinical Grade Implementation

**Date:** 2026-01-23
**Phase:** 1+2 Complete
**Status:** Ready for Testing

## Summary

Complete reimplementation of the Panel Builder module with clinical-grade traceability, split-view UI, semantic names throughout, and full cost tracking.

---

## Changes Implemented

### 1. Database Schema Enhancements

**New Tables Created:**
- `acquisition_protocols` - Stores acquisition settings by name (simplified, no complex JSON)
- `compensation_protocols` - Stores compensation matrix references by name
- `analysis_protocols` - Stores gating strategy references by name
- `schema_migrations` - Tracks applied migrations

**Enhanced Existing Tables:**

**panels:**
- `version` (TEXT) - Semantic versioning (1.0.0)
- `parent_panel_id` (TEXT) - Link to previous version
- `version_notes` (TEXT) - Change description
- `validated_at` (TEXT) - Validation timestamp
- `validated_by` (TEXT) - Validator identity
- `clinical_indication` (TEXT) - Clinical use case
- `sample_type` (TEXT) - Specimen type (Whole Blood, etc.)
- `estimated_cost_per_test` (REAL) - Auto-calculated cost
- `estimated_time_minutes` (INTEGER) - Workflow time
- `updated_at` (TEXT) - Last modification
- `created_by` (TEXT) - Creator identity

**panel_reagents:**
- `preferred_reagent_unit_id` (TEXT) - Link to specific lot
- `channel_display_name` (TEXT) - Semantic name (e.g., "PE", "B585/42")
- `is_surface` (INTEGER) - Surface marker flag
- `staining_step` (INTEGER) - Multi-step staining order
- `display_order` (INTEGER) - UI display sequence
- `unit_cost` (REAL) - Cost per µL
- `cost_per_test` (REAL) - Calculated cost for this reagent
- `added_by` (TEXT) - Who added it

**panel_general_reagents:**
- `preferred_unit_id` (TEXT) - Link to specific lot
- `usage_type` (TEXT) - fixation, lysis, wash, etc.
- `application_step` (INTEGER) - Workflow sequence
- `is_required` (INTEGER) - Mandatory flag
- `display_name` (TEXT) - Custom name
- `cost_per_test` (REAL) - Cost contribution

**cytometers:**
- `is_default` (INTEGER) - Default selection flag
- `laser_configuration` (TEXT) - Laser specs
- `detector_count` (INTEGER) - Number of PMTs/APDs
- `status` (TEXT) - active | maintenance | decommissioned
- `installation_date` (TEXT)
- `last_maintenance_date` (TEXT)
- `next_maintenance_due` (TEXT)

**reagents:**
- `target_antigen` (TEXT) - Marker name (CD3, CD4, etc.) separate from fluorochrome

**reagent_units:**
- `current_volume` (REAL) - Remaining volume (decremented on use)
- `opened_date` (TEXT) - First use date
- `closed_date` (TEXT) - Exhaustion/disposal date
- `qc_status` (TEXT) - pending | passed | failed
- `qc_date` (TEXT) - QC timestamp
- `qc_notes` (TEXT) - QC observations
- `storage_location` (TEXT) - Physical location

**cytometer_optical_channels:**
- `primary_fluorochrome` (TEXT) - Main fluorochrome for this channel
- `display_order` (INTEGER) - UI ordering
- `is_scatter` (INTEGER) - Is FSC/SSC?
- `detector_type` (TEXT) - PMT, APD, SiPM
- `laser_wavelength` (INTEGER) - nm

### 2. Migration System

**Files Created:**
- `migrations/001_panel_builder_v2.sql` - Complete schema migration
- `run_migration.py` - Migration runner with backup and verification

**Features:**
- Automatic database backup before migration
- Safe rollback on failure
- Duplicate column detection (idempotent)
- Post-migration verification checks
- Automatic data population (channel names, default cytometer, sample protocols)

**Migration Results:**
- ✅ 3 new protocol tables created
- ✅ 50+ new columns added across 8 tables
- ✅ CytoFLEX set as default cytometer
- ✅ 106 existing panel reagents updated with channel display names
- ✅ 3 sample protocols created for immediate use

### 3. Panel Builder Complete Rewrite

**File:** `ui/panel_builder.py` (637 lines)

**New Architecture:**

**Split-View Layout:**
- **Left Panel:** Antibody selection with search and filters
- **Right Panel:** Live panel composition with cost tracking

**Key Features:**

1. **Semantic Names Everywhere**
   - Channel names: "PE", "B585/42", "V450/45" (NEVER show IDs)
   - Reagent names: "CD3 APC-H7 (SK7)"
   - Cytometer: "CytoFLEX" (not UUID)
   - All database IDs hidden from user

2. **CytoFLEX Default**
   - Automatically selects CytoFLEX on page load
   - Uses `is_default` flag in database
   - Fallback: CytoFLEX by name → first cytometer

3. **Intelligent Channel Assignment**
   - Auto-suggests channel based on fluorochrome
   - Shows "✓ Suggested: PE" with confidence
   - Manual override if no automatic match
   - Warns if channel already in use (duplicate detection)

4. **Real-Time Cost Calculation**
   - Cost per antibody: `volume × (price / 100µL)`
   - Panel total cost displayed prominently
   - Updates live as reagents are added/removed
   - Stored in database for historical tracking

5. **Clinical Metadata Capture**
   - Panel name (required)
   - Clinical indication (free text)
   - Sample type (dropdown: Whole Blood, Bone Marrow, CSF, Tissue, Other)
   - Sample volume (µL, required)
   - Pre-washed sample flag
   - Description

6. **Protocol Integration**
   - Acquisition protocol dropdown (filtered by cytometer)
   - Compensation protocol dropdown (filtered by cytometer)
   - Analysis protocol dropdown (all)
   - Shows version and validation status (✓ for validated)

7. **Multi-Step Staining Support**
   - Staining step field (1-5)
   - Intracellular checkbox
   - Surface/Intracellular tracking
   - Enables complex protocols (surface → fix → permeabilize → intracellular)

8. **Stock Availability**
   - Shows available vial count per reagent
   - Alerts if no stock available
   - Shows earliest expiration date
   - Prevents adding reagents with zero stock

9. **Panel Composition View**
   - Sorted by channel name (V450, V525, B525, B585, ...)
   - Visual table with:
     - Channel
     - Marker (display name)
     - Volume (µL)
     - Staining step
     - Intracellular flag (✓)
     - Cost per test
   - Multi-select for deletion
   - Summary metrics: # antibodies, # general reagents, total cost

10. **Validation on Save**
    - Panel name required
    - Sample type required
    - Sample volume > 0
    - At least one antibody required
    - Clear error messages

11. **Session State Management**
    - Draft saved in session state
    - Survives page interactions
    - Cleared on successful save or explicit clear
    - No data loss during editing

### 4. Helper Functions (New)

**Utility Functions:**
- `get_default_cytometer()` - Intelligent cytometer selection
- `get_available_channels(cytometer_id)` - Semantic channel list
- `get_reagents_with_details()` - Full reagent catalog with stock
- `get_suggested_channel(cytometer_id, fluorochrome)` - Smart channel matching
- `calculate_panel_cost(panel_reagents)` - Real-time cost computation
- `render_antibody_card(ab, cytometer_id, key_prefix)` - Antibody selection UI component
- `render_panel_composition(panel_reagents, panel_general_reagents)` - Panel preview

**All Functions:**
- Use semantic names in queries and returns
- Never expose UUIDs to caller
- Include comprehensive error handling
- Documented with docstrings

---

## Design Decisions

### 1. Simplified Protocol Storage

**Decision:** Store protocol references by name/version only, NOT full JSON schemas.

**Rationale:**
- User requirement: "only must save the name, status, and changes"
- Simpler data model for single-user system
- Protocols documented externally (SOPs, instrument software)
- Full traceability via name + version + notes
- Future: Can add PDF attachment for protocol documents

**Implementation:**
- `acquisition_protocols`: name, version, status, notes
- `compensation_protocols`: name, version, status, notes
- `analysis_protocols`: name, version, status, notes

### 2. Automatic Versioning

**Decision:** Automatic versioning on edit (1.0.0 → 1.0.1).

**Rationale:**
- User requirement: "i want automatic versioning"
- Prevents manual version conflicts
- Enforces immutability of validated panels
- Semantic versioning allows major/minor/patch changes
- Future: Implement auto-increment logic on panel edit

**Current State:**
- Version field exists in database
- Defaults to "1.0.0"
- Edit workflow not yet implemented (Phase 3)

### 3. Channel Display Names Stored

**Decision:** Store `channel_display_name` in `panel_reagents` table.

**Rationale:**
- Panels must be reproducible years later
- Channel configurations might change (instrument upgrade, recalibration)
- Storing "PE" or "B585/42" ensures panel worksheets remain accurate
- Trade-off: Slight denormalization for guaranteed traceability

### 4. CytoFLEX as Default

**Decision:** Flag-based default cytometer system, set to CytoFLEX.

**Rationale:**
- User requirement: "CytoFLEX as default cytometer"
- Single-user lab likely has one primary instrument
- `is_default` flag allows easy future changes
- Multiple fallbacks ensure robust selection

### 5. Cost Calculation Inline

**Decision:** Calculate and store cost at panel creation time.

**Rationale:**
- Reagent prices change over time
- Historical panels must show cost *at the time of creation*
- Enables profitability analysis without re-calculation
- Trade-off: Denormalized but accurate historical data

### 6. Lot Traceability (Prepared, Not Enforced)

**Decision:** Add `preferred_reagent_unit_id` field but don't enforce yet.

**Rationale:**
- Clinical requirement: Know exact lot used in test
- Phase 1+2: Panel *design* phase (abstract reagents)
- Phase 5: Panel *execution* phase (specific lots)
- Future: When running a panel, system prompts for lot selection
- Database ready for full traceability when patient tracking added

---

## Database Changes Summary

**Tables Added:** 4
- acquisition_protocols
- compensation_protocols
- analysis_protocols
- schema_migrations

**Tables Modified:** 8
- panels (17 new columns)
- panel_reagents (9 new columns)
- panel_general_reagents (6 new columns)
- cytometers (7 new columns)
- reagents (1 new column)
- reagent_units (7 new columns)
- cytometer_optical_channels (5 new columns)

**Indexes Added:** 8
- Panel versioning lookup
- Status filtering
- Lot number search
- Expiration tracking
- Protocol lookups

**Total New Columns:** 52

---

## Testing Instructions

### 1. Verify Migration

```bash
# Check migration was applied
sqlite3 db/inventory.db "SELECT * FROM schema_migrations;"

# Verify new tables exist
sqlite3 db/inventory.db ".tables" | grep protocol

# Check CytoFLEX is default
sqlite3 db/inventory.db "SELECT name, is_default FROM cytometers;"

# Verify column additions
sqlite3 db/inventory.db "PRAGMA table_info(panels);" | grep version
```

### 2. Start Application

```bash
streamlit run app.py
```

### 3. Test Panel Builder

**Navigate to:** Panel Builder (sidebar)

**Test Checklist:**

- [ ] **Metadata Section**
  - [ ] Panel name input works
  - [ ] Clinical indication input works
  - [ ] Sample type dropdown shows 5 options
  - [ ] Sample volume accepts numeric input
  - [ ] Pre-washed checkbox toggles
  - [ ] Description text area accepts multi-line text

- [ ] **Cytometer Selection**
  - [ ] CytoFLEX is pre-selected
  - [ ] Dropdown shows "Cytoflex" (not UUID)
  - [ ] Info message shows "Using CytoFLEX"

- [ ] **Protocol Selection**
  - [ ] Acquisition protocol dropdown shows sample protocol
  - [ ] Compensation protocol dropdown shows sample protocol
  - [ ] Analysis protocol dropdown shows sample protocol
  - [ ] Version and status displayed ("v1.0.0 ✓")

- [ ] **Antibody Selection (Left Panel)**
  - [ ] Search box filters reagents in real-time
  - [ ] Antibody cards show:
    - [ ] Target antigen
    - [ ] Fluorochrome name (not ID)
    - [ ] Clone
    - [ ] Brand
    - [ ] Price per 100µL
    - [ ] Available vial count
  - [ ] Channel assignment shows semantic names ("PE", "B585/42")
  - [ ] Auto-suggestion works (shows "✓ Suggested: PE")
  - [ ] Volume input accepts decimals (0.25 step)
  - [ ] Intracellular checkbox works
  - [ ] Staining step selector works
  - [ ] Display name pre-fills correctly
  - [ ] "Add to Panel" button works

- [ ] **Panel Composition (Right Panel)**
  - [ ] Shows "No reagents" message when empty
  - [ ] Antibodies appear after adding
  - [ ] Table shows:
    - [ ] Channel name (not ID)
    - [ ] Marker display name
    - [ ] Volume in µL
    - [ ] Staining step number
    - [ ] Intracellular checkmark
    - [ ] Cost per reagent
  - [ ] Total cost updates in real-time
  - [ ] Antibody count correct
  - [ ] Table sorted by channel name
  - [ ] Multi-select works
  - [ ] "Remove Selected" button deletes reagents

- [ ] **Save Panel**
  - [ ] Validation errors show:
    - [ ] Missing panel name
    - [ ] Missing sample type
    - [ ] Zero sample volume
    - [ ] No antibodies added
  - [ ] Successful save shows:
    - [ ] Success message
    - [ ] Panel ID
    - [ ] Balloons animation
  - [ ] Draft cleared after save
  - [ ] Panel appears in Panels view

- [ ] **Clear Panel**
  - [ ] "Clear Panel" button empties both lists
  - [ ] Confirmation message shows

### 4. Database Verification

After creating a test panel:

```sql
-- Check panel was saved
SELECT id, name, version, estimated_cost_per_test, sample_type, clinical_indication
FROM panels
ORDER BY created_at DESC LIMIT 1;

-- Check panel reagents have semantic names
SELECT
    pr.display_name,
    pr.channel_display_name,  -- Should show "PE", not UUID
    pr.volume_per_test,
    pr.cost_per_test
FROM panel_reagents pr
WHERE panel_id = '<your_panel_id>';

-- Verify cost calculation
SELECT
    name,
    estimated_cost_per_test,
    (SELECT SUM(cost_per_test) FROM panel_reagents WHERE panel_id = panels.id)
FROM panels
ORDER BY created_at DESC LIMIT 1;
```

---

## Known Limitations

1. **No Panel Editing Yet**
   - Can create panels, but cannot edit after save
   - Versioning infrastructure in place for future edit workflow
   - Workaround: Create new panel with updated composition

2. **No General Reagents UI**
   - Table and fields exist
   - UI not implemented in this phase
   - Focus was on antibody workflow

3. **No Lot Selection**
   - `preferred_reagent_unit_id` field exists but not populated
   - Will be implemented in Phase 5 (patient/sample tracking)
   - Current design uses abstract reagent definitions

4. **No PDF Export**
   - Panel worksheet generation planned for Phase 4
   - Data model complete for export

5. **No Duplicate Panel Name Check**
   - System allows multiple panels with same name but different versions
   - Unique constraint should be added: `UNIQUE(name, version)`

6. **No Protocol Management UI**
   - Sample protocols created by migration
   - Admin UI for creating/editing protocols planned for Phase 3
   - Workaround: Manual SQL inserts

---

## Next Steps (Phase 3 & Beyond)

### Immediate Priorities

1. **Panel Viewer Enhancement**
   - Show new metadata fields (clinical indication, sample type, cost)
   - Display protocol names (not IDs)
   - Show validation status
   - Add version history view

2. **Panel Editing Workflow**
   - Load existing panel into draft
   - Auto-increment version on save
   - Add version notes field
   - Lock validated panels (read-only)

3. **Protocol Management UI**
   - Create acquisition protocols
   - Create compensation protocols
   - Create analysis protocols
   - Validate protocols (change status to "validated")
   - Link PDF attachments

### Future Enhancements

4. **Panel Validation Workflow**
   - Status lifecycle: draft → under_validation → validated → in_use → archived
   - Electronic signature (password confirmation)
   - Lock validated panels (create new version to modify)
   - Validation checklist

5. **Panel Comparison Tool**
   - Diff two panel versions
   - Highlight added/removed reagents
   - Show cost delta

6. **Reagent Consumption Tracking**
   - Decrement `current_volume` when panel executed
   - Link to specific lot (populate `preferred_reagent_unit_id`)
   - Low stock alerts

7. **General Reagents UI**
   - Add general reagents to panel (buffers, fixatives)
   - Usage type selection (fixation, lysis, wash)
   - Application step sequencing

---

## Files Modified

```
migrations/
  001_panel_builder_v2.sql          [NEW] Schema migration

run_migration.py                    [NEW] Migration runner

ui/
  panel_builder.py                  [REWRITTEN] 637 lines, split-view, semantic names

db/
  backups/                          [NEW] Automatic migration backups
    inventory_backup_20260123_*.db

CHANGELOG_PANEL_BUILDER_V2.md       [NEW] This document
```

---

## Success Criteria

✅ **Phase 1: Data Model** (Complete)
- [x] Protocol tables created
- [x] Versioning columns added
- [x] Cost tracking fields added
- [x] Lot traceability prepared
- [x] Migration system implemented
- [x] CytoFLEX set as default

✅ **Phase 2: Panel Builder** (Complete)
- [x] Split-view UI implemented
- [x] Semantic names throughout (no IDs)
- [x] CytoFLEX default selection
- [x] Real-time cost calculation
- [x] Clinical metadata capture
- [x] Protocol dropdowns
- [x] Smart channel assignment
- [x] Stock availability display
- [x] Multi-step staining support
- [x] Session state management
- [x] Validation on save

---

## Maintenance Notes

### Adding New Cytometers

```sql
INSERT INTO cytometers (id, name, manufacturer, model, is_default, status, created_at)
VALUES (
    lower(hex(randomblob(16))),
    'FACSCanto II',
    'BD Biosciences',
    'FACSCanto II',
    0,  -- Not default
    'active',
    datetime('now')
);
```

### Adding New Protocols

```sql
-- Acquisition protocol
INSERT INTO acquisition_protocols (id, name, cytometer_id, status, version, notes, created_at)
VALUES (
    lower(hex(randomblob(16))),
    'High Throughput Acquisition',
    '<cytometer_id>',
    'draft',
    '1.0.0',
    'Fast flow rate, 50k events, for screening',
    datetime('now')
);
```

### Changing Default Cytometer

```sql
-- Unset all defaults
UPDATE cytometers SET is_default = 0;

-- Set new default
UPDATE cytometers SET is_default = 1 WHERE name = 'FACSCanto II';
```

### Rolling Back Migration

```bash
# Restore from backup
cp db/backups/inventory_backup_20260123_165013.db db/inventory.db

# Remove migration record
sqlite3 db/inventory.db "DELETE FROM schema_migrations WHERE migration_name = '001_panel_builder_v2';"
```

---

## Contact

For questions or issues with this implementation:
1. Check this changelog
2. Review migration SQL: `migrations/001_panel_builder_v2.sql`
3. Review panel builder code: `ui/panel_builder.py`
4. Test with provided checklist above

---

**End of Changelog**
