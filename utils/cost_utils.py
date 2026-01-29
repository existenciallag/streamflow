"""
Dynamic Cost Calculation Utilities
Ensures costs are always calculated from panel definitions, never stored in patient records
"""

from ui.crud_panels import query_panels
from utils.pricing import calculate_panel_cost_current


def get_panel_cost_breakdown(panel_id):
    """
    Get complete cost breakdown for a panel
    
    Returns:
        dict: {
            'total_cost': float,
            'is_complete': bool (all reagents have prices),
            'missing_prices': list of reagent names without prices,
            'breakdown': list of {'reagent': name, 'cost': amount}
        }
    """
    result = calculate_panel_cost_current(panel_id, strategy='cheapest')
    
    if 'error' in result:
        return {
            'total_cost': 0.0,
            'is_complete': False,
            'missing_prices': [],
            'breakdown': [],
            'error': result['error']
        }
    
    return {
        'total_cost': result.get('total_cost', 0.0),
        'is_complete': result.get('is_complete', True),
        'missing_prices': result.get('missing_reagents', []),
        'breakdown': result.get('breakdown', [])
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
