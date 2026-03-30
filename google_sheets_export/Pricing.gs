/**
 * StreamFlow – Pricing & Cost Calculations
 *
 * Recreates Python utils/pricing.py and utils/cost_utils.py logic.
 * Supports the same strategies: cheapest, average, fifo, lifo, fefo.
 */

// ─── PANEL COST CALCULATION ───────────────────────────────────────────────────

/**
 * Calculate cost of a saved panel from its reagents.
 * Equivalent to Python calculate_panel_cost_current().
 *
 * @param {string} panelId
 * @param {string} strategy  'cheapest'|'average'|'fifo'|'lifo'|'fefo'
 * @returns {object}
 */
function calculatePanelCost(panelId, strategy) {
  strategy = strategy || 'cheapest';

  const panels       = getSheetData(SHEETS.PANELS);
  const panelReagents= getSheetData(SHEETS.PANEL_REAGENTS);
  const units        = getSheetData(SHEETS.REAGENT_UNITS);
  const reagents     = getSheetData(SHEETS.REAGENTS);

  const panel = panels.find(p => p.id === panelId);
  if (!panel) return { error: 'Panel not found', panel_id: panelId };

  const prList = panelReagents.filter(pr => pr.panel_id === panelId);
  if (prList.length === 0) {
    return {
      panel_id: panelId, panel_name: panel.name,
      total_cost: 0, breakdown: [],
      warnings: ['Panel has no reagents assigned'], is_complete: false,
    };
  }

  const reagentMap = {};
  reagents.forEach(r => { reagentMap[r.id] = r; });

  let totalCost    = 0;
  const breakdown  = [];
  const warnings   = [];
  let allAvailable = true;

  prList.forEach(pr => {
    const reagent       = reagentMap[pr.reagent_id] || {};
    const reagentName   = reagent.name || pr.reagent_id;
    const volumeNeeded  = parseFloat(pr.volume_used || pr.volume_per_test || 0);
    const catalogPrice  = parseFloat(reagent.price || 0);

    if (volumeNeeded <= 0) {
      warnings.push(`⚠️ ${reagentName}: No volume specified`);
      breakdown.push({ reagent: reagentName, volume_needed: 0, status: 'no_volume_specified', cost: 0 });
      return;
    }

    // Filter valid units for this reagent
    const now = today();
    const activeStatuses = ['stored', 'in use'];
    let availableUnits = units.filter(u => {
      if (u.reagent_id !== pr.reagent_id) return false;
      if (!activeStatuses.includes((u.status || '').toLowerCase())) return false;
      const vol = parseFloat(u.current_volume || u.initial_volume || 0);
      if (vol < volumeNeeded) return false;
      const initVol = parseFloat(u.initial_volume || 0);
      if (initVol <= 0) return false;
      return true;
    });

    // Calculate cost_per_ul for each unit
    availableUnits = availableUnits.map(u => {
      const purchase = parseFloat(u.purchase_price || 0);
      const initVol  = parseFloat(u.initial_volume  || 0);
      const stored   = parseFloat(u.cost_per_ul     || 0);
      let cpu = stored > 0 ? stored :
                (purchase > 0 && initVol > 0) ? purchase / initVol :
                (catalogPrice > 0 && initVol > 0) ? catalogPrice / initVol : 0;
      return { ...u, _cpu: cpu };
    }).filter(u => u._cpu > 0);

    if (availableUnits.length === 0) {
      allAvailable = false;
      warnings.push(`⚠️ ${reagentName}: OUT OF STOCK (need ${volumeNeeded}µL)`);
      breakdown.push({
        reagent: reagentName, channel: pr.channel_display_name,
        volume_needed: volumeNeeded, status: 'out_of_stock', cost: null,
      });
      return;
    }

    const selected = selectUnitByStrategy(availableUnits, strategy);
    if (!selected) {
      allAvailable = false;
      breakdown.push({ reagent: reagentName, volume_needed: volumeNeeded, status: 'no_suitable_unit', cost: null });
      return;
    }

    const reagentCost = selected._cpu * volumeNeeded;
    totalCost += reagentCost;
    breakdown.push({
      reagent:          reagentName,
      channel:          pr.channel_display_name,
      volume_needed:    volumeNeeded,
      using_lot:        selected.lot,
      cost_per_ul:      selected._cpu,
      reagent_cost:     Math.round(reagentCost * 100) / 100,
      available_volume: parseFloat(selected.current_volume || selected.initial_volume),
      unit_expiration:  selected.expiration_date,
      status:           'available',
    });
  });

  return {
    panel_id:     panelId,
    panel_name:   panel.name,
    total_cost:   Math.round(totalCost * 100) / 100,
    breakdown,
    warnings,
    strategy,
    is_complete:  allAvailable,
    num_reagents: breakdown.length,
    num_available: breakdown.filter(b => b.status === 'available').length,
  };
}

// ─── STRATEGY SELECTOR ────────────────────────────────────────────────────────

function selectUnitByStrategy(units, strategy) {
  if (!units || units.length === 0) return null;

  switch (strategy) {
    case 'cheapest':
      return units.reduce((a, b) => a._cpu < b._cpu ? a : b);

    case 'average': {
      const avg = units.reduce((s, u) => s + u._cpu, 0) / units.length;
      return units.reduce((a, b) => Math.abs(a._cpu - avg) < Math.abs(b._cpu - avg) ? a : b);
    }

    case 'fifo': {
      const withDate = units.filter(u => u.arrival_date);
      if (withDate.length === 0) return units[0];
      return withDate.reduce((a, b) => new Date(a.arrival_date) < new Date(b.arrival_date) ? a : b);
    }

    case 'lifo': {
      const withDate = units.filter(u => u.arrival_date);
      if (withDate.length === 0) return units[0];
      return withDate.reduce((a, b) => new Date(a.arrival_date) > new Date(b.arrival_date) ? a : b);
    }

    case 'fefo': {
      const withExp = units.filter(u => u.expiration_date);
      if (withExp.length === 0) return units.reduce((a, b) => a._cpu < b._cpu ? a : b);
      return withExp.reduce((a, b) => new Date(a.expiration_date) < new Date(b.expiration_date) ? a : b);
    }

    default:
      return units.reduce((a, b) => a._cpu < b._cpu ? a : b);
  }
}

// ─── GENERAL REAGENT COST ─────────────────────────────────────────────────────

/**
 * Equivalent to Python calculate_general_reagent_cost_dynamic().
 */
function calculateGeneralReagentCost(panelId) {
  const panelGR      = getSheetData(SHEETS.PANEL_GEN_REAGENTS).filter(r => r.panel_id === panelId);
  const genReagents  = getSheetData(SHEETS.GENERAL_REAGENTS);
  const genUnits     = getSheetData(SHEETS.GEN_REAGENT_UNITS);

  if (panelGR.length === 0) return { total_cost: 0, is_complete: true, missing_data: [], breakdown: [] };

  const grMap = {};
  genReagents.forEach(r => { grMap[r.id] = r; });

  const guMap = {};
  genUnits.forEach(u => { guMap[u.id] = u; });

  let totalCost  = 0;
  const missing  = [];
  const breakdown = [];

  panelGR.forEach(pgr => {
    const gr      = grMap[pgr.general_reagent_id] || {};
    const name    = pgr.display_name || gr.name || pgr.general_reagent_id;
    const price   = parseFloat(gr.price || 0);
    const type    = (pgr.usage_type || pgr.consumption_type || '').toLowerCase();
    const amount  = parseFloat(pgr.volume_used || pgr.consumption_amount || 0);

    if (!type || !amount) {
      missing.push({ reagent: name, missing: 'consumption data not set' });
      breakdown.push({ reagent: name, cost: 0, type: 'general_reagent', details: '⚠️ Consumption not configured' });
      return;
    }
    if (!price) {
      missing.push({ reagent: name, missing: 'price not set' });
      breakdown.push({ reagent: name, cost: 0, type: 'general_reagent', details: '⚠️ Price not set' });
      return;
    }

    let cost = 0;
    let details = '';

    if (type === 'ml') {
      let vol = 0;
      const unit = guMap[pgr.preferred_unit_id || pgr.general_reagent_unit_id];
      if (unit && parseFloat(unit.volume || 0) > 0) {
        vol = parseFloat(unit.volume);
        details = `Unit volume (${vol} mL)`;
      } else if (parseFloat(gr.standard_volume || 0) > 0) {
        vol = parseFloat(gr.standard_volume);
        details = `Standard volume (${vol} mL)`;
      }
      if (vol > 0) {
        cost = (price / vol) * amount;
        details = `${amount} mL @ $${(price / vol).toFixed(4)}/mL`;
      } else {
        missing.push({ reagent: name, missing: 'volume missing' });
        breakdown.push({ reagent: name, cost: 0, type: 'general_reagent', details: '⚠️ Volume missing' });
        return;
      }
    } else if (type === 'units') {
      const totalUnits = parseFloat(gr.standard_units || 0) || 1;
      cost = (price / totalUnits) * amount;
      details = `${amount} units @ $${(price / totalUnits).toFixed(4)}/unit`;
    } else {
      missing.push({ reagent: name, missing: `unknown type: ${type}` });
      breakdown.push({ reagent: name, cost: 0, type: 'general_reagent', details: `⚠️ Unknown type: ${type}` });
      return;
    }

    totalCost += cost;
    breakdown.push({ reagent: name, cost: Math.round(cost * 10000) / 10000, type: 'general_reagent', details });
  });

  return { total_cost: Math.round(totalCost * 10000) / 10000, is_complete: missing.length === 0, missing_data: missing, breakdown };
}

// ─── COMPLETE PANEL COST ──────────────────────────────────────────────────────

/**
 * Full cost (antibodies + general reagents) for a panel.
 * Equivalent to Python get_panel_cost_breakdown().
 */
function getFullPanelCost(panelId, strategy) {
  strategy = strategy || 'cheapest';
  const ab = calculatePanelCost(panelId, strategy);
  const gr = calculateGeneralReagentCost(panelId);

  const totalCost = (ab.total_cost || 0) + (gr.total_cost || 0);
  const isComplete = (ab.is_complete !== false) && gr.is_complete;
  const breakdown  = [...(ab.breakdown || []), ...(gr.breakdown || [])];
  const missing    = [...(ab.warnings || [])];
  gr.missing_data.forEach(m => missing.push(`${m.reagent} (${m.missing})`));

  return { panel_id: panelId, panel_name: ab.panel_name, total_cost: Math.round(totalCost * 100) / 100, is_complete: isComplete, missing_prices: missing, breakdown };
}

// ─── CALCULATE ALL PANEL COSTS (writes to Panels sheet) ──────────────────────

function calculateAllPanelCosts() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const panelSheet = ss.getSheetByName(SHEETS.PANELS);
  if (!panelSheet || panelSheet.getLastRow() < 2) {
    SpreadsheetApp.getUi().alert('No panels found. Import panels.csv first.');
    return;
  }

  const headers   = panelSheet.getRange(1, 1, 1, panelSheet.getLastColumn()).getValues()[0];
  const idCol     = headers.indexOf('id') + 1;
  const nameCol   = headers.indexOf('name') + 1;
  const panels    = getSheetData(SHEETS.PANELS);

  // Add or find cost columns
  let costCol = headers.indexOf('calculated_cost') + 1;
  let statusCol = headers.indexOf('cost_status') + 1;

  if (costCol === 0) {
    costCol = panelSheet.getLastColumn() + 1;
    panelSheet.getRange(1, costCol).setValue('calculated_cost').setFontWeight('bold').setBackground('#1565C0').setFontColor('#FFFFFF');
  }
  if (statusCol === 0) {
    statusCol = panelSheet.getLastColumn() + 1;
    panelSheet.getRange(1, statusCol).setValue('cost_status').setFontWeight('bold').setBackground('#1565C0').setFontColor('#FFFFFF');
  }

  let done = 0;
  panels.forEach((panel, i) => {
    const result = getFullPanelCost(panel.id);
    const dataRow = i + 2;
    panelSheet.getRange(dataRow, costCol).setValue(result.total_cost);
    panelSheet.getRange(dataRow, statusCol).setValue(result.is_complete ? '✅ Complete' : `⚠️ Missing ${result.missing_prices.length}`);
    done++;
  });

  SpreadsheetApp.getUi().alert(`✅ Calculated costs for ${done} panels.\nCheck the "${SHEETS.PANELS}" sheet for calculated_cost column.`);
}

// ─── COST REPORT SHEET ────────────────────────────────────────────────────────

function showCostReport() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let report = ss.getSheetByName('💰 Cost Report');
  if (!report) report = ss.insertSheet('💰 Cost Report');
  report.clearContents().clearFormats();

  const panels = getSheetData(SHEETS.PANELS);

  report.getRange(1, 1).setValue('💰 StreamFlow – Panel Cost Report')
    .setFontSize(16).setFontWeight('bold').setFontColor('#0D47A1');
  report.getRange(2, 1).setValue('Generated: ' + new Date().toLocaleString()).setFontColor('#757575');

  const headers = ['Panel Name', 'Status', 'Total Cost ($)', 'Antibody Cost ($)', 'Gen. Reagent Cost ($)', 'Reagents', 'Available', 'Missing'];
  report.getRange(4, 1, 1, headers.length)
    .setValues([headers]).setFontWeight('bold').setBackground('#37474F').setFontColor('#FFFFFF');

  let row = 5;
  let grandTotal = 0;

  panels.forEach(panel => {
    const ab = calculatePanelCost(panel.id, 'cheapest');
    const gr = calculateGeneralReagentCost(panel.id);
    const total = (ab.total_cost || 0) + (gr.total_cost || 0);
    grandTotal += total;

    const rowData = [
      panel.name,
      ab.is_complete && gr.is_complete ? '✅' : '⚠️',
      total.toFixed(2),
      (ab.total_cost || 0).toFixed(2),
      (gr.total_cost || 0).toFixed(2),
      ab.num_reagents || 0,
      ab.num_available || 0,
      ab.is_complete ? '' : ab.warnings.join('; '),
    ];
    report.getRange(row, 1, 1, rowData.length).setValues([rowData]);
    report.getRange(row, 1, 1, rowData.length).setBackground(row % 2 === 0 ? '#F5F5F5' : '#FFFFFF');
    row++;
  });

  // Grand total
  row++;
  report.getRange(row, 1).setValue('GRAND TOTAL').setFontWeight('bold');
  report.getRange(row, 3).setValue(grandTotal.toFixed(2)).setFontWeight('bold').setFontColor('#1565C0');

  for (let c = 1; c <= headers.length; c++) report.autoResizeColumn(c);
  report.setFrozenRows(4);
  ss.setActiveSheet(report);
}
