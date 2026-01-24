"""
Enhanced Dashboard Metrics for Flow Cytometry Laboratory

Provides operational metrics for stock control, traceability, and decision-making.
"""

from datetime import datetime, timedelta
from ui.crud_panels import query_panels
import pandas as pd


def get_stock_health_metrics():
    """
    Calculate stock health metrics for Dashboard top row.

    Returns:
        dict with keys:
        - unique_reagents: Number of distinct reagent types in stock
        - total_value_at_risk: $ value expiring in next 30 days
        - low_stock_count: Number of reagents with <2 available units
        - expired_units: Number of expired units
    """
    # Unique reagents in stock
    unique_reagents = query_panels("""
        SELECT COUNT(DISTINCT reagent_id) as count
        FROM reagent_units
        WHERE LOWER(status) IN ('stored', 'in use')
    """)

    # Total value expiring in next 30 days
    thirty_days = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    value_at_risk = query_panels("""
        SELECT COALESCE(SUM(purchase_price), 0) as total
        FROM reagent_units
        WHERE expiration_date IS NOT NULL
          AND expiration_date <= ?
          AND expiration_date >= date('now')
          AND LOWER(status) IN ('stored', 'in use')
    """, (thirty_days,))

    # Reagents with low stock (<2 available units)
    low_stock = query_panels("""
        SELECT COUNT(*) as count
        FROM (
            SELECT reagent_id, COUNT(*) as available_count
            FROM reagent_units
            WHERE LOWER(status) IN ('stored', 'in use')
              AND (expiration_date IS NULL OR expiration_date > date('now'))
            GROUP BY reagent_id
            HAVING COUNT(*) < 2
        )
    """)

    # Expired units
    expired = query_panels("""
        SELECT COUNT(*) as count
        FROM reagent_units
        WHERE expiration_date < date('now')
          AND LOWER(status) IN ('stored', 'in use')
    """)

    return {
        'unique_reagents': int(unique_reagents.iloc[0]['count']) if not unique_reagents.empty else 0,
        'total_value_at_risk': float(value_at_risk.iloc[0]['total']) if not value_at_risk.empty else 0.0,
        'low_stock_count': int(low_stock.iloc[0]['count']) if not low_stock.empty else 0,
        'expired_units': int(expired.iloc[0]['count']) if not expired.empty else 0
    }


def get_expiring_inventory(days=30, limit=10):
    """
    Get top expiring inventory by value.

    Args:
        days: Number of days to look ahead
        limit: Maximum number of items to return

    Returns:
        DataFrame with columns:
        - reagent_name
        - expiration_date
        - days_until_expiration
        - purchase_price
        - initial_volume
        - lot
        - status
    """
    expiration_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

    result = query_panels("""
        SELECT
            r.name as reagent_name,
            ru.expiration_date,
            CAST(julianday(ru.expiration_date) - julianday('now') AS INTEGER) as days_until_expiration,
            ru.purchase_price,
            ru.initial_volume,
            ru.lot,
            ru.status,
            ru.id as unit_id
        FROM reagent_units ru
        JOIN reagents r ON r.id = ru.reagent_id
        WHERE ru.expiration_date IS NOT NULL
          AND ru.expiration_date <= ?
          AND ru.expiration_date >= date('now')
          AND LOWER(ru.status) IN ('stored', 'in use')
        ORDER BY ru.purchase_price DESC, ru.expiration_date ASC
        LIMIT ?
    """, (expiration_date, limit))

    return result


def get_expired_inventory(limit=20):
    """
    Get expired inventory that should be disposed of.

    Returns:
        DataFrame with expired units sorted by value
    """
    result = query_panels("""
        SELECT
            r.name as reagent_name,
            ru.expiration_date,
            CAST(julianday('now') - julianday(ru.expiration_date) AS INTEGER) as days_expired,
            ru.purchase_price,
            ru.initial_volume,
            ru.lot,
            ru.status,
            ru.id as unit_id
        FROM reagent_units ru
        JOIN reagents r ON r.id = ru.reagent_id
        WHERE ru.expiration_date < date('now')
          AND LOWER(ru.status) IN ('stored', 'in use')
        ORDER BY ru.purchase_price DESC, ru.expiration_date ASC
        LIMIT ?
    """, (limit,))

    return result


def get_panel_readiness_status():
    """
    Check which panels can be run right now (all reagents in stock).

    Returns:
        DataFrame with columns:
        - panel_id
        - panel_name
        - total_reagents
        - available_reagents
        - is_complete (True if all reagents available)
        - next_expiration (soonest expiring reagent)
    """
    # This is more complex - need to check each panel's reagents
    panels = query_panels("""
        SELECT id, name
        FROM panels
        ORDER BY name
    """)

    if panels.empty:
        return pd.DataFrame()

    results = []
    for _, panel in panels.iterrows():
        panel_id = panel['id']
        panel_name = panel['name']

        # Get panel reagents
        panel_reagents = query_panels("""
            SELECT reagent_id
            FROM panel_reagents
            WHERE panel_id = ?
        """, (panel_id,))

        if panel_reagents.empty:
            continue

        total_reagents = len(panel_reagents)
        available_count = 0
        earliest_expiration = None

        for _, pr in panel_reagents.iterrows():
            # Check if reagent has available units
            available = query_panels("""
                SELECT MIN(expiration_date) as next_exp
                FROM reagent_units
                WHERE reagent_id = ?
                  AND LOWER(status) IN ('stored', 'in use')
                  AND (expiration_date IS NULL OR expiration_date > date('now'))
            """, (pr['reagent_id'],))

            if not available.empty and available.iloc[0]['next_exp'] is not None:
                available_count += 1
                exp_date = available.iloc[0]['next_exp']
                if earliest_expiration is None or exp_date < earliest_expiration:
                    earliest_expiration = exp_date

        results.append({
            'panel_id': panel_id,
            'panel_name': panel_name,
            'total_reagents': total_reagents,
            'available_reagents': available_count,
            'is_complete': available_count == total_reagents,
            'next_expiration': earliest_expiration
        })

    return pd.DataFrame(results)


def get_general_reagents_enhanced(general_reagents, general_units):
    """
    Enhanced version of general_reagents_quick_status with volumes.

    Returns:
        DataFrame with columns:
        - Reactivo (name)
        - In Use (count)
        - Stored (count)
        - Total Volume (µL)
        - Next Expiration
        - Ratio (In Use / Total)
    """
    if general_units is None or general_units.empty:
        return pd.DataFrame()

    if general_reagents is None or general_reagents.empty:
        return pd.DataFrame()

    # Join units with reagents
    df = general_units.merge(
        general_reagents[["id", "name"]],
        left_on="general_reagent_id",
        right_on="id",
        how="left"
    )

    df = df.dropna(subset=["name"])

    # Aggregate by reagent
    summary = df.groupby("name").agg({
        'status': lambda x: x.value_counts().to_dict(),
        'volume': 'sum',
        'expiration_date': lambda x: x.min() if x.notna().any() else None
    }).reset_index()

    # Expand status counts
    summary['In Use'] = summary['status'].apply(lambda x: x.get('In Use', 0))
    summary['Stored'] = summary['status'].apply(lambda x: x.get('Stored', 0))
    summary['Total'] = summary['In Use'] + summary['Stored']
    summary['Ratio'] = summary['In Use'] / summary['Total'].replace(0, 1)

    # Rename columns
    summary = summary.rename(columns={
        'name': 'Reactivo',
        'volume': 'Total Volume',
        'expiration_date': 'Next Expiration'
    })

    # Select and sort
    summary = summary[[
        'Reactivo', 'In Use', 'Stored', 'Total Volume', 'Next Expiration', 'Ratio'
    ]].sort_values(
        by=['Ratio', 'Total'],
        ascending=[False, False]
    ).reset_index(drop=True)

    return summary


def get_cost_insights():
    """
    Get cost-related insights for budget management.

    Returns:
        dict with keys:
        - top_expensive_reagents: List of (name, total_value) tuples
        - expired_value_this_month: $ thrown away
        - avg_reagent_age: Average days since arrival
    """
    # Top 5 most expensive reagents in inventory
    top_expensive = query_panels("""
        SELECT
            r.name,
            SUM(ru.purchase_price) as total_value
        FROM reagent_units ru
        JOIN reagents r ON r.id = ru.reagent_id
        WHERE LOWER(ru.status) IN ('stored', 'in use')
          AND ru.purchase_price IS NOT NULL
        GROUP BY r.id, r.name
        ORDER BY total_value DESC
        LIMIT 5
    """)

    # Value expired this month
    month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    expired_this_month = query_panels("""
        SELECT COALESCE(SUM(purchase_price), 0) as total
        FROM reagent_units
        WHERE expiration_date >= ?
          AND expiration_date < date('now')
          AND purchase_price IS NOT NULL
    """, (month_start,))

    # Average reagent age
    avg_age = query_panels("""
        SELECT AVG(julianday('now') - julianday(arrival_date)) as avg_days
        FROM reagent_units
        WHERE LOWER(status) = 'stored'
          AND arrival_date IS NOT NULL
    """)

    return {
        'top_expensive_reagents': list(zip(
            top_expensive['name'].tolist() if not top_expensive.empty else [],
            top_expensive['total_value'].tolist() if not top_expensive.empty else []
        )),
        'expired_value_this_month': float(expired_this_month.iloc[0]['total']) if not expired_this_month.empty else 0.0,
        'avg_reagent_age': float(avg_age.iloc[0]['avg_days']) if not avg_age.empty and avg_age.iloc[0]['avg_days'] is not None else 0.0
    }
