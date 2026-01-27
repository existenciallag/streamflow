"""
Economic & Panel Tracking Section
MVP: Usage logging, cost summaries, and basic dashboards
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date, timedelta
from ui.crud_panels import query_panels
import plotly.express as px
import plotly.graph_objects as go


def run_economic():
    """Main economic tracking interface"""
    st.title("💰 Economic & Panel Tracking")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 Log Usage", "📈 Reports"])

    # =============================================================================
    # DASHBOARD
    # =============================================================================
    with tab1:
        st.markdown("### Cost & Usage Overview")

        # Date range selector
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_date = st.date_input("From", value=date.today() - timedelta(days=30))
        with col_d2:
            end_date = st.date_input("To", value=date.today())

        st.markdown("---")

        # Key metrics
        metrics_query = query_panels("""
            SELECT
                COUNT(*) as total_tests,
                SUM(total_cost) as total_cost,
                AVG(cost_per_test) as avg_cost_per_test
            FROM panel_usage_log
            WHERE execution_date BETWEEN ? AND ?
        """, (str(start_date), str(end_date)))

        if metrics_query is not None and not metrics_query.empty:
            m = metrics_query.iloc[0]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tests", int(m['total_tests']) if m['total_tests'] else 0)
            with col2:
                st.metric("Total Cost", f"${m['total_cost']:.2f}" if m['total_cost'] else "$0.00")
            with col3:
                st.metric("Avg Cost/Test", f"${m['avg_cost_per_test']:.2f}" if m['avg_cost_per_test'] else "$0.00")

        st.markdown("---")

        # Panel usage frequency
        st.markdown("### 📊 Panel Usage Frequency")
        panel_usage = query_panels("""
            SELECT
                p.name as panel_name,
                pa.name as area_name,
                COUNT(pul.id) as times_used,
                SUM(pul.total_cost) as total_cost,
                AVG(pul.cost_per_test) as avg_cost
            FROM panel_usage_log pul
            JOIN panels p ON p.id = pul.panel_id
            LEFT JOIN panel_classifications pc ON pc.panel_id = p.id AND pc.is_primary = 1
            LEFT JOIN panel_areas pa ON pa.id = pc.area_id
            WHERE pul.execution_date BETWEEN ? AND ?
            GROUP BY p.id, p.name, pa.name
            ORDER BY times_used DESC
            LIMIT 10
        """, (str(start_date), str(end_date)))

        if panel_usage is not None and not panel_usage.empty:
            # Bar chart
            fig = px.bar(
                panel_usage,
                x='panel_name',
                y='times_used',
                color='area_name',
                title='Top 10 Most Used Panels',
                labels={'times_used': 'Times Used', 'panel_name': 'Panel'},
                text='times_used'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Table
            st.dataframe(
                panel_usage[['panel_name', 'area_name', 'times_used', 'total_cost', 'avg_cost']].rename(columns={
                    'panel_name': 'Panel',
                    'area_name': 'Area',
                    'times_used': 'Times Used',
                    'total_cost': 'Total Cost',
                    'avg_cost': 'Avg Cost/Test'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No usage data for this period")

        st.markdown("---")

        # Cost breakdown by area
        st.markdown("### 💵 Cost Breakdown by Area")
        area_costs = query_panels("""
            SELECT
                COALESCE(pa.name, 'Unclassified') as area_name,
                SUM(pul.total_cost) as total_cost,
                COUNT(pul.id) as test_count
            FROM panel_usage_log pul
            LEFT JOIN panel_classifications pc ON pc.panel_id = pul.panel_id AND pc.is_primary = 1
            LEFT JOIN panel_areas pa ON pa.id = pc.area_id
            WHERE pul.execution_date BETWEEN ? AND ?
            GROUP BY pa.name
            ORDER BY total_cost DESC
        """, (str(start_date), str(end_date)))

        if area_costs is not None and not area_costs.empty:
            # Pie chart
            fig = px.pie(
                area_costs,
                values='total_cost',
                names='area_name',
                title='Cost Distribution by Clinical Area'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cost data available")

        st.markdown("---")

        # Top consumed reagents
        st.markdown("### 🧪 Top Consumed Reagents")
        reagent_consumption = query_panels("""
            SELECT
                r.name as reagent_name,
                f.name as fluorochrome,
                b.name as brand,
                COUNT(rcl.id) as usage_count,
                SUM(rcl.volume_used) as total_volume,
                SUM(rcl.total_cost) as total_cost
            FROM reagent_consumption_log rcl
            JOIN reagents r ON r.id = rcl.reagent_id
            LEFT JOIN fluorochromes f ON f.id = r.fluorochrome
            LEFT JOIN brands b ON b.id = r.brand_id
            WHERE rcl.consumption_date BETWEEN ? AND ?
            GROUP BY r.id, r.name, f.name, b.name
            ORDER BY total_volume DESC
            LIMIT 10
        """, (str(start_date), str(end_date)))

        if reagent_consumption is not None and not reagent_consumption.empty:
            st.dataframe(
                reagent_consumption.rename(columns={
                    'reagent_name': 'Reagent',
                    'fluorochrome': 'Fluorochrome',
                    'brand': 'Brand',
                    'usage_count': 'Times Used',
                    'total_volume': 'Total Volume (µL)',
                    'total_cost': 'Total Cost ($)'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No reagent consumption data yet")

    # =============================================================================
    # LOG USAGE
    # =============================================================================
    with tab2:
        st.markdown("### Log Panel Usage")

        st.info("📝 Use this form to log panel usage for non-Oncohematology areas (Immunology, Fertility, etc.)")

        with st.form("log_usage"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Execution Details**")

                # Select area
                areas = query_panels("SELECT id, name FROM panel_areas ORDER BY name")
                if areas is None or areas.empty:
                    st.warning("No clinical areas configured")
                    area_options = []
                else:
                    area_options = list(areas['name'])
                    area_ids = list(areas['id'])

                    selected_area_name = st.selectbox("Clinical Area *", area_options)
                    selected_area_idx = area_options.index(selected_area_name)
                    selected_area_id = area_ids[selected_area_idx]

                    # Get panels for this area
                    panels_in_area = query_panels("""
                        SELECT DISTINCT p.id, p.name, p.version
                        FROM panels p
                        JOIN panel_classifications pc ON pc.panel_id = p.id
                        WHERE pc.area_id = ? AND p.status IN ('validated', 'active')
                        ORDER BY p.name
                    """, (selected_area_id,))

                    if panels_in_area is None or panels_in_area.empty:
                        st.warning(f"No panels available for {selected_area_name}")
                        panel_options = []
                    else:
                        panel_options = [f"{p['name']} (v{p['version']})" for _, p in panels_in_area.iterrows()]
                        selected_panel_idx = st.selectbox("Panel *", range(len(panel_options)),
                                                         format_func=lambda x: panel_options[x])

                        execution_date = st.date_input("Execution Date *", value=date.today())

            with col2:
                st.markdown("**Volume & Cost**")

                tests_count = st.number_input("Number of Tests *", min_value=1, value=1, step=1)
                operator = st.text_input("Operator", placeholder="e.g., Dr. Smith")
                notes = st.text_area("Notes", height=100, placeholder="Any additional notes...")

            if st.form_submit_button("✓ Log Usage", type="primary", use_container_width=True):
                if not area_options or not panel_options:
                    st.error("Please configure areas and panels first")
                else:
                    try:
                        panel_id = panels_in_area.iloc[selected_panel_idx]['id']
                        panel_version = panels_in_area.iloc[selected_panel_idx]['version']

                        # Calculate cost from panel
                        from utils.pricing import calculate_panel_cost_current
                        cost_result = calculate_panel_cost_current(panel_id, strategy='cheapest')

                        if 'error' in cost_result:
                            st.warning(f"Could not calculate cost: {cost_result['error']}")
                            cost_per_test = 0.0
                        else:
                            cost_per_test = cost_result.get('total_cost', 0.0)

                        total_cost = cost_per_test * tests_count

                        # Insert usage log
                        usage_id = str(uuid.uuid4())
                        query_panels("""
                            INSERT INTO panel_usage_log (
                                id, panel_id, panel_version, execution_date, area_id,
                                is_patient_tracked, tests_count,
                                cost_per_test, total_cost,
                                operator, notes, created_at
                            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                        """, (
                            usage_id, panel_id, panel_version, str(execution_date), selected_area_id,
                            tests_count, cost_per_test, total_cost,
                            operator or None, notes or None, datetime.now().isoformat()
                        ), commit=True)

                        st.success(f"✅ Logged {tests_count} test(s) for {panels_in_area.iloc[selected_panel_idx]['name']}")
                        st.info(f"Total cost: ${total_cost:.2f}")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error logging usage: {e}")

        st.markdown("---")

        # Recent logs
        st.markdown("### Recent Usage Logs")
        recent_logs = query_panels("""
            SELECT
                pul.execution_date,
                p.name as panel_name,
                pa.name as area_name,
                pul.tests_count,
                pul.total_cost,
                pul.operator
            FROM panel_usage_log pul
            JOIN panels p ON p.id = pul.panel_id
            LEFT JOIN panel_areas pa ON pa.id = pul.area_id
            WHERE pul.is_patient_tracked = 0
            ORDER BY pul.created_at DESC
            LIMIT 20
        """)

        if recent_logs is not None and not recent_logs.empty:
            st.dataframe(
                recent_logs.rename(columns={
                    'execution_date': 'Date',
                    'panel_name': 'Panel',
                    'area_name': 'Area',
                    'tests_count': 'Tests',
                    'total_cost': 'Cost ($)',
                    'operator': 'Operator'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No usage logs yet")

    # =============================================================================
    # REPORTS
    # =============================================================================
    with tab3:
        st.markdown("### Reports & Analysis")

        # Monthly summary
        st.markdown("#### 📅 Monthly Summary")

        monthly_data = query_panels("""
            SELECT
                strftime('%Y-%m', execution_date) as month,
                COUNT(*) as total_tests,
                SUM(total_cost) as total_cost
            FROM panel_usage_log
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)

        if monthly_data is not None and not monthly_data.empty:
            # Line chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=monthly_data['month'],
                y=monthly_data['total_cost'],
                mode='lines+markers',
                name='Total Cost',
                line=dict(color='#1f77b4', width=2)
            ))
            fig.update_layout(
                title='Monthly Cost Trend',
                xaxis_title='Month',
                yaxis_title='Total Cost ($)',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                monthly_data.rename(columns={
                    'month': 'Month',
                    'total_tests': 'Total Tests',
                    'total_cost': 'Total Cost ($)'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No data for monthly analysis")

        st.markdown("---")

        # Export data
        st.markdown("#### 📥 Export Data")

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("📊 Export Usage Data (CSV)", use_container_width=True):
                export_data = query_panels("""
                    SELECT
                        pul.execution_date,
                        p.name as panel_name,
                        pa.name as area_name,
                        pul.tests_count,
                        pul.cost_per_test,
                        pul.total_cost,
                        pul.operator,
                        pul.notes
                    FROM panel_usage_log pul
                    JOIN panels p ON p.id = pul.panel_id
                    LEFT JOIN panel_areas pa ON pa.id = pul.area_id
                    ORDER BY pul.execution_date DESC
                """)

                if export_data is not None and not export_data.empty:
                    csv = export_data.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"panel_usage_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No data to export")

        with col_e2:
            if st.button("💰 Export Cost Summary (CSV)", use_container_width=True):
                cost_summary = query_panels("""
                    SELECT
                        p.name as panel_name,
                        pa.name as area_name,
                        COUNT(pul.id) as times_used,
                        SUM(pul.tests_count) as total_tests,
                        SUM(pul.total_cost) as total_cost,
                        AVG(pul.cost_per_test) as avg_cost_per_test,
                        MIN(pul.execution_date) as first_used,
                        MAX(pul.execution_date) as last_used
                    FROM panel_usage_log pul
                    JOIN panels p ON p.id = pul.panel_id
                    LEFT JOIN panel_classifications pc ON pc.panel_id = p.id AND pc.is_primary = 1
                    LEFT JOIN panel_areas pa ON pa.id = pc.area_id
                    GROUP BY p.id, p.name, pa.name
                    ORDER BY total_cost DESC
                """)

                if cost_summary is not None and not cost_summary.empty:
                    csv = cost_summary.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"cost_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No data to export")
