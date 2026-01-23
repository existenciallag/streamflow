# ui/panel_builder.py
"""
Panel Builder v2 - Clinical Grade Flow Cytometry Panel Designer
Split-view interface with semantic names, automatic versioning, and full traceability
"""

import streamlit as st
import uuid
from datetime import datetime
import pandas as pd
import json
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
    """Get all reagents with detailed stock breakdown"""
    return query_panels("""
        SELECT
            r.id as reagent_id,
            r.name as reagent_name,
            r.target_antigen,
            r.clone,
            r.price,
            r.fluorochrome as fluorochrome_id,
            f.name as fluorochrome,
            b.name as brand,

            -- Available (not expired, stored or in use)
            COUNT(DISTINCT CASE
                WHEN LOWER(ru.status) IN ('stored', 'in use')
                AND (ru.expiration_date IS NULL OR ru.expiration_date > datetime('now'))
                THEN ru.id
            END) as available_vials,

            -- In use (regardless of expiration)
            COUNT(DISTINCT CASE
                WHEN LOWER(ru.status) = 'in use'
                THEN ru.id
            END) as in_use_vials,

            -- Expired but not closed
            COUNT(DISTINCT CASE
                WHEN LOWER(ru.status) IN ('stored', 'in use')
                AND ru.expiration_date IS NOT NULL
                AND ru.expiration_date <= datetime('now')
                THEN ru.id
            END) as expired_vials,

            -- Earliest expiration of available vials
            MIN(CASE
                WHEN LOWER(ru.status) IN ('stored', 'in use')
                AND (ru.expiration_date IS NULL OR ru.expiration_date > datetime('now'))
                THEN ru.expiration_date
            END) as earliest_expiration,

            -- Average volume for cost calculation (only available vials)
            AVG(CASE
                WHEN LOWER(ru.status) IN ('stored', 'in use')
                AND (ru.expiration_date IS NULL OR ru.expiration_date > datetime('now'))
                THEN ru.initial_volume
            END) as avg_initial_volume

        FROM reagents r
        JOIN fluorochromes f ON f.id = r.fluorochrome
        LEFT JOIN brands b ON b.id = r.brand_id
        LEFT JOIN reagent_units ru ON ru.reagent_id = r.id
        GROUP BY r.id, r.name, r.target_antigen, r.clone, r.price, r.fluorochrome, f.name, b.name
        ORDER BY r.name
    """)


def get_suggested_channel(cytometer_id, fluorochrome_id):
    """
    Get the suggested optical channel for a fluorochrome using ID-based matching.
    The associated_fluorochrome column contains JSON array of fluorochrome IDs.
    """
    result = query_panels("""
        SELECT
            oc.id as channel_id,
            oc.name as channel_name,
            coc.associated_fluorochrome,
            coc.primary_fluorochrome
        FROM cytometer_optical_channels coc
        JOIN optical_channels oc ON oc.id = coc.optical_channel_id
        WHERE coc.cytometer_id = ?
    """, (cytometer_id,))

    if result.empty:
        return None, None

    # Parse associated_fluorochrome JSON and find match
    for _, row in result.iterrows():
        assoc_fluoro_json = row['associated_fluorochrome']

        if not assoc_fluoro_json or assoc_fluoro_json == '[]':
            continue

        try:
            # Parse JSON array
            fluorochrome_list = json.loads(assoc_fluoro_json)

            # Clean up escaped quotes if present (handle both formats)
            cleaned_list = []
            for item in fluorochrome_list:
                # Remove extra quotes: "\"FL-0006\"" -> FL-0006
                cleaned = item.strip('"').strip('\\').strip('"')
                cleaned_list.append(cleaned)

            # Check if fluorochrome_id is in the list
            if fluorochrome_id in cleaned_list:
                return row['channel_id'], row['channel_name']

        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, try simple string matching
            if fluorochrome_id in str(assoc_fluoro_json):
                return row['channel_id'], row['channel_name']
            continue

    # Check primary fluorochrome as fallback
    for _, row in result.iterrows():
        if row['primary_fluorochrome'] == fluorochrome_id:
            return row['channel_id'], row['channel_name']

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
            if ab['price'] and ab['avg_initial_volume']:
                # Calculate correct price per µL
                unit_cost = ab['price'] / ab['avg_initial_volume']
                st.write(f"${ab['price']:.2f} / {ab['avg_initial_volume']:.0f} µL")
                st.caption(f"(${unit_cost:.3f} per µL)")
            elif ab['price']:
                st.write(f"${ab['price']:.2f}")
            else:
                st.write("N/A")

            # Stock status with detailed breakdown
            st.caption("**Stock Status:**")
            stock_parts = []

            if ab['available_vials'] > 0:
                stock_parts.append(f"✓ {ab['available_vials']} available")

            if ab['in_use_vials'] > 0:
                stock_parts.append(f"🔵 {ab['in_use_vials']} in use")

            if ab['expired_vials'] > 0:
                stock_parts.append(f"⚠️ {ab['expired_vials']} expired")

            if stock_parts:
                for part in stock_parts:
                    st.write(part)

                if ab['earliest_expiration']:
                    st.caption(f"Next exp: {ab['earliest_expiration'][:10]}")
            else:
                st.error("No stock available")

        # Channel assignment
        st.markdown("---")
        st.caption("**Channel Assignment:**")

        # Auto-suggest channel using fluorochrome ID
        suggested_channel_id, suggested_channel_name = get_suggested_channel(
            cytometer_id, ab['fluorochrome_id']
        )

        if suggested_channel_id:
            st.info(f"✓ Suggested: **{suggested_channel_name}**")
            selected_channel_id = suggested_channel_id
            selected_channel_name = suggested_channel_name
        else:
            st.warning("⚠ No automatic channel match found")
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
        col1, col2 = st.columns(2)

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

        staining_step = st.number_input(
            "Staining Step",
            min_value=1,
            max_value=5,
            value=1 if not is_intracellular else 2,
            help="Workflow order: 1=first, 2=second, etc.",
            key=f"{key_prefix}_step_{ab['reagent_id']}"
        )

        # Display name customization
        default_display = f"{ab['target_antigen'] or ab['reagent_name']} {ab['fluorochrome']}"
        display_name = st.text_input(
            "Display name in panel",
            value=default_display,
            key=f"{key_prefix}_display_{ab['reagent_id']}"
        )

        # Calculate cost using ACTUAL volume from reagent_units
        cost_per_test = 0.0
        unit_cost = 0.0

        if ab['price'] and ab['avg_initial_volume'] and volume > 0:
            # Correct calculation: price / actual_vial_volume * volume_used
            unit_cost = ab['price'] / ab['avg_initial_volume']
            cost_per_test = volume * unit_cost

        # Add button
        if st.button("➕ Add to Panel", key=f"{key_prefix}_add_{ab['reagent_id']}", type="secondary"):
            return {
                "reagent_id": ab['reagent_id'],
                "reagent_name": ab['reagent_name'],
                "fluorochrome": ab['fluorochrome'],
                "fluorochrome_id": ab['fluorochrome_id'],
                "clone": ab['clone'],
                "optical_channel_id": selected_channel_id,
                "channel_display_name": selected_channel_name,
                "volume_per_test": volume,
                "is_intracellular": 1 if is_intracellular else 0,
                "is_surface": 0 if is_intracellular else 1,
                "staining_step": staining_step,
                "display_name": display_name,
                "unit_cost": unit_cost,
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


def load_existing_panel_for_editing(panel_id):
    """Load existing panel data into Panel Builder for editing"""
    # Load panel metadata
    panel = query_panels("SELECT * FROM panels WHERE id = ?", (panel_id,))
    if panel.empty:
        return None

    panel_data = panel.iloc[0]

    # Load panel reagents
    panel_reagents = query_panels("""
        SELECT
            pr.reagent_id,
            r.name as reagent_name,
            r.fluorochrome as fluorochrome_id,
            f.name as fluorochrome,
            r.clone,
            pr.optical_channel_id,
            pr.channel_display_name,
            pr.volume_used as volume_per_test,
            pr.is_intracellular,
            pr.is_surface,
            pr.staining_step,
            pr.display_name,
            pr.unit_cost,
            pr.cost_per_test
        FROM panel_reagents pr
        JOIN reagents r ON r.id = pr.reagent_id
        JOIN fluorochromes f ON f.id = r.fluorochrome
        WHERE pr.panel_id = ?
    """, (panel_id,))

    # Convert to list of dicts
    reagents_list = panel_reagents.to_dict('records') if not panel_reagents.empty else []

    return {
        "panel": panel_data,
        "reagents": reagents_list
    }


def save_panel_updates(panel_id, panel_reagents):
    """Update an existing panel's reagents"""
    try:
        # Delete existing panel reagents
        query_panels("DELETE FROM panel_reagents WHERE panel_id = ?", (panel_id,), commit=True)

        # Insert updated reagents
        now = datetime.utcnow().isoformat()
        for reagent in panel_reagents:
            query_panels("""
                INSERT INTO panel_reagents (
                    id, panel_id, reagent_id,
                    optical_channel_id, channel_display_name,
                    volume_used, unit_cost, cost_per_test,
                    is_intracellular, is_surface, staining_step,
                    display_name,
                    assigned_at, added_by
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

        # Update panel cost
        total_cost = calculate_panel_cost(panel_reagents)
        query_panels(
            "UPDATE panels SET estimated_cost_per_test = ?, updated_at = ? WHERE id = ?",
            (total_cost, now, panel_id),
            commit=True
        )

        return True
    except Exception as e:
        st.error(f"Error saving panel updates: {e}")
        return False


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
    if "editing_panel_id" not in st.session_state:
        st.session_state["editing_panel_id"] = None

    # Check if we're editing an existing panel (from Panels view)
    editing_mode = st.session_state.get("editing_panel_id") is not None

    # Load existing panel data if editing
    if editing_mode and not st.session_state["panel_draft_reagents"]:
        panel_data = load_existing_panel_for_editing(st.session_state["editing_panel_id"])
        if panel_data:
            st.session_state["panel_draft_reagents"] = panel_data["reagents"]
            st.info(f"✏️ Editing panel: {panel_data['panel']['name']}")

    # ============================================================
    # PANEL METADATA
    # ============================================================
    with st.expander("📝 Panel Metadata", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            panel_name = st.text_input("Panel Name *", placeholder="e.g., LST Panel",
                                       disabled=editing_mode)
            if editing_mode:
                st.caption("Panel name cannot be changed when editing")

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
    # PROTOCOLS SELECTION (Simplified - use existing columns)
    # ============================================================
    with st.expander("📋 Protocols", expanded=False):
        col1, col2, col3 = st.columns(3)

        # Acquisition protocol (use name-based approach)
        with col1:
            st.caption("**Acquisition Protocol**")
            acquisition_protocol_name = st.text_input(
                "Protocol Name",
                value="Standard Acquisition",
                key="acq_protocol_name",
                help="Name of acquisition protocol"
            )
            acquisition_protocol_status = st.selectbox(
                "Status",
                ["draft", "validated", "archived"],
                index=1,
                key="acq_protocol_status"
            )

        # Compensation protocol
        with col2:
            st.caption("**Compensation Protocol**")
            compensation_protocol_name = st.text_input(
                "Protocol Name",
                value="Standard Compensation",
                key="comp_protocol_name",
                help="Name of compensation protocol"
            )
            compensation_protocol_status = st.selectbox(
                "Status",
                ["draft", "validated", "archived"],
                index=1,
                key="comp_protocol_status"
            )

        # Analysis protocol
        with col3:
            st.caption("**Analysis Protocol**")
            analysis_protocol_name = st.text_input(
                "Protocol Name",
                value="Standard Gating",
                key="analysis_protocol_name",
                help="Name of analysis protocol"
            )
            analysis_protocol_status = st.selectbox(
                "Status",
                ["draft", "validated", "archived"],
                index=1,
                key="analysis_protocol_status"
            )

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

        # Search only (removed surface/intracellular filter)
        search_query = st.text_input(
            "Search",
            placeholder="Search by name, antigen, clone, or fluorochrome...",
            key="ab_search"
        )

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

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        st.caption("Ready to save? All fields marked with * are required.")

    with col2:
        if editing_mode and st.button("❌ Cancel Edit", use_container_width=True):
            st.session_state["editing_panel_id"] = None
            st.session_state["panel_draft_reagents"] = []
            st.session_state["panel_draft_general_reagents"] = []
            st.success("Cancelled editing")
            st.rerun()

    with col3:
        if st.button("🗑️ Clear Panel", type="secondary", use_container_width=True):
            st.session_state["panel_draft_reagents"] = []
            st.session_state["panel_draft_general_reagents"] = []
            st.success("Panel cleared")
            st.rerun()

    with col4:
        save_button_label = "💾 Update Panel" if editing_mode else "💾 Save Panel"
        save_button = st.button(save_button_label, type="primary", use_container_width=True)

    if save_button:
        # Validation
        errors = []
        if not editing_mode:
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

        # Save or update panel
        try:
            if editing_mode:
                # UPDATE existing panel
                panel_id = st.session_state["editing_panel_id"]

                if save_panel_updates(panel_id, st.session_state["panel_draft_reagents"]):
                    st.success(f"✅ Panel updated successfully!")

                    # Clear editing state
                    st.session_state["editing_panel_id"] = None
                    st.session_state["panel_draft_reagents"] = []
                    st.session_state["panel_draft_general_reagents"] = []
                    st.balloons()
                else:
                    st.error("Failed to update panel")

            else:
                # CREATE new panel
                panel_id = str(uuid.uuid4())
                now = datetime.utcnow().isoformat()

                # Calculate total cost
                total_cost = calculate_panel_cost(st.session_state["panel_draft_reagents"])

                # Insert panel using EXISTING columns (not FK references)
                query_panels("""
                    INSERT INTO panels (
                        id, name, version, description,
                        sample_type, sample_volume, washed_sample,
                        clinical_indication,
                        cytometer_id,
                        acquisition_protocol_name, acquisition_protocol_status,
                        compensation_name, compensation_status,
                        analysis_protocol_name, analysis_protocol_status,
                        estimated_cost_per_test,
                        status,
                        created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    acquisition_protocol_name,
                    acquisition_protocol_status,
                    compensation_protocol_name,
                    compensation_protocol_status,
                    analysis_protocol_name,
                    analysis_protocol_status,
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
                            volume_used, unit_cost, cost_per_test,
                            is_intracellular, is_surface, staining_step,
                            display_name,
                            assigned_at, added_by
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
                st.info(f"Total Cost: ${total_cost:.2f} per test")

                # Clear draft
                st.session_state["panel_draft_reagents"] = []
                st.session_state["panel_draft_general_reagents"] = []

                # Wait a moment before rerun
                st.balloons()

        except Exception as e:
            st.error(f"❌ Error saving panel: {e}")
            import traceback
            st.code(traceback.format_exc())
