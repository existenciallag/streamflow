# 📊 StreamFlow - Excel Edition

**Complete Flow Cytometry Inventory Manager in Excel**

---

## 🚀 Quick Start (30 seconds!)

### Option 1: Use Pre-Built Workbook (RECOMMENDED)

1. **Open** `StreamFlow.xlsm` in Excel
2. **Import VBA modules**:
   - Press `ALT + F11` (opens VBA Editor)
   - File → Import File
   - Import all 4 `.bas` files:
     - `VBA_Module_Main.bas`
     - `VBA_Module_Inventory.bas`
     - `VBA_Module_Panels.bas`
     - `VBA_Module_Alerts.bas`
3. **Close VBA Editor** and return to Excel
4. **Enable macros** when prompted
5. **Done!** Dashboard is ready with all 116 reagents and 145 units

### Option 2: Build from Scratch

See `SETUP_INSTRUCTIONS.md` for detailed manual setup

---

## 📦 What's Included

### Files

- `StreamFlow.xlsm` - **Pre-configured Excel workbook with all data**
- `VBA_Module_Main.bas` - Dashboard and navigation
- `VBA_Module_Inventory.bas` - Inventory management functions
- `VBA_Module_Panels.bas` - Panel management functions
- `VBA_Module_Alerts.bas` - Alerts and reporting
- `SETUP_INSTRUCTIONS.md` - Complete setup guide
- `create_excel_workbook.py` - Regenerate workbook from database
- `*.csv` - Raw data exports (backup)

### Data Included

- ✅ **116 Reagents** (antibodies with clones, fluorochromes)
- ✅ **145 Units** (vials with lot numbers, expiration dates)
- ✅ **35 Panels** (antibody panels)
- ✅ **21 Fluorochromes** (fluorophore definitions)
- ✅ **7 Brands** (manufacturers)
- ✅ **7 General Reagents** (consumables)
- ✅ **19 General Units** (consumable units)

---

## ✨ Features

### Inventory Management
- ➕ **Add new units** - Register new vials with lot numbers
- 🔄 **Change status** - Update unit status (Stored/In Use/Empty)
- 📊 **Register usage** - Track volume consumed, auto-update status
- 📦 **View inventory** - Browse all reagents and units

### Panel Management
- 🔬 **View panels** - See panel compositions
- ✅ **Check stock** - Verify all reagents available
- 📋 **Panel details** - Full reagent lists

### Alerts & Reports
- 🔔 **Expiration alerts** - Find expired/expiring units
- ⚠️ **Low stock warnings** - Reagents with ≤2 units
- 📊 **Inventory reports** - Comprehensive stock analysis with color coding

### Dashboard
- 📈 **Real-time metrics** - Total reagents, units by status
- 🔄 **Auto-refresh** - Click button to update statistics
- 🎯 **Quick navigation** - Buttons to access all features

---

## 🎯 Quick Reference

### Common Tasks

| Task | How To |
|------|--------|
| **Add new vial** | Dashboard → "Add New Unit" button |
| **Mark as used** | Dashboard → "Register Usage" button |
| **Change status** | Dashboard → "Change Unit Status" button |
| **Check expiring** | Dashboard → "Check Expiring Units" button |
| **View panel** | Dashboard → "View Panel Details" button |
| **Generate report** | Dashboard → "Generate Report" button |

### Keyboard Shortcuts

- `CTRL + HOME` - Go to Dashboard
- `ALT + F11` - Open VBA Editor
- `CTRL + S` - Save workbook
- `F5` - Run macro (in VBA Editor)

---

## 🛠️ Advanced

### Regenerate Workbook from Database

If database is updated:

```bash
python create_excel_workbook.py
```

This creates a fresh `StreamFlow.xlsm` with latest data.

### Customize Thresholds

Edit VBA modules to change:
- Low stock threshold (default: 2 units)
- Expiration warning period (default: 30 days)
- Dashboard metrics

---

## 📋 Requirements

- **Excel 2016 or later** (Windows or Mac)
- **Macros enabled** (File → Options → Trust Center)
- **VBA modules imported** (see Quick Start)

---

## 🔧 Troubleshooting

### "Macros have been disabled"
- File → Options → Trust Center → Trust Center Settings
- Macro Settings → Enable all macros
- Restart Excel

### Buttons don't work
- Check VBA modules are imported (ALT+F11, look for modules in left panel)
- Verify macros are enabled

### "Column not found" error
- Sheet names must match exactly (case-sensitive)
- First row must be headers
- No extra spaces in column names

### Data not showing
- Check correct sheet is selected
- Verify CSV imported correctly
- Click "Refresh Dashboard" button

---

## 💡 Tips

- **Backup regularly**: File → Save As → Create dated copies
- **Filter data**: Use Excel's built-in filters on data sheets
- **Export reports**: Copy report sheet to new workbook
- **Customize dashboard**: Add charts, conditional formatting
- **Print labels**: Use Mail Merge with Reagent_Units sheet

---

## 📖 Full Documentation

See `SETUP_INSTRUCTIONS.md` for:
- Detailed setup walkthrough
- Sheet structure reference
- VBA code explanation
- Advanced customization
- Complete troubleshooting guide

---

## 🎉 Ready to Use!

**Your complete flow cytometry inventory system in Excel** - no installation, no internet, no dependencies. Just open, enable macros, and start managing your lab!

---

## 📞 Support

For questions or issues:
1. Check `SETUP_INSTRUCTIONS.md`
2. Review VBA code (ALT+F11)
3. Verify data import was successful
4. Check Excel macro settings

---

**Made with ❤️ for flow cytometry labs**
