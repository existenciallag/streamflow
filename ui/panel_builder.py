# ui/panel_builder.py
"""
Panel Builder v2 - Clinical Grade Flow Cytometry Panel Designer
Split-view interface with semantic names, automatic versioning, and full traceability
"""

import streamlit as st
import uuid
from datetime import datetime
import pandas as pd
from ui.crud_panels import query_panels


def get_default_cytometer():
    """Get the default cytometer (CytoFLEX)"""
    result = query_panels("SELECT id, name FROM cytometers WHERE is_default = 1 LIMIT 1")
    if not result.empty:
        return result.iloc[0]["id"], result.iloc[0]["name"]

    # Fallback: get CytoFLEX by name
    result = query_panels("SELECT id, name FROM cytometers WHERE name = 'Cytoflex' LIMIT 1")
    if not result.empty:
        return result.iloc[0]["id"], result.iloc[0]["name"]

    # Fallback: get first cytometer
    result = query_panels("SELECT id, name FROM cytometers LIMIT 1")
    if not result.empty:
        return result.iloc[0]["id"], result.iloc[0]["name"]

    return None, None


def get_available_channels(cytometer_id):
    """Get all optical channels for a cytometer with semantic names"""
    return query_panels("""
        SELECT
            oc.id as channel_id,
            oc.name as channel_name,
            coc.primary_fluorochrome,
            coc.display_order
        FROM cytometer_optical_channels coc
        JOIN optical_channels oc ON oc.id = coc.optical_channel_id
        WHERE coc.cytometer_id = ?
        ORDER BY COALESCE(coc.display_order, 999), oc.name
    """, (cytometer_id,))


def get_reagents_with_details():
    """Get all reagents with their details (semantic names only)"""
    return query_panels("""
        SELECT
            r.id as reagent_id,
            r.name as reagent_name,
            r.target_antigen,
            r.clone,
            r.price,
            f.name as fluorochrome,
            b.name as brand,
            COUNT(DISTINCT ru.id) as available_vials,
            MIN(ru.expiration_date) as earliest_expiration
        FROM reagents r
        JOIN fluorochromes f ON f.id = r.fluorochrome
        LEFT JOIN brands b ON b.id = r.brand_id
        LEFT JOIN reagent_units ru ON ru.reagent_id = r.id
            AND ru.status IN ('Stored', 'In Use')
            AND (ru.expiration_date IS NULL OR ru.expiration_date > datetime('now'))
        GROUP BY r.id, r.name, r.target_antigen, r.clone, r.price, f.name, b.name
        ORDER BY r.name
    """)


def get_suggested_channel(cytometer_id, fluorochrome):
    """Get the suggested optical channel for a fluorochrome"""
    result = query_panels("""
        SELECT
            oc.id as channel_id,
            oc.name as channel_name
        FROM cytometer_optical_channels coc
        JOIN optical_channels oc ON oc.id = coc.optical_channel_id
        WHERE coc.cytometer_id = ?
        AND (
            coc.primary_fluorochrome = ?
            OR coc.associated_fluorochrome LIKE '%' || ? || '%'
        )
        LIMIT 1
    """, (cytometer_id, fluorochrome, fluorochrome))

    if not result.empty:
        return result.iloc[0]["channel_id"], result.iloc[0]["channel_name"]
    return None, None


def calculate_panel_cost(panel_reagents):
    """Calculate total cost per test for a panel"""
    total_cost = 0.0
    for reagent in panel_reagents:
        if reagent.get("cost_per_test"):
            total_cost += reagent["cost_per_test"]
    return total_cost


def render_antibody_card(ab, cytometer_id, key_prefix):
    """Render an antibody selection card with all details"""
    with st.expander(
        f"**{ab['reagent_name']}** {ab['fluorochrome']} ({ab['clone'] or 'N/A'})",
        expanded=False
    ):
        # Display antibody details
        col1, col2 = st.columns(2)

        with col1:
            st.caption("**Target:**")
            st.write(ab['target_antigen'] or ab['reagent_name'])

            st.caption("**Fluorochrome:**")
            st.write(ab['fluorochrome'])

            st.caption("**Clone:**")
            st.write(ab['clone'] or "N/A")

        with col2:
            st.caption("**Brand:**")
            st.write(ab['brand'] or "N/A")

            st.caption("**Price:**")
            if ab['price']:
                st.write(f"${ab['price']:.2f} / 100 µL")
            else:
                st.write("N/A")

            st.caption("**Available Vials:**")
            if ab['available_vials'] > 0:
                st.success(f"{ab['available_vials']} vial(s)")
            else:
                st.error("No stock available")

        # Channel assignment
        st.markdown("---")
        st.caption("**Channel Assignment:**")

        # Auto-suggest channel
        suggested_channel_id, suggested_channel_name = get_suggested_channel(
            cytometer_id, ab['fluorochrome']
        )

        if suggested_channel_id:
            st.info(f"✓ Suggested: **{suggested_channel_name}**")
            selected_channel_id = suggested_channel_id
            selected_channel_name = suggested_channel_name
        else:
            st.warning("⚠ No automatic channel match")
            # Manual selection
            channels = get_available_channels(cytometer_id)
            if channels.empty:
                st.error("No channels configured for this cytometer")
                return None

            channel_options = {row['channel_name']: row['channel_id']
                             for _, row in channels.iterrows()}
            selected_channel_name = st.selectbox(
                "Select channel manually",
                options=list(channel_options.keys()),
                key=f"{key_prefix}_channel_{ab['reagent_id']}"
            )
            selected_channel_id = channel_options[selected_channel_name]

        # Usage parameters
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            volume = st.number_input(
                "Volume (µL)",
                min_value=0.0,
                max_value=50.0,
                value=1.25,
                step=0.25,
                key=f"{key_prefix}_vol_{ab['reagent_id']}"
            )

        with col2:
            is_intracellular = st.checkbox(
                "Intracellular",
                value=False,
                key=f"{key_prefix}_intra_{ab['reagent_id']}"
            )

        with col3:
            staining_step = st.number_input(
                "Step",
                min_value=1,
                max_value=5,
                value=1,
                help="Staining step order (1=first, 2=second, etc.)",
                key=f"{key_prefix}_step_{ab['reagent_id']}"
            )

        # Display name customization
        default_display = f"{ab['target_antigen'] or ab['reagent_name']} {ab['fluorochrome']}"
        display_name = st.text_input(
            "Display name in panel",
            value=default_display,
            key=f"{key_prefix}_display_{ab['reagent_id']}"
        )

        # Calculate cost
        cost_per_test = 0.0
        if ab['price'] and volume > 0:
            # price is per 100 µL
            unit_cost = ab['price'] / 100.0
            cost_per_test = volume * unit_cost

        # Add button
        if st.button("➕ Add to Panel", key=f"{key_prefix}_add_{ab['reagent_id']}", type="secondary"):
            return {
                "reagent_id": ab['reagent_id'],
                "reagent_name": ab['reagent_name'],
                "fluorochrome": ab['fluorochrome'],
                "clone": ab['clone'],
                "optical_channel_id": selected_channel_id,
                "channel_display_name": selected_channel_name,
                "volume_per_test": volume,
                "is_intracellular": 1 if is_intracellular else 0,
                "is_surface": 0 if is_intracellular else 1,
                "staining_step": staining_step,
                "display_name": display_name,
                "unit_cost": ab['price'] / 100.0 if ab['price'] else 0.0,
                "cost_per_test": cost_per_test,
            }

    return None


def render_panel_composition(panel_reagents, panel_general_reagents):
    """Render the right-side panel composition view"""
    st.markdown("### 📋 Panel Composition")

    if not panel_reagents and not panel_general_reagents:
        st.info("No reagents added yet. Add antibodies from the left panel.")
        return

    # Calculate total cost
    total_cost = calculate_panel_cost(panel_reagents)
    if panel_general_reagents:
        for gr in panel_general_reagents:
            total_cost += gr.get("cost_per_test", 0.0)

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Antibodies", len(panel_reagents))
    with col2:
        st.metric("General Reagents", len(panel_general_reagents))
    with col3:
        st.metric("Cost/Test", f"${total_cost:.2f}")

    # Antibodies table
    if panel_reagents:
        st.markdown("#### Antibodies")

        # Sort by channel display order
        sorted_reagents = sorted(panel_reagents, key=lambda x: x.get('channel_display_name', ''))

        df_data = []
        for i, reagent in enumerate(sorted_reagents):
            df_data.append({
                "Channel": reagent['channel_display_name'],
                "Marker": reagent['display_name'],
                "Vol (µL)": f"{reagent['volume_per_test']:.2f}",
                "Step": reagent['staining_step'],
                "Intra": "✓" if reagent['is_intracellular'] else "",
                "Cost": f"${reagent['cost_per_test']:.2f}",
                "idx": i
            })

        df = pd.DataFrame(df_data)

        # Display table with selection for deletion
        selected = st.dataframe(
            df[["Channel", "Marker", "Vol (µL)", "Step", "Intra", "Cost"]],
            use_container_width=True,
            selection_mode="multi-row",
            on_select="rerun",
            height=min(400, 35 + len(df) * 35)
        )

        # Delete button
        if selected and selected.get("selection", {}).get("rows"):
            if st.button("🗑️ Remove Selected", type="secondary"):
                # Remove selected indices (in reverse to avoid index issues)
                for idx in sorted(selected["selection"]["rows"], reverse=True):
                    actual_idx = df.iloc[idx]["idx"]
                    del panel_reagents[int(actual_idx)]
                st.rerun()

    # General reagents
    if panel_general_reagents:
        st.markdown("#### General Reagents")
        for gr in panel_general_reagents:
            st.text(f"• {gr['display_name']}: {gr.get('volume_per_test', 'N/A')} µL - ${gr.get('cost_per_test', 0):.2f}")


def create_panel():
    """Main panel builder interface - split view"""

    st.title("🧬 Panel Builder v2.0")
    st.caption("Clinical-grade panel designer with full traceability")

    # ============================================================
    # INITIALIZE SESSION STATE
    # ============================================================
    if "panel_draft_reagents" not in st.session_state:
        st.session_state["panel_draft_reagents"] = []
    if "panel_draft_general_reagents" not in st.session_state:
        st.session_state["panel_draft_general_reagents"] = []

    # ============================================================
    # PANEL METADATA
    # ============================================================
    with st.expander("📝 Panel Metadata", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            panel_name = st.text_input("Panel Name *", placeholder="e.g., LST Panel")
            clinical_indication = st.text_input(
                "Clinical Indication",
                placeholder="e.g., Lymphocyte subset analysis"
            )
            sample_type = st.selectbox(
                "Sample Type *",
                ["Whole Blood", "Bone Marrow", "CSF", "Tissue", "Other"],
                index=0
            )

        with col2:
            panel_version = st.text_input("Version", value="1.0.0", disabled=True,
                                        help="Auto-versioned on save")
            sample_volume = st.number_input(
                "Sample Volume (µL) *",
                min_value=0.0,
                max_value=500.0,
                value=50.0,
                step=5.0
            )
            washed_sample = st.checkbox("Pre-washed Sample", value=False)

        description = st.text_area(
            "Description",
            height=80,
            placeholder="Brief description of the panel purpose and composition..."
        )

    # ============================================================
    # CYTOMETER SELECTION (Default: CytoFLEX)
    # ============================================================
    st.markdown("---")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🔬 Cytometer Configuration")

    # Get default cytometer
    default_cyt_id, default_cyt_name = get_default_cytometer()

    if not default_cyt_id:
        st.error("⚠️ No cytometer configured. Please add a cytometer first.")
        return

    # Get all cytometers
    all_cytometers = query_panels("SELECT id, name FROM cytometers ORDER BY is_default DESC, name")
    cyt_map = dict(zip(all_cytometers["name"], all_cytometers["id"]))

    with col2:
        selected_cyt_name = st.selectbox(
            "Select Cytometer",
            options=list(cyt_map.keys()),
            index=list(cyt_map.keys()).index(default_cyt_name) if default_cyt_name in cyt_map else 0,
            help="CytoFLEX is the default"
        )
        cytometer_id = cyt_map[selected_cyt_name]

    st.info(f"✓ Using **{selected_cyt_name}** — All channels configured for this instrument")

    # ============================================================
    # PROTOCOLS SELECTION (Simplified)
    # ============================================================
    with st.expander("📋 Protocols", expanded=False):
        col1, col2, col3 = st.columns(3)

        # Acquisition protocols
        with col1:
            acq_protocols = query_panels("""
                SELECT id, name, version, status
                FROM acquisition_protocols
                WHERE cytometer_id = ?
                ORDER BY status DESC, name
            """, (cytometer_id,))

            if not acq_protocols.empty:
                acq_options = ["(None)"] + [
                    f"{row['name']} v{row['version']}" + (" ✓" if row['status'] == 'validated' else "")
                    for _, row in acq_protocols.iterrows()
                ]
                selected_acq = st.selectbox("Acquisition Protocol", acq_options)
                acquisition_protocol_id = acq_protocols.iloc[acq_options.index(selected_acq) - 1]["id"] if selected_acq != "(None)" else None
            else:
                st.caption("No acquisition protocols available")
                acquisition_protocol_id = None

        # Compensation protocols
        with col2:
            comp_protocols = query_panels("""
                SELECT id, name, version, status
                FROM compensation_protocols
                WHERE cytometer_id = ?
                ORDER BY status DESC, name
            """, (cytometer_id,))

            if not comp_protocols.empty:
                comp_options = ["(None)"] + [
                    f"{row['name']} v{row['version']}" + (" ✓" if row['status'] == 'validated' else "")
                    for _, row in comp_protocols.iterrows()
                ]
                selected_comp = st.selectbox("Compensation Protocol", comp_options)
                compensation_protocol_id = comp_protocols.iloc[comp_options.index(selected_comp) - 1]["id"] if selected_comp != "(None)" else None
            else:
                st.caption("No compensation protocols available")
                compensation_protocol_id = None

        # Analysis protocols
        with col3:
            analysis_protocols = query_panels("""
                SELECT id, name, version, status
                FROM analysis_protocols
                ORDER BY status DESC, name
            """)

            if not analysis_protocols.empty:
                analysis_options = ["(None)"] + [
                    f"{row['name']} v{row['version']}" + (" ✓" if row['status'] == 'validated' else "")
                    for _, row in analysis_protocols.iterrows()
                ]
                selected_analysis = st.selectbox("Analysis Protocol", analysis_options)
                analysis_protocol_id = analysis_protocols.iloc[analysis_options.index(selected_analysis) - 1]["id"] if selected_analysis != "(None)" else None
            else:
                st.caption("No analysis protocols available")
                analysis_protocol_id = None

    # ============================================================
    # SPLIT VIEW: LEFT (Selection) | RIGHT (Composition)
    # ============================================================
    st.markdown("---")

    left_col, right_col = st.columns([1, 1])

    # ============================================================
    # LEFT PANEL: ANTIBODY SELECTION
    # ============================================================
    with left_col:
        st.markdown("### 🔍 Antibody Selection")

        # Search and filter
        search_query = st.text_input(
            "Search",
            placeholder="Search by name, antigen, or clone...",
            key="ab_search"
        )

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_surface = st.checkbox("Surface markers", value=True, key="filter_surface")
        with col_f2:
            filter_intra = st.checkbox("Intracellular", value=True, key="filter_intra")

        # Load reagents
        reagents_df = get_reagents_with_details()

        if reagents_df.empty:
            st.warning("No reagents found in database")
        else:
            # Apply search filter
            if search_query:
                mask = (
                    reagents_df["reagent_name"].str.contains(search_query, case=False, na=False) |
                    reagents_df["target_antigen"].str.contains(search_query, case=False, na=False) |
                    reagents_df["clone"].str.contains(search_query, case=False, na=False) |
                    reagents_df["fluorochrome"].str.contains(search_query, case=False, na=False)
                )
                reagents_df = reagents_df[mask]

            # Show count
            st.caption(f"Showing {len(reagents_df)} antibodies")

            # Render antibody cards (limit to 20 for performance)
            for _, ab in reagents_df.head(20).iterrows():
                result = render_antibody_card(ab, cytometer_id, key_prefix="builder")
                if result:
                    # Check for duplicate channel
                    existing_channels = [r['optical_channel_id'] for r in st.session_state["panel_draft_reagents"]]
                    if result['optical_channel_id'] in existing_channels:
                        st.warning(f"⚠️ Channel {result['channel_display_name']} already in use!")

                    st.session_state["panel_draft_reagents"].append(result)
                    st.success(f"✓ Added {result['display_name']}")
                    st.rerun()

            if len(reagents_df) > 20:
                st.info(f"Showing first 20 of {len(reagents_df)} results. Use search to narrow down.")

    # ============================================================
    # RIGHT PANEL: PANEL COMPOSITION
    # ============================================================
    with right_col:
        render_panel_composition(
            st.session_state["panel_draft_reagents"],
            st.session_state["panel_draft_general_reagents"]
        )

    # ============================================================
    # SAVE PANEL
    # ============================================================
    st.markdown("---")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.caption("Ready to save? All fields marked with * are required.")

    with col2:
        if st.button("🗑️ Clear Panel", type="secondary", use_container_width=True):
            st.session_state["panel_draft_reagents"] = []
            st.session_state["panel_draft_general_reagents"] = []
            st.success("Panel cleared")
            st.rerun()

    with col3:
        save_button = st.button("💾 Save Panel", type="primary", use_container_width=True)

    if save_button:
        # Validation
        errors = []
        if not panel_name or not panel_name.strip():
            errors.append("Panel name is required")
        if not sample_type:
            errors.append("Sample type is required")
        if sample_volume <= 0:
            errors.append("Sample volume must be greater than 0")
        if not st.session_state["panel_draft_reagents"]:
            errors.append("Add at least one antibody to the panel")

        if errors:
            for error in errors:
                st.error(f"❌ {error}")
            return

        # Save panel
        try:
            panel_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            # Calculate total cost
            total_cost = calculate_panel_cost(st.session_state["panel_draft_reagents"])

            # Insert panel
            query_panels("""
                INSERT INTO panels (
                    id, name, version, description,
                    sample_type, sample_volume, washed_sample,
                    clinical_indication,
                    cytometer_id,
                    acquisition_protocol_id, compensation_protocol_id, analysis_protocol_id,
                    estimated_cost_per_test,
                    status,
                    created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                panel_id,
                panel_name.strip(),
                panel_version,
                description or None,
                sample_type,
                sample_volume,
                1 if washed_sample else 0,
                clinical_indication or None,
                cytometer_id,
                acquisition_protocol_id,
                compensation_protocol_id,
                analysis_protocol_id,
                total_cost,
                "draft",
                now,
                "system"  # TODO: replace with actual user when auth is added
            ), commit=True)

            # Insert panel reagents
            for reagent in st.session_state["panel_draft_reagents"]:
                query_panels("""
                    INSERT INTO panel_reagents (
                        id, panel_id, reagent_id,
                        optical_channel_id, channel_display_name,
                        volume_per_test, unit_cost, cost_per_test,
                        is_intracellular, is_surface, staining_step,
                        display_name,
                        added_at, added_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    panel_id,
                    reagent["reagent_id"],
                    reagent["optical_channel_id"],
                    reagent["channel_display_name"],
                    reagent["volume_per_test"],
                    reagent["unit_cost"],
                    reagent["cost_per_test"],
                    reagent["is_intracellular"],
                    reagent["is_surface"],
                    reagent["staining_step"],
                    reagent["display_name"],
                    now,
                    "system"
                ), commit=True)

            st.success(f"✅ Panel '{panel_name}' created successfully!")
            st.info(f"Panel ID: {panel_id}")

            # Clear draft
            st.session_state["panel_draft_reagents"] = []
            st.session_state["panel_draft_general_reagents"] = []

            # Wait a moment before rerun
            st.balloons()

        except Exception as e:
            st.error(f"❌ Error saving panel: {e}")
            import traceback
            st.code(traceback.format_exc())
