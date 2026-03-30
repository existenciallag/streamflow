/**
 * StreamFlow – Inventory Management
 *
 * CRUD operations and views for reagents and reagent units.
 * Equivalent to ui/crud.py, ui/inventory_advanced.py
 */

// ─── ADD REAGENT UNIT ─────────────────────────────────────────────────────────

/**
 * Show a sidebar form to add a new reagent unit.
 * Opens a sidebar in Google Sheets where the user can fill in details.
 */
function showAddUnitForm() {
  const reagents = getSheetData(SHEETS.REAGENTS);
  const options  = reagents.map(r => `<option value="${r.id}">${r.name} (${r.clone || ''})</option>`).join('\n');

  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: Arial, sans-serif; padding: 12px; font-size: 13px; }
      label { display: block; margin-top: 10px; font-weight: bold; }
      input, select { width: 100%; padding: 6px; margin-top: 4px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
      button { margin-top: 16px; width: 100%; padding: 10px; background: #1565C0; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
    </style>
    <h3>➕ Add Reagent Unit</h3>

    <label>Reagent *</label>
    <select id="reagent_id"><option value="">-- select --</option>${options}</select>

    <label>Lot Number *</label>
    <input id="lot" placeholder="e.g. AB123456">

    <label>Initial Volume (µL) *</label>
    <input id="initial_volume" type="number" placeholder="e.g. 500">

    <label>Current Volume (µL)</label>
    <input id="current_volume" type="number" placeholder="leave blank = same as initial">

    <label>Purchase Price ($)</label>
    <input id="purchase_price" type="number" step="0.01" placeholder="e.g. 89.50">

    <label>Arrival Date</label>
    <input id="arrival_date" type="date">

    <label>Expiration Date</label>
    <input id="expiration_date" type="date">

    <label>Status</label>
    <select id="status">
      <option value="Stored">Stored</option>
      <option value="In Use">In Use</option>
      <option value="Depleted">Depleted</option>
      <option value="Expired">Expired</option>
    </select>

    <button onclick="submit()">Save Unit</button>
    <p id="msg" style="color:green;"></p>

    <script>
      function submit() {
        const data = {
          reagent_id:     document.getElementById('reagent_id').value,
          lot:            document.getElementById('lot').value,
          initial_volume: document.getElementById('initial_volume').value,
          current_volume: document.getElementById('current_volume').value,
          purchase_price: document.getElementById('purchase_price').value,
          arrival_date:   document.getElementById('arrival_date').value,
          expiration_date:document.getElementById('expiration_date').value,
          status:         document.getElementById('status').value,
        };
        if (!data.reagent_id || !data.lot || !data.initial_volume) {
          document.getElementById('msg').style.color = 'red';
          document.getElementById('msg').textContent = 'Reagent, Lot, and Volume are required.';
          return;
        }
        google.script.run
          .withSuccessHandler(msg => {
            document.getElementById('msg').style.color = 'green';
            document.getElementById('msg').textContent = msg;
          })
          .withFailureHandler(err => {
            document.getElementById('msg').style.color = 'red';
            document.getElementById('msg').textContent = 'Error: ' + err.message;
          })
          .addReagentUnit(data);
      }
    </script>
  `).setTitle('Add Reagent Unit').setWidth(320);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * Appends a new reagent unit row to the reagent_units sheet.
 * Called from the sidebar via google.script.run.
 */
function addReagentUnit(data) {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEETS.REAGENT_UNITS);
  if (!sheet) throw new Error('reagent_units sheet not found. Import data first.');

  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];

  // Generate a simple UUID-like ID
  const id = Utilities.getUuid();
  const now = new Date().toISOString().split('T')[0];

  const row = headers.map(h => {
    switch (h) {
      case 'id':             return id;
      case 'reagent_id':     return data.reagent_id;
      case 'lot':            return data.lot;
      case 'initial_volume': return parseFloat(data.initial_volume || 0);
      case 'current_volume': return parseFloat(data.current_volume || data.initial_volume || 0);
      case 'purchase_price': return parseFloat(data.purchase_price || 0) || '';
      case 'cost_per_ul':    return data.initial_volume && data.purchase_price ?
                               parseFloat(data.purchase_price) / parseFloat(data.initial_volume) : '';
      case 'arrival_date':   return data.arrival_date || now;
      case 'expiration_date':return data.expiration_date || '';
      case 'status':         return data.status || 'Stored';
      case 'created_at':     return now;
      default:               return '';
    }
  });

  sheet.appendRow(row);

  // Colour the new row
  const newRow = sheet.getLastRow();
  sheet.getRange(newRow, 1, 1, headers.length)
    .setBackground(newRow % 2 === 0 ? '#F5F5F5' : '#FFFFFF');

  return `✅ Unit added: ${data.lot} (ID: ${id})`;
}

// ─── INVENTORY SUMMARY VIEW ───────────────────────────────────────────────────

function showInventorySummary() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let inv  = ss.getSheetByName('📋 Inventory Summary');
  if (!inv) inv = ss.insertSheet('📋 Inventory Summary');
  inv.clearContents().clearFormats();

  const units    = getSheetData(SHEETS.REAGENT_UNITS);
  const reagents = getSheetData(SHEETS.REAGENTS);
  const brands   = getSheetData(SHEETS.BRANDS);

  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r; });
  const brandMap = {};
  brands.forEach(b => { brandMap[b.id] = b.name; });

  const now = today();
  const in30 = addDays(now, 30);

  // Title
  inv.getRange(1, 1).setValue('📋 Inventory Summary')
    .setFontSize(16).setFontWeight('bold').setFontColor('#0D47A1');
  inv.getRange(2, 1).setValue('Generated: ' + new Date().toLocaleString()).setFontColor('#757575');

  const headers = ['Reagent', 'Clone', 'Brand', 'Lot', 'Status', 'Volume (µL)', 'Expiration', 'Days Left', 'Price ($)', 'Alert'];
  inv.getRange(4, 1, 1, headers.length)
    .setValues([headers]).setFontWeight('bold').setBackground('#37474F').setFontColor('#FFFFFF');

  const activeStatuses = ['stored', 'in use'];
  const activeUnits = units.filter(u => activeStatuses.includes((u.status || '').toLowerCase()));

  let row = 5;
  activeUnits
    .sort((a, b) => {
      const expA = parseDate(a.expiration_date);
      const expB = parseDate(b.expiration_date);
      if (!expA && !expB) return 0;
      if (!expA) return 1;
      if (!expB) return -1;
      return expA - expB;
    })
    .forEach(u => {
      const reagent  = reagentMap[u.reagent_id] || {};
      const exp      = parseDate(u.expiration_date);
      const daysLeft = exp ? daysDiff(now, exp) : null;

      let alert = '';
      let bgColor = row % 2 === 0 ? '#F5F5F5' : '#FFFFFF';
      if (exp && exp < now) { alert = '🔴 EXPIRED'; bgColor = '#FFCDD2'; }
      else if (exp && exp <= in30) { alert = `⚠️ ${daysLeft}d`; bgColor = '#FFF9C4'; }

      const rowData = [
        reagent.name || u.reagent_id,
        reagent.clone || '',
        brandMap[reagent.brand_id] || '',
        u.lot || '',
        u.status || '',
        parseFloat(u.current_volume || u.initial_volume || 0),
        u.expiration_date || '',
        daysLeft !== null ? daysLeft : '',
        parseFloat(u.purchase_price || 0) || '',
        alert,
      ];
      inv.getRange(row, 1, 1, rowData.length).setValues([rowData]).setBackground(bgColor);
      row++;
    });

  for (let c = 1; c <= headers.length; c++) inv.autoResizeColumn(c);
  inv.setFrozenRows(4);
  ss.setActiveSheet(inv);
}

// ─── LOW STOCK ALERT ──────────────────────────────────────────────────────────

function showLowStockAlert() {
  const units    = getSheetData(SHEETS.REAGENT_UNITS);
  const reagents = getSheetData(SHEETS.REAGENTS);
  const now      = today();

  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r; });

  const activeStatuses = ['stored', 'in use'];
  const countByReagent = {};
  units.forEach(u => {
    if (!activeStatuses.includes((u.status || '').toLowerCase())) return;
    const exp = parseDate(u.expiration_date);
    if (exp && exp < now) return;
    countByReagent[u.reagent_id] = (countByReagent[u.reagent_id] || 0) + 1;
  });

  const low = Object.entries(countByReagent)
    .filter(([, count]) => count < 2)
    .map(([id, count]) => ({ name: (reagentMap[id] || {}).name || id, count }))
    .sort((a, b) => a.count - b.count);

  if (low.length === 0) {
    SpreadsheetApp.getUi().alert('✅ All reagents have adequate stock (≥2 units).');
    return;
  }

  let msg = `${low.length} reagents with low stock (<2 units):\n\n`;
  low.forEach(r => { msg += `• ${r.name}: ${r.count} unit(s)\n`; });
  SpreadsheetApp.getUi().alert('⚠️ Low Stock Alert', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}
