/**
 * StreamFlow – Panel Management
 *
 * Views and helpers for panels, panel reagents, and panel builder.
 * Equivalent to ui/panels.py and ui/panel_builder.py
 */

// ─── PANEL SUMMARY SHEET ──────────────────────────────────────────────────────

function showPanelsSummary() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let panelSheet = ss.getSheetByName('🧬 Panels Summary');
  if (!panelSheet) panelSheet = ss.insertSheet('🧬 Panels Summary');
  panelSheet.clearContents().clearFormats();

  const panels       = getSheetData(SHEETS.PANELS);
  const panelReagents= getSheetData(SHEETS.PANEL_REAGENTS);
  const areas        = getSheetData(SHEETS.PANEL_AREAS);
  const diseaseCats  = getSheetData(SHEETS.PANEL_DISEASE_CATS);

  const areaMap = {};
  areas.forEach(a => { areaMap[a.id] = a.name; });
  const catMap = {};
  diseaseCats.forEach(c => { catMap[c.id] = c.name; });

  // Count reagents per panel
  const reagentCount = {};
  panelReagents.forEach(pr => {
    reagentCount[pr.panel_id] = (reagentCount[pr.panel_id] || 0) + 1;
  });

  // Get readiness data
  const readiness = {};
  getPanelReadinessStatus().forEach(p => { readiness[p.panel_id] = p; });

  // Title
  panelSheet.getRange(1, 1).setValue('🧬 Panel Registry')
    .setFontSize(16).setFontWeight('bold').setFontColor('#0D47A1');
  panelSheet.getRange(2, 1).setValue('Generated: ' + new Date().toLocaleString()).setFontColor('#757575');

  const headers = [
    'Panel Name', 'Version', 'Status', 'Area', 'Disease Category',
    'Reagents', 'Readiness', 'Next Expiration',
    'Acq. Protocol', 'Comp. Protocol', 'Analysis Protocol',
    'Created', 'Updated',
  ];
  panelSheet.getRange(4, 1, 1, headers.length)
    .setValues([headers]).setFontWeight('bold').setBackground('#37474F').setFontColor('#FFFFFF');

  let row = 5;
  panels
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    .forEach(p => {
      const r = readiness[p.id] || {};
      const rowData = [
        p.name || '',
        p.version || '1.0.0',
        p.status || '',
        areaMap[p.area_id] || p.area_id || '',
        catMap[p.disease_category_id] || p.disease_category_id || '',
        reagentCount[p.id] || 0,
        r.status || '',
        r.next_expiration || '',
        p.acquisition_protocol_name || '',
        p.compensation_name || '',
        p.analysis_protocol_name || '',
        p.created_at ? p.created_at.toString().split('T')[0] : '',
        p.updated_at ? p.updated_at.toString().split('T')[0] : '',
      ];
      panelSheet.getRange(row, 1, 1, rowData.length).setValues([rowData]);
      const bgColor = r.is_complete ? '#E8F5E9' : (r.total_reagents > 0 ? '#FFEBEE' : '#F5F5F5');
      panelSheet.getRange(row, 1, 1, rowData.length).setBackground(bgColor);
      row++;
    });

  for (let c = 1; c <= headers.length; c++) panelSheet.autoResizeColumn(c);
  panelSheet.setFrozenRows(4);
  ss.setActiveSheet(panelSheet);
}

// ─── PANEL DETAIL VIEW ────────────────────────────────────────────────────────

/**
 * Show a selected panel's full reagent list in a sidebar.
 * The user selects a panel name from a dropdown.
 */
function showPanelDetailDialog() {
  const panels  = getSheetData(SHEETS.PANELS);
  const options = panels.map(p => `<option value="${p.id}">${p.name} (v${p.version || '1.0.0'})</option>`).join('\n');

  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: Arial, sans-serif; padding: 12px; font-size: 13px; }
      select, button { width: 100%; padding: 8px; margin: 6px 0; border-radius: 4px; }
      button { background: #1565C0; color: white; border: none; cursor: pointer; }
      table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }
      th { background: #37474F; color: white; padding: 6px; text-align: left; }
      td { border-bottom: 1px solid #ddd; padding: 5px; }
      tr:nth-child(even) { background: #F5F5F5; }
      .cost { font-weight: bold; color: #1565C0; }
    </style>
    <h3>🧬 Panel Detail</h3>
    <select id="panel">${options}</select>
    <button onclick="load()">Load Panel ➜</button>
    <div id="result"></div>
    <script>
      function load() {
        const id = document.getElementById('panel').value;
        document.getElementById('result').innerHTML = '<p>Loading…</p>';
        google.script.run
          .withSuccessHandler(html => {
            document.getElementById('result').innerHTML = html;
          })
          .getPanelDetailHtml(id);
      }
    </script>
  `).setTitle('Panel Detail').setWidth(460);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * Returns an HTML string with a panel's reagent table + cost.
 * Called from the sidebar via google.script.run.
 */
function getPanelDetailHtml(panelId) {
  const panels        = getSheetData(SHEETS.PANELS);
  const panelReagents = getSheetData(SHEETS.PANEL_REAGENTS);
  const reagents      = getSheetData(SHEETS.REAGENTS);
  const fluorochromes = getSheetData(SHEETS.FLUOROCHROMES);

  const panel = panels.find(p => p.id === panelId);
  if (!panel) return '<p style="color:red">Panel not found.</p>';

  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r; });
  const fluoMap = {};
  fluorochromes.forEach(f => { fluoMap[f.id] = f.name; });

  const prList = panelReagents
    .filter(pr => pr.panel_id === panelId)
    .sort((a, b) => (a.display_order || 99) - (b.display_order || 99));

  const costResult = calculatePanelCost(panelId, 'cheapest');

  const costByReagent = {};
  (costResult.breakdown || []).forEach(b => { costByReagent[b.reagent] = b; });

  let rows = prList.map(pr => {
    const r      = reagentMap[pr.reagent_id] || {};
    const name   = r.name || pr.reagent_id;
    const clone  = r.clone || '';
    const fluo   = pr.fluorochrome_name || fluoMap[pr.fluorochrome_id] || '';
    const channel= pr.channel_display_name || '';
    const vol    = pr.volume_used || pr.volume_per_test || '';
    const cb     = costByReagent[name];
    const cost   = cb && cb.status === 'available' ? `$${cb.reagent_cost.toFixed(2)}` : (cb ? '⚠️ OOS' : '—');
    return `<tr>
      <td>${name}</td>
      <td>${clone}</td>
      <td>${fluo}</td>
      <td>${channel}</td>
      <td>${vol} µL</td>
      <td>${cost}</td>
    </tr>`;
  }).join('');

  return `
    <h4>${panel.name} <small style="color:#777">v${panel.version || '1.0.0'} – ${panel.status || ''}</small></h4>
    <table>
      <tr><th>Reagent</th><th>Clone</th><th>Fluorochrome</th><th>Channel</th><th>Volume</th><th>Cost/Test</th></tr>
      ${rows || '<tr><td colspan="6">No reagents assigned</td></tr>'}
    </table>
    <p class="cost">Total cost/test: $${costResult.total_cost.toFixed(2)}
      ${costResult.is_complete ? ' ✅' : ' ⚠️ Incomplete'}
    </p>
  `;
}

// ─── PANEL BUILDER (ADD REAGENT TO PANEL) ─────────────────────────────────────

function showAddReagentToPanelForm() {
  const panels   = getSheetData(SHEETS.PANELS);
  const reagents = getSheetData(SHEETS.REAGENTS);
  const fluoros  = getSheetData(SHEETS.FLUOROCHROMES);

  const pOpts = panels.map(p => `<option value="${p.id}">${p.name} (v${p.version || '1.0.0'})</option>`).join('\n');
  const rOpts = reagents.map(r => `<option value="${r.id}">${r.name} (${r.clone || ''})</option>`).join('\n');
  const fOpts = fluoros.map(f => `<option value="${f.name}">${f.name}</option>`).join('\n');

  const html = HtmlService.createHtmlOutput(`
    <style>
      body { font-family: Arial, sans-serif; padding: 12px; font-size: 13px; }
      label { display: block; margin-top: 10px; font-weight: bold; }
      input, select { width: 100%; padding: 6px; margin-top: 4px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
      button { margin-top: 16px; width: 100%; padding: 10px; background: #1565C0; color: white; border: none; border-radius: 4px; cursor: pointer; }
      #msg { margin-top: 8px; font-weight: bold; }
    </style>
    <h3>➕ Add Reagent to Panel</h3>

    <label>Panel *</label>
    <select id="panel_id"><option value="">-- select panel --</option>${pOpts}</select>

    <label>Reagent *</label>
    <select id="reagent_id"><option value="">-- select reagent --</option>${rOpts}</select>

    <label>Fluorochrome</label>
    <select id="fluorochrome"><option value="">-- select --</option>${fOpts}</select>

    <label>Channel Display Name</label>
    <input id="channel" placeholder="e.g. BV421-A">

    <label>Volume per Test (µL) *</label>
    <input id="volume" type="number" step="0.1" placeholder="e.g. 5.0">

    <label>Display Order</label>
    <input id="order" type="number" placeholder="1">

    <button onclick="submit()">Add Reagent</button>
    <p id="msg"></p>

    <script>
      function submit() {
        const data = {
          panel_id:             document.getElementById('panel_id').value,
          reagent_id:           document.getElementById('reagent_id').value,
          fluorochrome_name:    document.getElementById('fluorochrome').value,
          channel_display_name: document.getElementById('channel').value,
          volume_used:          document.getElementById('volume').value,
          display_order:        document.getElementById('order').value,
        };
        if (!data.panel_id || !data.reagent_id || !data.volume_used) {
          document.getElementById('msg').style.color = 'red';
          document.getElementById('msg').textContent = 'Panel, Reagent and Volume are required.';
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
          .addReagentToPanel(data);
      }
    </script>
  `).setTitle('Add Reagent to Panel').setWidth(340);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * Appends a new row to the panel_reagents sheet.
 */
function addReagentToPanel(data) {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEETS.PANEL_REAGENTS);
  if (!sheet) throw new Error('panel_reagents sheet not found. Import data first.');

  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const now     = new Date().toISOString().split('T')[0];
  const id      = Utilities.getUuid();

  const row = headers.map(h => {
    switch (h) {
      case 'id':                   return id;
      case 'panel_id':             return data.panel_id;
      case 'reagent_id':           return data.reagent_id;
      case 'fluorochrome_name':    return data.fluorochrome_name || '';
      case 'channel_display_name': return data.channel_display_name || '';
      case 'volume_used':
      case 'volume_per_test':      return parseFloat(data.volume_used || 0);
      case 'display_order':        return parseInt(data.display_order || 99);
      case 'created_at':           return now;
      default:                     return '';
    }
  });

  sheet.appendRow(row);
  return `✅ Reagent added to panel (ID: ${id})`;
}

// ─── PURCHASE ORDER SUMMARY ───────────────────────────────────────────────────

function showPurchaseOrders() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let poSheet = ss.getSheetByName('🛒 Purchase Orders');
  if (!poSheet) poSheet = ss.insertSheet('🛒 Purchase Orders');
  poSheet.clearContents().clearFormats();

  const orders = getSheetData(SHEETS.PURCHASE_ORDERS);
  const items  = getSheetData(SHEETS.PURCHASE_ORDER_ITEMS);
  const brands = getSheetData(SHEETS.BRANDS);
  const reagents = getSheetData(SHEETS.REAGENTS);

  const brandMap   = {};
  brands.forEach(b => { brandMap[b.id] = b.name; });
  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r.name; });

  poSheet.getRange(1, 1).setValue('🛒 Purchase Orders')
    .setFontSize(16).setFontWeight('bold').setFontColor('#0D47A1');
  poSheet.getRange(2, 1).setValue('Generated: ' + new Date().toLocaleString()).setFontColor('#757575');

  let row = 4;
  orders.forEach(order => {
    // Order header
    poSheet.getRange(row, 1, 1, 6).merge()
      .setValue(`Order #${order.order_number || order.id} — ${brandMap[order.brand_id] || order.brand_id} — ${order.status || ''} — ${order.order_date || ''}`)
      .setFontWeight('bold').setBackground('#E3F2FD');
    row++;

    const orderItems = items.filter(i => i.purchase_order_id === order.id);
    if (orderItems.length > 0) {
      const iHeaders = ['Reagent', 'Quantity', 'Unit Price ($)', 'Total ($)', 'Lot', 'Status'];
      poSheet.getRange(row, 1, 1, iHeaders.length)
        .setValues([iHeaders]).setFontWeight('bold').setBackground('#37474F').setFontColor('#FFFFFF');
      row++;

      let orderTotal = 0;
      orderItems.forEach(item => {
        const qty   = parseFloat(item.quantity || 1);
        const price = parseFloat(item.unit_price || 0);
        const total = qty * price;
        orderTotal += total;
        poSheet.getRange(row, 1, 1, 6).setValues([[
          reagentMap[item.reagent_id] || item.reagent_id,
          qty, price.toFixed(2), total.toFixed(2),
          item.lot || '', item.status || '',
        ]]).setBackground(row % 2 === 0 ? '#F5F5F5' : '#FFFFFF');
        row++;
      });
      poSheet.getRange(row, 1).setValue('Order Total:').setFontWeight('bold');
      poSheet.getRange(row, 4).setValue(orderTotal.toFixed(2)).setFontWeight('bold').setFontColor('#1565C0');
    }
    row += 2;
  });

  for (let c = 1; c <= 6; c++) poSheet.autoResizeColumn(c);
  ss.setActiveSheet(poSheet);
}
