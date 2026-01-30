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
from utils.pricing import calculate_draft_panel_cost
from utils.translations import get_lang_dict


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

            -- Average volume for cost calculation (prefer available, fallback to all)
            COALESCE(
                AVG(CASE
                    WHEN LOWER(ru.status) IN ('stored', 'in use')
                    AND (ru.expiration_date IS NULL OR ru.expiration_date > datetime('now'))
                    THEN ru.initial_volume
                END),
                AVG(ru.initial_volume)
            ) as avg_initial_volume

        FROM reagents r
        JOIN fluorochromes f ON f.id = r.fluorochrome
        LEFT JOIN brands b ON b.id = r.brand_id
        LEFT JOIN reagent_units ru ON ru.reagent_id = r.id
        GROUP BY r.id, r.name, r.target_antigen, r.clone, r.price, r.fluorochrome, f.name, b.name
        ORDER BY r.name
    """)


def get_general_reagents_with_units():
    """Get all general reagents with their available units"""
    return query_panels("""
        SELECT
            gr.id as reagent_id,
            gr.name as reagent_name,
            gr.type as reagent_type,
            gr.concentration,
            gr.price,
            gr.standard_volume,
            gr.standard_units,
            b.name as brand,

            -- Count available units (not closed, not expired)
            COUNT(DISTINCT CASE
                WHEN LOWER(gru.status) IN ('stored', 'in use')
                AND (gru.expiration_date IS NULL OR gru.expiration_date > datetime('now'))
                THEN gru.id
            END) as available_units,

            -- Average volume for units
            AVG(CASE
                WHEN LOWER(gru.status) IN ('stored', 'in use')
                AND (gru.expiration_date IS NULL OR gru.expiration_date > datetime('now'))
                THEN gru.volume
            END) as avg_volume

        FROM general_reagents gr
        LEFT JOIN brands b ON b.id = gr.brand_id
        LEFT JOIN general_reagent_units gru ON gru.general_reagent_id = gr.id
        GROUP BY gr.id, gr.name, gr.type, gr.concentration, gr.price, gr.standard_volume, gr.standard_units, b.name
        ORDER BY gr.name
    """)


def get_general_reagent_units(reagent_id):
    """Get available units for a specific general reagent"""
    return query_panels("""
        SELECT
            gru.id as unit_id,
            gru.lot_number,
            gru.volume,
            gru.expiration_date,
            gru.status,
            gru.location
        FROM general_reagent_units gru
        WHERE gru.general_reagent_id = ?
        AND LOWER(gru.status) IN ('stored', 'in use')
        AND (gru.expiration_date IS NULL OR gru.expiration_date > datetime('now'))
        ORDER BY gru.expiration_date ASC
    """, (reagent_id,))


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
    """
    Calculate total cost per test for a panel DYNAMICALLY from current stock.

    This replaces the old fixed-cost approach with real-time pricing
    based on available reagent units.
    """
    if not panel_reagents:
        return 0.0

    # Use new dynamic pricing system
    result = calculate_draft_panel_cost(panel_reagents, strategy='cheapest')
    return result['total_cost']


def render_antibody_card(ab, cytometer_id, key_prefix, t=None):
    """Render an antibody selection card with all details"""
    # Get translations if not provided
    if t is None:
        lang = st.session_state.get('language', 'en')
        t = get_lang_dict('panel_builder', lang)

    with st.expander(
        f"**{ab['reagent_name']}** {ab['fluorochrome']} ({ab['clone'] or t['unavailable_label']})",
        expanded=False
    ):
        # Display antibody details
        col1, col2 = st.columns(2)

        with col1:
            st.caption(f"**{t['target_label']}**")
            st.write(ab['target_antigen'] or ab['reagent_name'])

            st.caption(f"**{t['fluorochrome_label']}**")
            st.write(ab['fluorochrome'])

            st.caption(f"**{t['clone_label']}**")
            st.write(ab['clone'] or t['unavailable_label'])

        with col2:
            st.caption(f"**{t['brand_label']}**")
            st.write(ab['brand'] or t['unavailable_label'])

            st.caption(f"**{t['price_label']}**")
            if ab['price'] and ab['avg_initial_volume']:
                # Calculate correct price per µL
                unit_cost = ab['price'] / ab['avg_initial_volume']
                st.write(f"${ab['price']:.2f} / {ab['avg_initial_volume']:.0f} µL")
                st.caption(t['price_per_ul'].format(cost=unit_cost))
            elif ab['price']:
                st.write(f"${ab['price']:.2f}")
            else:
                st.write(t['unavailable_label'])

            # Stock status with detailed breakdown
            st.caption(f"**{t['stock_status_label']}**")
            stock_parts = []

            if ab['available_vials'] > 0:
                stock_parts.append(f"✓ {t['available_stock'].format(count=ab['available_vials'])}")

            if ab['in_use_vials'] > 0:
                stock_parts.append(f"🔵 {t['in_use_stock'].format(count=ab['in_use_vials'])}")

            if ab['expired_vials'] > 0:
                stock_parts.append(f"⚠️ {t['expired_stock'].format(count=ab['expired_vials'])}")

            if stock_parts:
                for part in stock_parts:
                    st.write(part)

                if ab['earliest_expiration']:
                    st.caption(t['next_expiration'].format(date=ab['earliest_expiration'][:10]))
            else:
                st.error(t['no_stock_error'])

        # Channel assignment
        st.markdown("---")
        st.caption(f"**{t['channel_assignment_label']}**")

        # Auto-suggest channel using fluorochrome ID
        suggested_channel_id, suggested_channel_name = get_suggested_channel(
            cytometer_id, ab['fluorochrome_id']
        )

        if suggested_channel_id:
            st.info(f"✓ {t['suggested_channel']} **{suggested_channel_name}**")
            selected_channel_id = suggested_channel_id
            selected_channel_name = suggested_channel_name
        else:
            st.warning(f"⚠ {t['no_channel_match_warning']}")
            # Manual selection
            channels = get_available_channels(cytometer_id)
            if channels.empty:
                st.error(t['no_channels_error'])
                return None

            channel_options = {row['channel_name']: row['channel_id']
                             for _, row in channels.iterrows()}
            selected_channel_name = st.selectbox(
                t['select_channel_manually'],
                options=list(channel_options.keys()),
                key=f"{key_prefix}_channel_{ab['reagent_id']}"
            )
            selected_channel_id = channel_options[selected_channel_name]

        # Usage parameters
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            volume = st.number_input(
                t['volume_label'],
                min_value=0.0,
                max_value=50.0,
                value=1.25,
                step=0.25,
                key=f"{key_prefix}_vol_{ab['reagent_id']}"
            )

        with col2:
            is_intracellular = st.checkbox(
                t['intracellular_label'],
                value=False,
                key=f"{key_prefix}_intra_{ab['reagent_id']}"
            )

        staining_step = st.number_input(
            t['staining_step_label'],
            min_value=1,
            max_value=5,
            value=1 if not is_intracellular else 2,
            help=t['staining_step_help'],
            key=f"{key_prefix}_step_{ab['reagent_id']}"
        )

        # Display name customization
        default_display = f"{ab['target_antigen'] or ab['reagent_name']} {ab['fluorochrome']}"
        display_name = st.text_input(
            t['display_name_label'],
            value=default_display,
            key=f"{key_prefix}_display_{ab['reagent_id']}"
        )

        # Add button
        if st.button(f"➕ {t['add_to_panel_button']}", key=f"{key_prefix}_add_{ab['reagent_id']}", type="secondary"):
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
                # Note: costs are NOT stored here - calculated dynamically from current stock
            }

    return None


def render_general_reagent_card(gr, key_prefix):
    """Render a general reagent selection card with consumption configuration"""
    # Get translations
    lang = st.session_state.get('language', 'en')
    t = get_lang_dict('panel_builder', lang)

    with st.expander(
        f"**{gr['reagent_name']}** ({gr['reagent_type'] or 'General'})",
        expanded=False
    ):
        # Display reagent details
        col1, col2 = st.columns(2)

        with col1:
            st.caption("**Name**")
            st.write(gr['reagent_name'])

            st.caption("**Type**")
            st.write(gr['reagent_type'] or "N/A")

            if gr['concentration']:
                st.caption("**Concentration**")
                st.write(gr['concentration'])

        with col2:
            st.caption("**Brand**")
            st.write(gr['brand'] or "N/A")

            st.caption("**Price**")
            if gr['price']:
                st.write(f"${gr['price']:.2f}")
            else:
                st.write("N/A")

            st.caption("**Available Units**")
            if gr['available_units'] and gr['available_units'] > 0:
                st.write(f"✓ {int(gr['available_units'])} units")
            else:
                st.error("⚠️ No stock available")

        # Select specific unit/batch
        st.markdown("---")
        st.caption("**Select Unit/Batch**")

        units = get_general_reagent_units(gr['reagent_id'])
        if units.empty:
            st.error("No available units for this reagent")
            return None

        unit_options = {}
        for _, unit in units.iterrows():
            vol_display = f"{unit['volume']:.0f} mL" if unit['volume'] is not None else "N/A mL"
            label = f"Lot {unit['lot_number']} - {vol_display} - Exp: {unit['expiration_date'][:10] if unit['expiration_date'] else 'N/A'}"
            unit_options[label] = unit['unit_id']

        selected_unit_label = st.selectbox(
            "Unit/Batch",
            options=list(unit_options.keys()),
            key=f"{key_prefix}_unit_{gr['reagent_id']}"
        )
        selected_unit_id = unit_options[selected_unit_label]
        selected_unit_data = units[units['unit_id'] == selected_unit_id].iloc[0]

        # Consumption configuration
        st.markdown("---")
        st.caption("**Consumption Configuration**")

        col1, col2 = st.columns(2)

        with col1:
            consumption_type = st.selectbox(
                "Consumption Type",
                options=["ml", "units"],
                help="ml for liquids (buffers, solutions), units for discrete items (tubes, filters)",
                key=f"{key_prefix}_type_{gr['reagent_id']}"
            )

        with col2:
            consumption_amount = st.number_input(
                f"Amount ({consumption_type})",
                min_value=0.0,
                max_value=1000.0,
                value=1.0 if consumption_type == "ml" else 1.0,
                step=0.1 if consumption_type == "ml" else 1.0,
                key=f"{key_prefix}_amount_{gr['reagent_id']}"
            )

        # Calculate cost per test
        if gr['price'] and consumption_amount > 0:
            if consumption_type == "ml":
                # Use unit volume or fallback to standard volume
                total_volume = selected_unit_data['volume'] if selected_unit_data['volume'] else gr.get('standard_volume')
                if total_volume and total_volume > 0:
                    unit_price_per_ml = gr['price'] / total_volume
                    cost_per_test = unit_price_per_ml * consumption_amount
                    volume_source = "unit" if selected_unit_data['volume'] else "standard"
                    st.info(f"💵 Cost per test: ${cost_per_test:.4f} (${unit_price_per_ml:.4f}/mL × {consumption_amount} mL)")
                    if volume_source == "standard":
                        st.caption(f"ℹ️ Using standard volume ({total_volume:.0f} mL) - unit volume not set")
                else:
                    cost_per_test = 0.0
                    st.warning("⚠️ Cannot calculate cost: volume is missing. Please set volume in General Reagents or on the unit.")
            else:  # units
                # Use standard_units as default or let user override
                default_units = gr.get('standard_units') if gr.get('standard_units') else 1.0
                total_units_in_batch = st.number_input(
                    "Total units in this batch",
                    min_value=1.0,
                    value=float(default_units),
                    help="e.g., if this is a box of 100 tubes, enter 100",
                    key=f"{key_prefix}_total_units_{gr['reagent_id']}"
                )
                unit_price_per_unit = gr['price'] / total_units_in_batch
                cost_per_test = unit_price_per_unit * consumption_amount
                st.info(f"💵 Cost per test: ${cost_per_test:.4f} (${unit_price_per_unit:.4f}/unit × {consumption_amount} units)")
        else:
            cost_per_test = 0.0
            total_units_in_batch = None
            st.caption("No cost information available")

        # Display name
        default_display = f"{gr['reagent_name']} ({consumption_amount} {consumption_type})"
        display_name = st.text_input(
            "Display Name",
            value=default_display,
            key=f"{key_prefix}_display_{gr['reagent_id']}"
        )

        # Add button
        if st.button(f"➕ Add to Panel", key=f"{key_prefix}_add_{gr['reagent_id']}", type="secondary"):
            # Determine volume/units to store (use fallback if needed)
            if consumption_type == "ml":
                volume_to_store = selected_unit_data['volume'] if selected_unit_data['volume'] else gr.get('standard_volume')
            else:
                volume_to_store = total_units_in_batch

            return {
                "general_reagent_id": gr['reagent_id'],
                "general_reagent_name": gr['reagent_name'],
                "general_reagent_unit_id": selected_unit_id,
                "consumption_type": consumption_type,
                "consumption_amount": consumption_amount,
                "unit_price": gr['price'],
                "total_volume_or_units": volume_to_store,
                "cost_per_test": cost_per_test,
                "display_name": display_name,
            }

    return None


def render_panel_composition(panel_reagents, panel_general_reagents):
    """Render the right-side panel composition view"""
    # Get translations
    lang = st.session_state.get('language', 'en')
    t = get_lang_dict('panel_builder', lang)

    st.markdown(f"### 📋 {t['panel_composition_header']}")

    if not panel_reagents and not panel_general_reagents:
        st.info(t['no_reagents_message'])
        return

    # Calculate total cost DYNAMICALLY from current stock
    total_cost = calculate_panel_cost(panel_reagents)
    if panel_general_reagents:
        for gr in panel_general_reagents:
            # General reagents still use old cost if set, but should be migrated
            total_cost += gr.get("cost_per_test", 0.0)

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t['antibodies_metric'], len(panel_reagents))
    with col2:
        st.metric(t['general_reagents_metric'], len(panel_general_reagents))
    with col3:
        st.metric(
            t['est_cost_metric'],
            f"${total_cost:.2f}",
            help=t['cost_help']
        )

    # Antibodies table
    if panel_reagents:
        st.markdown(f"#### {t['antibodies_table_header']}")

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
                "idx": i
            })

        df = pd.DataFrame(df_data)

        # Display table with selection for deletion
        selected = st.dataframe(
            df[["Channel", "Marker", "Vol (µL)", "Step", "Intra"]],
            use_container_width=True,
            selection_mode="multi-row",
            on_select="rerun",
            height=min(400, 35 + len(df) * 35)
        )

        # Delete button
        if selected and selected.get("selection", {}).get("rows"):
            if st.button(f"🗑️ {t['remove_selected_button']}", type="secondary"):
                # Remove selected indices (in reverse to avoid index issues)
                for idx in sorted(selected["selection"]["rows"], reverse=True):
                    actual_idx = df.iloc[idx]["idx"]
                    del panel_reagents[int(actual_idx)]
                st.rerun()

    # General reagents
    if panel_general_reagents:
        st.markdown(f"#### {t['general_reagents_header']}")

        gr_df_data = []
        for i, gr in enumerate(panel_general_reagents):
            gr_df_data.append({
                "Reagent": gr['display_name'],
                "Amount": f"{gr['consumption_amount']:.2f} {gr['consumption_type']}",
                "Cost": f"${gr['cost_per_test']:.4f}",
                "idx": i
            })

        gr_df = pd.DataFrame(gr_df_data)

        # Display table with selection for deletion
        sel_gr = st.dataframe(
            gr_df[["Reagent", "Amount", "Cost"]],
            use_container_width=True,
            selection_mode="multi-row",
            on_select="rerun",
            height=min(300, 35 + len(gr_df) * 35)
        )

        # Delete button for general reagents
        if sel_gr and sel_gr.get("selection", {}).get("rows"):
            if st.button("🗑️ Remove Selected General Reagents", type="secondary"):
                # Remove selected indices (in reverse to avoid index issues)
                for idx in sorted(sel_gr["selection"]["rows"], reverse=True):
                    actual_idx = gr_df.iloc[idx]["idx"]
                    del panel_general_reagents[int(actual_idx)]
                st.rerun()


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

    # Load panel general reagents
    panel_general_reagents = query_panels("""
        SELECT
            pgr.general_reagent_id,
            gr.name as general_reagent_name,
            pgr.general_reagent_unit_id,
            pgr.consumption_type,
            pgr.consumption_amount,
            pgr.unit_price,
            pgr.total_volume_or_units,
            pgr.cost_per_test,
            pgr.display_name
        FROM panel_general_reagents pgr
        JOIN general_reagents gr ON gr.id = pgr.general_reagent_id
        WHERE pgr.panel_id = ?
    """, (panel_id,))

    # Convert to list of dicts
    general_reagents_list = panel_general_reagents.to_dict('records') if not panel_general_reagents.empty else []

    return {
        "panel": panel_data,
        "reagents": reagents_list,
        "general_reagents": general_reagents_list
    }


def save_panel_updates(panel_id, panel_reagents, panel_general_reagents=None, sample_type=None, sample_volume=None,
                      washed_sample=None, description=None, clinical_indication=None):
    """Update an existing panel's reagents and metadata"""
    try:
        # Delete existing panel reagents
        query_panels("DELETE FROM panel_reagents WHERE panel_id = ?", (panel_id,), commit=True)

        # Delete existing panel general reagents
        query_panels("DELETE FROM panel_general_reagents WHERE panel_id = ?", (panel_id,), commit=True)

        # Insert updated reagents
        now = datetime.utcnow().isoformat()
        for reagent in panel_reagents:
            query_panels("""
                INSERT INTO panel_reagents (
                    id, panel_id, reagent_id,
                    optical_channel_id, channel_display_name,
                    volume_used,
                    is_intracellular, is_surface, staining_step,
                    display_name,
                    assigned_at, added_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                panel_id,
                reagent["reagent_id"],
                reagent["optical_channel_id"],
                reagent["channel_display_name"],
                reagent["volume_per_test"],
                reagent["is_intracellular"],
                reagent["is_surface"],
                reagent["staining_step"],
                reagent["display_name"],
                now,
                "system"
            ), commit=True)

        # Insert updated general reagents
        if panel_general_reagents:
            for gr in panel_general_reagents:
                query_panels("""
                    INSERT INTO panel_general_reagents (
                        id, panel_id, general_reagent_id, general_reagent_unit_id,
                        consumption_type, consumption_amount,
                        unit_price, total_volume_or_units, cost_per_test,
                        display_name, assigned_at, added_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    panel_id,
                    gr["general_reagent_id"],
                    gr.get("general_reagent_unit_id"),
                    gr["consumption_type"],
                    gr["consumption_amount"],
                    gr.get("unit_price"),
                    gr.get("total_volume_or_units"),
                    gr.get("cost_per_test", 0.0),
                    gr["display_name"],
                    now,
                    "system"
                ), commit=True)

        # Update panel metadata
        update_fields = ["updated_at = ?"]
        update_values = [now]

        if sample_type is not None:
            update_fields.append("sample_type = ?")
            update_values.append(sample_type)

        if sample_volume is not None:
            update_fields.append("sample_volume = ?")
            update_values.append(sample_volume)

        if washed_sample is not None:
            update_fields.append("washed_sample = ?")
            update_values.append(1 if washed_sample else 0)

        if description is not None:
            update_fields.append("description = ?")
            update_values.append(description)

        if clinical_indication is not None:
            update_fields.append("clinical_indication = ?")
            update_values.append(clinical_indication)

        update_values.append(panel_id)

        query_panels(
            f"UPDATE panels SET {', '.join(update_fields)} WHERE id = ?",
            tuple(update_values),
            commit=True
        )

        return True
    except Exception as e:
        st.error(f"Error saving panel updates: {e}")
        return False


def create_panel():
    """Main panel builder interface - split view"""

    # Get language from session state
    lang = st.session_state.get('language', 'en')
    t = get_lang_dict('panel_builder', lang)

    st.title(f"🧬 {t['title']}")
    st.caption(t['subtitle'])

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
            st.session_state["panel_draft_general_reagents"] = panel_data.get("general_reagents", [])
            st.info(f"✏️ {t['editing_mode_info']} {panel_data['panel']['name']}")

    # ============================================================
    # PANEL METADATA
    # ============================================================
    with st.expander(f"📝 {t['panel_metadata_header']}", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            panel_name = st.text_input(t['panel_name_label'], placeholder=t['panel_name_placeholder'],
                                       disabled=editing_mode)
            if editing_mode:
                st.caption(t['panel_name_locked'])

            clinical_indication = st.text_input(
                t['clinical_indication_label'],
                placeholder=t['clinical_indication_placeholder']
            )
            sample_type = st.selectbox(
                t['sample_type_label'],
                [t['whole_blood'], t['bone_marrow'], t['csf'], t['tissue'], t['other']],
                index=0
            )

        with col2:
            panel_version = st.text_input(t['panel_version_label'], value="1.0.0", disabled=True,
                                        help=t['version_help'])
            sample_volume = st.number_input(
                t['sample_volume_label'],
                min_value=0.0,
                max_value=500.0,
                value=50.0,
                step=5.0
            )
            washed_sample = st.checkbox(t['prewashed_sample_label'], value=False)

        description = st.text_area(
            t['description_label'],
            height=80,
            placeholder=t['description_placeholder']
        )

    # ============================================================
    # PANEL CLASSIFICATION (Areas & Disease Categories)
    # ============================================================
    st.markdown("---")
    st.markdown(f"### 📁 {t['classification_header']}")

    from utils.categories import get_all_areas, get_all_disease_categories

    # Get available areas and categories
    areas_df = get_all_areas()
    if areas_df is None or areas_df.empty:
        st.warning(t['no_clinical_areas_warning'])
        selected_area_id = None
        selected_disease_category_id = None
    else:
        col1, col2 = st.columns(2)

        with col1:
            area_options = ["(None)"] + list(areas_df["name"])
            area_ids = [None] + list(areas_df["id"])

            selected_area_name = st.selectbox(
                t['clinical_area_label'],
                options=area_options,
                help=t['clinical_area_help']
            )
            selected_area_id = area_ids[area_options.index(selected_area_name)]

        with col2:
            # Get disease categories for selected area
            if selected_area_id:
                categories_df = get_all_disease_categories(selected_area_id)
            else:
                categories_df = pd.DataFrame()

            if categories_df is not None and not categories_df.empty:
                category_options = ["(None)"] + list(categories_df["name"])
                category_ids = [None] + list(categories_df["id"])

                selected_disease_category_name = st.selectbox(
                    t['disease_category_label'],
                    options=category_options,
                    help=t['disease_category_help']
                )
                selected_disease_category_id = category_ids[category_options.index(selected_disease_category_name)]
            else:
                st.selectbox(t['disease_category_label'], options=[t['no_categories_message']], disabled=True)
                selected_disease_category_id = None

    # ============================================================
    # CYTOMETER SELECTION (Default: CytoFLEX)
    # ============================================================
    st.markdown("---")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"### 🔬 {t['cytometer_config_header']}")

    # Get default cytometer
    default_cyt_id, default_cyt_name = get_default_cytometer()

    if not default_cyt_id:
        st.error(f"⚠️ {t['no_cytometer_error']}")
        return

    # Get all cytometers
    all_cytometers = query_panels("SELECT id, name FROM cytometers ORDER BY is_default DESC, name")
    cyt_map = dict(zip(all_cytometers["name"], all_cytometers["id"]))

    with col2:
        selected_cyt_name = st.selectbox(
            t['select_cytometer_label'],
            options=list(cyt_map.keys()),
            index=list(cyt_map.keys()).index(default_cyt_name) if default_cyt_name in cyt_map else 0,
            help=t['cytometer_help']
        )
        cytometer_id = cyt_map[selected_cyt_name]

    st.info(f"✓ {t['cytometer_info']} **{selected_cyt_name}** — {t['all_channels_configured']}")

    # ============================================================
    # PROTOCOLS SELECTION (Simplified - use existing columns)
    # ============================================================
    with st.expander(f"📋 {t['protocols_header']}", expanded=False):
        col1, col2, col3 = st.columns(3)

        # Acquisition protocol (use name-based approach)
        with col1:
            st.caption(f"**{t['acquisition_protocol_section']}**")
            acquisition_protocol_name = st.text_input(
                t['protocol_name_label'],
                value=t['acquisition_protocol_default'],
                key="acq_protocol_name",
                help=t['acquisition_protocol_help']
            )
            acquisition_protocol_status = st.selectbox(
                t['protocol_status_label'],
                ["draft", "validated", "archived"],
                index=1,
                key="acq_protocol_status"
            )

        # Compensation protocol
        with col2:
            st.caption(f"**{t['compensation_protocol_section']}**")
            compensation_protocol_name = st.text_input(
                t['protocol_name_label'],
                value=t['compensation_protocol_default'],
                key="comp_protocol_name",
                help=t['compensation_protocol_help']
            )
            compensation_protocol_status = st.selectbox(
                t['protocol_status_label'],
                ["draft", "validated", "archived"],
                index=1,
                key="comp_protocol_status"
            )

        # Analysis protocol
        with col3:
            st.caption(f"**{t['analysis_protocol_section']}**")
            analysis_protocol_name = st.text_input(
                t['protocol_name_label'],
                value=t['analysis_protocol_default'],
                key="analysis_protocol_name",
                help=t['analysis_protocol_help']
            )
            analysis_protocol_status = st.selectbox(
                t['protocol_status_label'],
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
    # LEFT PANEL: REAGENT SELECTION (Antibodies + General Reagents)
    # ============================================================
    with left_col:
        st.markdown(f"### 🔍 Reagent Selection")

        # Tabs for Antibodies and General Reagents
        tab1, tab2 = st.tabs(["🧬 Antibodies", "🧪 General Reagents"])

        # ============================================================
        # TAB 1: ANTIBODY SELECTION
        # ============================================================
        with tab1:
            # Search only (removed surface/intracellular filter)
            search_query = st.text_input(
                t['search_label'],
                placeholder=t['search_placeholder'],
                key="ab_search"
            )

            # Load reagents
            reagents_df = get_reagents_with_details()

            if reagents_df.empty:
                st.warning(t['no_reagents_warning'])
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
                st.caption(t['showing_count'].format(count=len(reagents_df)))

                # Render antibody cards (limit to 20 for performance)
                for _, ab in reagents_df.head(20).iterrows():
                    result = render_antibody_card(ab, cytometer_id, key_prefix="builder", t=t)
                    if result:
                        # Check for duplicate channel
                        existing_channels = [r['optical_channel_id'] for r in st.session_state["panel_draft_reagents"]]
                        if result['optical_channel_id'] in existing_channels:
                            st.warning(t['channel_in_use_warning'].format(name=result['channel_display_name']))

                        st.session_state["panel_draft_reagents"].append(result)
                        st.success(f"✓ {t['added_success'].format(name=result['display_name'])}")
                        st.rerun()

                if len(reagents_df) > 20:
                    st.info(t['showing_first_20'].format(count=len(reagents_df)))

        # ============================================================
        # TAB 2: GENERAL REAGENTS SELECTION
        # ============================================================
        with tab2:
            st.caption("Add buffers, solutions, and consumables used in this panel")

            # Search for general reagents
            gr_search_query = st.text_input(
                "Search",
                placeholder="PBS, lysing buffer, tubes...",
                key="gr_search"
            )

            # Load general reagents
            general_reagents_df = get_general_reagents_with_units()

            if general_reagents_df.empty:
                st.warning("No general reagents available. Add them in the General Reagents section first.")
            else:
                # Apply search filter
                if gr_search_query:
                    mask = (
                        general_reagents_df["reagent_name"].str.contains(gr_search_query, case=False, na=False) |
                        general_reagents_df["reagent_type"].str.contains(gr_search_query, case=False, na=False)
                    )
                    general_reagents_df = general_reagents_df[mask]

                # Show count
                st.caption(f"Showing {len(general_reagents_df)} general reagents")

                # Render general reagent cards (limit to 20 for performance)
                for _, gr in general_reagents_df.head(20).iterrows():
                    result = render_general_reagent_card(gr, key_prefix="builder_gr")
                    if result:
                        st.session_state["panel_draft_general_reagents"].append(result)
                        st.success(f"✓ Added {result['display_name']}")
                        st.rerun()

                if len(general_reagents_df) > 20:
                    st.info(f"Showing first 20 of {len(general_reagents_df)} reagents. Use search to narrow down.")

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
        st.caption(t['save_requirements'])

    with col2:
        if editing_mode and st.button(f"❌ {t['cancel_edit_button']}", use_container_width=True):
            st.session_state["editing_panel_id"] = None
            st.session_state["panel_draft_reagents"] = []
            st.session_state["panel_draft_general_reagents"] = []
            st.success(t['cancelled_editing'])
            st.rerun()

    with col3:
        if st.button(f"🗑️ {t['clear_panel_button']}", type="secondary", use_container_width=True):
            st.session_state["panel_draft_reagents"] = []
            st.session_state["panel_draft_general_reagents"] = []
            st.success(t['panel_cleared_message'])
            st.rerun()

    with col4:
        save_button_label = f"💾 {t['update_button']}" if editing_mode else f"💾 {t['save_button']}"
        save_button = st.button(save_button_label, type="primary", use_container_width=True)

    if save_button:
        # Validation
        errors = []
        if not editing_mode:
            if not panel_name or not panel_name.strip():
                errors.append(t['validation_panel_name_required'])
        if not sample_type:
            errors.append(t['validation_sample_type_required'])
        if sample_volume <= 0:
            errors.append(t['validation_sample_volume_required'])
        if not st.session_state["panel_draft_reagents"]:
            errors.append(t['validation_reagents_required'])

        if errors:
            for error in errors:
                st.error(f"❌ {error}")
            return

        # Save or update panel
        try:
            if editing_mode:
                # UPDATE existing panel
                panel_id = st.session_state["editing_panel_id"]

                if save_panel_updates(
                    panel_id,
                    st.session_state["panel_draft_reagents"],
                    panel_general_reagents=st.session_state["panel_draft_general_reagents"],
                    sample_type=sample_type,
                    sample_volume=sample_volume,
                    washed_sample=washed_sample,
                    description=description,
                    clinical_indication=clinical_indication
                ):
                    # Update panel classification (area + disease category)
                    if selected_area_id:
                        from utils.categories import set_panel_classification
                        set_panel_classification(panel_id, selected_area_id, selected_disease_category_id, is_primary=True)

                    st.success(f"✅ {t['panel_updated_success']}")

                    # Clear editing state
                    st.session_state["editing_panel_id"] = None
                    st.session_state["panel_draft_reagents"] = []
                    st.session_state["panel_draft_general_reagents"] = []
                    st.balloons()
                else:
                    st.error(t['failed_update'])

            else:
                # CREATE new panel
                panel_id = str(uuid.uuid4())
                now = datetime.utcnow().isoformat()

                # Calculate total cost (antibodies + general reagents)
                total_cost = calculate_panel_cost(st.session_state["panel_draft_reagents"])
                for gr in st.session_state["panel_draft_general_reagents"]:
                    total_cost += gr.get("cost_per_test", 0.0)

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
                            volume_used,
                            is_intracellular, is_surface, staining_step,
                            display_name,
                            assigned_at, added_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        panel_id,
                        reagent["reagent_id"],
                        reagent["optical_channel_id"],
                        reagent["channel_display_name"],
                        reagent["volume_per_test"],
                        reagent["is_intracellular"],
                        reagent["is_surface"],
                        reagent["staining_step"],
                        reagent["display_name"],
                        now,
                        "system"
                    ), commit=True)

                # Insert panel general reagents
                for gr in st.session_state["panel_draft_general_reagents"]:
                    query_panels("""
                        INSERT INTO panel_general_reagents (
                            id, panel_id, general_reagent_id, general_reagent_unit_id,
                            consumption_type, consumption_amount,
                            unit_price, total_volume_or_units, cost_per_test,
                            display_name, assigned_at, added_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        panel_id,
                        gr["general_reagent_id"],
                        gr.get("general_reagent_unit_id"),
                        gr["consumption_type"],
                        gr["consumption_amount"],
                        gr.get("unit_price"),
                        gr.get("total_volume_or_units"),
                        gr.get("cost_per_test", 0.0),
                        gr["display_name"],
                        now,
                        "system"
                    ), commit=True)

                # Set panel classification (area + disease category)
                if selected_area_id:
                    from utils.categories import set_panel_classification
                    set_panel_classification(panel_id, selected_area_id, selected_disease_category_id, is_primary=True)

                st.success(f"✅ {t['panel_created_success'].format(name=panel_name)}")
                st.info(f"{t['panel_id_info']} {panel_id}")
                st.info(t['est_cost_info'].format(cost=f"{total_cost:.2f}"))

                # Clear draft
                st.session_state["panel_draft_reagents"] = []
                st.session_state["panel_draft_general_reagents"] = []

                # Wait a moment before rerun
                st.balloons()

        except Exception as e:
            st.error(f"❌ {t['save_error']} {e}")
            import traceback
            st.code(traceback.format_exc())
