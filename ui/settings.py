"""
Settings Section - Configuration Management
Manage panel categories, areas, and application settings
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from ui.crud_panels import query_panels
from utils.categories import (
    get_all_areas,
    get_all_disease_categories,
    add_area,
    add_disease_category
)


def run_settings():
    """Main settings interface"""
    st.title("Settings")

    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs(["Clinical Areas", "Disease Categories", "Diagnostic Algorithms", "Application"])

    # =============================================================================
    # CLINICAL AREAS MANAGEMENT
    # =============================================================================
    with tab1:
        st.markdown("### Clinical Areas Management")
        st.caption("Configure the clinical areas used for panel classification")

        # Display existing areas
        areas = get_all_areas()

        if areas is not None and not areas.empty:
            st.markdown("#### Current Areas")

            # Editable dataframe display
            display_areas = areas[['name', 'code', 'description', 'display_order']].copy()
            display_areas = display_areas.rename(columns={
                'name': 'Name',
                'code': 'Code',
                'description': 'Description',
                'display_order': 'Order'
            })

            st.dataframe(display_areas, use_container_width=True, hide_index=True)

            # Edit area
            st.markdown("---")
            st.markdown("#### Edit Area")

            area_to_edit = st.selectbox(
                "Select area to edit",
                options=list(areas['name']),
                key="edit_area_select"
            )

            if area_to_edit:
                selected_area = areas[areas['name'] == area_to_edit].iloc[0]

                with st.form("edit_area_form"):
                    col1, col2 = st.columns(2)

                    with col1:
                        edit_name = st.text_input("Name", value=selected_area['name'])
                        edit_code = st.text_input("Code", value=selected_area['code'])

                    with col2:
                        edit_description = st.text_area("Description", value=selected_area.get('description', ''))
                        edit_order = st.number_input("Display Order", value=int(selected_area['display_order']), min_value=1)

                    if st.form_submit_button("Save Changes", use_container_width=True):
                        try:
                            query_panels("""
                                UPDATE panel_areas
                                SET name = ?, code = ?, description = ?, display_order = ?
                                WHERE id = ?
                            """, (edit_name, edit_code, edit_description, edit_order, selected_area['id']), commit=True)

                            st.success(f"Area '{edit_name}' updated successfully")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating area: {e}")
        else:
            st.info("No clinical areas configured yet")

        # Add new area
        st.markdown("---")
        st.markdown("#### Add New Clinical Area")

        with st.form("new_area_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_name = st.text_input("Name *", placeholder="e.g., Immunology")
                new_code = st.text_input("Code *", placeholder="e.g., IMMUNO", max_chars=20)

            with col2:
                new_description = st.text_area("Description", placeholder="Brief description of this clinical area")
                new_order = st.number_input("Display Order", value=99, min_value=1)

            if st.form_submit_button("Add Area", type="primary", use_container_width=True):
                if not new_name or not new_code:
                    st.error("Name and Code are required")
                else:
                    try:
                        # Check if code already exists
                        existing = query_panels("SELECT id FROM panel_areas WHERE code = ?", (new_code,))
                        if not existing.empty:
                            st.error(f"Code '{new_code}' already exists")
                        else:
                            add_area(new_name, new_code, new_description)
                            st.success(f"Area '{new_name}' added successfully")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error adding area: {e}")

    # =============================================================================
    # DISEASE CATEGORIES MANAGEMENT
    # =============================================================================
    with tab2:
        st.markdown("### Disease Categories Management")
        st.caption("Configure disease categories for clinical classification")

        # Display existing categories
        categories = get_all_disease_categories()

        if categories is not None and not categories.empty:
            st.markdown("#### Current Categories")

            display_cats = categories[['name', 'area_name', 'icd_code', 'requires_patient_tracking']].copy()
            display_cats = display_cats.rename(columns={
                'name': 'Category',
                'area_name': 'Area',
                'icd_code': 'ICD-10',
                'requires_patient_tracking': 'Patient Tracking'
            })
            display_cats['Patient Tracking'] = display_cats['Patient Tracking'].apply(lambda x: '✓' if x else '')

            st.dataframe(display_cats, use_container_width=True, hide_index=True)

            # Edit category
            st.markdown("---")
            st.markdown("#### Edit Category")

            cat_to_edit = st.selectbox(
                "Select category to edit",
                options=list(categories['name']),
                key="edit_cat_select"
            )

            if cat_to_edit:
                selected_cat = categories[categories['name'] == cat_to_edit].iloc[0]

                with st.form("edit_category_form"):
                    col1, col2 = st.columns(2)

                    with col1:
                        edit_cat_name = st.text_input("Category Name", value=selected_cat['name'])
                        edit_icd = st.text_input("ICD-10 Code", value=selected_cat.get('icd_code', ''))

                    with col2:
                        # Get areas for dropdown
                        all_areas = get_all_areas()
                        if all_areas is not None and not all_areas.empty:
                            area_options = ["(None)"] + list(all_areas['name'])
                            area_ids = [None] + list(all_areas['id'])

                            current_area_name = selected_cat.get('area_name', '(None)')
                            if current_area_name not in area_options:
                                current_area_name = "(None)"

                            edit_area_name = st.selectbox(
                                "Clinical Area",
                                options=area_options,
                                index=area_options.index(current_area_name)
                            )
                            edit_area_id = area_ids[area_options.index(edit_area_name)]
                        else:
                            st.warning("No clinical areas available")
                            edit_area_id = None

                        edit_patient_tracking = st.checkbox(
                            "Requires Patient Tracking",
                            value=bool(selected_cat.get('requires_patient_tracking'))
                        )

                    edit_cat_description = st.text_area("Description", value=selected_cat.get('description', ''))

                    if st.form_submit_button("Save Changes", use_container_width=True):
                        try:
                            query_panels("""
                                UPDATE panel_disease_categories
                                SET name = ?, area_id = ?, description = ?, icd_code = ?, requires_patient_tracking = ?
                                WHERE id = ?
                            """, (
                                edit_cat_name, edit_area_id, edit_cat_description, edit_icd,
                                1 if edit_patient_tracking else 0, selected_cat['id']
                            ), commit=True)

                            st.success(f"Category '{edit_cat_name}' updated successfully")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating category: {e}")

        else:
            st.info("No disease categories configured yet")

        # Add new category
        st.markdown("---")
        st.markdown("#### Add New Disease Category")

        with st.form("new_category_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_cat_name = st.text_input("Category Name *", placeholder="e.g., Acute Myeloid Leukemia")
                new_cat_icd = st.text_input("ICD-10 Code", placeholder="e.g., C92.0")

            with col2:
                # Get areas for dropdown
                all_areas = get_all_areas()
                if all_areas is not None and not all_areas.empty:
                    area_options = ["(None)"] + list(all_areas['name'])
                    area_ids = [None] + list(all_areas['id'])

                    new_cat_area_name = st.selectbox("Clinical Area", options=area_options)
                    new_cat_area_id = area_ids[area_options.index(new_cat_area_name)]
                else:
                    st.warning("No clinical areas available. Create an area first.")
                    new_cat_area_id = None

                new_cat_patient_tracking = st.checkbox("Requires Patient Tracking")

            new_cat_description = st.text_area("Description", placeholder="Brief description of this disease category")

            if st.form_submit_button("Add Category", type="primary", use_container_width=True):
                if not new_cat_name:
                    st.error("Category name is required")
                else:
                    try:
                        add_disease_category(
                            new_cat_name,
                            new_cat_area_id,
                            new_cat_description,
                            new_cat_icd,
                            new_cat_patient_tracking
                        )
                        st.success(f"Category '{new_cat_name}' added successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding category: {e}")

    # =============================================================================
    # DIAGNOSTIC ALGORITHMS
    # =============================================================================
    with tab3:
        st.markdown("### Diagnostic Algorithms Management")
        st.caption("Create and manage clinical decision trees for diagnostic pathways")

        # Display existing algorithms
        algorithms = query_panels("""
            SELECT
                da.id,
                da.name,
                da.rule_logic,
                da.description,
                da.starting_panel_id,
                pa.name as clinical_area,
                p.name as starting_panel_name,
                da.created_by,
                da.created_at
            FROM diagnostic_algorithms da
            LEFT JOIN panel_areas pa ON pa.id = da.clinical_area_id
            LEFT JOIN panels p ON p.id = da.starting_panel_id
            ORDER BY da.name
        """)

        if algorithms is not None and not algorithms.empty:
            st.markdown("#### Current Algorithms")

            for idx, alg in algorithms.iterrows():
                with st.expander(f"🌳 {alg['name']} - {alg['clinical_area'] or 'General'}"):
                    # Show starting panel
                    if alg['starting_panel_name']:
                        st.markdown(f"**Starting Panel:** {alg['starting_panel_name']}")
                    else:
                        st.warning("⚠️ No starting panel defined")

                    st.markdown(f"**Logic:** `{alg['rule_logic']}`")
                    if alg['description']:
                        st.markdown(f"**Description:** {alg['description']}")
                    st.caption(f"Created by {alg['created_by']} on {alg['created_at'][:10]}")

                    st.markdown("---")

                    # Display decision tree nodes
                    st.markdown("**Decision Tree Nodes:**")
                    nodes = query_panels("""
                        SELECT
                            an.id,
                            an.node_name,
                            an.condition_logic,
                            an.condition_type,
                            an.parent_node_id,
                            an.node_order,
                            an.description,
                            p.name as suggested_panel_name
                        FROM algorithm_nodes an
                        LEFT JOIN panels p ON p.id = an.suggested_panel_id
                        WHERE an.algorithm_id = ?
                        ORDER BY an.node_order, an.node_name
                    """, (alg['id'],))

                    if nodes is not None and not nodes.empty:
                        for _, node in nodes.iterrows():
                            node_display = f"**{node['node_name']}**"
                            if node['condition_logic']:
                                node_display += f" - IF `{node['condition_logic']}`"
                            if node['suggested_panel_name']:
                                node_display += f" → THEN suggest: **{node['suggested_panel_name']}**"

                            # Show parent relationship
                            parent_label = ""
                            if node['parent_node_id']:
                                parent = nodes[nodes['id'] == node['parent_node_id']]
                                if not parent.empty:
                                    parent_label = f" (after {parent.iloc[0]['node_name']})"

                            st.markdown(f"  {node['node_order']}. {node_display}{parent_label}")
                            if node['description']:
                                st.caption(f"     ℹ️ {node['description']}")
                    else:
                        st.info("No decision nodes defined - add nodes below")

                    # Manage Nodes button
                    st.markdown("---")
                    manage_nodes_key = f"manage_nodes_{alg['id']}"
                    if st.button(f"Manage Decision Nodes", key=f"btn_{manage_nodes_key}", use_container_width=True):
                        st.session_state[manage_nodes_key] = True

                    # Node management section
                    if st.session_state.get(manage_nodes_key, False):
                        st.markdown("#### Add New Decision Node")
                        with st.form(f"add_node_{alg['id']}"):
                            col_n1, col_n2 = st.columns(2)
                            with col_n1:
                                new_node_name = st.text_input("Node Name *", placeholder="e.g., CD5 Check")
                                new_node_order = st.number_input("Order", min_value=1, value=1, help="Sequence in decision tree")
                            with col_n2:
                                # Parent node selection
                                parent_options = ["(Root - No Parent)"]
                                parent_ids = [None]
                                if nodes is not None and not nodes.empty:
                                    parent_options += list(nodes['node_name'])
                                    parent_ids += list(nodes['id'])

                                new_parent = st.selectbox("Parent Node", parent_options)
                                new_parent_id = parent_ids[parent_options.index(new_parent)]

                                # Condition type
                                new_cond_type = st.selectbox("Condition Type",
                                                            ["boolean", "expression", "range", "custom"],
                                                            help="Type of logical condition")

                            new_condition = st.text_input("Condition Logic",
                                                         placeholder="e.g., CD5+ AND clonal",
                                                         help="Logical expression to evaluate")

                            # Suggested panel selection
                            all_panels = query_panels("SELECT id, name, version FROM panels WHERE status IN ('validated', 'active') ORDER BY name")
                            if all_panels is not None and not all_panels.empty:
                                panel_options = ["(None - No Panel Suggestion)"] + [f"{p['name']} (v{p['version']})" for _, p in all_panels.iterrows()]
                                panel_ids = [None] + list(all_panels['id'])

                                new_suggested_panel = st.selectbox("Suggested Panel (when condition is TRUE)", panel_options)
                                new_suggested_panel_id = panel_ids[panel_options.index(new_suggested_panel)]
                            else:
                                st.warning("No panels available")
                                new_suggested_panel_id = None

                            new_node_desc = st.text_area("Description",
                                                        placeholder="Explain when this node should trigger...",
                                                        height=60)

                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.form_submit_button("Add Node", use_container_width=True):
                                    if not new_node_name:
                                        st.error("Node name is required")
                                    else:
                                        try:
                                            node_id = str(uuid.uuid4())
                                            query_panels("""
                                                INSERT INTO algorithm_nodes (
                                                    id, algorithm_id, node_name, condition_logic,
                                                    condition_type, suggested_panel_id, parent_node_id,
                                                    node_order, description
                                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                            """, (
                                                node_id, alg['id'], new_node_name, new_condition or None,
                                                new_cond_type, new_suggested_panel_id, new_parent_id,
                                                new_node_order, new_node_desc or None
                                            ), commit=True)

                                            st.success(f"Node '{new_node_name}' added")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")
                            with col_btn2:
                                if st.form_submit_button("Close", use_container_width=True):
                                    st.session_state[manage_nodes_key] = False
                                    st.rerun()

                        # Delete nodes
                        if nodes is not None and not nodes.empty:
                            st.markdown("---")
                            st.markdown("#### Delete Node")
                            node_to_delete = st.selectbox("Select node to delete",
                                                         list(nodes['node_name']),
                                                         key=f"del_node_{alg['id']}")
                            if st.button("Delete Selected Node", key=f"btn_del_node_{alg['id']}", type="secondary"):
                                try:
                                    node_id = nodes[nodes['node_name'] == node_to_delete].iloc[0]['id']
                                    query_panels("DELETE FROM algorithm_nodes WHERE id = ?", (node_id,), commit=True)
                                    st.success(f"Node '{node_to_delete}' deleted")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                    # Edit button
                    st.markdown("---")
                    edit_key = f"edit_algo_{alg['id']}"
                    if st.button(f"Edit Algorithm Info", key=f"btn_{edit_key}", use_container_width=True):
                        st.session_state[edit_key] = True

                    if st.session_state.get(edit_key, False):
                        with st.form(f"edit_algo_form_{alg['id']}"):
                            edit_algo_name = st.text_input("Name", value=alg['name'])
                            edit_algo_logic = st.text_input("Rule Logic", value=alg['rule_logic'],
                                                           help="e.g., LST → CD5+ → B2 and B3")
                            edit_algo_description = st.text_area("Description", value=alg['description'] or "")

                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                # Get areas for dropdown
                                areas = get_all_areas()
                                area_options = ["(None)"] + list(areas['name']) if areas is not None and not areas.empty else ["(None)"]
                                current_area_idx = area_options.index(alg['clinical_area']) if alg['clinical_area'] in area_options else 0

                                edit_algo_area = st.selectbox("Clinical Area", area_options, index=current_area_idx)

                            with col_e2:
                                # Starting panel selection
                                all_panels = query_panels("SELECT id, name, version FROM panels WHERE status IN ('validated', 'active') ORDER BY name")
                                if all_panels is not None and not all_panels.empty:
                                    panel_options = ["(None)"] + [f"{p['name']} (v{p['version']})" for _, p in all_panels.iterrows()]
                                    panel_ids = [None] + list(all_panels['id'])

                                    # Find current starting panel index
                                    current_panel_idx = 0
                                    if alg['starting_panel_id']:
                                        try:
                                            current_panel_idx = panel_ids.index(alg['starting_panel_id'])
                                        except ValueError:
                                            current_panel_idx = 0

                                    edit_starting_panel = st.selectbox("Starting Panel", panel_options, index=current_panel_idx,
                                                                       help="First panel to execute in this algorithm")
                                    edit_starting_panel_id = panel_ids[panel_options.index(edit_starting_panel)]
                                else:
                                    st.warning("No panels available")
                                    edit_starting_panel_id = None

                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.form_submit_button("Save Changes", use_container_width=True):
                                    try:
                                        # Get area_id
                                        area_id = None
                                        if edit_algo_area != "(None)" and areas is not None:
                                            area_row = areas[areas['name'] == edit_algo_area]
                                            if not area_row.empty:
                                                area_id = area_row.iloc[0]['id']

                                        query_panels("""
                                            UPDATE diagnostic_algorithms
                                            SET name = ?, rule_logic = ?, description = ?, clinical_area_id = ?, starting_panel_id = ?, updated_at = ?
                                            WHERE id = ?
                                        """, (edit_algo_name, edit_algo_logic, edit_algo_description, area_id,
                                             edit_starting_panel_id, datetime.now().isoformat(), alg['id']), commit=True)

                                        st.success(f"Algorithm '{edit_algo_name}' updated")
                                        st.session_state[edit_key] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                            with col_btn2:
                                if st.form_submit_button("Cancel", use_container_width=True):
                                    st.session_state[edit_key] = False
                                    st.rerun()

                    # Delete button
                    if st.button(f"Delete '{alg['name']}'", key=f"del_{alg['id']}", type="secondary"):
                        try:
                            query_panels("DELETE FROM diagnostic_algorithms WHERE id = ?", (alg['id'],), commit=True)
                            st.success(f"Algorithm '{alg['name']}' deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No algorithms configured yet")

        # Add new algorithm
        st.markdown("---")
        st.markdown("#### Add New Diagnostic Algorithm")

        with st.form("new_algorithm_form"):
            new_algo_name = st.text_input("Algorithm Name *", placeholder="e.g., LST B-Cell Panel")
            new_algo_logic = st.text_input("Rule Logic *",
                                          placeholder="e.g., LST → CD5+ → B2 and B3",
                                          help="Define the clinical logic pathway")
            new_algo_description = st.text_area("Description",
                                               placeholder="Explain when and how to use this algorithm...",
                                               height=100)

            col_new1, col_new2 = st.columns(2)
            with col_new1:
                # Area selection
                areas = get_all_areas()
                if areas is not None and not areas.empty:
                    area_options = ["(None)"] + list(areas['name'])
                    new_algo_area = st.selectbox("Clinical Area", area_options)
                else:
                    st.warning("No clinical areas available")
                    new_algo_area = "(None)"

            with col_new2:
                # Starting panel selection
                all_panels = query_panels("SELECT id, name, version FROM panels WHERE status IN ('validated', 'active') ORDER BY name")
                if all_panels is not None and not all_panels.empty:
                    panel_options = ["(None)"] + [f"{p['name']} (v{p['version']})" for _, p in all_panels.iterrows()]
                    panel_ids = [None] + list(all_panels['id'])

                    new_starting_panel = st.selectbox("Starting Panel", panel_options,
                                                      help="First panel to execute in this algorithm")
                    new_starting_panel_id = panel_ids[panel_options.index(new_starting_panel)]
                else:
                    st.warning("No panels available")
                    new_starting_panel_id = None

            new_algo_created_by = st.text_input("Created By *", placeholder="Your name")

            if st.form_submit_button("Create Algorithm", use_container_width=True):
                if not new_algo_name or not new_algo_logic or not new_algo_created_by:
                    st.error("Please fill in all required fields (*)")
                else:
                    try:
                        # Get area_id
                        area_id = None
                        if new_algo_area != "(None)" and areas is not None:
                            area_row = areas[areas['name'] == new_algo_area]
                            if not area_row.empty:
                                area_id = area_row.iloc[0]['id']

                        algo_id = str(uuid.uuid4())
                        query_panels("""
                            INSERT INTO diagnostic_algorithms (
                                id, name, rule_logic, description, clinical_area_id, starting_panel_id, created_by, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (algo_id, new_algo_name, new_algo_logic, new_algo_description, area_id,
                             new_starting_panel_id, new_algo_created_by, datetime.now().isoformat()), commit=True)

                        st.success(f"Algorithm '{new_algo_name}' created successfully")
                        st.info("💡 Next: Add decision nodes to build your diagnostic pathway")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating algorithm: {e}")

    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    with tab4:
        st.markdown("### Application Settings")

        # Language setting
        st.markdown("#### Language / Idioma")

        # Get current language from session state
        if 'language' not in st.session_state:
            st.session_state['language'] = 'en'  # Default to English

        current_lang = st.session_state['language']

        lang_options = {
            'en': 'English',
            'es': 'Español'
        }

        selected_lang = st.selectbox(
            "Interface Language",
            options=list(lang_options.keys()),
            format_func=lambda x: lang_options[x],
            index=list(lang_options.keys()).index(current_lang)
        )

        if selected_lang != current_lang:
            st.session_state['language'] = selected_lang
            st.success(f"Language changed to {lang_options[selected_lang]}")
            st.info("Note: Full language support will be implemented in a future update. Currently affects navigation labels.")
            st.rerun()

        st.markdown("---")

        # Database info
        st.markdown("#### Database Information")

        db_stats = query_panels("""
            SELECT
                (SELECT COUNT(*) FROM panels) as panel_count,
                (SELECT COUNT(*) FROM reagents) as reagent_count,
                (SELECT COUNT(*) FROM reagent_units) as unit_count,
                (SELECT COUNT(*) FROM patients) as patient_count,
                (SELECT COUNT(*) FROM clinical_cases) as case_count
        """)

        if not db_stats.empty:
            stats = db_stats.iloc[0]
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Panels", stats['panel_count'])
            with col2:
                st.metric("Reagents", stats['reagent_count'])
            with col3:
                st.metric("Units", stats['unit_count'])
            with col4:
                st.metric("Patients", stats['patient_count'])
            with col5:
                st.metric("Cases", stats['case_count'])

        st.markdown("---")

        # Application info
        st.markdown("#### Application Information")
        st.caption("**Streamflow** - Flow Cytometry Laboratory Management System")
        st.caption("Version: 2.0.0")
        st.caption("Database: SQLite")
