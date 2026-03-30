# StreamFlow → Google Sheets Migration Guide

## What You Get

| File | Purpose |
|------|---------|
| `Code.gs` | Menu, sheet setup, CSV importer |
| `Dashboard.gs` | Live dashboard (stock health, expiry alerts, panel readiness) |
| `Pricing.gs` | Panel cost calculations (cheapest / average / FIFO / FEFO) |
| `Inventory.gs` | Add units, inventory summary, low-stock alerts |
| `Panels.gs` | Panel registry, reagent detail, purchase orders |
| `CustomFunctions.gs` | Cell formulas like `=SF_PANEL_COST()` |
| `*.csv` | Your exported database (24 tables) |

---

## Step 1 – Create the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) → **New spreadsheet**
2. Name it **StreamFlow Lab Manager**

---

## Step 2 – Open Apps Script

1. Click **Extensions → Apps Script**
2. You'll see a default `Code.gs` file — delete its contents

---

## Step 3 – Create Script Files

For each `.gs` file in this folder, do the following:

1. Click **+** (Add file) → **Script**
2. Name it exactly (e.g. `Dashboard`, `Pricing`, `Inventory`, `Panels`, `CustomFunctions`)
3. Paste the full contents of the corresponding `.gs` file

> You should end up with **6 script files**:
> `Code.gs`, `Dashboard.gs`, `Pricing.gs`, `Inventory.gs`, `Panels.gs`, `CustomFunctions.gs`

---

## Step 4 – Save & Authorize

1. Press **Ctrl+S** (or Cmd+S) to save
2. Click **Run → Run function → onOpen**
3. You'll be asked to authorize the script → click **Review permissions → Allow**

---

## Step 5 – Initialize the Spreadsheet

1. Go back to the Google Sheet (close Apps Script tab)
2. Reload the page — you'll see a new **🔬 StreamFlow** menu appear
3. Click **🔬 StreamFlow → ⚙️ Setup → Initialize Spreadsheet**
4. This creates all sheets and formats them

---

## Step 6 – Import Your Data (CSV files)

Import each CSV using the menu:

**🔬 StreamFlow → 📥 Import Data → Import [table].csv**

### Import Order (recommended):

| Priority | File | Why |
|----------|------|-----|
| 1 | `brands.csv` | Referenced by reagents |
| 2 | `fluorochromes.csv` | Referenced by panel_reagents |
| 3 | `reagents.csv` | Core data |
| 4 | `reagent_units.csv` | Stock data |
| 5 | `reagents_units.csv` | Unit mapping |
| 6 | `panels.csv` | Panel registry |
| 7 | `panel_reagents.csv` | What's in each panel |
| 8 | `panel_areas.csv` | Panel areas/categories |
| 9 | `panel_disease_categories.csv` | Disease categories |
| 10 | `panel_versions.csv` | Version history |
| 11 | `panel_status_history.csv` | Status tracking |
| 12 | `panel_general_reagents.csv` | Consumables per panel |
| 13 | `general_reagents.csv` | Consumables |
| 14 | `general_reagent_units.csv` | Consumable stock |
| 15 | `general_reagents_units.csv` | Consumable mapping |
| 16 | `purchase_orders.csv` | Orders |
| 17 | `purchase_order_items.csv` | Order line items |
| 18 | `reagent_unit_history.csv` | History log |

### How to paste a CSV:

1. Open the CSV file (in `google_sheets_export/` folder)
2. Select all → Copy (Ctrl+A, Ctrl+C)
3. In the dialog that opens, paste and click **Import →**

---

## Step 7 – Refresh the Dashboard

1. Click **🔬 StreamFlow → 📊 Dashboard → Refresh Dashboard**
2. The **📊 Dashboard** sheet will populate with:
   - Stock health KPIs
   - Expiring reagents (next 30 days)
   - Panel readiness status
   - Cost insights

---

## Using the Custom Functions

After importing data, use these formulas in any cell:

```
=SF_PANEL_COST("panel-id-here")          → Total cost per test ($)
=SF_PANEL_COST("panel-id-here","fefo")   → Cost using FEFO strategy
=SF_PANEL_STATUS("panel-id-here")        → ✅ Ready / ⚠️ 3/5 reagents
=SF_REAGENT_UNITS_AVAILABLE("reagent-id")→ Number of available units
=SF_DAYS_TO_EXPIRY("2025-06-01")        → 63 (days remaining)
=SF_EXPIRY_ALERT("2025-06-01")          → 🟡 63d
=SF_REAGENT_STOCK_VALUE("reagent-id")   → $247.50 (total stock value)
=SF_REAGENT_NAME("reagent-id")          → "CD3 BV421"
=SF_PANEL_NAME("panel-id")             → "B-Cell Lymphoma Panel"
=SF_PANEL_REAGENT_COUNT("panel-id")    → 8
```

> **Tip:** To get a panel's ID, look in the `panels` sheet, column `id`.

---

## Available Menu Actions

### 📥 Import Data
Import each CSV table manually via paste dialog.

### 📊 Dashboard
| Action | Description |
|--------|-------------|
| Refresh Dashboard | Updates the dashboard sheet |
| Show Stock Health | Alert with KPI summary |
| Show Expiring (30d) | Alert listing expiring reagents |
| Show Panel Readiness | Alert with readiness status |

### 💰 Costs
| Action | Description |
|--------|-------------|
| Calculate All Panel Costs | Adds `calculated_cost` column to panels sheet |
| Show Cost Report | Creates `💰 Cost Report` sheet |

### ⚙️ Setup
| Action | Description |
|--------|-------------|
| Initialize Spreadsheet | First-time setup |
| Create All Sheets | Create missing sheets |
| Apply Formatting | Re-apply headers/colors |

---

## Sheets Created

After full setup and import, you'll have these sheets:

| Sheet | Contents |
|-------|---------|
| 📊 Dashboard | Live metrics and alerts |
| reagents | 116 antibody reagents |
| reagent_units | 145 units/lots in stock |
| reagents_units | Unit-reagent mapping |
| panels | 35 panels |
| panel_reagents | Reagent assignments |
| panel_areas | Clinical areas (5) |
| panel_disease_categories | Disease categories (8) |
| panel_versions | Version history |
| panel_status_history | Status tracking |
| panel_general_reagents | Consumables per panel |
| general_reagents | 7 consumables |
| general_reagent_units | 19 consumable units |
| general_reagents_units | Unit mapping |
| brands | 7 brands/suppliers |
| fluorochromes | 21 fluorochromes |
| cytometers | Cytometer config |
| optical_channels | Channel definitions |
| purchase_orders | 2 purchase orders |
| purchase_order_items | 17 order items |
| reagent_unit_history | 142 history records |

**Auto-created views** (from menu actions):
- 📋 Inventory Summary
- 🧬 Panels Summary
- 💰 Cost Report
- 🛒 Purchase Orders

---

## Feature Comparison

| Feature | StreamFlow App | Google Sheets |
|---------|---------------|--------------|
| Stock tracking | ✅ | ✅ |
| Expiry alerts | ✅ | ✅ Dashboard |
| Panel management | ✅ | ✅ |
| Panel cost calc | ✅ | ✅ `=SF_PANEL_COST()` |
| FIFO/FEFO/cheapest | ✅ | ✅ Pricing.gs |
| Add units (form) | ✅ | ✅ Sidebar form |
| Add panel reagents | ✅ | ✅ Sidebar form |
| Dashboard KPIs | ✅ | ✅ |
| Multi-user editing | ❌ | ✅ Google Sheets |
| Offline use | ✅ Windows EXE | Needs internet |
| No login needed | ✅ | Needs Google account |
| Real-time formulas | ❌ | ✅ Custom functions |

---

## Troubleshooting

### Menu doesn't appear
→ Reload the page. If still missing: Apps Script → Run → `onOpen`

### "Sheet not found" errors
→ Run **🔬 StreamFlow → ⚙️ Setup → Create All Sheets** first, then import data.

### Functions return errors
→ Make sure data is imported. Functions read from the named sheets.

### Custom functions return "Loading..."
→ Google is calculating. Wait a few seconds and try again.

### Authorization errors
→ Apps Script → Run → authorize the script with your Google account.

---

## Data Refresh

The Google Sheets version does **not** auto-refresh. To update:

1. **Dashboard:** Run **Refresh Dashboard** from the menu
2. **Cost Report:** Run **Show Cost Report** again
3. **Inventory:** Run **Inventory Summary** again

To auto-refresh on open, add this to `Code.gs`:
```javascript
function onOpen() {
  // ... existing menu code ...
  refreshDashboard();  // Auto-refresh dashboard on open
}
```

---

## Support

For issues or questions, check the `FINAL_SUMMARY.md` for the full StreamFlow documentation.
