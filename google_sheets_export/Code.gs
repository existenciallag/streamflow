/**
 * StreamFlow – Flow Cytometry Lab Manager
 * Google Apps Script – Main Entry Point
 *
 * SETUP INSTRUCTIONS:
 *  1. Open Google Sheets → Extensions → Apps Script
 *  2. Create a new project named "StreamFlow"
 *  3. Create one .gs file per file in this folder (Code.gs, Dashboard.gs, etc.)
 *  4. Paste the contents of each file into the corresponding Apps Script file
 *  5. Run: StreamFlow → Setup → Initialize Spreadsheet
 *  6. Import CSV data: StreamFlow → Import Data → Import All Tables
 */

// ─── SHEET NAMES (single source of truth) ────────────────────────────────────
const SHEETS = {
  REAGENTS:           'reagents',
  REAGENT_UNITS:      'reagent_units',
  REAGENTS_UNITS:     'reagents_units',
  PANELS:             'panels',
  PANEL_REAGENTS:     'panel_reagents',
  PANEL_AREAS:        'panel_areas',
  PANEL_DISEASE_CATS: 'panel_disease_categories',
  PANEL_VERSIONS:     'panel_versions',
  PANEL_STATUS_HIST:  'panel_status_history',
  PANEL_GEN_REAGENTS: 'panel_general_reagents',
  GENERAL_REAGENTS:   'general_reagents',
  GEN_REAGENT_UNITS:  'general_reagent_units',
  GEN_REAGENTS_UNITS: 'general_reagents_units',
  BRANDS:             'brands',
  FLUOROCHROMES:      'fluorochromes',
  CYTOMETERS:         'cytometers',
  OPTICAL_CHANNELS:   'optical_channels',
  PURCHASE_ORDERS:    'purchase_orders',
  PURCHASE_ORDER_ITEMS: 'purchase_order_items',
  UNIT_HISTORY:       'reagent_unit_history',
  DASHBOARD:          '📊 Dashboard',
};

// ─── MENU ─────────────────────────────────────────────────────────────────────
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🔬 StreamFlow')
    .addSubMenu(SpreadsheetApp.getUi().createMenu('📥 Import Data')
      .addItem('Import reagents.csv',              'importReagents')
      .addItem('Import reagent_units.csv',         'importReagentUnits')
      .addItem('Import panels.csv',                'importPanels')
      .addItem('Import panel_reagents.csv',        'importPanelReagents')
      .addItem('Import all tables at once',        'importAllFromDialog')
    )
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('📊 Dashboard')
      .addItem('Refresh Dashboard',     'refreshDashboard')
      .addItem('Show Stock Health',     'showStockHealth')
      .addItem('Show Expiring (30d)',   'showExpiringSoon')
      .addItem('Show Panel Readiness', 'showPanelReadiness')
    )
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('💰 Costs')
      .addItem('Calculate All Panel Costs', 'calculateAllPanelCosts')
      .addItem('Show Cost Report',          'showCostReport')
    )
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('⚙️ Setup')
      .addItem('Initialize Spreadsheet', 'initializeSpreadsheet')
      .addItem('Create All Sheets',      'createAllSheets')
      .addItem('Apply Formatting',       'applyAllFormatting')
    )
    .addToUi();
}

// ─── INITIALIZATION ───────────────────────────────────────────────────────────
function initializeSpreadsheet() {
  const ui = SpreadsheetApp.getUi();
  ui.alert('StreamFlow Setup', 'Creating sheets and formatting…', ui.ButtonSet.OK);

  createAllSheets();
  applyAllFormatting();
  createDashboardSheet();

  ui.alert('✅ Done!',
    'StreamFlow is ready.\n\n' +
    'Next step: Use StreamFlow → Import Data to load your CSV files.\n\n' +
    'After importing, run StreamFlow → Dashboard → Refresh Dashboard.',
    ui.ButtonSet.OK);
}

function createAllSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheetOrder = [
    SHEETS.DASHBOARD,
    SHEETS.REAGENTS,
    SHEETS.REAGENT_UNITS,
    SHEETS.REAGENTS_UNITS,
    SHEETS.PANELS,
    SHEETS.PANEL_REAGENTS,
    SHEETS.PANEL_AREAS,
    SHEETS.PANEL_DISEASE_CATS,
    SHEETS.PANEL_VERSIONS,
    SHEETS.PANEL_STATUS_HIST,
    SHEETS.PANEL_GEN_REAGENTS,
    SHEETS.GENERAL_REAGENTS,
    SHEETS.GEN_REAGENT_UNITS,
    SHEETS.GEN_REAGENTS_UNITS,
    SHEETS.BRANDS,
    SHEETS.FLUOROCHROMES,
    SHEETS.CYTOMETERS,
    SHEETS.OPTICAL_CHANNELS,
    SHEETS.PURCHASE_ORDERS,
    SHEETS.PURCHASE_ORDER_ITEMS,
    SHEETS.UNIT_HISTORY,
  ];

  sheetOrder.forEach(name => {
    if (!ss.getSheetByName(name)) {
      ss.insertSheet(name);
    }
  });

  SpreadsheetApp.getUi().alert('✅ All sheets created.');
}

// ─── IMPORT HELPERS ───────────────────────────────────────────────────────────

/**
 * Paste CSV text into a sheet (overwrites existing data).
 * @param {string} sheetName
 * @param {string} csvText  Raw CSV content
 */
function loadCsvIntoSheet(sheetName, csvText) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(sheetName);
  if (!sheet) sheet = ss.insertSheet(sheetName);

  sheet.clearContents();

  const rows = Utilities.parseCsv(csvText);
  if (rows.length === 0) return;

  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);

  // Freeze header row
  sheet.setFrozenRows(1);

  // Bold the header
  sheet.getRange(1, 1, 1, rows[0].length)
    .setFontWeight('bold')
    .setBackground('#1565C0')
    .setFontColor('#FFFFFF');

  // Auto-resize columns
  for (let c = 1; c <= rows[0].length; c++) {
    sheet.autoResizeColumn(c);
  }
}

/**
 * Show a dialog to let the user paste CSV text and load it into a named sheet.
 */
function importCsvDialog(sheetName) {
  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: Arial, sans-serif; padding: 16px; }
      textarea { width: 100%; height: 200px; font-size: 11px; }
      button { margin-top: 8px; padding: 8px 16px; background: #1565C0; color: white; border: none; border-radius: 4px; cursor: pointer; }
    </style>
    <h3>Import <code>${sheetName}</code></h3>
    <p>Paste the contents of <strong>${sheetName}.csv</strong> below:</p>
    <textarea id="csv" placeholder="id,name,clone,…"></textarea><br>
    <button onclick="submit()">Import →</button>
    <script>
      function submit() {
        const csv = document.getElementById('csv').value;
        google.script.run.withSuccessHandler(() => {
          google.script.host.close();
        }).loadCsvIntoSheet('${sheetName}', csv);
      }
    </script>
  `).setWidth(500).setHeight(320);
  SpreadsheetApp.getUi().showModalDialog(html, `Import ${sheetName}`);
}

function importReagents()      { importCsvDialog(SHEETS.REAGENTS); }
function importReagentUnits()  { importCsvDialog(SHEETS.REAGENT_UNITS); }
function importPanels()        { importCsvDialog(SHEETS.PANELS); }
function importPanelReagents() { importCsvDialog(SHEETS.PANEL_REAGENTS); }

function importAllFromDialog() {
  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: Arial, sans-serif; padding: 16px; font-size: 13px; }
      p { margin: 6px 0; }
      ol { padding-left: 20px; }
      a { color: #1565C0; }
    </style>
    <h3>Import All Tables</h3>
    <p>Use <b>StreamFlow → Import Data</b> to import each CSV file individually.</p>
    <p>Available tables to import:</p>
    <ol>
      <li>reagents.csv</li>
      <li>reagent_units.csv</li>
      <li>reagents_units.csv</li>
      <li>panels.csv</li>
      <li>panel_reagents.csv</li>
      <li>panel_areas.csv</li>
      <li>panel_disease_categories.csv</li>
      <li>panel_versions.csv</li>
      <li>panel_status_history.csv</li>
      <li>panel_general_reagents.csv</li>
      <li>general_reagents.csv</li>
      <li>general_reagent_units.csv</li>
      <li>general_reagents_units.csv</li>
      <li>brands.csv</li>
      <li>fluorochromes.csv</li>
      <li>purchase_orders.csv</li>
      <li>purchase_order_items.csv</li>
      <li>reagent_unit_history.csv</li>
    </ol>
    <p><i>Paste each CSV via StreamFlow → Import Data → Import [table].csv</i></p>
  `).setWidth(400).setHeight(420);
  SpreadsheetApp.getUi().showModelessDialog(html, 'Import All Tables');
}

// ─── FORMATTING ───────────────────────────────────────────────────────────────
function applyAllFormatting() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  Object.values(SHEETS).forEach(name => {
    const sheet = ss.getSheetByName(name);
    if (!sheet || sheet.getLastRow() < 1) return;
    applySheetFormatting(sheet);
  });
}

function applySheetFormatting(sheet) {
  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 1) return;

  // Zebra striping on data rows
  for (let r = 2; r <= lastRow; r++) {
    const color = r % 2 === 0 ? '#F5F5F5' : '#FFFFFF';
    sheet.getRange(r, 1, 1, lastCol).setBackground(color);
  }

  // Freeze header
  sheet.setFrozenRows(1);
}
