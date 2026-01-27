# Clinical & Economic Sections - Design Document

## I. PANEL BUILDER BUGS - ROOT CAUSE ANALYSIS

### Bug 1: Pre-washed Sample Not Displayed
**Root Cause**: `ui/panels.py:120-135` - The query loading panels excludes `washed_sample` field
```sql
SELECT p.id, p.name, p.version, p.status, p.sample_type, p.sample_volume, ...
-- Missing: p.washed_sample
```
**Fix**: Add `p.washed_sample` to SELECT statement

### Bug 2: Status Always Shows DRAFT
**Root Cause**: Database contains `status = 'Active'`, but UI expects `'draft'/'validated'/'archived'`
- Database has: "Active"
- UI expects: "draft", "validated", "archived"
- Current panels have wrong status vocabulary
**Fix**:
1. Standardize status values in database
2. Update UI to handle proper status lifecycle

### Bug 3: Version and Status Not Editable
**Root Cause**: `ui/panels.py:204` - Version and status are display-only, no edit form exists
**Fix**: Add version management and status transition workflow

### Bug 4: No Panel Categories
**Root Cause**: No `panel_categories` table exists. `panels.category_id` references non-existent table.
**Fix**: Create proper category system with hierarchical structure

---

## II. DATA MODEL DESIGN

### A. Panel Categories & Classification

```sql
-- Clinical areas (Immunology, Oncohematology, Fertility, etc.)
CREATE TABLE panel_areas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    code TEXT UNIQUE,  -- Short code: IMMUNO, ONCOHEM, FERT, etc.
    display_order INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Disease categories (custom, manageable)
CREATE TABLE panel_disease_categories (
    id TEXT PRIMARY KEY,
    area_id TEXT,  -- Can belong to an area (optional)
    name TEXT NOT NULL,
    description TEXT,
    icd_code TEXT,  -- Optional ICD-10 reference
    requires_patient_tracking INTEGER DEFAULT 0,  -- 1 for Oncohematology
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (area_id) REFERENCES panel_areas(id)
);

-- Link panels to both areas and diseases
CREATE TABLE panel_classifications (
    id TEXT PRIMARY KEY,
    panel_id TEXT NOT NULL,
    area_id TEXT,
    disease_category_id TEXT,
    is_primary INTEGER DEFAULT 1,  -- Main classification
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE,
    FOREIGN KEY (area_id) REFERENCES panel_areas(id),
    FOREIGN KEY (disease_category_id) REFERENCES panel_disease_categories(id)
);
```

### B. Panel Versioning & Status Management

```sql
-- Update panels table
ALTER TABLE panels ADD COLUMN status TEXT DEFAULT 'draft';  -- Already exists
ALTER TABLE panels ADD COLUMN version TEXT DEFAULT '1.0.0';  -- Already exists

-- Valid statuses: 'draft', 'validated', 'active', 'deprecated', 'archived'
-- Status lifecycle:
--   draft -> validated -> active -> deprecated -> archived
--              ↓           ↓
--           (can revert to draft)

-- Version history tracking
CREATE TABLE panel_versions (
    id TEXT PRIMARY KEY,
    panel_id TEXT NOT NULL,
    version TEXT NOT NULL,
    previous_version TEXT,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    created_by TEXT,
    validation_notes TEXT,
    changes_summary TEXT,
    snapshot_json TEXT,  -- Full panel snapshot at this version
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE
);

-- Status transition log
CREATE TABLE panel_status_history (
    id TEXT PRIMARY KEY,
    panel_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_at TEXT DEFAULT (datetime('now')),
    changed_by TEXT,
    reason TEXT,
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE
);
```

### C. Clinical Section - Oncohematology Patients

```sql
-- Patient registry (only for Oncohematology)
CREATE TABLE patients (
    id TEXT PRIMARY KEY,
    -- Identification
    medical_record_number TEXT UNIQUE NOT NULL,  -- Historia clínica
    national_id TEXT,  -- Cédula/DNI (optional, privacy)
    initials TEXT NOT NULL,  -- e.g., "JPS" for anonymization

    -- Demographics
    date_of_birth DATE,
    age_at_registration INTEGER,
    sex TEXT CHECK(sex IN ('M', 'F', 'Other', 'Unknown')),

    -- Clinical
    referring_physician TEXT,
    referring_institution TEXT,

    -- Administrative
    registration_date TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active',  -- active, discharged, deceased, transferred
    notes TEXT,

    -- Audit
    created_at TEXT DEFAULT (datetime('now')),
    created_by TEXT,
    updated_at TEXT
);

-- Clinical cases (one patient can have multiple cases/episodes)
CREATE TABLE clinical_cases (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    case_number TEXT UNIQUE NOT NULL,  -- Lab-generated case ID

    -- Clinical context
    clinical_suspicion TEXT,  -- Initial suspicion
    sample_date DATE NOT NULL,
    sample_type TEXT,  -- Blood, bone marrow, etc.
    referring_physician TEXT,

    -- Disease classification
    disease_category_id TEXT,  -- Link to panel_disease_categories

    -- Status
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, reported
    priority TEXT DEFAULT 'routine',  -- routine, urgent, stat

    -- Timestamps
    received_at TEXT DEFAULT (datetime('now')),
    reported_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,

    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_category_id) REFERENCES panel_disease_categories(id)
);

-- Panels assigned to cases (traceability)
CREATE TABLE case_panels (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    panel_id TEXT NOT NULL,

    -- Execution details
    run_date DATE,
    run_number TEXT,  -- Cytometer run identifier
    cytometer_id TEXT,
    operator TEXT,

    -- Quality control
    events_acquired INTEGER,
    viability_percent REAL,
    quality_flags TEXT,  -- JSON: {debris: low, doublets: acceptable, etc.}

    -- Results
    immunophenotype TEXT,  -- Structured result (JSON or text)
    interpretation TEXT,  -- Cytometrist interpretation

    -- Status
    status TEXT DEFAULT 'pending',  -- pending, running, completed, rejected

    -- Lot tracking for traceability
    reagent_lots_used TEXT,  -- JSON: [{reagent_id, lot, volume_used}, ...]

    -- Cost tracking (snapshot at execution time)
    actual_cost REAL,
    cost_calculation_json TEXT,  -- Detailed breakdown

    -- Timestamps
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,

    FOREIGN KEY (case_id) REFERENCES clinical_cases(id) ON DELETE CASCADE,
    FOREIGN KEY (panel_id) REFERENCES panels(id),
    FOREIGN KEY (cytometer_id) REFERENCES cytometers(id)
);

-- Final diagnosis (one per case)
CREATE TABLE case_diagnoses (
    id TEXT PRIMARY KEY,
    case_id TEXT UNIQUE NOT NULL,

    -- Diagnosis
    final_diagnosis TEXT NOT NULL,
    icd_code TEXT,
    disease_category_id TEXT,

    -- Classification
    who_classification TEXT,  -- WHO 2016/2022 classification
    fab_classification TEXT,  -- FAB classification if applicable

    -- Clinical correlation
    correlates_with_morphology INTEGER,  -- Boolean
    correlates_with_cytogenetics INTEGER,
    additional_findings TEXT,

    -- Reporting
    reported_by TEXT,
    reviewed_by TEXT,
    report_date DATE,

    -- Timestamps
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,

    FOREIGN KEY (case_id) REFERENCES clinical_cases(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_category_id) REFERENCES panel_disease_categories(id)
);
```

### D. Economic & Panel Tracking Section

```sql
-- Panel usage tracking (both Oncohematology and other areas)
CREATE TABLE panel_usage_log (
    id TEXT PRIMARY KEY,

    -- Panel identification
    panel_id TEXT NOT NULL,
    panel_version TEXT,  -- Version used at time of execution

    -- Execution context
    execution_date DATE NOT NULL,
    area_id TEXT,  -- Which clinical area

    -- Patient tracking (only for Oncohematology)
    case_panel_id TEXT,  -- Link to case_panels if Oncohematology
    is_patient_tracked INTEGER DEFAULT 0,  -- 1 if linked to patient

    -- Volume tracking (for non-Oncohematology areas)
    tests_count INTEGER DEFAULT 1,  -- Number of tests performed

    -- Cost tracking (snapshot at execution)
    cost_per_test REAL,
    total_cost REAL,
    cost_calculation_json TEXT,

    -- Operator
    operator TEXT,
    notes TEXT,

    -- Timestamps
    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (panel_id) REFERENCES panels(id),
    FOREIGN KEY (area_id) REFERENCES panel_areas(id),
    FOREIGN KEY (case_panel_id) REFERENCES case_panels(id)
);

-- Reagent consumption tracking (detailed)
CREATE TABLE reagent_consumption_log (
    id TEXT PRIMARY KEY,

    -- What was used
    reagent_unit_id TEXT NOT NULL,  -- Specific vial
    reagent_id TEXT NOT NULL,

    -- When and where
    consumption_date DATE NOT NULL,
    panel_usage_log_id TEXT,  -- Link to specific panel run
    case_panel_id TEXT,  -- Link to patient case if applicable

    -- How much
    volume_used REAL NOT NULL,  -- µL consumed
    cost_per_ul REAL,
    total_cost REAL,

    -- Context
    operator TEXT,

    -- Timestamps
    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (reagent_unit_id) REFERENCES reagent_units(id),
    FOREIGN KEY (reagent_id) REFERENCES reagents(id),
    FOREIGN KEY (panel_usage_log_id) REFERENCES panel_usage_log(id),
    FOREIGN KEY (case_panel_id) REFERENCES case_panels(id)
);

-- Cost summary views (for dashboards)
CREATE VIEW v_panel_cost_summary AS
SELECT
    p.id as panel_id,
    p.name as panel_name,
    pa.name as area_name,
    COUNT(pul.id) as times_used,
    SUM(pul.total_cost) as total_cost,
    AVG(pul.cost_per_test) as avg_cost_per_test,
    MIN(pul.execution_date) as first_used,
    MAX(pul.execution_date) as last_used
FROM panels p
LEFT JOIN panel_classifications pc ON pc.panel_id = p.id AND pc.is_primary = 1
LEFT JOIN panel_areas pa ON pa.id = pc.area_id
LEFT JOIN panel_usage_log pul ON pul.panel_id = p.id
GROUP BY p.id, p.name, pa.name;

-- Reagent consumption summary
CREATE VIEW v_reagent_consumption_summary AS
SELECT
    r.id as reagent_id,
    r.name as reagent_name,
    f.name as fluorochrome,
    b.name as brand,
    COUNT(rcl.id) as consumption_events,
    SUM(rcl.volume_used) as total_volume_used,
    SUM(rcl.total_cost) as total_cost,
    MIN(rcl.consumption_date) as first_used,
    MAX(rcl.consumption_date) as last_used
FROM reagents r
JOIN fluorochromes f ON f.id = r.fluorochrome
LEFT JOIN brands b ON b.id = r.brand_id
LEFT JOIN reagent_consumption_log rcl ON rcl.reagent_id = r.id
GROUP BY r.id, r.name, f.name, b.name;
```

---

## III. USER INTERFACE DESIGN

### A. Panel Builder Fixes

#### 1. Pre-washed Sample
- Fix: Add `p.washed_sample` to panels query
- Location: `ui/panels.py:120-135`

#### 2. Version Management
Add version controls to panel edit form:
```
Current Version: v1.0.0
⚙️ Version Actions:
  [ ] Increment patch (1.0.1) - Minor fixes
  [ ] Increment minor (1.1.0) - New features
  [ ] Increment major (2.0.0) - Breaking changes
Version notes: [text area]
```

#### 3. Status Management
Add status workflow with controls:
```
Current Status: DRAFT 🟡

Available Actions:
  [Validate Panel] → Validated 🟢
  [Archive] → Archived 🔴

Status Transition Log:
  2025-01-20: draft → validated (by: Dr. Smith)
  2025-01-15: created as draft
```

#### 4. Panel Categories
Add category selectors to Panel Builder:
```
📁 Classification
  Clinical Area: [Dropdown: Oncohematology, Immunology, Fertility, ...]
                  [+ Add New Area]

  Disease Category: [Dropdown: AML, ALL, CLL, Myeloma, ...]
                     [+ Add New Category]

  ☑ Requires patient tracking (auto-checked for Oncohematology)
```

### B. Clinical Section UI Structure

#### Navigation: "🔬 Clinical - Oncohematology"

**Sub-pages:**
1. **Patient Registry**
   - List patients with search/filter
   - Add new patient
   - View patient history

2. **Active Cases**
   - Dashboard of pending/in-progress cases
   - Case list with status indicators
   - Quick actions (assign panel, view results)

3. **Case Details** (drill-down view)
   ```
   Case #: 2025-012345
   Patient: [JPS] - MRN: 98765

   📋 Case Information
     Sample Date: 2025-01-20
     Sample Type: Bone Marrow
     Clinical Suspicion: Acute leukemia
     Status: In Progress 🟡

   🧪 Assigned Panels
     [✓] AML/MDS Panel v2.1 - Completed
     [ ] B-ALL Panel v1.3 - Pending
     [+ Assign Additional Panel]

   📊 Results
     [View Immunophenotype]
     [Enter Interpretation]

   🩺 Final Diagnosis
     [Enter Diagnosis] (only when all panels complete)
   ```

4. **Results Entry** (for each panel)
   ```
   Panel: AML/MDS Panel v2.1
   Case: 2025-012345
   Run Date: 2025-01-21

   Execution Details:
     Cytometer: CytoFLEX
     Operator: [Dropdown]
     Run Number: [Text]
     Events Acquired: [Number]
     Viability: [Number] %

   Quality Control:
     ☑ Adequate cell count
     ☑ Low debris
     ☑ Minimal doublets
     Notes: [Text area]

   Immunophenotype Results: [Rich text editor]

   Lot Tracking (auto-populated from panel):
     CD45 V500-C (BD) - Lot B123456 - 5µL used
     CD34 PE (BD) - Lot B234567 - 5µL used
     [Edit volumes if different from panel design]

   Actual Cost: $47.23 (calculated from lots used)

   [Save Results]
   ```

5. **Diagnosis Entry**
   ```
   Case: 2025-012345

   Final Diagnosis:
     Diagnosis: [Text field + autocomplete from ICD]
     ICD-10 Code: [Dropdown]
     Disease Category: [Dropdown]

   Classification:
     WHO 2022: [Text field]
     FAB: [Text field]

   Clinical Correlation:
     ☑ Correlates with morphology
     ☐ Correlates with cytogenetics
     Additional findings: [Text area]

   Reporting:
     Reported by: [User]
     Reviewed by: [Dropdown]
     Report Date: [Date picker]

   [Generate Report] [Save Diagnosis]
   ```

### C. Economic Section UI Structure

#### Navigation: "💰 Economic & Tracking"

**Dashboard Layout:**

```
=== OVERVIEW METRICS ===
[Total Tests (Month)]  [Total Cost]  [Cost per Test Avg]  [Most Used Panel]
     127                 $8,450           $66.54               AML/MDS

=== PANEL USAGE - LAST 30 DAYS ===
[Bar Chart]
  AML/MDS Panel     ████████████ 45 tests
  B-ALL Panel       ████████ 28 tests
  Immunology Basic  ██████ 20 tests
  T-Cell Panel      ████ 15 tests

=== COST BREAKDOWN BY AREA ===
[Pie Chart]
  Oncohematology (patient-tracked): 68% ($5,746)
  Immunology (volume-counted): 22% ($1,859)
  Fertility (volume-counted): 10% ($845)

=== TOP CONSUMED REAGENTS ===
[Table with sortable columns]
Reagent          Fluorochrome  Brand  Times Used  Volume Used  Total Cost
CD45             V500-C        BD     72          360 µL       $892.40
CD34             PE            BD     45          225 µL       $1,245.00
CD3              FITC          BD     38          190 µL       $234.50
...

=== COST TRENDS ===
[Line Chart - Cost per test over time]
Shows if costs are increasing/decreasing, helps identify waste
```

**Sub-pages:**

1. **Panel Usage Details**
   - Filterable table of all panel executions
   - Columns: Date, Panel, Area, Patient (if tracked), Cost, Operator
   - Export to Excel

2. **Reagent Consumption**
   - Detailed consumption log
   - Filter by: Date range, Reagent, Panel, Area
   - Shows: What, when, how much, by whom
   - Alerts for high-consumption reagents

3. **Quick Entry** (for non-Oncohematology areas)
   ```
   📝 Log Panel Usage (Non-Patient Areas)

   Date: [Date picker]
   Area: [Dropdown: Immunology, Fertility, Transplant, ...]
   Panel: [Dropdown: filtered by area]
   Number of tests: [Number input]
   Operator: [Dropdown]
   Notes: [Text area]

   Estimated Cost: $XXX.XX (auto-calculated)

   [Log Usage]
   ```

4. **Reports**
   - Monthly summary reports
   - Cost analysis by area/panel/reagent
   - Efficiency metrics
   - Export capabilities

---

## IV. IMPLEMENTATION PRIORITY

### Phase 1: Critical Fixes (Immediate)
1. Fix pre-washed sample display bug
2. Fix status vocabulary (Active → draft/validated)
3. Add panel categories infrastructure

### Phase 2: Panel Management (Week 1)
1. Implement version management
2. Implement status workflow
3. Add category UI to Panel Builder

### Phase 3: Clinical Section (Week 2-3)
1. Create patient registry
2. Implement case management
3. Build results entry workflow
4. Add diagnosis entry

### Phase 4: Economic Section (Week 3-4)
1. Implement usage logging
2. Build consumption tracking
3. Create dashboards and charts
4. Add reporting capabilities

---

## V. KEY DESIGN PRINCIPLES APPLIED

1. **Clinical Realism**
   - Patient anonymization (initials, not full names in main view)
   - Proper case workflow (pending → in_progress → completed → reported)
   - Lot traceability for quality control

2. **Traceability**
   - Every panel execution linked to specific reagent lots
   - Audit trails for status changes
   - Version history preserved

3. **Cost Control**
   - Snapshot costs at execution time (not retrospective estimation)
   - Detailed breakdown available
   - Trend analysis to identify inefficiencies

4. **Reproducibility**
   - Full panel snapshots at each version
   - Execution parameters logged
   - Quality control flags preserved

5. **Two-Track System**
   - Full patient tracking for Oncohematology
   - Simple volume counting for other areas
   - Unified cost analysis across both

---

## VI. NEXT STEPS

1. Review this design with you
2. Create database migration scripts
3. Implement fixes and new features incrementally
4. Test each phase before moving to next

**Estimated Total Implementation Time: 3-4 weeks**

Would you like me to proceed with implementation, or would you like to discuss any modifications to this design first?
