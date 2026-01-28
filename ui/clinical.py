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
                        age = st.number_input("Age", min_value=0, max_value=120, value=0)
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

                    st.markdown(f"### 👤 {p['initials']}")
                    st.caption(f"MRN: {p['medical_record_number']}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Age", p['age_at_registration'] or "—")
                    with col2:
                        st.metric("Sex", p['sex'] or "—")
                    with col3:
                        st.metric("Status", p['status'].upper())

                    if p['referring_physician']:
                        st.text(f"Requesting: Dr. {p['referring_physician']}")
                    if p['referring_institution']:
                        st.text(f"Institution: {p['referring_institution']}")

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

                    st.markdown(f"### {c['case_number']}")
                    st.caption(f"Patient: {c['patient_initials']} ({c['patient_mrn']})")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Status", c['status'].upper())
                    with col2:
                        st.metric("Priority", c['priority'].upper())
                    with col3:
                        st.metric("Sample Date", str(c['sample_date']))

                    st.markdown(f"**Clinical Suspicion:** {c['clinical_suspicion']}")
                    st.markdown(f"**Sample Type:** {c['sample_type']}")

                    # Assigned panels
                    st.markdown("---")
                    st.markdown("### Assigned Panels")

                    case_panels = query_panels("""
                        SELECT
                            cp.id,
                            p.name as panel_name,
                            cp.run_date,
                            cp.status,
                            cp.actual_cost
                        FROM case_panels cp
                        JOIN panels p ON p.id = cp.panel_id
                        WHERE cp.case_id = ?
                        ORDER BY cp.created_at
                    """, (c['id'],))

                    if case_panels is not None and not case_panels.empty:
                        st.dataframe(case_panels[['panel_name', 'run_date', 'status', 'actual_cost']],
                                   use_container_width=True, hide_index=True)
                    else:
                        st.info("No panels assigned yet")

                    # Assign new panel
                    with st.expander("Assign Panel", expanded=False):
                        # Get oncohematology panels
                        onco_panels = query_panels("""
                            SELECT DISTINCT p.id, p.name, p.version
                            FROM panels p
                            JOIN panel_classifications pc ON pc.panel_id = p.id
                            JOIN panel_areas pa ON pa.id = pc.area_id
                            WHERE pa.code = 'ONCOHEM' AND p.status IN ('validated', 'active')
                            ORDER BY p.name
                        """)

                        if onco_panels is None or onco_panels.empty:
                            st.warning("No Oncohematology panels available")
                        else:
                            with st.form("assign_panel_form"):
                                panel_options = [f"{p['name']} (v{p['version']})" for _, p in onco_panels.iterrows()]
                                selected_panel_idx = st.selectbox("Panel", range(len(panel_options)),
                                                                 format_func=lambda x: panel_options[x])

                                if st.form_submit_button("Assign Panel", use_container_width=True):
                                    try:
                                        case_panel_id = str(uuid.uuid4())
                                        panel_id = onco_panels.iloc[selected_panel_idx]['id']

                                        query_panels("""
                                            INSERT INTO case_panels (
                                                id, case_id, panel_id, status, created_at
                                            ) VALUES (?, ?, ?, 'pending', ?)
                                        """, (
                                            case_panel_id, c['id'], panel_id, datetime.now().isoformat()
                                        ), commit=True)

                                        st.success("Panel assigned successfully")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
