# 🔬 StreamFlow Google Sheets – Simple Installation

## ✨ **ONE FILE. FIVE STEPS. DONE.**

No CSVs to import. No multiple files. Just one file with everything.

---

## 📥 **How to Install** (5 minutes)

### Step 1: Download the file

Download **`STREAMFLOW_COMPLETE.gs`** from this folder to your computer

### Step 2: Create a Google Sheet

1. Go to **sheets.google.com**
2. Click the **big `+`** button
3. A blank sheet opens

### Step 3: Open Apps Script

1. Click **Extensions** (top menu)
2. Click **Apps Script**
3. A new tab opens with a code editor

### Step 4: Paste the file

1. You'll see a file called `Code.gs` with some default code
2. **Select all** the default code (Ctrl+A)
3. **Delete** it (Backspace)
4. Open `STREAMFLOW_COMPLETE.gs` on your computer
5. **Select all** (Ctrl+A)
6. **Copy** (Ctrl+C)
7. Go back to Apps Script tab
8. **Paste** (Ctrl+V)
9. **Save** (Ctrl+S)

### Step 5: Run the installer

1. Click the **▶ Run** button at the top
2. In the dropdown next to it, select **`installStreamFlow`**
3. Click **▶ Run**
4. A popup says "Authorization required" → Click **Review permissions**
5. Choose your Google account
6. Click **Allow**
7. **Wait 30-60 seconds** (you'll see a loading spinner)
8. When you see **"✅ Installation Complete!"** → Click OK

---

## ✅ **Done!**

Go back to your Google Sheet tab. You'll see:

- ✅ **📊 Dashboard** sheet with live data
- ✅ **reagents** sheet with 116 antibodies
- ✅ **panels** sheet with 35 panels
- ✅ **reagent_units** sheet with 145 lots/units
- ✅ **🔬 StreamFlow** menu at the top
- ✅ Working formulas like `=SF_EXPIRY_ALERT()`

---

## 🎯 **What You Can Do**

### Use the Menu

Click **🔬 StreamFlow** at the top:
- **📊 Dashboard** — Jump to dashboard
- **📋 Reagents** — View all antibodies
- **🧬 Panels** — View all panels
- **ℹ️ About** — Learn more
- **🔄 Reinstall** — Reset everything

### Use Custom Formulas

In any cell, type:

| Formula | What it does |
|---------|--------------|
| `=SF_EXPIRY_ALERT("2025-06-01")` | 🟡 63d (color-coded alert) |
| `=SF_DAYS_TO_EXPIRY("2025-06-01")` | 63 (days remaining) |
| `=SF_REAGENT_NAME(A2)` | CD3 BV421 (looks up name) |
| `=SF_PANEL_NAME(A2)` | B-Cell Panel (looks up name) |
| `=SF_REAGENT_UNITS_AVAILABLE(A2)` | 3 (available units) |

*Note: Replace `A2` with the cell containing the ID*

### View Your Data

- **reagents** sheet — All antibodies (name, clone, brand)
- **reagent_units** sheet — All stock (lot, expiry, price)
- **panels** sheet — All panels (name, status, reagents)
- **brands**, **fluorochromes** — Reference data

---

## 🆘 **Troubleshooting**

### "Can't find function installStreamFlow"
→ Make sure you pasted the ENTIRE file (it's 1,000+ lines)

### "Authorization required" won't go away
→ Make sure you're logged into Google. Try in an incognito window.

### Nothing happens after clicking Run
→ Wait 60 seconds. Large files take time to process.

### "Script timeout" error
→ The file is too large for some Google accounts. This is rare but can happen.

### Menu doesn't appear
→ Reload the Google Sheet page (F5)

---

## 📊 **What's Included**

| Item | Count |
|------|-------|
| Antibody Reagents | 116 |
| Reagent Units/Lots | 145 |
| Flow Cytometry Panels | 35 |
| Brands/Suppliers | 7 |
| Fluorochromes | 21 |
| Purchase Orders | 2 |
| Database Tables | 24 |

**All automatically loaded. Zero manual work.**

---

## 💡 **Tips**

- The **Dashboard** updates automatically when you open the sheet
- You can add more data directly in the sheets
- Use **🔬 StreamFlow → Reinstall** to reset if something breaks
- The formulas work anywhere in the spreadsheet

---

## ❓ **Questions**

**Q: Can I edit the data?**
A: Yes! Just edit directly in the sheets.

**Q: Will this work on my phone?**
A: Yes, Google Sheets works on mobile.

**Q: Can multiple people use it?**
A: Yes! Share the sheet like any Google Sheet.

**Q: Does it update automatically?**
A: The data is static. Add new entries manually in the sheets.

**Q: Can I export back to the original app?**
A: No, this is a one-way migration.

---

**Enjoy your Flow Cytometry Lab Manager in Google Sheets! 🔬**
