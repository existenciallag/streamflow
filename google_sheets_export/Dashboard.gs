/**
 * StreamFlow – Dashboard Metrics
 *
 * Recreates the Python dashboard_metrics.py logic using spreadsheet data.
 * All functions read from the named sheets imported from the CSV export.
 */

// ─── HELPERS ──────────────────────────────────────────────────────────────────

/** Return all data from a sheet as an array of plain objects (header row → keys). */
function getSheetData(sheetName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(sheetName);
  if (!sheet || sheet.getLastRow() < 2) return [];

  const [headers, ...rows] = sheet.getDataRange().getValues();
  return rows.map(row => {
    const obj = {};
    headers.forEach((h, i) => { obj[h] = row[i]; });
    return obj;
  });
}

/** Today as a Date (midnight). */
function today() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Add N days to a date. */
function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

/** Parse a date string like '2025-06-01' into a Date. Returns null for blanks. */
function parseDate(val) {
  if (!val) return null;
  const d = new Date(val);
  return isNaN(d.getTime()) ? null : d;
}

/** Day difference between two dates (b - a, in whole days). */
function daysDiff(a, b) {
  return Math.round((b - a) / 86400000);
}

// ─── STOCK HEALTH ─────────────────────────────────────────────────────────────

/**
 * Equivalent to Python get_stock_health_metrics().
 * Returns { uniqueReagents, valueAtRisk, lowStockCount, expiredUnits }
 */
function getStockHealthMetrics() {
  const units = getSheetData(SHEETS.REAGENT_UNITS);
  const now   = today();
  const in30  = addDays(now, 30);

  const activeStatuses = ['stored', 'in use'];
  const activeUnits = units.filter(u =>
    activeStatuses.includes((u.status || '').toLowerCase())
  );

  // Unique reagents in stock
  const uniqueReagentIds = new Set(activeUnits.map(u => u.reagent_id));
  const uniqueReagents = uniqueReagentIds.size;

  // Value expiring in ≤ 30 days
  let valueAtRisk = 0;
  activeUnits.forEach(u => {
    const exp = parseDate(u.expiration_date);
    if (exp && exp >= now && exp <= in30) {
      valueAtRisk += parseFloat(u.purchase_price || 0);
    }
  });

  // Reagents with < 2 available non-expired units
  const unitCountByReagent = {};
  activeUnits.forEach(u => {
    const exp = parseDate(u.expiration_date);
    if (!exp || exp > now) {
      unitCountByReagent[u.reagent_id] = (unitCountByReagent[u.reagent_id] || 0) + 1;
    }
  });
  const lowStockCount = Object.values(unitCountByReagent).filter(c => c < 2).length;

  // Expired units still showing as active
  const expiredUnits = activeUnits.filter(u => {
    const exp = parseDate(u.expiration_date);
    return exp && exp < now;
  }).length;

  return { uniqueReagents, valueAtRisk, lowStockCount, expiredUnits };
}

// ─── EXPIRING INVENTORY ───────────────────────────────────────────────────────

/**
 * Equivalent to Python get_expiring_inventory(days, limit).
 * Returns rows sorted by purchase_price DESC.
 */
function getExpiringInventory(days, limit) {
  days  = days  || 30;
  limit = limit || 10;

  const units    = getSheetData(SHEETS.REAGENT_UNITS);
  const reagents = getSheetData(SHEETS.REAGENTS);
  const now      = today();
  const cutoff   = addDays(now, days);

  // Build reagent id → name map
  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r.name; });

  const activeStatuses = ['stored', 'in use'];

  const expiring = units
    .filter(u => {
      const exp = parseDate(u.expiration_date);
      return exp && exp >= now && exp <= cutoff &&
             activeStatuses.includes((u.status || '').toLowerCase());
    })
    .map(u => ({
      reagent_name:          reagentMap[u.reagent_id] || u.reagent_id,
      expiration_date:       u.expiration_date,
      days_until_expiration: daysDiff(now, parseDate(u.expiration_date)),
      purchase_price:        parseFloat(u.purchase_price || 0),
      initial_volume:        u.initial_volume,
      lot:                   u.lot,
      status:                u.status,
      unit_id:               u.id,
    }))
    .sort((a, b) => b.purchase_price - a.purchase_price || a.days_until_expiration - b.days_until_expiration)
    .slice(0, limit);

  return expiring;
}

// ─── EXPIRED INVENTORY ────────────────────────────────────────────────────────

function getExpiredInventory(limit) {
  limit = limit || 20;

  const units    = getSheetData(SHEETS.REAGENT_UNITS);
  const reagents = getSheetData(SHEETS.REAGENTS);
  const now      = today();

  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r.name; });

  const activeStatuses = ['stored', 'in use'];

  return units
    .filter(u => {
      const exp = parseDate(u.expiration_date);
      return exp && exp < now &&
             activeStatuses.includes((u.status || '').toLowerCase());
    })
    .map(u => ({
      reagent_name:   reagentMap[u.reagent_id] || u.reagent_id,
      expiration_date: u.expiration_date,
      days_expired:    daysDiff(parseDate(u.expiration_date), now),
      purchase_price:  parseFloat(u.purchase_price || 0),
      lot:             u.lot,
      status:          u.status,
    }))
    .sort((a, b) => b.purchase_price - a.purchase_price)
    .slice(0, limit);
}

// ─── PANEL READINESS ──────────────────────────────────────────────────────────

/**
 * Equivalent to Python get_panel_readiness_status().
 * Returns an array of panel readiness objects.
 */
function getPanelReadinessStatus() {
  const panels       = getSheetData(SHEETS.PANELS);
  const panelReagents= getSheetData(SHEETS.PANEL_REAGENTS);
  const units        = getSheetData(SHEETS.REAGENT_UNITS);
  const now          = today();

  const activeStatuses = ['stored', 'in use'];

  // For each reagent_id → list of valid unit expiration dates
  const availableByReagent = {};
  units.forEach(u => {
    if (!activeStatuses.includes((u.status || '').toLowerCase())) return;
    const exp = parseDate(u.expiration_date);
    if (exp && exp < now) return;  // expired

    if (!availableByReagent[u.reagent_id]) availableByReagent[u.reagent_id] = [];
    availableByReagent[u.reagent_id].push(exp);
  });

  // Group panel_reagents by panel_id
  const prByPanel = {};
  panelReagents.forEach(pr => {
    if (!prByPanel[pr.panel_id]) prByPanel[pr.panel_id] = [];
    prByPanel[pr.panel_id].push(pr.reagent_id);
  });

  return panels.map(panel => {
    const reagentIds = prByPanel[panel.id] || [];
    const total = reagentIds.length;
    let available = 0;
    let soonestExp = null;

    reagentIds.forEach(rid => {
      const exps = availableByReagent[rid];
      if (exps && exps.length > 0) {
        available++;
        const minExp = exps.filter(Boolean).sort((a, b) => a - b)[0];
        if (minExp && (!soonestExp || minExp < soonestExp)) soonestExp = minExp;
      }
    });

    return {
      panel_id:           panel.id,
      panel_name:         panel.name,
      total_reagents:     total,
      available_reagents: available,
      is_complete:        total > 0 && available === total,
      next_expiration:    soonestExp ? soonestExp.toISOString().split('T')[0] : null,
      status:             total === 0 ? 'empty' : available === total ? '✅ Ready' : `⚠️ ${available}/${total}`,
    };
  });
}

// ─── COST INSIGHTS ────────────────────────────────────────────────────────────

function getCostInsights() {
  const units    = getSheetData(SHEETS.REAGENT_UNITS);
  const reagents = getSheetData(SHEETS.REAGENTS);
  const now      = today();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r.name; });

  const activeStatuses = ['stored', 'in use'];

  // Top 5 expensive reagents in stock
  const valueByReagent = {};
  units.forEach(u => {
    if (!activeStatuses.includes((u.status || '').toLowerCase())) return;
    const price = parseFloat(u.purchase_price || 0);
    if (!price) return;
    const name = reagentMap[u.reagent_id] || u.reagent_id;
    valueByReagent[name] = (valueByReagent[name] || 0) + price;
  });
  const topExpensive = Object.entries(valueByReagent)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, total]) => ({ name, total_value: total }));

  // Value expired this month
  let expiredValueThisMonth = 0;
  units.forEach(u => {
    const exp = parseDate(u.expiration_date);
    if (exp && exp >= monthStart && exp < now) {
      expiredValueThisMonth += parseFloat(u.purchase_price || 0);
    }
  });

  // Average reagent age (days since arrival)
  const ages = units
    .filter(u => u.arrival_date && (u.status || '').toLowerCase() === 'stored')
    .map(u => daysDiff(parseDate(u.arrival_date), now))
    .filter(d => d >= 0);
  const avgAge = ages.length > 0 ? ages.reduce((a, b) => a + b, 0) / ages.length : 0;

  return { topExpensive, expiredValueThisMonth, avgAge: Math.round(avgAge) };
}

// ─── DASHBOARD SHEET ──────────────────────────────────────────────────────────

function createDashboardSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let dash = ss.getSheetByName(SHEETS.DASHBOARD);
  if (!dash) dash = ss.insertSheet(SHEETS.DASHBOARD, 0);
  dash.clearContents();
  dash.clearFormats();
  dash.setColumnWidth(1, 30);
  dash.setColumnWidth(2, 220);
  dash.setColumnWidth(3, 160);
  dash.setColumnWidth(4, 160);
  dash.setColumnWidth(5, 160);
  dash.setColumnWidth(6, 160);

  dash.getRange('B1').setValue('🔬 StreamFlow – Flow Cytometry Lab Manager')
    .setFontSize(18).setFontWeight('bold').setFontColor('#0D47A1');
  dash.getRange('B2').setValue('Dashboard – updated: ' + new Date().toLocaleString())
    .setFontSize(10).setFontColor('#757575');

  refreshDashboard();
  ss.setActiveSheet(dash);
}

function refreshDashboard() {
  const ss   = SpreadsheetApp.getActiveSpreadsheet();
  const dash = ss.getSheetByName(SHEETS.DASHBOARD);
  if (!dash) { SpreadsheetApp.getUi().alert('Dashboard sheet not found. Run Setup first.'); return; }

  // Clear content below header
  if (dash.getLastRow() > 2) dash.getRange(3, 1, dash.getLastRow() - 2, dash.getLastColumn()).clearContent().clearFormat();

  let row = 4;

  // ── STOCK HEALTH ──
  row = writeSectionHeader(dash, row, '📦 Stock Health');
  const h = getStockHealthMetrics();
  row = writeKpiRow(dash, row, [
    ['Reagent Types in Stock', h.uniqueReagents,       '#1565C0', '#E3F2FD'],
    ['Value Expiring (30 days)', '$' + h.valueAtRisk.toFixed(2), '#E65100', '#FFF3E0'],
    ['Low Stock Reagents',      h.lowStockCount,        '#C62828', '#FFEBEE'],
    ['Expired Units (Active)',  h.expiredUnits,         '#4A148C', '#F3E5F5'],
  ]);
  row++;

  // ── EXPIRING SOON ──
  row = writeSectionHeader(dash, row, '⏰ Expiring in Next 30 Days (Top 10 by Value)');
  const expRows = getExpiringInventory(30, 10);
  if (expRows.length === 0) {
    dash.getRange(row, 2).setValue('No reagents expiring in the next 30 days ✅').setFontColor('#388E3C');
    row += 2;
  } else {
    const expHeaders = ['Reagent', 'Lot', 'Expiration Date', 'Days Left', 'Price ($)', 'Status'];
    writeTableHeaders(dash, row, expHeaders);
    row++;
    expRows.forEach(r => {
      const rowData = [r.reagent_name, r.lot, r.expiration_date, r.days_until_expiration, r.purchase_price.toFixed(2), r.status];
      dash.getRange(row, 2, 1, rowData.length).setValues([rowData]);
      const bgColor = r.days_until_expiration <= 7 ? '#FFCDD2' : r.days_until_expiration <= 14 ? '#FFE0B2' : '#FFFDE7';
      dash.getRange(row, 2, 1, rowData.length).setBackground(bgColor);
      row++;
    });
    row++;
  }

  // ── PANEL READINESS ──
  row = writeSectionHeader(dash, row, '🧬 Panel Readiness');
  const panels = getPanelReadinessStatus();
  if (panels.length === 0) {
    dash.getRange(row, 2).setValue('No panels found. Import panels.csv first.');
    row += 2;
  } else {
    const pHeaders = ['Panel Name', 'Total Reagents', 'Available', 'Next Expiration', 'Status'];
    writeTableHeaders(dash, row, pHeaders);
    row++;
    panels.sort((a, b) => a.is_complete === b.is_complete ? 0 : a.is_complete ? 1 : -1).forEach(p => {
      const rowData = [p.panel_name, p.total_reagents, p.available_reagents, p.next_expiration || '', p.status];
      dash.getRange(row, 2, 1, rowData.length).setValues([rowData]);
      dash.getRange(row, 2, 1, rowData.length).setBackground(p.is_complete ? '#E8F5E9' : '#FFEBEE');
      row++;
    });
    row++;
  }

  // ── COST INSIGHTS ──
  row = writeSectionHeader(dash, row, '💰 Cost Insights');
  const costs = getCostInsights();
  dash.getRange(row, 2).setValue('Expired value this month: $' + costs.expiredValueThisMonth.toFixed(2)).setFontColor('#C62828');
  dash.getRange(row, 4).setValue('Avg reagent age (stored): ' + costs.avgAge + ' days');
  row += 2;

  const cHeaders = ['Reagent', 'Total Stock Value ($)'];
  writeTableHeaders(dash, row, cHeaders);
  row++;
  costs.topExpensive.forEach(c => {
    dash.getRange(row, 2, 1, 2).setValues([[c.name, c.total_value.toFixed(2)]]);
    row++;
  });
  row++;

  // Update timestamp
  dash.getRange('B2').setValue('Dashboard – updated: ' + new Date().toLocaleString());
  SpreadsheetApp.getActiveSpreadsheet().setActiveSheet(dash);
}

// ─── DASHBOARD WRITE HELPERS ──────────────────────────────────────────────────

function writeSectionHeader(sheet, row, title) {
  const cell = sheet.getRange(row, 2, 1, 5);
  cell.merge()
    .setValue(title)
    .setFontSize(13)
    .setFontWeight('bold')
    .setFontColor('#FFFFFF')
    .setBackground('#1565C0');
  return row + 1;
}

function writeKpiRow(sheet, startRow, kpis) {
  kpis.forEach((kpi, i) => {
    const [label, value, textColor, bgColor] = kpi;
    const col = 2 + i;
    sheet.getRange(startRow, col).setValue(label).setFontWeight('bold').setFontSize(9).setFontColor('#555555');
    sheet.getRange(startRow + 1, col).setValue(value).setFontSize(18).setFontWeight('bold').setFontColor(textColor).setBackground(bgColor).setHorizontalAlignment('center');
  });
  return startRow + 3;
}

function writeTableHeaders(sheet, row, headers) {
  const range = sheet.getRange(row, 2, 1, headers.length);
  range.setValues([headers])
    .setFontWeight('bold')
    .setBackground('#37474F')
    .setFontColor('#FFFFFF');
}

// ─── MENU ACTIONS ─────────────────────────────────────────────────────────────

function showStockHealth() {
  const h = getStockHealthMetrics();
  SpreadsheetApp.getUi().alert('📦 Stock Health',
    `Reagent types in stock: ${h.uniqueReagents}\n` +
    `Value expiring in 30 days: $${h.valueAtRisk.toFixed(2)}\n` +
    `Low stock reagents (< 2 units): ${h.lowStockCount}\n` +
    `Expired units still active: ${h.expiredUnits}`,
    SpreadsheetApp.getUi().ButtonSet.OK);
}

function showExpiringSoon() {
  const items = getExpiringInventory(30, 20);
  if (items.length === 0) {
    SpreadsheetApp.getUi().alert('✅ No reagents expiring in the next 30 days.');
    return;
  }
  let msg = `${items.length} reagents expiring soon:\n\n`;
  items.forEach(r => {
    msg += `• ${r.reagent_name} — ${r.expiration_date} (${r.days_until_expiration}d) — $${r.purchase_price.toFixed(2)}\n`;
  });
  SpreadsheetApp.getUi().alert('⏰ Expiring Reagents', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}

function showPanelReadiness() {
  const panels = getPanelReadinessStatus();
  const ready  = panels.filter(p => p.is_complete).length;
  const notReady = panels.length - ready;
  let msg = `Total panels: ${panels.length}\n✅ Ready: ${ready}\n⚠️ Incomplete: ${notReady}\n\n`;
  panels.filter(p => !p.is_complete).forEach(p => {
    msg += `• ${p.panel_name}: ${p.available_reagents}/${p.total_reagents} reagents\n`;
  });
  SpreadsheetApp.getUi().alert('🧬 Panel Readiness', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}
