"""
Dynamic Cost Calculation Utilities
Ensures costs are always calculated from panel definitions, never stored in patient records
"""

from ui.crud_panels import query_panels
from utils.pricing import calculate_panel_cost_current


def calculate_general_reagent_cost_dynamic(panel_id):
    """
    Calculate general reagent costs dynamically from current prices and consumption data.

    This works like antibody cost calculation - always uses current prices, never static snapshots.

    Returns:
        dict: {
            'total_cost': float,
            'is_complete': bool,
            'missing_data': list of dicts with reagent name and what's missing,
            'breakdown': list of {'reagent': name, 'cost': amount, 'type': 'general_reagent', 'details': str}
        }
    """
    # Get general reagents assigned to this panel
    panel_gr = query_panels("""
        SELECT
            pgr.id as assignment_id,
            pgr.general_reagent_id,
            pgr.consumption_type,
            pgr.consumption_amount,
            pgr.display_name,
            pgr.general_reagent_unit_id,
            gr.name as reagent_name,
            gr.price as current_price,
            gr.standard_volume,
            gr.standard_units
        FROM panel_general_reagents pgr
        JOIN general_reagents gr ON gr.id = pgr.general_reagent_id
        WHERE pgr.panel_id = ?
    """, (panel_id,))

    if panel_gr is None or panel_gr.empty:
        return {
            'total_cost': 0.0,
            'is_complete': True,
            'missing_data': [],
            'breakdown': []
        }

    total_cost = 0.0
    missing_data = []
    breakdown = []

    for _, gr in panel_gr.iterrows():
        reagent_display_name = gr['display_name'] or gr['reagent_name']
        cost_per_test = None
        details = ""

        # Check if we have consumption data (might be NULL for old panels)
        if not gr['consumption_type'] or gr['consumption_amount'] is None:
            missing_data.append({
                'reagent': reagent_display_name,
                'missing': 'consumption data (type/amount not set)'
            })
            breakdown.append({
                'reagent': reagent_display_name,
                'cost': 0.0,
                'type': 'general_reagent',
                'details': '⚠️ Consumption not configured'
            })
            continue

        # Check if we have price
        if not gr['current_price'] or gr['current_price'] <= 0:
            missing_data.append({
                'reagent': reagent_display_name,
                'missing': 'price not set in General Reagents'
            })
            breakdown.append({
                'reagent': reagent_display_name,
                'cost': 0.0,
                'type': 'general_reagent',
                'details': '⚠️ Price not set'
            })
            continue

        consumption_type = gr['consumption_type'].lower()
        consumption_amount = float(gr['consumption_amount'])
        price = float(gr['current_price'])

        # Calculate based on consumption type
        if consumption_type == 'ml':
            # Try to get volume from selected unit, fallback to standard_volume
            if gr['general_reagent_unit_id']:
                unit_info = query_panels("""
                    SELECT volume FROM general_reagent_units
                    WHERE id = ?
                """, (gr['general_reagent_unit_id'],))

                if unit_info is not None and not unit_info.empty and unit_info.iloc[0]['volume']:
                    total_volume = float(unit_info.iloc[0]['volume'])
                    details = f"Using unit volume ({total_volume:.0f} mL)"
                elif gr['standard_volume'] and gr['standard_volume'] > 0:
                    total_volume = float(gr['standard_volume'])
                    details = f"Using standard volume ({total_volume:.0f} mL)"
                else:
                    total_volume = None
            elif gr['standard_volume'] and gr['standard_volume'] > 0:
                total_volume = float(gr['standard_volume'])
                details = f"Using standard volume ({total_volume:.0f} mL)"
            else:
                total_volume = None

            if total_volume and total_volume > 0:
                price_per_ml = price / total_volume
                cost_per_test = price_per_ml * consumption_amount
                if not details:
                    details = f"{consumption_amount} mL @ ${price_per_ml:.4f}/mL"
            else:
                missing_data.append({
                    'reagent': reagent_display_name,
                    'missing': 'volume (unit volume and standard_volume both missing)'
                })
                cost_per_test = None
                details = f"⚠️ Volume missing"

        elif consumption_type == 'units':
            # Use standard_units or fallback to 1
            total_units = float(gr['standard_units']) if gr['standard_units'] and gr['standard_units'] > 0 else 1.0
            price_per_unit = price / total_units
            cost_per_test = price_per_unit * consumption_amount
            details = f"{consumption_amount} units @ ${price_per_unit:.4f}/unit"

        else:
            missing_data.append({
                'reagent': reagent_display_name,
                'missing': f'unknown consumption_type: {consumption_type}'
            })
            cost_per_test = None
            details = f"⚠️ Unknown type: {consumption_type}"

        # Add to breakdown
        if cost_per_test is not None:
            total_cost += cost_per_test
            breakdown.append({
                'reagent': reagent_display_name,
                'cost': cost_per_test,
                'type': 'general_reagent',
                'details': details
            })
        else:
            breakdown.append({
                'reagent': reagent_display_name,
                'cost': 0.0,
                'type': 'general_reagent',
                'details': details
            })

    is_complete = len(missing_data) == 0

    return {
        'total_cost': total_cost,
        'is_complete': is_complete,
        'missing_data': missing_data,
        'breakdown': breakdown
    }


def get_panel_cost_breakdown(panel_id):
    """
    Get complete cost breakdown for a panel (antibodies + general reagents).

    This is the SINGLE SOURCE OF TRUTH for panel costs.
    All pages (Panels, Clinical, Economic) must use this function.

    Returns:
        dict: {
            'total_cost': float,
            'is_complete': bool (all reagents have prices),
            'missing_prices': list of reagent names without prices,
            'missing_data': list of dicts with detailed missing data info (for general reagents),
            'breakdown': list of {'reagent': name, 'cost': amount, 'type': str, 'details': str}
        }
    """
    # Get antibody costs (already dynamic)
    antibody_result = calculate_panel_cost_current(panel_id, strategy='cheapest')

    if 'error' in antibody_result:
        antibody_cost = 0.0
        is_complete = False
        missing_prices = []
        breakdown = []
    else:
        antibody_cost = antibody_result.get('total_cost', 0.0)
        is_complete = antibody_result.get('is_complete', True)
        missing_prices = antibody_result.get('missing_reagents', [])
        breakdown = antibody_result.get('breakdown', [])

    # Get general reagent costs DYNAMICALLY (not from static cost_per_test)
    gr_result = calculate_general_reagent_cost_dynamic(panel_id)

    general_reagent_cost = gr_result['total_cost']
    breakdown.extend(gr_result['breakdown'])

    # Merge completeness flags
    if not gr_result['is_complete']:
        is_complete = False
        # Add general reagent missing items to missing_prices
        for missing_item in gr_result['missing_data']:
            missing_prices.append(f"{missing_item['reagent']} ({missing_item['missing']})")

    total_cost = antibody_cost + general_reagent_cost

    return {
        'total_cost': total_cost,
        'is_complete': is_complete,
        'missing_prices': missing_prices,
        'missing_data': gr_result['missing_data'],  # Detailed missing data for general reagents
        'breakdown': breakdown
    }


def get_case_total_cost(case_id):
    """
    Calculate total cost for a case by summing all assigned panel costs dynamically
    
    Args:
        case_id: The clinical case ID
        
    Returns:
        dict: {
            'total_cost': float,
            'panel_costs': list of {'panel_id': id, 'panel_name': name, 'cost': amount, 'is_complete': bool},
            'incomplete_panels': list of panel names with missing pricing
        }
    """
    # Get all panels assigned to this case
    case_panels = query_panels("""
        SELECT
            cp.panel_id,
            p.name as panel_name,
            p.version
        FROM case_panels cp
        JOIN panels p ON p.id = cp.panel_id
        WHERE cp.case_id = ?
    """, (case_id,))
    
    if case_panels is None or case_panels.empty:
        return {
            'total_cost': 0.0,
            'panel_costs': [],
            'incomplete_panels': []
        }
    
    panel_costs = []
    incomplete_panels = []
    total = 0.0
    
    for _, panel_row in case_panels.iterrows():
        cost_info = get_panel_cost_breakdown(panel_row['panel_id'])
        
        panel_cost_entry = {
            'panel_id': panel_row['panel_id'],
            'panel_name': f"{panel_row['panel_name']} (v{panel_row['version']})",
            'cost': cost_info['total_cost'],
            'is_complete': cost_info['is_complete']
        }
        
        panel_costs.append(panel_cost_entry)
        total += cost_info['total_cost']
        
        if not cost_info['is_complete']:
            incomplete_panels.append(panel_cost_entry['panel_name'])
    
    return {
        'total_cost': total,
        'panel_costs': panel_costs,
        'incomplete_panels': incomplete_panels
    }


def get_missing_prices_for_panel(panel_id):
    """
    Get list of reagents without pricing for a specific panel
    
    Returns:
        list: List of reagent names that are missing pricing information
    """
    cost_info = get_panel_cost_breakdown(panel_id)
    return cost_info.get('missing_prices', [])
