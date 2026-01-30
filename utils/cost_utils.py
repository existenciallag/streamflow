"""
Dynamic Cost Calculation Utilities
Ensures costs are always calculated from panel definitions, never stored in patient records
"""

from ui.crud_panels import query_panels
from utils.pricing import calculate_panel_cost_current


def get_panel_cost_breakdown(panel_id):
    """
    Get complete cost breakdown for a panel (antibodies + general reagents)

    Returns:
        dict: {
            'total_cost': float,
            'is_complete': bool (all reagents have prices),
            'missing_prices': list of reagent names without prices,
            'breakdown': list of {'reagent': name, 'cost': amount}
        }
    """
    # Get antibody costs
    result = calculate_panel_cost_current(panel_id, strategy='cheapest')

    if 'error' in result:
        antibody_cost = 0.0
        is_complete = False
        missing_prices = []
        breakdown = []
    else:
        antibody_cost = result.get('total_cost', 0.0)
        is_complete = result.get('is_complete', True)
        missing_prices = result.get('missing_reagents', [])
        breakdown = result.get('breakdown', [])

    # Get general reagent costs
    general_reagents = query_panels("""
        SELECT
            gr.name as reagent_name,
            pgr.cost_per_test,
            pgr.consumption_amount,
            pgr.consumption_type,
            pgr.display_name
        FROM panel_general_reagents pgr
        JOIN general_reagents gr ON gr.id = pgr.general_reagent_id
        WHERE pgr.panel_id = ?
    """, (panel_id,))

    general_reagent_cost = 0.0
    if general_reagents is not None and not general_reagents.empty:
        for _, gr in general_reagents.iterrows():
            gr_cost = gr['cost_per_test'] or 0.0
            general_reagent_cost += gr_cost
            breakdown.append({
                'reagent': gr['display_name'] or gr['reagent_name'],
                'cost': gr_cost,
                'type': 'general_reagent'
            })

            # If cost is 0, mark as missing price
            if gr_cost == 0.0:
                is_complete = False
                missing_prices.append(gr['display_name'] or gr['reagent_name'])

    total_cost = antibody_cost + general_reagent_cost

    return {
        'total_cost': total_cost,
        'is_complete': is_complete,
        'missing_prices': missing_prices,
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
