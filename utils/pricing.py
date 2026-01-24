"""
Dynamic Pricing System for Flow Cytometry Panels

This module provides functions to calculate panel costs dynamically based on:
- Current reagent unit (lot) prices
- Volume requirements per test
- Available stock and selection strategies

Design Philosophy:
- NO fixed costs stored in database
- ALL costs calculated from current reagent_unit prices
- Supports multiple costing strategies (cheapest, FIFO, FEFO, average)
- Transparent breakdown for traceability
"""

from datetime import datetime
from typing import Dict, List, Optional, Literal
import json
from ui.crud_panels import query_panels

CostStrategy = Literal['cheapest', 'average', 'fifo', 'lifo', 'fefo']


def calculate_panel_cost_current(
    panel_id: str,
    strategy: CostStrategy = 'cheapest',
    include_unavailable: bool = False
) -> Dict:
    """
    Calculate current panel cost dynamically from available reagent units.

    Args:
        panel_id: UUID of the panel
        strategy: Cost calculation strategy
            - 'cheapest': Use lowest cost-per-µL available unit
            - 'average': Average cost across all available units
            - 'fifo': First-in-first-out (oldest arrival_date)
            - 'lifo': Last-in-first-out (newest arrival_date)
            - 'fefo': First-expired-first-out (earliest expiration)
        include_unavailable: If True, show reagents even if out of stock

    Returns:
        Dictionary containing:
        {
            'panel_id': str,
            'panel_name': str,
            'total_cost': float,
            'breakdown': List[Dict],  # Per-reagent details
            'warnings': List[str],    # Out of stock, etc.
            'calculated_at': datetime,
            'strategy': str,
            'is_complete': bool       # False if any reagents unavailable
        }
    """

    # Get panel details
    panel_query = query_panels("""
        SELECT p.id, p.name, p.version
        FROM panels p
        WHERE p.id = ?
    """, (panel_id,))

    if panel_query.empty:
        return {
            'error': 'Panel not found',
            'panel_id': panel_id
        }

    panel = panel_query.iloc[0]

    # Get panel reagents with volume requirements
    panel_reagents = query_panels("""
        SELECT
            pr.id as panel_reagent_id,
            pr.reagent_id,
            r.name as reagent_name,
            r.catalog_price,
            pr.volume_used as volume_per_test,
            pr.channel_display_name
        FROM panel_reagents pr
        JOIN reagents r ON r.id = pr.reagent_id
        WHERE pr.panel_id = ?
        ORDER BY pr.display_order, r.name
    """, (panel_id,))

    if panel_reagents.empty:
        return {
            'panel_id': panel_id,
            'panel_name': panel.get('name'),
            'total_cost': 0.0,
            'breakdown': [],
            'warnings': ['Panel has no reagents assigned'],
            'calculated_at': datetime.now().isoformat(),
            'strategy': strategy,
            'is_complete': False
        }

    # Calculate cost for each reagent
    total_cost = 0.0
    breakdown = []
    warnings = []
    all_available = True

    for _, reagent in panel_reagents.iterrows():
        reagent_id = reagent['reagent_id']
        volume_needed = reagent.get('volume_per_test') or 0.0

        if volume_needed <= 0:
            warnings.append(
                f"⚠️ {reagent['reagent_name']}: No volume specified"
            )
            breakdown.append({
                'reagent': reagent['reagent_name'],
                'channel': reagent.get('channel_display_name'),
                'volume_needed': 0.0,
                'status': 'no_volume_specified',
                'cost': 0.0
            })
            continue

        # Get available units for this reagent
        available_units = query_panels("""
            SELECT
                ru.id,
                ru.lot,
                ru.purchase_price,
                ru.initial_volume,
                ru.current_volume,
                ru.cost_per_ul,
                ru.arrival_date,
                ru.expiration_date,
                ru.status
            FROM reagent_units ru
            WHERE ru.reagent_id = ?
              AND LOWER(ru.status) IN ('stored', 'in use')
              AND COALESCE(ru.current_volume, ru.initial_volume) >= ?
              AND (ru.expiration_date IS NULL OR ru.expiration_date > datetime('now'))
              AND ru.cost_per_ul IS NOT NULL
              AND ru.cost_per_ul > 0
        """, (reagent_id, volume_needed))

        # Handle out of stock
        if available_units.empty:
            all_available = False
            warnings.append(
                f"⚠️ {reagent['reagent_name']}: OUT OF STOCK (need {volume_needed}µL)"
            )

            # Check if there are any units at all (for better error message)
            any_units = query_panels("""
                SELECT COUNT(*) as count
                FROM reagent_units ru
                WHERE ru.reagent_id = ?
            """, (reagent_id,))

            if any_units.iloc[0]['count'] == 0:
                status_detail = 'no_units_exist'
            else:
                status_detail = 'all_units_unavailable'

            breakdown.append({
                'reagent': reagent['reagent_name'],
                'channel': reagent.get('channel_display_name'),
                'volume_needed': volume_needed,
                'status': 'out_of_stock',
                'status_detail': status_detail,
                'cost': None,
                'catalog_price': reagent.get('catalog_price')
            })
            continue

        # Select unit based on strategy
        selected_unit = _select_unit_by_strategy(available_units, strategy)

        if selected_unit is None:
            all_available = False
            warnings.append(
                f"⚠️ {reagent['reagent_name']}: No suitable unit found"
            )
            breakdown.append({
                'reagent': reagent['reagent_name'],
                'channel': reagent.get('channel_display_name'),
                'volume_needed': volume_needed,
                'status': 'no_suitable_unit',
                'cost': None
            })
            continue

        # Calculate cost for this reagent
        reagent_cost = selected_unit['cost_per_ul'] * volume_needed
        total_cost += reagent_cost

        breakdown.append({
            'reagent': reagent['reagent_name'],
            'channel': reagent.get('channel_display_name'),
            'volume_needed': volume_needed,
            'using_lot': selected_unit['lot'],
            'cost_per_ul': selected_unit['cost_per_ul'],
            'reagent_cost': round(reagent_cost, 2),
            'available_volume': selected_unit.get('current_volume') or selected_unit.get('initial_volume'),
            'unit_expiration': selected_unit.get('expiration_date'),
            'status': 'available'
        })

    return {
        'panel_id': panel_id,
        'panel_name': panel.get('name'),
        'panel_version': panel.get('version'),
        'total_cost': round(total_cost, 2),
        'breakdown': breakdown,
        'warnings': warnings,
        'calculated_at': datetime.now().isoformat(),
        'strategy': strategy,
        'is_complete': all_available,
        'num_reagents': len(breakdown),
        'num_available': sum(1 for b in breakdown if b.get('status') == 'available')
    }


def _select_unit_by_strategy(available_units, strategy: CostStrategy):
    """
    Select the best reagent unit based on the specified strategy.

    Args:
        available_units: DataFrame of available reagent units
        strategy: Cost selection strategy

    Returns:
        Dictionary (row) of selected unit, or None if no suitable unit
    """
    if available_units.empty:
        return None

    if strategy == 'cheapest':
        # Lowest cost per µL
        selected = available_units.loc[available_units['cost_per_ul'].idxmin()]

    elif strategy == 'average':
        # Use average cost (still need to pick a specific unit, so pick median)
        avg_cost = available_units['cost_per_ul'].mean()
        # Find unit closest to average
        available_units['diff_from_avg'] = abs(available_units['cost_per_ul'] - avg_cost)
        selected = available_units.loc[available_units['diff_from_avg'].idxmin()]

    elif strategy == 'fifo':
        # First in (oldest arrival date)
        available_units['arrival_sort'] = available_units['arrival_date'].fillna('9999-12-31')
        selected = available_units.loc[available_units['arrival_sort'].idxmin()]

    elif strategy == 'lifo':
        # Last in (newest arrival date)
        available_units['arrival_sort'] = available_units['arrival_date'].fillna('0000-01-01')
        selected = available_units.loc[available_units['arrival_sort'].idxmax()]

    elif strategy == 'fefo':
        # First expired (earliest expiration date)
        # Filter to only units with expiration dates
        with_expiration = available_units[available_units['expiration_date'].notna()]
        if not with_expiration.empty:
            selected = with_expiration.loc[with_expiration['expiration_date'].idxmin()]
        else:
            # Fall back to cheapest if no units have expiration dates
            selected = available_units.loc[available_units['cost_per_ul'].idxmin()]

    else:
        # Default to cheapest
        selected = available_units.loc[available_units['cost_per_ul'].idxmin()]

    return selected.to_dict()


def get_panel_cost_summary(panel_id: str, strategy: CostStrategy = 'cheapest') -> str:
    """
    Get a formatted string summary of panel cost.

    Args:
        panel_id: UUID of the panel
        strategy: Cost calculation strategy

    Returns:
        Formatted string with cost summary
    """
    result = calculate_panel_cost_current(panel_id, strategy)

    if 'error' in result:
        return f"❌ Error: {result['error']}"

    if not result['is_complete']:
        status_icon = "⚠️"
        status_text = "INCOMPLETE"
    else:
        status_icon = "✅"
        status_text = "Complete"

    summary = f"{status_icon} {result['panel_name']} (v{result.get('panel_version', '1.0.0')})\n"
    summary += f"Total Cost: €{result['total_cost']:.2f} ({strategy} strategy)\n"
    summary += f"Status: {status_text} ({result['num_available']}/{result['num_reagents']} reagents available)\n"

    if result['warnings']:
        summary += "\nWarnings:\n"
        for warning in result['warnings']:
            summary += f"  {warning}\n"

    return summary


def get_panel_cost_breakdown(panel_id: str, strategy: CostStrategy = 'cheapest') -> str:
    """
    Get a detailed formatted breakdown of panel cost.

    Args:
        panel_id: UUID of the panel
        strategy: Cost calculation strategy

    Returns:
        Formatted string with detailed breakdown
    """
    result = calculate_panel_cost_current(panel_id, strategy)

    if 'error' in result:
        return f"❌ Error: {result['error']}"

    output = f"Panel: {result['panel_name']} (v{result.get('panel_version', '1.0.0')})\n"
    output += f"Cost Strategy: {strategy}\n"
    output += f"Calculated: {result['calculated_at']}\n"
    output += "=" * 80 + "\n\n"

    for item in result['breakdown']:
        reagent_name = item['reagent']
        channel = item.get('channel', 'N/A')

        if item['status'] == 'available':
            output += f"✅ {reagent_name:<30} ({channel})\n"
            output += f"   {item['volume_needed']:>6.1f}µL × €{item['cost_per_ul']:.4f}/µL = €{item['reagent_cost']:.2f}\n"
            output += f"   Using Lot: {item['using_lot']} ({item['available_volume']:.1f}µL available)\n"

        elif item['status'] == 'out_of_stock':
            output += f"❌ {reagent_name:<30} ({channel})\n"
            output += f"   OUT OF STOCK (need {item['volume_needed']}µL)\n"

        else:
            output += f"⚠️ {reagent_name:<30} ({channel})\n"
            output += f"   Status: {item['status']}\n"

        output += "\n"

    output += "=" * 80 + "\n"
    output += f"TOTAL COST: €{result['total_cost']:.2f}\n"

    if not result['is_complete']:
        output += "\n⚠️ WARNING: This panel is incomplete due to missing reagents.\n"

    return output


def compare_panel_costs(panel_id: str, strategies: List[CostStrategy] = None) -> Dict:
    """
    Compare panel costs across different strategies.

    Args:
        panel_id: UUID of the panel
        strategies: List of strategies to compare (default: all)

    Returns:
        Dictionary with comparison data
    """
    if strategies is None:
        strategies = ['cheapest', 'average', 'fifo', 'fefo']

    results = {}
    for strategy in strategies:
        results[strategy] = calculate_panel_cost_current(panel_id, strategy)

    return {
        'panel_id': panel_id,
        'strategies': results,
        'cost_range': {
            'min': min(r['total_cost'] for r in results.values() if r['is_complete']),
            'max': max(r['total_cost'] for r in results.values() if r['is_complete']),
        } if any(r['is_complete'] for r in results.values()) else None
    }


def calculate_draft_panel_cost(reagent_list: List[Dict], strategy: CostStrategy = 'cheapest') -> Dict:
    """
    Calculate cost for a draft panel (not yet saved) from a list of reagents.

    This is used in Panel Builder UI when creating a new panel.

    Args:
        reagent_list: List of reagent dictionaries with keys:
            - reagent_id: str (UUID)
            - reagent_name: str (display name)
            - volume_per_test: float (µL needed)
            - channel_display_name: str (optional)
        strategy: Cost calculation strategy

    Returns:
        Dictionary with same structure as calculate_panel_cost_current
    """
    total_cost = 0.0
    breakdown = []
    warnings = []
    all_available = True

    for reagent in reagent_list:
        reagent_id = reagent.get('reagent_id')
        reagent_name = reagent.get('reagent_name') or reagent.get('display_name', 'Unknown')
        volume_needed = float(reagent.get('volume_per_test', 0) or reagent.get('volume_used', 0))

        if not reagent_id:
            warnings.append(f"⚠️ {reagent_name}: No reagent ID")
            breakdown.append({
                'reagent': reagent_name,
                'volume_needed': volume_needed,
                'status': 'invalid',
                'cost': None
            })
            all_available = False
            continue

        if volume_needed <= 0:
            warnings.append(f"⚠️ {reagent_name}: No volume specified")
            breakdown.append({
                'reagent': reagent_name,
                'volume_needed': 0.0,
                'status': 'no_volume_specified',
                'cost': 0.0
            })
            continue

        # Get available units for this reagent (same logic as calculate_panel_cost_current)
        available_units = query_panels("""
            SELECT
                ru.id,
                ru.lot,
                ru.purchase_price,
                ru.initial_volume,
                ru.current_volume,
                ru.cost_per_ul,
                ru.arrival_date,
                ru.expiration_date,
                ru.status
            FROM reagent_units ru
            WHERE ru.reagent_id = ?
              AND LOWER(ru.status) IN ('stored', 'in use')
              AND COALESCE(ru.current_volume, ru.initial_volume) >= ?
              AND (ru.expiration_date IS NULL OR ru.expiration_date > datetime('now'))
              AND ru.cost_per_ul IS NOT NULL
              AND ru.cost_per_ul > 0
        """, (reagent_id, volume_needed))

        if available_units.empty:
            all_available = False
            warnings.append(f"⚠️ {reagent_name}: OUT OF STOCK (need {volume_needed}µL)")
            breakdown.append({
                'reagent': reagent_name,
                'channel': reagent.get('channel_display_name'),
                'volume_needed': volume_needed,
                'status': 'out_of_stock',
                'cost': None
            })
            continue

        # Select unit based on strategy
        selected_unit = _select_unit_by_strategy(available_units, strategy)

        if selected_unit is None:
            all_available = False
            warnings.append(f"⚠️ {reagent_name}: No suitable unit found")
            breakdown.append({
                'reagent': reagent_name,
                'channel': reagent.get('channel_display_name'),
                'volume_needed': volume_needed,
                'status': 'no_suitable_unit',
                'cost': None
            })
            continue

        # Calculate cost
        reagent_cost = selected_unit['cost_per_ul'] * volume_needed
        total_cost += reagent_cost

        breakdown.append({
            'reagent': reagent_name,
            'channel': reagent.get('channel_display_name'),
            'volume_needed': volume_needed,
            'using_lot': selected_unit['lot'],
            'cost_per_ul': selected_unit['cost_per_ul'],
            'reagent_cost': round(reagent_cost, 2),
            'available_volume': selected_unit.get('current_volume') or selected_unit.get('initial_volume'),
            'status': 'available'
        })

    return {
        'panel_name': 'Draft Panel',
        'total_cost': round(total_cost, 2),
        'breakdown': breakdown,
        'warnings': warnings,
        'calculated_at': datetime.now().isoformat(),
        'strategy': strategy,
        'is_complete': all_available,
        'num_reagents': len(breakdown),
        'num_available': sum(1 for b in breakdown if b.get('status') == 'available')
    }
