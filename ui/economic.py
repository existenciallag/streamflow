"""
Economic & Panel Tracking Section
MVP: Usage logging, cost summaries, and basic dashboards
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date, timedelta
from ui.crud_panels import query_panels
from utils.translations import get_lang_dict
import plotly.express as px
import plotly.graph_objects as go


def run_economic():
    """Main economic tracking interface"""
    # Get language from session state
    lang = st.session_state.get('language', 'en')
    t = get_lang_dict('economic', lang)

    st.title(f"💰 {t['title']}")

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        f"📊 {t['dashboard_tab']}",
        f"📝 {t['log_usage_tab']}",
        f"📈 {t['reports_tab']}"
    ])

    # =============================================================================
    # DASHBOARD
    # =============================================================================
    with tab1:
        st.markdown(f"### {t['cost_usage_overview']}")

        # Date range selector
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_date = st.date_input(t['from_date_label'], value=date.today() - timedelta(days=30))
        with col_d2:
            end_date = st.date_input(t['to_date_label'], value=date.today())

        st.markdown("---")

        # Key metrics with cost validation
        metrics_query = query_panels("""
            SELECT
                SUM(COALESCE(tests_count, 1)) as total_tests,
                SUM(COALESCE(total_cost, 0)) as total_cost,
                AVG(COALESCE(cost_per_test, 0)) as avg_cost_per_test,
                SUM(CASE WHEN cost_per_test IS NULL OR cost_per_test = 0 THEN 1 ELSE 0 END) as incomplete_cost_count
            FROM panel_usage_log
            WHERE execution_date BETWEEN ? AND ?
        """, (str(start_date), str(end_date)))

        if metrics_query is not None and not metrics_query.empty:
            m = metrics_query.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(t['total_tests_metric'], int(m['total_tests']) if m['total_tests'] else 0)
            with col2:
                total_cost_val = float(m['total_cost']) if m['total_cost'] else 0.0
                st.metric(t['total_cost_metric'], f"${total_cost_val:.2f}")
            with col3:
                avg_cost_val = float(m['avg_cost_per_test']) if m['avg_cost_per_test'] else 0.0
                st.metric(t['avg_cost_metric'], f"${avg_cost_val:.2f}")
            with col4:
                incomplete_count = int(m['incomplete_cost_count']) if m['incomplete_cost_count'] else 0
                st.metric(
                    t.get('incomplete_costs', 'Incomplete Costs'),
                    incomplete_count,
                    delta=None if incomplete_count == 0 else "⚠️",
                    delta_color="off" if incomplete_count == 0 else "inverse"
                )

            # Warning if there are incomplete costs
            if incomplete_count > 0:
                st.warning(f"⚠️ {incomplete_count} panel execution(s) have missing or zero cost data. Please verify panel pricing.")

        # Usage source breakdown (Patient-tracked vs Manual)
        st.markdown("---")
        st.markdown(f"#### {t.get('usage_source_breakdown', '📊 Usage Source Breakdown')}")

        source_breakdown = query_panels("""
            SELECT
                CASE WHEN is_patient_tracked = 1 THEN 'Patient-Tracked' ELSE 'Manual' END as source,
                COUNT(*) as count,
                SUM(COALESCE(total_cost, 0)) as total_cost
            FROM panel_usage_log
            WHERE execution_date BETWEEN ? AND ?
            GROUP BY is_patient_tracked
        """, (str(start_date), str(end_date)))

        if source_breakdown is not None and not source_breakdown.empty:
            col_s1, col_s2 = st.columns(2)

            with col_s1:
                fig = px.pie(
                    source_breakdown,
                    values='count',
                    names='source',
                    title=t.get('usage_by_source', 'Panel Executions by Source'),
                    color_discrete_map={'Patient-Tracked': '#2ecc71', 'Manual': '#3498db'}
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_s2:
                for _, row in source_breakdown.iterrows():
                    source_name = row['source']
                    icon = "📋" if source_name == "Patient-Tracked" else "✏️"
                    st.metric(
                        f"{icon} {source_name}",
                        f"{int(row['count'])} panels",
                        delta=f"${row['total_cost']:.2f} total"
                    )

                st.caption("💡 Patient-Tracked: Automatically logged from Clinical cases | Manual: Logged via Economic section")

        st.markdown("---")

        # Panel usage frequency with cost validation
        st.markdown(f"### 📊 {t['panel_usage_frequency']}")
        panel_usage = query_panels("""
            SELECT
                p.name as panel_name,
                COALESCE(pa.name, 'Unclassified') as area_name,
                COUNT(pul.id) as times_logged,
                SUM(COALESCE(pul.tests_count, 1)) as total_tests,
                SUM(COALESCE(pul.total_cost, 0)) as total_cost,
                AVG(COALESCE(pul.cost_per_test, 0)) as avg_cost,
                SUM(CASE WHEN pul.cost_per_test IS NULL OR pul.cost_per_test = 0 THEN 1 ELSE 0 END) as incomplete_count
            FROM panel_usage_log pul
            JOIN panels p ON p.id = pul.panel_id
            LEFT JOIN panel_classifications pc ON pc.panel_id = p.id AND pc.is_primary = 1
            LEFT JOIN panel_areas pa ON pa.id = pc.area_id
            WHERE pul.execution_date BETWEEN ? AND ?
            GROUP BY p.id, p.name, pa.name
            ORDER BY total_tests DESC
            LIMIT 10
        """, (str(start_date), str(end_date)))

        if panel_usage is not None and not panel_usage.empty:
            # Bar chart
            fig = px.bar(
                panel_usage,
                x='panel_name',
                y='total_tests',
                color='area_name',
                title=t.get('top_10_panels_by_tests', 'Top 10 Panels by Test Volume'),
                labels={'total_tests': t.get('total_tests_label', 'Total Tests'), 'panel_name': t['panel_label']},
                text='total_tests'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Table
            st.dataframe(
                panel_usage[['panel_name', 'area_name', 'times_logged', 'total_tests', 'total_cost', 'avg_cost']].rename(columns={
                    'panel_name': t['panel_column'],
                    'area_name': t['area_column'],
                    'times_logged': t.get('times_logged_column', 'Times Logged'),
                    'total_tests': t.get('total_tests_column', 'Total Tests'),
                    'total_cost': t['total_cost_column'],
                    'avg_cost': t['avg_cost_column']
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(t['no_usage_data'])

        st.markdown("---")

        # Cost breakdown by area with validation
        st.markdown(f"### 💵 {t['cost_breakdown_header']}")
        area_costs = query_panels("""
            SELECT
                COALESCE(pa.name, 'Unclassified') as area_name,
                SUM(COALESCE(pul.total_cost, 0)) as total_cost,
                SUM(COALESCE(pul.tests_count, 1)) as test_count
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
                title=t['cost_distribution_title']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(t['no_cost_data'])

        st.markdown("---")

        # Cost breakdown by disease category with validation
        st.markdown(f"### 🔬 {t.get('cost_by_disease_category', 'Cost Breakdown by Disease Category')}")
        disease_costs = query_panels("""
            SELECT
                COALESCE(pdc.name, 'Unclassified') as disease_name,
                SUM(COALESCE(pul.total_cost, 0)) as total_cost,
                SUM(COALESCE(pul.tests_count, 1)) as test_count
            FROM panel_usage_log pul
            LEFT JOIN panel_classifications pc ON pc.panel_id = pul.panel_id AND pc.is_primary = 1
            LEFT JOIN panel_disease_categories pdc ON pdc.id = pc.disease_category_id
            WHERE pul.execution_date BETWEEN ? AND ?
            GROUP BY pdc.name
            ORDER BY total_cost DESC
        """, (str(start_date), str(end_date)))

        if disease_costs is not None and not disease_costs.empty:
            col_d1, col_d2 = st.columns(2)

            with col_d1:
                # Pie chart for disease distribution
                fig = px.pie(
                    disease_costs,
                    values='total_cost',
                    names='disease_name',
                    title=t.get('disease_cost_distribution', 'Cost Distribution by Disease')
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_d2:
                # Table with details
                st.dataframe(
                    disease_costs.rename(columns={
                        'disease_name': t.get('disease_column', 'Disease'),
                        'total_cost': t.get('total_cost_column', 'Total Cost'),
                        'test_count': t.get('tests_column', 'Tests')
                    }),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info(t.get('no_disease_data', 'No disease category data available'))

        st.markdown("---")

        # Antibody vs General Reagent cost breakdown
        st.markdown(f"### 💊 {t.get('reagent_type_breakdown', 'Antibody vs General Reagent Costs')}")

        # Get all panels used in the period
        panels_in_period = query_panels("""
            SELECT DISTINCT pul.panel_id
            FROM panel_usage_log pul
            WHERE pul.execution_date BETWEEN ? AND ?
        """, (str(start_date), str(end_date)))

        if panels_in_period is not None and not panels_in_period.empty:
            antibody_total = 0.0
            general_reagent_total = 0.0

            for _, row in panels_in_period.iterrows():
                from utils.cost_utils import get_panel_cost_breakdown
                breakdown = get_panel_cost_breakdown(row['panel_id'])

                for item in breakdown.get('breakdown', []):
                    # Safely get cost - handle both 'cost' and 'reagent_cost' fields
                    item_cost = item.get('cost') or item.get('reagent_cost') or 0.0

                    # Skip if cost is None (out of stock items)
                    if item_cost is None:
                        item_cost = 0.0

                    if item.get('type') == 'general_reagent':
                        general_reagent_total += item_cost
                    else:
                        antibody_total += item_cost

            if antibody_total > 0 or general_reagent_total > 0:
                col_r1, col_r2 = st.columns(2)

                with col_r1:
                    # Pie chart
                    reagent_type_data = pd.DataFrame({
                        'Type': [
                            t.get('antibodies_label', 'Antibodies'),
                            t.get('general_reagents_label', 'General Reagents')
                        ],
                        'Cost': [antibody_total, general_reagent_total]
                    })

                    fig = px.pie(
                        reagent_type_data,
                        values='Cost',
                        names='Type',
                        title=t.get('cost_by_reagent_type', 'Cost Split by Reagent Type'),
                        color_discrete_sequence=['#1f77b4', '#ff7f0e']
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col_r2:
                    # Metrics
                    st.metric(
                        t.get('antibody_costs', 'Antibody Costs'),
                        f"${antibody_total:.2f}",
                        help=t.get('antibody_costs_help', 'Total cost of antibodies used in panels')
                    )
                    st.metric(
                        t.get('general_reagent_costs', 'General Reagent Costs'),
                        f"${general_reagent_total:.2f}",
                        help=t.get('general_reagent_costs_help', 'Total cost of buffers, solutions, and consumables')
                    )

                    total = antibody_total + general_reagent_total
                    if total > 0:
                        ab_pct = (antibody_total / total) * 100
                        gr_pct = (general_reagent_total / total) * 100
                        st.caption(f"📊 {t.get('antibodies_label', 'Antibodies')}: {ab_pct:.1f}% | {t.get('general_reagents_label', 'General Reagents')}: {gr_pct:.1f}%")
        else:
            st.info(t.get('no_reagent_type_data', 'No reagent type breakdown available'))

        st.markdown("---")

        # Top consumed general reagents
        st.markdown(f"### 🧪 {t.get('top_general_reagents', 'Top Consumed General Reagents')}")

        general_reagent_usage = query_panels("""
            SELECT
                gr.name as reagent_name,
                gr.type as reagent_type,
                b.name as brand,
                pgr.consumption_type,
                SUM(pgr.consumption_amount * COALESCE(pul.tests_count, 1)) as total_consumed,
                SUM(pgr.cost_per_test * COALESCE(pul.tests_count, 1)) as total_cost,
                COUNT(DISTINCT pgr.panel_id) as panel_count,
                SUM(COALESCE(pul.tests_count, 1)) as total_tests
            FROM panel_general_reagents pgr
            JOIN general_reagents gr ON gr.id = pgr.general_reagent_id
            LEFT JOIN brands b ON b.id = gr.brand_id
            JOIN panels p ON p.id = pgr.panel_id
            JOIN panel_usage_log pul ON pul.panel_id = p.id
            WHERE pul.execution_date BETWEEN ? AND ?
            GROUP BY gr.id, gr.name, gr.type, b.name, pgr.consumption_type
            ORDER BY total_cost DESC
            LIMIT 10
        """, (str(start_date), str(end_date)))

        if general_reagent_usage is not None and not general_reagent_usage.empty:
            # Format consumption with units
            general_reagent_usage['formatted_consumption'] = general_reagent_usage.apply(
                lambda x: f"{x['total_consumed']:.1f} {x['consumption_type']}", axis=1
            )

            st.dataframe(
                general_reagent_usage[['reagent_name', 'reagent_type', 'brand', 'formatted_consumption', 'total_cost', 'panel_count']].rename(columns={
                    'reagent_name': t.get('reagent_column', 'Reagent'),
                    'reagent_type': t.get('type_column', 'Type'),
                    'brand': t.get('brand_column', 'Brand'),
                    'formatted_consumption': t.get('consumption_column', 'Total Consumed'),
                    'total_cost': t.get('total_cost_column', 'Total Cost'),
                    'panel_count': t.get('panels_column', 'Panels')
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(t.get('no_general_reagent_usage', 'No general reagent usage data available'))

        st.markdown("---")

        # Top consumed reagents (antibodies)
        st.markdown(f"### 🧪 {t['top_consumed_reagents']}")
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
                    'reagent_name': t['panel_label'],
                    'fluorochrome': t['fluorochrome_column'],
                    'brand': t['brand_column'],
                    'usage_count': t['times_used_column'],
                    'total_volume': t['total_volume_column'],
                    'total_cost': t['total_cost_column']
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(t['no_reagent_consumption'])

    # =============================================================================
    # LOG USAGE
    # =============================================================================
    with tab2:
        st.markdown(f"### {t['log_usage_header']}")

        st.info(f"📝 {t['log_usage_info']}")

        # Selection controls OUTSIDE the form for dynamic updates
        col_sel1, col_sel2 = st.columns(2)

        with col_sel1:
            st.markdown(f"**{t.get('select_panel_label', 'Select Panel')}**")

            # Select area
            areas = query_panels("SELECT id, name FROM panel_areas ORDER BY name")
            if areas is None or areas.empty:
                st.warning(t['no_clinical_areas_warning'])
                st.stop()

            area_options = list(areas['name'])
            area_ids = list(areas['id'])

            selected_area_name = st.selectbox(t['clinical_area_label'], area_options, key="log_area_select")
            selected_area_idx = area_options.index(selected_area_name)
            selected_area_id = area_ids[selected_area_idx]

            # Try to get panels classified for this area first
            panels_in_area = query_panels("""
                SELECT DISTINCT p.id, p.name, p.version
                FROM panels p
                JOIN panel_classifications pc ON pc.panel_id = p.id
                WHERE pc.area_id = ? AND p.status IN ('validated', 'active')
                ORDER BY p.name
            """, (selected_area_id,))

            # If no classified panels, show all panels with a warning
            if panels_in_area is None or panels_in_area.empty:
                st.info(f"ℹ️ No panels classified for {selected_area_name}. Showing all active panels.")
                panels_in_area = query_panels("""
                    SELECT DISTINCT p.id, p.name, p.version
                    FROM panels p
                    WHERE p.status IN ('validated', 'active')
                    ORDER BY p.name
                """)

            if panels_in_area is None or panels_in_area.empty:
                st.error(t.get('no_panels_available_at_all', 'No active panels found in the system'))
                st.stop()

            panel_options = [f"{p['name']} (v{p['version']})" for _, p in panels_in_area.iterrows()]
            selected_panel_display = st.selectbox(t['panel_label_form'], panel_options, key="log_panel_select")
            selected_panel_idx = panel_options.index(selected_panel_display)

        with col_sel2:
            st.markdown(f"**{t.get('select_dates_label', 'Select Date(s)')}**")

            # Date range selection
            date_mode = st.radio(
                t.get('date_mode_label', 'Logging Mode'),
                options=['single', 'range'],
                format_func=lambda x: t.get(f'date_mode_{x}', 'Single Date' if x == 'single' else 'Date Range'),
                horizontal=True,
                key="log_date_mode"
            )

            if date_mode == 'single':
                execution_date = st.date_input(t['execution_date_label'], value=date.today(), key="log_single_date")
                start_date_sel = execution_date
                end_date_sel = execution_date
            else:
                col_dr1, col_dr2 = st.columns(2)
                with col_dr1:
                    start_date_sel = st.date_input(
                        t.get('start_date_label', 'Start Date'),
                        value=date.today() - timedelta(days=7),
                        key="log_start_date"
                    )
                with col_dr2:
                    end_date_sel = st.date_input(
                        t.get('end_date_label', 'End Date'),
                        value=date.today(),
                        key="log_end_date"
                    )
                execution_date = start_date_sel  # For backward compatibility

        st.markdown("---")

        # Form for submission details
        with st.form("log_usage"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**{t['volume_cost_section']}**")
                tests_count = st.number_input(t['tests_count_label'], min_value=1, value=1, step=1)

            with col2:
                st.markdown(f"**{t.get('additional_info_label', 'Additional Information')}**")
                operator = st.text_input(t['operator_label'], placeholder=t['operator_placeholder'])
                notes = st.text_area(t['notes_label'], height=100, placeholder=t['notes_placeholder'])

            if st.form_submit_button(f"✓ {t['log_usage_button']}", type="primary", use_container_width=True):
                try:
                    panel_id = panels_in_area.iloc[selected_panel_idx]['id']
                    panel_version = panels_in_area.iloc[selected_panel_idx]['version']
                    panel_name = panels_in_area.iloc[selected_panel_idx]['name']

                    # Calculate cost from panel (includes antibodies + general reagents)
                    from utils.cost_utils import get_panel_cost_breakdown
                    cost_result = get_panel_cost_breakdown(panel_id)

                    if 'error' in cost_result:
                        st.warning(t.get('cost_calculation_error', 'Error calculating cost: {error}').format(error=cost_result.get('error', 'Unknown')))
                        cost_per_test = 0.0
                    else:
                        cost_per_test = cost_result.get('total_cost', 0.0)

                        # Show cost breakdown
                        if not cost_result.get('is_complete', True):
                            st.warning(f"⚠️ Some reagents are missing prices: {', '.join(cost_result.get('missing_prices', []))}")

                    total_cost = cost_per_test * tests_count

                    # Validate date range
                    if start_date_sel > end_date_sel:
                        st.error(t.get('invalid_date_range', 'Start date must be before or equal to end date'))
                        st.stop()

                    # Insert usage log
                    usage_id = str(uuid.uuid4())
                    query_panels("""
                        INSERT INTO panel_usage_log (
                            id, panel_id, panel_version, execution_date, start_date, end_date, area_id,
                            is_patient_tracked, tests_count,
                            cost_per_test, total_cost,
                            operator, notes, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                    """, (
                        usage_id, panel_id, panel_version, str(execution_date), str(start_date_sel), str(end_date_sel), selected_area_id,
                        tests_count, cost_per_test, total_cost,
                        operator or None, notes or None, datetime.now().isoformat()
                    ), commit=True)

                    date_range_text = ""
                    if start_date_sel == end_date_sel:
                        date_range_text = str(start_date_sel)
                    else:
                        date_range_text = f"{start_date_sel} to {end_date_sel}"

                    st.success(f"✅ {t.get('logged_success', 'Successfully logged {count} test(s) for panel {panel}').format(count=tests_count, panel=panel_name)} ({date_range_text})")
                    st.info(t.get('total_cost_info', 'Total cost: ${amount}').format(amount=f"{total_cost:.2f}"))
                    st.rerun()

                except Exception as e:
                    st.error(t.get('logging_error', 'Error logging usage: {error}').format(error=str(e)))

        st.markdown("---")

        # Recent logs
        st.markdown(f"### {t['recent_usage_logs']}")
        recent_logs = query_panels("""
            SELECT
                pul.execution_date,
                pul.start_date,
                pul.end_date,
                p.name as panel_name,
                pa.name as area_name,
                pul.tests_count,
                pul.total_cost,
                pul.operator,
                pul.is_patient_tracked,
                cc.case_number
            FROM panel_usage_log pul
            JOIN panels p ON p.id = pul.panel_id
            LEFT JOIN panel_areas pa ON pa.id = pul.area_id
            LEFT JOIN case_panels cp ON cp.id = pul.case_panel_id
            LEFT JOIN clinical_cases cc ON cc.id = cp.case_id
            ORDER BY pul.created_at DESC
            LIMIT 20
        """)

        if recent_logs is not None and not recent_logs.empty:
            # Format date range display
            def format_date_range(row):
                start = row.get('start_date') or row.get('execution_date')
                end = row.get('end_date') or row.get('execution_date')
                if start and end:
                    if start == end:
                        return str(start)
                    else:
                        return f"{start} to {end}"
                return row.get('execution_date', 'N/A')

            # Format source display
            def format_source(row):
                if row.get('is_patient_tracked') == 1:
                    case_num = row.get('case_number')
                    if case_num:
                        return f"📋 Patient ({case_num})"
                    return "📋 Patient"
                return "✏️ Manual"

            recent_logs['date_range'] = recent_logs.apply(format_date_range, axis=1)
            recent_logs['source'] = recent_logs.apply(format_source, axis=1)

            st.dataframe(
                recent_logs[['date_range', 'panel_name', 'area_name', 'source', 'tests_count', 'total_cost', 'operator']].rename(columns={
                    'date_range': t.get('date_range_column', 'Date / Period'),
                    'panel_name': t['panel_column'],
                    'area_name': t['area_column'],
                    'source': t.get('source_column', 'Source'),
                    'tests_count': t['tests_column'],
                    'total_cost': t['cost_column'],
                    'operator': t['operator_column']
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(t['no_usage_logs'])

    # =============================================================================
    # REPORTS
    # =============================================================================
    with tab3:
        st.markdown(f"### {t['reports_analysis']}")

        # Monthly summary
        st.markdown(f"#### 📅 {t['monthly_summary']}")

        monthly_data = query_panels("""
            SELECT
                strftime('%Y-%m', execution_date) as month,
                SUM(COALESCE(tests_count, 1)) as total_tests,
                SUM(COALESCE(total_cost, 0)) as total_cost
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
                name=t['total_cost_metric'],
                line=dict(color='#1f77b4', width=2)
            ))
            fig.update_layout(
                title=t['monthly_cost_trend_title'],
                xaxis_title=t['month_label'],
                yaxis_title=t['total_cost_label'],
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                monthly_data.rename(columns={
                    'month': t['month_label'],
                    'total_tests': t['total_tests_column'],
                    'total_cost': t['total_cost_label']
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(t['no_monthly_data'])

        st.markdown("---")

        # Export data
        st.markdown(f"#### 📥 {t['export_data_header']}")

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button(f"📊 {t['export_usage_button']}", use_container_width=True):
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
                        label=t['download_csv_label'],
                        data=csv,
                        file_name=f"panel_usage_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning(t['no_data_to_export'])

        with col_e2:
            if st.button(f"💰 {t['cost_summary_button']}", use_container_width=True):
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
                        label=t['download_csv_label'],
                        data=csv,
                        file_name=f"cost_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning(t['no_data_to_export'])
