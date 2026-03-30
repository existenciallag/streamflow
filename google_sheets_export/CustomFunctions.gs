/**
 * StreamFlow – Custom Spreadsheet Functions
 *
 * These can be used directly in cells, like:
 *   =SF_PANEL_COST("panel-uuid-here")
 *   =SF_STOCK_STATUS("reagent-uuid-here")
 *   =SF_DAYS_TO_EXPIRY("2025-06-01")
 *   =SF_EXPIRY_ALERT("2025-06-01")
 */

/**
 * Calculate the current cost of a panel.
 * @param {string} panelId  UUID of the panel (from the panels sheet, id column)
 * @param {string} strategy Optional: cheapest (default), average, fifo, lifo, fefo
 * @return {number} Total cost per test in dollars
 * @customfunction
 */
function SF_PANEL_COST(panelId, strategy) {
  if (!panelId) return 'ERROR: panelId required';
  const result = calculatePanelCost(panelId, strategy || 'cheapest');
  if (result.error) return 'ERROR: ' + result.error;
  return result.total_cost;
}

/**
 * Check if a panel is ready to run (all reagents in stock).
 * @param {string} panelId  UUID of the panel
 * @return {string} "✅ Ready" or "⚠️ X/Y reagents"
 * @customfunction
 */
function SF_PANEL_STATUS(panelId) {
  if (!panelId) return 'ERROR: panelId required';
  const panels = getPanelReadinessStatus();
  const panel  = panels.find(p => p.panel_id === panelId);
  if (!panel) return 'Panel not found';
  return panel.status;
}

/**
 * Get the number of available units for a reagent.
 * @param {string} reagentId  UUID of the reagent
 * @return {number} Count of available, non-expired units
 * @customfunction
 */
function SF_REAGENT_UNITS_AVAILABLE(reagentId) {
  if (!reagentId) return 'ERROR: reagentId required';
  const units = getSheetData(SHEETS.REAGENT_UNITS);
  const now   = today();
  const activeStatuses = ['stored', 'in use'];
  return units.filter(u => {
    if (u.reagent_id !== reagentId) return false;
    if (!activeStatuses.includes((u.status || '').toLowerCase())) return false;
    const exp = parseDate(u.expiration_date);
    if (exp && exp < now) return false;
    return true;
  }).length;
}

/**
 * Calculate days until expiry from a date string.
 * Returns negative for already-expired dates.
 * @param {string|Date} expirationDate
 * @return {number} Days remaining (negative = expired)
 * @customfunction
 */
function SF_DAYS_TO_EXPIRY(expirationDate) {
  if (!expirationDate) return '';
  const exp = new Date(expirationDate);
  if (isNaN(exp.getTime())) return 'INVALID DATE';
  const now = today();
  return daysDiff(now, exp);
}

/**
 * Generate a traffic-light expiry alert label.
 * @param {string|Date} expirationDate
 * @return {string} "🔴 EXPIRED", "🟠 <7d", "🟡 <30d", "🟢 OK", or ""
 * @customfunction
 */
function SF_EXPIRY_ALERT(expirationDate) {
  if (!expirationDate) return '';
  const d = SF_DAYS_TO_EXPIRY(expirationDate);
  if (typeof d !== 'number') return d;
  if (d < 0)   return '🔴 EXPIRED';
  if (d <= 7)  return '🟠 ' + d + 'd';
  if (d <= 30) return '🟡 ' + d + 'd';
  return '🟢 OK';
}

/**
 * Look up a reagent's name by its ID.
 * @param {string} reagentId
 * @return {string} Reagent name
 * @customfunction
 */
function SF_REAGENT_NAME(reagentId) {
  if (!reagentId) return '';
  const reagents = getSheetData(SHEETS.REAGENTS);
  const r = reagents.find(r => r.id === reagentId);
  return r ? r.name : 'Not found';
}

/**
 * Look up a panel's name by its ID.
 * @param {string} panelId
 * @return {string} Panel name
 * @customfunction
 */
function SF_PANEL_NAME(panelId) {
  if (!panelId) return '';
  const panels = getSheetData(SHEETS.PANELS);
  const p = panels.find(p => p.id === panelId);
  return p ? p.name : 'Not found';
}

/**
 * Count reagents assigned to a panel.
 * @param {string} panelId
 * @return {number} Number of reagents
 * @customfunction
 */
function SF_PANEL_REAGENT_COUNT(panelId) {
  if (!panelId) return 0;
  const prs = getSheetData(SHEETS.PANEL_REAGENTS);
  return prs.filter(pr => pr.panel_id === panelId).length;
}

/**
 * Get the total inventory value for a reagent (sum of purchase_price for active units).
 * @param {string} reagentId
 * @return {number} Total dollar value in stock
 * @customfunction
 */
function SF_REAGENT_STOCK_VALUE(reagentId) {
  if (!reagentId) return 0;
  const units = getSheetData(SHEETS.REAGENT_UNITS);
  const now   = today();
  const activeStatuses = ['stored', 'in use'];
  return units
    .filter(u => {
      if (u.reagent_id !== reagentId) return false;
      if (!activeStatuses.includes((u.status || '').toLowerCase())) return false;
      const exp = parseDate(u.expiration_date);
      if (exp && exp < now) return false;
      return true;
    })
    .reduce((sum, u) => sum + parseFloat(u.purchase_price || 0), 0);
}
