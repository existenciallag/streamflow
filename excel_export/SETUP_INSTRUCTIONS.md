# StreamFlow Excel Edition - Setup Instructions

## 📋 Overview

This is a **fully functional Excel-based** version of StreamFlow that runs locally on your PC. It includes all features from the original app:

- ✅ Inventory management (reagents, units, stock tracking)
- ✅ Panel management (view panels, check stock availability)
- ✅ Expiration alerts and low stock warnings
- ✅ Usage tracking and status updates
- ✅ Comprehensive reporting
- ✅ Dashboard with real-time metrics

---

## 🚀 Quick Start (5 minutes)

### Step 1: Create the Excel Workbook

1. **Open Excel** (Microsoft Excel 2016 or later recommended)
2. **Create a new blank workbook**
3. **Save as**: `StreamFlow.xlsm` (macro-enabled workbook)
   - File → Save As → Select **Excel Macro-Enabled Workbook (*.xlsm)**

### Step 2: Import Data Sheets

Create these sheets and import CSV data:

| Sheet Name | CSV File | Description |
|------------|----------|-------------|
| `Reagents` | `reagents.csv` | Master list of antibodies (116 rows) |
| `Reagent_Units` | `reagent_units.csv` | Individual vials/units (145 rows) |
| `General_Reagents` | `general_reagents.csv` | Consumables (7 rows) |
| `General_Reagent_Units` | `general_reagent_units.csv` | Consumable units (19 rows) |
| `Brands` | `brands.csv` | Manufacturer brands (7 rows) |
| `Fluorochromes` | `fluorochromes.csv` | Fluorophore list (21 rows) |
| `Panels` | `panels.csv` | Antibody panels (35 rows) |
| `Panel_Reagents` | `panel_reagents.csv` | Panel compositions (105 rows) |
| `Cytometers` | `cytometers.csv` | Flow cytometers (1 row) |
| `Optical_Channels` | `optical_channels.csv` | Detector channels (9 rows) |
| `Purchase_Orders` | `purchase_orders.csv` | Purchase records (2 rows) |
| `Purchase_Order_Items` | `purchase_order_items.csv` | Order line items (17 rows) |

**How to import:**
1. Right-click sheet tab → Rename to match table above
2. Go to: **Data** → **From Text/CSV**
3. Select the corresponding CSV file
4. Click **Load**
5. Repeat for all 12 sheets

### Step 3: Create Dashboard Sheet

1. Create a new sheet named **`Dashboard`**
2. Set up the following structure:

```
A1: "StreamFlow Inventory Manager"  (Title, Font Size 18, Bold)
A2: "Total Reagents:"               B2: (formula will be added by VBA)
A3: "Total Units:"                  B3: (formula will be added by VBA)
A4: "Units In Use:"                 B4: (formula will be added by VBA)
A5: "Units Stored:"                 B5: (formula will be added by VBA)
A6: "Units Empty:"                  B6: (formula will be added by VBA)
A7: "Expiring Soon (30 days):"     B7: (formula will be added by VBA)
A8: "Expired:"                      B8: (formula will be added by VBA)
```

3. Add menu buttons (see Step 5)

### Step 4: Import VBA Modules

1. Press **ALT + F11** to open VBA Editor
2. In VBA Editor: **File** → **Import File**
3. Import these modules (in order):
   - `VBA_Module_Main.bas`
   - `VBA_Module_Inventory.bas`
   - `VBA_Module_Panels.bas`
   - `VBA_Module_Alerts.bas`

4. **Save** the workbook (Ctrl+S)

### Step 5: Create Menu Buttons on Dashboard

On the `Dashboard` sheet, insert buttons:

1. **Developer** tab → **Insert** → **Button (Form Control)**
2. Draw button, assign macro when prompted
3. Right-click button → **Edit Text** to rename

**Buttons to create:**

| Button Text | Assigned Macro | Position |
|-------------|----------------|----------|
| 🔄 Refresh Dashboard | `RefreshDashboard` | D2 |
| 📦 View Reagents | `GoToReagents` | D4 |
| 🧪 View Units | `GoToUnits` | D5 |
| 🔬 View Panels | `GoToPanels` | D6 |
| ➕ Add New Unit | `AddNewUnit` | D8 |
| 🔄 Change Unit Status | `ChangeUnitStatus` | D9 |
| 📊 Register Usage | `RegisterUsage` | D10 |
| 🔔 Check Expiring Units | `CheckExpiringUnits` | F4 |
| ⚠️ Check Low Stock | `CheckLowStock` | F5 |
| 📋 View Panel Details | `ViewPanelDetails` | F6 |
| ✅ Check Panel Stock | `CheckPanelStock` | F7 |
| 📊 Generate Report | `GenerateInventoryReport` | F9 |

### Step 6: Enable Macros

1. **File** → **Options** → **Trust Center** → **Trust Center Settings**
2. **Macro Settings** → Select **Enable all macros**
3. Check **Trust access to the VBA project object model**
4. Click **OK**
5. **Close and reopen** the workbook

---

## 🎯 Usage Guide

### Dashboard

- **Launch**: Open `StreamFlow.xlsm` → Dashboard appears automatically
- **Metrics**: View real-time inventory statistics
- **Navigation**: Use buttons to access features

### Inventory Management

#### Add New Unit
1. Click **Add New Unit** button
2. Enter reagent name (e.g., "CD3" or reagent ID)
3. Enter lot number
4. Enter expiration date (YYYY-MM-DD format)
5. Enter initial volume (µL)
6. Unit is automatically added with "Stored" status

#### Change Unit Status
1. Click **Change Unit Status** button
2. Enter unit ID or lot number
3. Select new status:
   - **YES** = In Use
   - **NO** = Stored
   - **CANCEL** = Empty

#### Register Usage
1. Click **Register Usage** button
2. Enter unit ID or lot number
3. Enter volume used (µL)
4. Volume is automatically decreased
5. Status auto-updates to "In Use" or "Empty"

### Panel Management

#### View Panel Details
1. Click **View Panel Details** button
2. Enter panel name (e.g., "B-cell Panel")
3. View panel info and reagent list

#### Check Panel Stock
1. Click **Check Panel Stock** button
2. Enter panel name
3. View stock availability for each reagent
4. See which reagents are out of stock

### Alerts & Reports

#### Expiration Alerts
- Click **Check Expiring Units**
- Shows expired units and units expiring within 30 days

#### Low Stock Alerts
- Click **Check Low Stock**
- Shows reagents with ≤2 units available

#### Inventory Report
- Click **Generate Report**
- Creates detailed report sheet with:
  - Reagent names, clones, fluorochromes
  - Unit counts by status
  - Color-coded stock levels

---

## 🛠️ Customization

### Modify Low Stock Threshold
In `VBA_Module_Alerts.bas`, line ~20:
```vba
If availableUnits <= 2 Then  ' Change 2 to your threshold
```

### Modify Expiration Warning Period
In `VBA_Module_Alerts.bas`, line ~10:
```vba
If expirationDate <= today + 30 Then  ' Change 30 to days
```

### Add Custom Reports
Create new Sub in `VBA_Module_Alerts.bas` following the pattern of `GenerateInventoryReport`

---

## 📊 Sheet Structure Reference

### Reagents Sheet
Key columns:
- `id` - Unique reagent identifier
- `name` - Antibody name (e.g., "CD3")
- `clone` - Clone designation
- `brand_id` - Link to Brands sheet
- `fluorochrome` - Link to Fluorochromes sheet

### Reagent_Units Sheet
Key columns:
- `id` - Unique unit identifier
- `reagent_id` - Link to Reagents sheet
- `lot` - Lot number
- `expiration_date` - Expiration date
- `arrival_date` - Arrival date
- `initial_volume` - Initial volume (µL)
- `current_volume` - Current volume (µL)
- `status` - "Stored", "In Use", or "Empty"

### Panels Sheet
Key columns:
- `id` - Unique panel identifier
- `name` - Panel name
- `description` - Panel description

### Panel_Reagents Sheet
Key columns:
- `panel_id` - Link to Panels sheet
- `reagent_id` - Link to Reagents sheet

---

## 🔧 Troubleshooting

### Macros not working
- Enable macros (see Step 6)
- Check that modules are imported correctly (ALT+F11)
- Verify sheet names match exactly (case-sensitive)

### "Column not found" error
- Verify CSV import preserved all columns
- Check that first row contains column headers
- Ensure no extra spaces in header names

### "Reagent not found" error
- Check reagent name spelling
- Try using reagent ID instead
- Verify Reagents sheet has data

### Dashboard not updating
- Click **Refresh Dashboard** button
- Check that formulas reference correct sheets
- Verify data is in expected columns

---

## 💾 Backup & Maintenance

### Daily Backup
File → Save As → Create dated copy (e.g., `StreamFlow_2024-03-23.xlsm`)

### Data Validation
- Reagent_Units.status should only contain: "Stored", "In Use", "Empty"
- Dates should use YYYY-MM-DD format
- Volumes should be numeric

### Performance
- Keep workbook under 50MB
- Archive old units (status="Empty") to separate sheet quarterly
- Compact workbook: File → Info → Inspect Workbook → Remove unused objects

---

## 📞 Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Verify all CSV files imported correctly
3. Check VBA modules are loaded (ALT+F11)
4. Review error messages for clues

---

## ✨ Features Summary

✅ **All StreamFlow features working in Excel:**
- Complete inventory tracking
- Panel management
- Usage recording
- Expiration tracking
- Low stock alerts
- Comprehensive reports
- User-friendly dashboard
- No internet required
- No installation needed
- Works offline

**Ready to use in 5 minutes!**
