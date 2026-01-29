"""
Clinical Section - Oncohematology Patient Management
MVP: Patient registry, case management, and basic results tracking
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date
from ui.crud_panels import query_panels
from utils.translations import CLINICAL


def run_clinical():
    """Main clinical section interface"""
    # Get language from session state
    lang = st.session_state.get('language', 'en')
    labels = CLINICAL[lang]

    st.title(labels['title'])

    # Initialize session state
    if "clinical_view" not in st.session_state:
        st.session_state["clinical_view"] = "dashboard"
    if "selected_patient_id" not in st.session_state:
        st.session_state["selected_patient_id"] = None
    if "selected_case_id" not in st.session_state:
        st.session_state["selected_case_id"] = None
    if "editing_patient" not in st.session_state:
        st.session_state["editing_patient"] = False
    if "editing_case" not in st.session_state:
        st.session_state["editing_case"] = False

    # Tab navigation
    tab1, tab2, tab3 = st.tabs([labels['dashboard_tab'], labels['patients_tab'], labels['cases_tab']])

    # =============================================================================
    # DASHBOARD
    # =============================================================================
    with tab1:
        st.markdown("### Clinical Dashboard")

        # Get metrics
        total_patients = query_panels("SELECT COUNT(*) as count FROM patients WHERE status = 'active'")
        active_cases = query_panels("SELECT COUNT(*) as count FROM clinical_cases WHERE status IN ('pending', 'in_progress')")
        completed_cases = query_panels("SELECT COUNT(*) as count FROM clinical_cases WHERE status = 'completed'")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Patients", total_patients.iloc[0]['count'] if not total_patients.empty else 0)
        with col2:
            st.metric("Active Cases", active_cases.iloc[0]['count'] if not active_cases.empty else 0)
        with col3:
            st.metric("Completed (Month)", completed_cases.iloc[0]['count'] if not completed_cases.empty else 0)

        st.markdown("---")

        # Recent cases
        st.markdown("### Recent Cases")
        recent_cases = query_panels("""
            SELECT
                cc.case_number,
                p.initials as patient_initials,
                cc.clinical_suspicion,
                cc.sample_date,
                cc.status,
                cc.priority
            FROM clinical_cases cc
            JOIN patients p ON p.id = cc.patient_id
            ORDER BY cc.created_at DESC
            LIMIT 10
        """)

        if recent_cases is not None and not recent_cases.empty:
            display_cases = recent_cases.copy()
            display_cases['status'] = display_cases['status'].apply(
                lambda x: {'pending': 'Pending', 'in_progress': 'In Progress',
                          'completed': 'Completed', 'reported': 'Reported'}.get(x, x)
            )
            st.dataframe(display_cases, use_container_width=True, hide_index=True)
        else:
            st.info("No cases yet")

    # =============================================================================
    # PATIENTS
    # =============================================================================
    with tab2:
        st.markdown("### Patient Registry")

        col_list, col_detail = st.columns([1, 2])

        with col_list:
            # Patient list
            patients = query_panels("""
                SELECT
                    id,
                    initials,
                    medical_record_number as mrn,
                    age_at_registration as age,
                    sex,
                    registration_date,
                    status
                FROM patients
                WHERE status = 'active'
                ORDER BY registration_date DESC
            """)

            if patients is None or patients.empty:
                st.info("No patients registered")
            else:
                # Display patient list
                display_patients = patients[['initials', 'mrn', 'age', 'sex']].copy()
                selected = st.dataframe(
                    display_patients,
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun",
                    hide_index=True
                )

                if selected and selected.get("selection", {}).get("rows"):
                    st.session_state["selected_patient_id"] = patients.iloc[selected["selection"]["rows"][0]]["id"]

            # Add new patient
            st.markdown("---")
            with st.expander("Register New Patient", expanded=False):
                with st.form("new_patient"):
                    st.markdown("**Patient Information**")

                    mrn = st.text_input("Admission Protocol *", placeholder="e.g., 2025-001234")
                    initials = st.text_input("Initials *", placeholder="e.g., JPS", max_chars=10)

                    col1, col2 = st.columns(2)
                    with col1:
                        dob = st.date_input("Date of Birth", value=None, min_value=date(1900, 1, 1), max_value=date.today())
                        sex = st.selectbox("Sex", ["M", "F", "Other", "Unknown"])
                    with col2:
                        # Calculate age automatically from DOB
                        if dob:
                            today = date.today()
                            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                            st.info(f"Age: {age} years (calculated from DOB)")
                        else:
                            age = None
                            st.info("Age: Not available (enter DOB)")
                        requesting_physician = st.text_input("Requesting Physician")

                    requesting_institution = st.text_input("Requesting Institution")
                    notes = st.text_area("Notes", height=60)

                    if st.form_submit_button("Register Patient", use_container_width=True):
                        if not mrn or not initials:
                            st.error("MRN and Initials are required")
                        else:
                            try:
                                patient_id = str(uuid.uuid4())
                                query_panels("""
                                    INSERT INTO patients (
                                        id, medical_record_number, initials,
                                        date_of_birth, age_at_registration, sex,
                                        referring_physician, referring_institution,
                                        notes, status, registration_date, created_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                                """, (
                                    patient_id, mrn, initials.upper(),
                                    str(dob) if dob else None, age, sex,
                                    requesting_physician or None, requesting_institution or None,
                                    notes or None, datetime.now().isoformat(), datetime.now().isoformat()
                                ), commit=True)

                                st.success(f"Patient {initials.upper()} registered successfully")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

        with col_detail:
            if not st.session_state["selected_patient_id"]:
                st.info("Select a patient to view details")
            else:
                # Load patient details
                patient = query_panels("""
                    SELECT * FROM patients WHERE id = ?
                """, (st.session_state["selected_patient_id"],))

                if patient.empty:
                    st.error("Patient not found")
                    st.session_state["selected_patient_id"] = None
                else:
                    p = patient.iloc[0]

                    col_header1, col_header2, col_header3 = st.columns([3, 1, 1])
                    with col_header1:
                        st.markdown(f"### {p['initials']}")
                        st.caption(f"MRN: {p['medical_record_number']}")
                    with col_header2:
                        if not st.session_state["editing_patient"]:
                            if st.button("Edit Patient", key="edit_patient_btn", use_container_width=True):
                                st.session_state["editing_patient"] = True
                                st.rerun()
                        else:
                            if st.button("Cancel Edit", key="cancel_edit_patient_btn", use_container_width=True):
                                st.session_state["editing_patient"] = False
                                st.rerun()
                    with col_header3:
                        if st.button("Delete", key="delete_patient_btn", type="secondary", use_container_width=True):
                            st.session_state["confirm_delete_patient"] = True
                            st.rerun()

                    # Delete confirmation dialog
                    if st.session_state.get("confirm_delete_patient", False):
                        st.warning("⚠️ Are you sure you want to delete this patient? This will also delete all related cases, panel assignments, and diagnoses.")
                        col_conf1, col_conf2 = st.columns(2)
                        with col_conf1:
                            if st.button("✓ Yes, Delete", type="primary", key="confirm_delete_yes"):
                                try:
                                    # Delete patient and cascade to related records
                                    query_panels("DELETE FROM patients WHERE id = ?", (p['id'],), commit=True)
                                    st.success(f"Patient {p['initials']} deleted successfully")
                                    st.session_state["selected_patient_id"] = None
                                    st.session_state["confirm_delete_patient"] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting patient: {e}")
                        with col_conf2:
                            if st.button("✗ Cancel", key="confirm_delete_no"):
                                st.session_state["confirm_delete_patient"] = False
                                st.rerun()

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Calculate current age dynamically from DOB
                        if p['date_of_birth']:
                            try:
                                dob = datetime.strptime(p['date_of_birth'], '%Y-%m-%d').date()
                                today = date.today()
                                current_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                                st.metric("Age", f"{current_age} years")
                            except:
                                st.metric("Age", p['age_at_registration'] or "—")
                        else:
                            st.metric("Age", p['age_at_registration'] or "—")
                    with col2:
                        st.metric("Sex", p['sex'] or "—")
                    with col3:
                        st.metric("Status", p['status'].upper())

                    if p['referring_physician']:
                        st.text(f"Requesting: Dr. {p['referring_physician']}")
                    if p['referring_institution']:
                        st.text(f"Institution: {p['referring_institution']}")

                    # Edit patient form
                    if st.session_state["editing_patient"]:
                        st.markdown("---")
                        st.markdown("### Edit Patient Information")

                        with st.form("edit_patient_form"):
                            edit_mrn = st.text_input("Admission Protocol", value=p['medical_record_number'])
                            edit_initials = st.text_input("Initials", value=p['initials'])

                            col1, col2 = st.columns(2)
                            with col1:
                                current_dob = datetime.strptime(p['date_of_birth'], '%Y-%m-%d').date() if p['date_of_birth'] else None
                                edit_dob = st.date_input("Date of Birth", value=current_dob, min_value=date(1900, 1, 1), max_value=date.today())
                                edit_sex = st.selectbox("Sex", ["M", "F", "Other", "Unknown"],
                                                       index=["M", "F", "Other", "Unknown"].index(p['sex']) if p['sex'] in ["M", "F", "Other", "Unknown"] else 3)
                            with col2:
                                edit_physician = st.text_input("Requesting Physician", value=p['referring_physician'] or "")
                                edit_institution = st.text_input("Requesting Institution", value=p['referring_institution'] or "")

                            edit_notes = st.text_area("Notes", value=p['notes'] or "", height=80)
                            edit_status = st.selectbox("Patient Status", ["active", "discharged", "deceased", "transferred"],
                                                      index=["active", "discharged", "deceased", "transferred"].index(p['status']) if p['status'] in ["active", "discharged", "deceased", "transferred"] else 0)

                            if st.form_submit_button("Save Changes", use_container_width=True):
                                try:
                                    # Calculate age at time of update
                                    if edit_dob:
                                        today = date.today()
                                        age = today.year - edit_dob.year - ((today.month, today.day) < (edit_dob.month, edit_dob.day))
                                    else:
                                        age = p['age_at_registration']

                                    query_panels("""
                                        UPDATE patients SET
                                            medical_record_number = ?,
                                            initials = ?,
                                            date_of_birth = ?,
                                            age_at_registration = ?,
                                            sex = ?,
                                            referring_physician = ?,
                                            referring_institution = ?,
                                            notes = ?,
                                            status = ?,
                                            updated_at = ?
                                        WHERE id = ?
                                    """, (
                                        edit_mrn, edit_initials.upper(),
                                        str(edit_dob) if edit_dob else None, age, edit_sex,
                                        edit_physician or None, edit_institution or None,
                                        edit_notes or None, edit_status,
                                        datetime.now().isoformat(), p['id']
                                    ), commit=True)

                                    st.session_state["editing_patient"] = False
                                    st.success("Patient updated successfully")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating patient: {e}")

                    # Patient cases
                    st.markdown("---")
                    st.markdown("### Cases")

                    patient_cases = query_panels("""
                        SELECT
                            id, case_number, clinical_suspicion,
                            sample_date, status, priority
                        FROM clinical_cases
                        WHERE patient_id = ?
                        ORDER BY sample_date DESC
                    """, (p['id'],))

                    if patient_cases is not None and not patient_cases.empty:
                        st.dataframe(patient_cases[['case_number', 'clinical_suspicion', 'sample_date', 'status']],
                                   use_container_width=True, hide_index=True)
                    else:
                        st.info("No cases for this patient")

    # =============================================================================
    # CASES
    # =============================================================================
    with tab3:
        st.markdown("### Case Management")

        col_list, col_detail = st.columns([1, 2])

        with col_list:
            # Case list
            cases = query_panels("""
                SELECT
                    cc.id,
                    cc.case_number,
                    p.initials as patient,
                    cc.clinical_suspicion,
                    cc.sample_date,
                    cc.status,
                    cc.priority
                FROM clinical_cases cc
                JOIN patients p ON p.id = cc.patient_id
                ORDER BY cc.sample_date DESC
            """)

            if cases is None or cases.empty:
                st.info("No cases yet")
            else:
                display_cases = cases[['case_number', 'patient', 'clinical_suspicion', 'status']].copy()
                selected = st.dataframe(
                    display_cases,
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun",
                    hide_index=True
                )

                if selected and selected.get("selection", {}).get("rows"):
                    st.session_state["selected_case_id"] = cases.iloc[selected["selection"]["rows"][0]]["id"]

            # Create new case
            st.markdown("---")
            with st.expander("Create New Case", expanded=False):
                with st.form("new_case"):
                    st.markdown("**Case Information**")

                    # Select patient
                    all_patients = query_panels("SELECT id, initials, medical_record_number FROM patients WHERE status = 'active'")
                    if all_patients is None or all_patients.empty:
                        st.warning("No active patients. Register a patient first.")
                    else:
                        patient_options = [f"{p['initials']} ({p['medical_record_number']})" for _, p in all_patients.iterrows()]
                        selected_patient_idx = st.selectbox("Patient *", range(len(patient_options)),
                                                           format_func=lambda x: patient_options[x])

                        case_number = st.text_input("Case Number *", placeholder="Auto-generated if empty")
                        clinical_suspicion = st.text_input("Clinical Suspicion *", placeholder="e.g., Acute leukemia")

                        col1, col2 = st.columns(2)
                        with col1:
                            sample_date = st.date_input("Sample Date *", value=date.today())
                            sample_type = st.selectbox("Sample Type", ["Blood", "Bone Marrow", "CSF", "Tissue", "Other"])
                        with col2:
                            priority = st.selectbox("Priority", ["routine", "urgent", "stat"])
                            requesting_physician = st.text_input("Requesting Physician")

                        if st.form_submit_button("Create Case", use_container_width=True):
                            if not clinical_suspicion:
                                st.error("Clinical suspicion is required")
                            else:
                                try:
                                    case_id = str(uuid.uuid4())
                                    patient_id = all_patients.iloc[selected_patient_idx]['id']

                                    # Generate case number if not provided
                                    if not case_number:
                                        case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

                                    query_panels("""
                                        INSERT INTO clinical_cases (
                                            id, patient_id, case_number, clinical_suspicion,
                                            sample_date, sample_type, referring_physician,
                                            priority, status, received_at, created_at
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                                    """, (
                                        case_id, patient_id, case_number, clinical_suspicion,
                                        str(sample_date), sample_type, requesting_physician or None,
                                        priority, datetime.now().isoformat(), datetime.now().isoformat()
                                    ), commit=True)

                                    st.success(f"Case {case_number} created successfully")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

        with col_detail:
            if not st.session_state["selected_case_id"]:
                st.info("Select a case to view details")
            else:
                # Load case details
                case = query_panels("""
                    SELECT
                        cc.*,
                        p.initials as patient_initials,
                        p.medical_record_number as patient_mrn
                    FROM clinical_cases cc
                    JOIN patients p ON p.id = cc.patient_id
                    WHERE cc.id = ?
                """, (st.session_state["selected_case_id"],))

                if case.empty:
                    st.error("Case not found")
                    st.session_state["selected_case_id"] = None
                else:
                    c = case.iloc[0]

                    col_header1, col_header2 = st.columns([3, 1])
                    with col_header1:
                        st.markdown(f"### {c['case_number']}")
                        st.caption(f"Patient: {c['patient_initials']} ({c['patient_mrn']})")
                    with col_header2:
                        if not st.session_state["editing_case"]:
                            if st.button("Edit Case", key="edit_case_btn"):
                                st.session_state["editing_case"] = True
                                st.rerun()
                        else:
                            if st.button("Cancel Edit", key="cancel_edit_case_btn"):
                                st.session_state["editing_case"] = False
                                st.rerun()

                    # Case editing form
                    if st.session_state["editing_case"]:
                        st.markdown("---")
                        st.markdown("### Edit Case")

                        with st.form("edit_case_form"):
                            edit_case_number = st.text_input("Case Number", value=c['case_number'])
                            edit_clinical_suspicion = st.text_input("Clinical Suspicion", value=c['clinical_suspicion'])

                            col1, col2 = st.columns(2)
                            with col1:
                                edit_sample_date = st.date_input("Sample Date", value=datetime.strptime(c['sample_date'], '%Y-%m-%d').date() if c['sample_date'] else date.today())
                                edit_sample_type = st.selectbox("Sample Type", ["Blood", "Bone Marrow", "CSF", "Tissue", "Other"],
                                                               index=["Blood", "Bone Marrow", "CSF", "Tissue", "Other"].index(c['sample_type']) if c['sample_type'] in ["Blood", "Bone Marrow", "CSF", "Tissue", "Other"] else 0)
                            with col2:
                                edit_priority = st.selectbox("Priority", ["routine", "urgent", "stat"],
                                                            index=["routine", "urgent", "stat"].index(c['priority']) if c['priority'] in ["routine", "urgent", "stat"] else 0)
                                edit_status = st.selectbox("Status", ["pending", "screening", "follow-up", "in_progress", "completed", "reported"],
                                                          index=["pending", "screening", "follow-up", "in_progress", "completed", "reported"].index(c['status']) if c['status'] in ["pending", "screening", "follow-up", "in_progress", "completed", "reported"] else 0)

                            edit_referring_physician = st.text_input("Requesting Physician", value=c['referring_physician'] or "")

                            if st.form_submit_button("Save Changes", use_container_width=True):
                                try:
                                    query_panels("""
                                        UPDATE clinical_cases SET
                                            case_number = ?,
                                            clinical_suspicion = ?,
                                            sample_date = ?,
                                            sample_type = ?,
                                            priority = ?,
                                            status = ?,
                                            referring_physician = ?,
                                            updated_at = ?
                                        WHERE id = ?
                                    """, (
                                        edit_case_number, edit_clinical_suspicion,
                                        str(edit_sample_date), edit_sample_type,
                                        edit_priority, edit_status,
                                        edit_referring_physician or None,
                                        datetime.now().isoformat(), c['id']
                                    ), commit=True)

                                    st.session_state["editing_case"] = False
                                    st.success("Case updated successfully")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating case: {e}")

                        st.markdown("---")

                    # Display case info with visual indicators
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Status with color indicators
                        status_colors = {
                            'pending': '🟡',
                            'screening': '🔵',
                            'follow-up': '🟠',
                            'in_progress': '🔵',
                            'completed': '🟢',
                            'reported': '✅'
                        }
                        status_icon = status_colors.get(c['status'], '⚪')
                        st.metric("Status", f"{status_icon} {c['status'].upper()}")
                    with col2:
                        # Priority with color indicators
                        priority_colors = {
                            'routine': '🟢',
                            'urgent': '🟠',
                            'stat': '🔴'
                        }
                        priority_icon = priority_colors.get(c['priority'], '⚪')
                        st.metric("Priority", f"{priority_icon} {c['priority'].upper()}")
                    with col3:
                        st.metric("Sample Date", str(c['sample_date']))

                    st.markdown(f"**Clinical Suspicion:** {c['clinical_suspicion']}")
                    st.markdown(f"**Sample Type:** {c['sample_type']}")

                    # Assigned panels with clinical reasoning tracking
                    st.markdown("---")
                    st.markdown("### Panel Assignment History")
                    st.caption("Track the evolution of this case - screening → follow-up → additional studies")

                    case_panels = query_panels("""
                        SELECT
                            cp.id,
                            p.name as panel_name,
                            p.version,
                            cp.created_at as assigned_at,
                            cp.operator as assigned_by,
                            cp.notes as assignment_reason,
                            cp.run_date,
                            cp.status,
                            cp.immunophenotype as results,
                            cp.actual_cost
                        FROM case_panels cp
                        JOIN panels p ON p.id = cp.panel_id
                        WHERE cp.case_id = ?
                        ORDER BY cp.created_at
                    """, (c['id'],))

                    if case_panels is not None and not case_panels.empty:
                        # Show detailed history with edit capability
                        for idx, panel_row in case_panels.iterrows():
                            panel_assignment_id = panel_row['id']
                            edit_key = f"edit_panel_{panel_assignment_id}"

                            # Check if this assignment is being edited
                            is_editing = st.session_state.get(edit_key, False)

                            with st.container():
                                # Status badge for panel assignment
                                status_badges = {
                                    'pending': '🟡 Pending',
                                    'in_process': '🔵 In Process',
                                    'acquired': '🟣 Acquired',
                                    'analyzed': '🟢 Analyzed',
                                    'completed': '✅ Completed'
                                }
                                status_display = status_badges.get(panel_row['status'], panel_row['status'].upper())

                                col_title, col_edit = st.columns([4, 1])
                                with col_title:
                                    st.markdown(f"**{idx+1}. {panel_row['panel_name']}** (v{panel_row['version']}) - {status_display}")
                                with col_edit:
                                    if not is_editing:
                                        if st.button("✏️ Edit", key=f"btn_edit_{panel_assignment_id}", use_container_width=True):
                                            st.session_state[edit_key] = True
                                            st.rerun()
                                    else:
                                        if st.button("✖ Cancel", key=f"btn_cancel_{panel_assignment_id}", use_container_width=True):
                                            st.session_state[edit_key] = False
                                            st.rerun()

                                if is_editing:
                                    # Edit form for this panel assignment
                                    with st.form(f"edit_assignment_{panel_assignment_id}"):
                                        st.markdown("**Edit Panel Assignment**")

                                        col_e1, col_e2 = st.columns(2)
                                        with col_e1:
                                            edit_asmt_status = st.selectbox(
                                                "Status",
                                                ["pending", "in_process", "acquired", "analyzed", "completed"],
                                                index=["pending", "in_process", "acquired", "analyzed", "completed"].index(panel_row['status']) if panel_row['status'] in ["pending", "in_process", "acquired", "analyzed", "completed"] else 0,
                                                key=f"status_{panel_assignment_id}"
                                            )
                                            edit_asmt_operator = st.text_input(
                                                "Operator",
                                                value=panel_row['assigned_by'] or "",
                                                key=f"operator_{panel_assignment_id}"
                                            )
                                        with col_e2:
                                            edit_asmt_date = st.date_input(
                                                "Run Date",
                                                value=datetime.strptime(panel_row['run_date'], '%Y-%m-%d').date() if panel_row['run_date'] else date.today(),
                                                key=f"date_{panel_assignment_id}"
                                            )
                                            edit_asmt_cost = st.number_input(
                                                "Actual Cost",
                                                value=float(panel_row['actual_cost'] or 0),
                                                min_value=0.0,
                                                key=f"cost_{panel_assignment_id}"
                                            )

                                        edit_asmt_reason = st.text_area(
                                            "Clinical Reasoning",
                                            value=panel_row['assignment_reason'] or "",
                                            key=f"reason_{panel_assignment_id}"
                                        )

                                        edit_asmt_results = st.text_area(
                                            "Results/Immunophenotype",
                                            value=panel_row['results'] or "",
                                            key=f"results_{panel_assignment_id}",
                                            height=150
                                        )

                                        if st.form_submit_button("Save Changes", use_container_width=True):
                                            try:
                                                query_panels("""
                                                    UPDATE case_panels SET
                                                        status = ?,
                                                        operator = ?,
                                                        run_date = ?,
                                                        actual_cost = ?,
                                                        notes = ?,
                                                        immunophenotype = ?
                                                    WHERE id = ?
                                                """, (
                                                    edit_asmt_status,
                                                    edit_asmt_operator,
                                                    str(edit_asmt_date),
                                                    edit_asmt_cost,
                                                    edit_asmt_reason,
                                                    edit_asmt_results,
                                                    panel_assignment_id
                                                ), commit=True)
                                                st.success("Panel assignment updated")
                                                st.session_state[edit_key] = False
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Error: {e}")
                                else:
                                    # Display mode
                                    col_info1, col_info2, col_info3 = st.columns(3)
                                    with col_info1:
                                        st.caption(f"📅 Assigned: {panel_row['assigned_at'][:10] if panel_row['assigned_at'] else 'N/A'}")
                                    with col_info2:
                                        st.caption(f"👤 By: {panel_row['assigned_by'] or 'Unknown'}")
                                    with col_info3:
                                        st.caption(f"💵 Cost: ${panel_row['actual_cost'] or 0:.2f}")

                                    if panel_row['assignment_reason']:
                                        st.info(f"📝 **Reason:** {panel_row['assignment_reason']}")
                                    else:
                                        st.caption("_No clinical reasoning recorded_")

                                    if panel_row['results']:
                                        with st.expander("View Results"):
                                            st.markdown(panel_row['results'])

                                st.markdown("---")
                    else:
                        st.info("No panels assigned yet - Start with a screening panel")

                    # Assign new panel/tube
                    num_existing_panels = len(case_panels) if case_panels is not None and not case_panels.empty else 0

                    if num_existing_panels == 0:
                        expander_label = "Add Screening Panel"
                        expander_help = "Start with an initial screening panel"
                    else:
                        expander_label = "Add Follow-up Panel/Tube"
                        expander_help = "Add additional studies based on initial results"

                    with st.expander(expander_label, expanded=False):
                        st.caption(expander_help)

                        # Get all available panels
                        available_panels = query_panels("""
                            SELECT DISTINCT p.id, p.name, p.version, p.status
                            FROM panels p
                            WHERE p.status IN ('draft', 'validated', 'active')
                            ORDER BY p.name
                        """)

                        if available_panels is None or available_panels.empty:
                            st.warning("No panels available")
                        else:
                            with st.form("assign_panel_form"):
                                st.markdown("**Panel Selection**")
                                panel_options = [f"{p['name']} (v{p['version']}) - {p['status']}" for _, p in available_panels.iterrows()]
                                selected_panel_idx = st.selectbox("Panel", range(len(panel_options)),
                                                                 format_func=lambda x: panel_options[x])

                                st.markdown("**Clinical Reasoning** (Required)")
                                if num_existing_panels == 0:
                                    reason_placeholder = "e.g., Initial screening for suspected acute leukemia"
                                else:
                                    reason_placeholder = "e.g., Previous panel showed CD34+ blasts, adding B-ALL markers for confirmation"

                                assignment_reason = st.text_area(
                                    "Why is this panel being requested?",
                                    height=100,
                                    placeholder=reason_placeholder,
                                    help="Document the clinical reasoning - this is essential for traceability"
                                )

                                col1, col2 = st.columns(2)
                                with col1:
                                    assigned_by = st.text_input(
                                        "Assigned By *",
                                        placeholder="Your name",
                                        help="Who is requesting this panel?"
                                    )
                                with col2:
                                    run_date = st.date_input("Scheduled Run Date", value=date.today())

                                if st.form_submit_button("Assign Panel", use_container_width=True):
                                    if not assignment_reason or not assignment_reason.strip():
                                        st.error("Clinical reasoning is required - explain WHY this panel is needed")
                                    elif not assigned_by or not assigned_by.strip():
                                        st.error("Please enter who is assigning this panel")
                                    else:
                                        try:
                                            case_panel_id = str(uuid.uuid4())
                                            panel_id = available_panels.iloc[selected_panel_idx]['id']

                                            query_panels("""
                                                INSERT INTO case_panels (
                                                    id, case_id, panel_id, status,
                                                    operator, notes, run_date, created_at
                                                ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
                                            """, (
                                                case_panel_id, c['id'], panel_id,
                                                assigned_by.strip(), assignment_reason.strip(),
                                                str(run_date), datetime.now().isoformat()
                                            ), commit=True)

                                            st.success(f"Panel assigned successfully by {assigned_by}")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")

                    # Diagnostic Algorithms Section
                    st.markdown("---")
                    st.markdown("### Diagnostic Algorithms")
                    st.caption("Clinical interpretation pathways - NOT panel/tube assignments")

                    # Get algorithms assigned to this case
                    case_algorithms = query_panels("""
                        SELECT
                            ca.id,
                            da.name as algorithm_name,
                            da.rule_logic,
                            da.description,
                            ca.assigned_date,
                            ca.assigned_by,
                            ca.notes,
                            ca.status
                        FROM case_algorithms ca
                        JOIN diagnostic_algorithms da ON da.id = ca.algorithm_id
                        WHERE ca.case_id = ?
                        ORDER BY ca.assigned_date DESC
                    """, (c['id'],))

                    if case_algorithms is not None and not case_algorithms.empty:
                        for idx, alg in case_algorithms.iterrows():
                            status_badges = {
                                'active': '🟢 Active',
                                'completed': '✅ Completed',
                                'superseded': '🔄 Superseded'
                            }
                            status_display = status_badges.get(alg['status'], alg['status'])

                            with st.container():
                                st.markdown(f"**{alg['algorithm_name']}** - {status_display}")
                                st.code(alg['rule_logic'], language=None)
                                if alg['description']:
                                    st.caption(f"ℹ️ {alg['description']}")
                                if alg['notes']:
                                    st.info(f"📝 {alg['notes']}")
                                st.caption(f"Assigned by {alg['assigned_by']} on {alg['assigned_date'][:10]}")
                                st.markdown("---")
                    else:
                        st.info("No diagnostic algorithms assigned yet")

                    # Assign Algorithm
                    with st.expander("Assign Diagnostic Algorithm", expanded=False):
                        # Get all available algorithms
                        available_algorithms = query_panels("""
                            SELECT id, name, rule_logic, description
                            FROM diagnostic_algorithms
                            ORDER BY name
                        """)

                        if available_algorithms is None or available_algorithms.empty:
                            st.warning("No algorithms available. Create algorithms in Settings first.")
                        else:
                            with st.form("assign_algorithm_form"):
                                algo_options = [f"{row['name']}: {row['rule_logic']}" for _, row in available_algorithms.iterrows()]
                                selected_algo_idx = st.selectbox("Algorithm", range(len(algo_options)),
                                                                format_func=lambda x: algo_options[x])

                                col_a1, col_a2 = st.columns(2)
                                with col_a1:
                                    algo_assigned_by = st.text_input("Assigned By *", placeholder="Your name")
                                with col_a2:
                                    algo_assigned_date = st.date_input("Date", value=date.today())

                                algo_notes = st.text_area("Notes",
                                                         placeholder="Why this algorithm was chosen, clinical context...",
                                                         height=100)

                                if st.form_submit_button("Assign Algorithm", use_container_width=True):
                                    if not algo_assigned_by or not algo_assigned_by.strip():
                                        st.error("Please enter who is assigning this algorithm")
                                    else:
                                        try:
                                            algorithm_id = available_algorithms.iloc[selected_algo_idx]['id']
                                            case_algo_id = str(uuid.uuid4())

                                            query_panels("""
                                                INSERT INTO case_algorithms (
                                                    id, case_id, algorithm_id, assigned_date, assigned_by, notes, status, created_at
                                                ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                                            """, (
                                                case_algo_id, c['id'], algorithm_id, str(algo_assigned_date),
                                                algo_assigned_by.strip(), algo_notes.strip() if algo_notes else None,
                                                datetime.now().isoformat()
                                            ), commit=True)

                                            st.success("Algorithm assigned successfully")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")

                    # Final Diagnosis Section
                    st.markdown("---")
                    st.markdown("### Final Diagnosis")

                    # Check if diagnosis exists
                    diagnosis = query_panels("""
                        SELECT * FROM case_diagnoses WHERE case_id = ?
                    """, (c['id'],))

                    if diagnosis is not None and not diagnosis.empty:
                        d = diagnosis.iloc[0]
                        st.markdown(f"**Diagnosis:** {d['final_diagnosis']}")
                        if d['icd_code']:
                            st.markdown(f"**ICD Code:** {d['icd_code']}")
                        if d['who_classification']:
                            st.markdown(f"**WHO Classification:** {d['who_classification']}")
                        if d['fab_classification']:
                            st.markdown(f"**FAB Classification:** {d['fab_classification']}")
                        if d['additional_findings']:
                            st.markdown(f"**Additional Findings:** {d['additional_findings']}")
                        if d['reported_by']:
                            st.caption(f"Reported by: {d['reported_by']} on {d['report_date'] if d['report_date'] else 'N/A'}")
                    else:
                        st.info("No diagnosis entered yet")

                    # Add/Edit Diagnosis Form
                    with st.expander("Enter/Update Diagnosis", expanded=False):
                        with st.form("diagnosis_form"):
                            st.markdown("**Diagnosis Information**")

                            diag_text = st.text_area("Final Diagnosis *",
                                                    value=diagnosis.iloc[0]['final_diagnosis'] if not diagnosis.empty else "",
                                                    placeholder="Enter final diagnosis",
                                                    height=100)

                            col1, col2 = st.columns(2)
                            with col1:
                                icd_code = st.text_input("ICD-10 Code",
                                                        value=diagnosis.iloc[0]['icd_code'] if not diagnosis.empty else "",
                                                        placeholder="e.g., C91.0")
                                who_class = st.text_input("WHO Classification",
                                                         value=diagnosis.iloc[0]['who_classification'] if not diagnosis.empty else "",
                                                         placeholder="e.g., WHO 2022")
                            with col2:
                                fab_class = st.text_input("FAB Classification",
                                                         value=diagnosis.iloc[0]['fab_classification'] if not diagnosis.empty else "",
                                                         placeholder="e.g., FAB M3")
                                report_date = st.date_input("Report Date",
                                                           value=date.today())

                            additional_findings = st.text_area("Additional Findings",
                                                             value=diagnosis.iloc[0]['additional_findings'] if not diagnosis.empty else "",
                                                             height=80,
                                                             placeholder="Any additional clinical findings or notes")

                            col_corr1, col_corr2 = st.columns(2)
                            with col_corr1:
                                corr_morphology = st.checkbox("Correlates with morphology",
                                                             value=bool(diagnosis.iloc[0]['correlates_with_morphology']) if not diagnosis.empty else False)
                            with col_corr2:
                                corr_cytogenetics = st.checkbox("Correlates with cytogenetics",
                                                               value=bool(diagnosis.iloc[0]['correlates_with_cytogenetics']) if not diagnosis.empty else False)

                            reported_by = st.text_input("Reported By",
                                                       value=diagnosis.iloc[0]['reported_by'] if not diagnosis.empty else "",
                                                       placeholder="Physician name")

                            if st.form_submit_button("Save Diagnosis", use_container_width=True):
                                if not diag_text:
                                    st.error("Final diagnosis is required")
                                else:
                                    try:
                                        if diagnosis.empty:
                                            # Insert new diagnosis
                                            query_panels("""
                                                INSERT INTO case_diagnoses (
                                                    id, case_id, final_diagnosis, icd_code,
                                                    who_classification, fab_classification,
                                                    correlates_with_morphology, correlates_with_cytogenetics,
                                                    additional_findings, reported_by, report_date, created_at
                                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                            """, (
                                                str(uuid.uuid4()), c['id'], diag_text, icd_code or None,
                                                who_class or None, fab_class or None,
                                                1 if corr_morphology else 0, 1 if corr_cytogenetics else 0,
                                                additional_findings or None, reported_by or None,
                                                str(report_date), datetime.now().isoformat()
                                            ), commit=True)
                                        else:
                                            # Update existing diagnosis
                                            query_panels("""
                                                UPDATE case_diagnoses SET
                                                    final_diagnosis = ?,
                                                    icd_code = ?,
                                                    who_classification = ?,
                                                    fab_classification = ?,
                                                    correlates_with_morphology = ?,
                                                    correlates_with_cytogenetics = ?,
                                                    additional_findings = ?,
                                                    reported_by = ?,
                                                    report_date = ?,
                                                    updated_at = ?
                                                WHERE case_id = ?
                                            """, (
                                                diag_text, icd_code or None,
                                                who_class or None, fab_class or None,
                                                1 if corr_morphology else 0, 1 if corr_cytogenetics else 0,
                                                additional_findings or None, reported_by or None,
                                                str(report_date), datetime.now().isoformat(), c['id']
                                            ), commit=True)

                                        st.success("Diagnosis saved successfully")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error saving diagnosis: {e}")
