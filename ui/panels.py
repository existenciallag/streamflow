# ui/panels.py
"""
Panels Viewer & CRUD - Clinical Grade Panel Management
Shows panels with semantic names, allows editing, deletion, and content modification
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from ui.crud_panels import query_panels
from utils.pricing import calculate_panel_cost_current


def delete_panel(panel_id):
    """Delete a panel and ALL related records with explicit transaction handling"""
    import sqlite3
    from models.loaders import DB_PATH

    try:
        # Use explicit transaction for deletion
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
        cursor = conn.cursor()

        # Verify panel exists
        cursor.execute("SELECT name FROM panels WHERE id = ?", (panel_id,))
        panel = cursor.fetchone()
        if not panel:
            conn.close()
            return False, "Panel not found"

        panel_name = panel[0]

        # Delete ALL related records manually (to be absolutely sure)
        # Order matters: children first, parent last

        # 1. Delete panel_reagents
        cursor.execute("DELETE FROM panel_reagents WHERE panel_id = ?", (panel_id,))
        reagents_deleted = cursor.rowcount

        # 2. Delete panel_general_reagents (if exists)
        cursor.execute("DELETE FROM panel_general_reagents WHERE panel_id = ?", (panel_id,))

        # 3. Delete panel_classifications
        cursor.execute("DELETE FROM panel_classifications WHERE panel_id = ?", (panel_id,))

        # 4. Delete panel_versions
        cursor.execute("DELETE FROM panel_versions WHERE panel_id = ?", (panel_id,))

        # 5. Delete panel_status_history
        cursor.execute("DELETE FROM panel_status_history WHERE panel_id = ?", (panel_id,))

        # 6. Delete case_panels (if any - these link to clinical cases)
        cursor.execute("DELETE FROM case_panels WHERE panel_id = ?", (panel_id,))

        # 7. Delete panel_usage_log (if any - economic tracking)
        cursor.execute("DELETE FROM panel_usage_log WHERE panel_id = ?", (panel_id,))

        # 8. Finally, delete the panel itself
        cursor.execute("DELETE FROM panels WHERE id = ?", (panel_id,))
        panel_deleted = cursor.rowcount

        # Commit transaction
        conn.commit()

        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM panels WHERE id = ?", (panel_id,))
        verify_count = cursor.fetchone()[0]

        conn.close()

        if verify_count == 0:
            return True, f"Panel '{panel_name}' deleted successfully ({reagents_deleted} reagents removed)"
        else:
            return False, "Panel deletion was not committed to database"

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False, f"Error deleting panel: {e}"


def update_panel_metadata(panel_id, name, description, sample_type, sample_volume, washed_sample,
                          clinical_indication):
    """Update panel metadata (protocols can only be edited in Panel Builder)"""
    try:
        query_panels("""
            UPDATE panels SET
                name = ?,
                description = ?,
                sample_type = ?,
                sample_volume = ?,
                washed_sample = ?,
                clinical_indication = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            name, description, sample_type, sample_volume, washed_sample,
            clinical_indication,
            datetime.utcnow().isoformat(), panel_id
        ), commit=True)

        return True, "Panel updated successfully"
    except Exception as e:
        return False, f"Error updating panel: {e}"


def remove_reagent_from_panel(panel_reagent_id):
    """Remove a reagent from a panel"""
    try:
        query_panels("DELETE FROM panel_reagents WHERE id = ?", (panel_reagent_id,), commit=True)
        return True, "Reagent removed from panel"
    except Exception as e:
        return False, f"Error removing reagent: {e}"


def show_panels(panels_df=None):
    """Main panels viewer with CRUD operations"""

    st.subheader("Panels")

    # Initialize session state
    if "panel_mode" not in st.session_state:
        st.session_state["panel_mode"] = "view"
    if "panel_selected_id" not in st.session_state:
        st.session_state["panel_selected_id"] = None

    # ALWAYS load panels fresh from database to ensure updates are reflected
    # This ensures the list updates after create/delete operations
    panels = query_panels("""
        SELECT
            p.id,
            p.name,
            p.version,
            p.status,
            p.sample_type,
            p.sample_volume,
            p.washed_sample,
            p.clinical_indication,
            p.estimated_cost_per_test,
            c.name as cytometer_name,
            p.created_at
        FROM panels p
        LEFT JOIN cytometers c ON c.id = p.cytometer_id
        ORDER BY p.created_at DESC
    """)

    if panels is None or panels.empty:
        st.info("No panels found. Create one in Panel Builder.")
        return

    # Two-column layout
    col_list, col_detail = st.columns([1, 3])

    # =============================================================
    # LEFT PANEL: PANEL LIST
    # =============================================================
    with col_list:
        search = st.text_input("Search panels", key="panel_search")

        df = panels.copy()
        if search:
            df = df[
                df["name"].astype(str).str.lower().str.contains(search.lower(), na=False)
            ]

        # Display panel list with semantic info
        display_df = df[["name", "version", "status"]].copy()
        display_df["status"] = display_df["status"].fillna("draft")

        selected = st.dataframe(
            display_df,
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun",
            height=500,
            hide_index=True
        )

    # =============================================================
    # RIGHT PANEL: PANEL DETAILS & CRUD
    # =============================================================
    with col_detail:
        # Get selected panel
        panel_id = None
        if selected and selected.get("selection", {}).get("rows"):
            panel_id = df.iloc[selected["selection"]["rows"][0]]["id"]
            st.session_state["panel_selected_id"] = panel_id

        if not panel_id:
            st.info("👈 Select a panel to view details")
            return

        # Load full panel data - validate panel still exists
        panel_match = panels[panels["id"] == panel_id]
        if panel_match.empty:
            st.error("Selected panel no longer exists")
            st.session_state["panel_selected_id"] = None
            st.session_state["panel_mode"] = "view"
            st.rerun()
            return

        panel = panel_match.iloc[0]

        # =============================================================
        # VIEW MODE
        # =============================================================
        if st.session_state["panel_mode"] == "view":
            # Header with action buttons
            col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1, 1, 1])

            with col_h1:
                st.markdown(f"## {panel['name']}")
                status_color = {
                    "draft": "🟡",
                    "validated": "🟢",
                    "active": "🟢",
                    "deprecated": "🟠",
                    "archived": "🔴"
                }.get(panel.get('status', 'draft').lower(), "⚪")
                st.caption(f"{status_color} {panel.get('status', 'draft').upper()} · v{panel.get('version', '1.0.0')}")

            with col_h2:
                if st.button("✏️ Edit", use_container_width=True):
                    st.session_state["panel_mode"] = "edit"
                    st.rerun()

            with col_h3:
                if st.button("Modify", use_container_width=True, help="Modify panel contents"):
                    st.session_state["panel_mode"] = "modify"
                    st.rerun()

            with col_h4:
                if st.button("Delete", use_container_width=True, type="secondary"):
                    st.session_state["panel_mode"] = "delete_confirm"
                    st.rerun()

            # Metadata display
            st.markdown("---")
            st.markdown("### Panel Information")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Sample Type", panel.get("sample_type") or "—")
            with col2:
                st.metric("Sample Volume", f"{panel.get('sample_volume') or '—'} µL")
            with col3:
                # Calculate cost dynamically from current stock
                cost_result = calculate_panel_cost_current(panel_id, strategy='cheapest')

                # Handle error cases (e.g., panel deleted, calculation failed)
                if 'error' in cost_result:
                    cost_display = "—"
                    help_text = f"Error: {cost_result.get('error', 'Unknown error')}"
                else:
                    cost_display = f"${cost_result.get('total_cost', 0.0):.2f}"
                    if not cost_result.get('is_complete', True):
                        cost_display += " ⚠️"
                    help_text = "Calculated dynamically from current cheapest stock. ⚠️ = incomplete (some reagents unavailable)"

                st.metric(
                    "Est. Cost/Test",
                    cost_display,
                    help=help_text
                )

            col4, col5, col6 = st.columns(3)
            with col4:
                st.metric("Cytometer", panel.get("cytometer_name") or "—")
            with col5:
                st.metric("Washed Sample", "Yes" if panel.get("washed_sample") else "No")
            with col6:
                st.metric("Created", panel.get("created_at", "—")[:10] if panel.get("created_at") else "—")

            # Display categories
            from utils.categories import get_primary_area, get_primary_disease_category
            area_id, area_name = get_primary_area(panel_id)
            disease_id, disease_name = get_primary_disease_category(panel_id)

            if area_name or disease_name:
                st.markdown("---")
                col_cat1, col_cat2 = st.columns(2)
                with col_cat1:
                    st.metric("Clinical Area", area_name or "—")
                with col_cat2:
                    st.metric("Disease Category", disease_name or "—")

            if panel.get("clinical_indication"):
                st.markdown("**Clinical Indication:**")
                st.info(panel["clinical_indication"])

            # Protocols
            st.markdown("---")
            st.markdown("### 📑 Protocols")

            # Load full panel data for protocols - check if exists first
            full_panel_query = query_panels("SELECT * FROM panels WHERE id = ?", (panel_id,))
            if full_panel_query.empty:
                st.error("Panel no longer exists (may have been deleted)")
                st.session_state["panel_mode"] = "view"
                st.session_state["panel_selected_id"] = None
                st.rerun()
                return

            full_panel = full_panel_query.iloc[0]

            p1, p2, p3 = st.columns(3)
            with p1:
                st.caption("**Acquisition**")
                st.write(full_panel.get("acquisition_protocol_name") or "—")
                st.caption(f"Status: {full_panel.get('acquisition_protocol_status') or '—'}")

            with p2:
                st.caption("**Compensation**")
                st.write(full_panel.get("compensation_name") or "—")
                st.caption(f"Status: {full_panel.get('compensation_status') or '—'}")

            with p3:
                st.caption("**Analysis**")
                st.write(full_panel.get("analysis_protocol_name") or "—")
                st.caption(f"Status: {full_panel.get('analysis_protocol_status') or '—'}")

            # Reagents table with SEMANTIC NAMES ONLY
            st.markdown("---")
            st.markdown("### Panel Composition")

            panel_reagents = query_panels("""
                SELECT
                    pr.id as panel_reagent_id,
                    r.name as antibody,
                    r.target_antigen,
                    r.clone,
                    f.name as fluorochrome,
                    b.name as brand,
                    pr.channel_display_name as channel,
                    pr.volume_used,
                    pr.staining_step,
                    pr.is_intracellular,
                    pr.display_name
                FROM panel_reagents pr
                JOIN reagents r ON r.id = pr.reagent_id
                LEFT JOIN fluorochromes f ON f.id = r.fluorochrome
                LEFT JOIN brands b ON b.id = r.brand_id
                WHERE pr.panel_id = ?
                ORDER BY pr.channel_display_name, pr.staining_step
            """, (panel_id,))

            if panel_reagents.empty:
                st.info("This panel has no reagents assigned.")
            else:
                # Calculate cost to get per-reagent breakdown
                cost_result = calculate_panel_cost_current(panel_id, strategy='cheapest')

                # Create cost lookup from breakdown
                cost_lookup = {}
                if 'breakdown' in cost_result:
                    for item in cost_result['breakdown']:
                        reagent_name = item.get('reagent', '')
                        cost_lookup[reagent_name] = item.get('cost', 0.0)

                # Format for display
                display_reagents = panel_reagents[[
                    "channel", "display_name", "antibody", "fluorochrome", "clone",
                    "brand", "volume_used", "staining_step", "is_intracellular"
                ]].copy()

                # Add cost per reagent
                display_reagents["cost"] = display_reagents["antibody"].apply(
                    lambda x: cost_lookup.get(x, 0.0)
                )
                display_reagents["cost_display"] = display_reagents["cost"].apply(
                    lambda x: f"${x:.2f}" if x is not None and x > 0 else "N/A"
                )

                display_reagents["is_intracellular"] = display_reagents["is_intracellular"].apply(
                    lambda x: "Yes" if x else ""
                )

                display_reagents = display_reagents.rename(columns={
                    "channel": "Channel",
                    "display_name": "Marker",
                    "fluorochrome": "Fluorochrome",
                    "clone": "Clone",
                    "brand": "Brand",
                    "volume_used": "Vol (µL)",
                    "staining_step": "Step",
                    "is_intracellular": "Intra",
                    "cost_display": "Cost"
                })

                # Drop temporary columns
                display_reagents = display_reagents.drop(columns=["antibody", "cost"])

                st.dataframe(display_reagents, use_container_width=True, hide_index=True)

                # Display total cost summary
                # Handle error cases
                if 'error' in cost_result:
                    st.warning(f"Could not calculate cost: {cost_result.get('error', 'Unknown error')}")
                else:
                    cost_status = "[Complete]" if cost_result.get('is_complete', True) else "[Incomplete]"
                    st.markdown(f"### {cost_status} Estimated Cost: **${cost_result.get('total_cost', 0.0):.2f}** per test")
                    st.caption("Calculated from current cheapest stock. Cost updates when reagent prices change.")

            # Version and Status History
            st.markdown("---")
            col_h1, col_h2 = st.columns(2)

            with col_h1:
                # Version History
                version_history = query_panels("""
                    SELECT version, previous_version, status, changes_summary, created_at
                    FROM panel_versions
                    WHERE panel_id = ?
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (panel_id,))

                if version_history is not None and not version_history.empty:
                    with st.expander(f"Version History ({len(version_history)} versions)", expanded=False):
                        for _, ver in version_history.iterrows():
                            st.caption(f"**v{ver['version']}** • {ver['created_at'][:10]}")
                            if ver['previous_version']:
                                st.text(f"  From: v{ver['previous_version']}")
                            if ver['changes_summary']:
                                st.text(f"  {ver['changes_summary']}")
                            st.markdown("---")
                else:
                    st.caption("No version history available")

            with col_h2:
                # Status History
                status_history = query_panels("""
                    SELECT from_status, to_status, reason, changed_at
                    FROM panel_status_history
                    WHERE panel_id = ?
                    ORDER BY changed_at DESC
                    LIMIT 10
                """, (panel_id,))

                if status_history is not None and not status_history.empty:
                    with st.expander(f"Status History ({len(status_history)} changes)", expanded=False):
                        for _, status in status_history.iterrows():
                            from_st = status['from_status'] or 'None'
                            st.caption(f"**{from_st} → {status['to_status']}** • {status['changed_at'][:10]}")
                            if status['reason']:
                                st.text(f"  {status['reason']}")
                            st.markdown("---")
                else:
                    st.caption("No status history available")

        # =============================================================
        # EDIT MODE
        # =============================================================
        elif st.session_state["panel_mode"] == "edit":
            st.markdown(f"## ✏️ Edit Panel: {panel['name']}")

            # Load full panel data - check if exists first
            full_panel_query = query_panels("SELECT * FROM panels WHERE id = ?", (panel_id,))
            if full_panel_query.empty:
                st.error("Panel no longer exists (may have been deleted)")
                st.session_state["panel_mode"] = "view"
                st.session_state["panel_selected_id"] = None
                st.rerun()
                return

            full_panel = full_panel_query.iloc[0]

            with st.form("edit_panel_form"):
                col1, col2 = st.columns(2)

                with col1:
                    new_name = st.text_input("Panel Name *", value=full_panel['name'])
                    new_clinical_indication = st.text_input(
                        "Clinical Indication",
                        value=full_panel.get('clinical_indication') or ""
                    )
                    new_sample_type = st.selectbox(
                        "Sample Type *",
                        ["Whole Blood", "Bone Marrow", "CSF", "Tissue", "Other"],
                        index=["Whole Blood", "Bone Marrow", "CSF", "Tissue", "Other"].index(full_panel.get('sample_type', 'Whole Blood'))
                        if full_panel.get('sample_type') in ["Whole Blood", "Bone Marrow", "CSF", "Tissue", "Other"] else 0
                    )

                with col2:
                    new_sample_volume = st.number_input(
                        "Sample Volume (µL) *",
                        min_value=0.0,
                        value=float(full_panel.get('sample_volume') or 50.0)
                    )
                    new_washed_sample = st.checkbox(
                        "Pre-washed Sample",
                        value=bool(full_panel.get('washed_sample'))
                    )

                new_description = st.text_area(
                    "Description",
                    value=full_panel.get('description') or "",
                    height=80
                )

                st.markdown("**Protocols** (read-only)")
                st.info("Protocols can only be edited in Panel Builder to maintain single source of truth")

                p1, p2, p3 = st.columns(3)

                with p1:
                    st.caption("Acquisition")
                    st.text(f"{full_panel.get('acquisition_protocol_name') or '—'}")
                    st.caption(f"Status: {full_panel.get('acquisition_protocol_status', 'draft')}")

                with p2:
                    st.caption("Compensation")
                    st.text(f"{full_panel.get('compensation_name') or '—'}")
                    st.caption(f"Status: {full_panel.get('compensation_status', 'draft')}")

                with p3:
                    st.caption("Analysis")
                    st.text(f"{full_panel.get('analysis_protocol_name') or '—'}")
                    st.caption(f"Status: {full_panel.get('analysis_protocol_status', 'draft')}")

                # Version and Status Management
                st.markdown("---")
                st.markdown("**Version & Status Management**")

                v_col1, v_col2 = st.columns(2)

                with v_col1:
                    st.caption(f"Current Version: v{full_panel.get('version', '1.0.0')}")
                    version_action = st.selectbox(
                        "Version Update",
                        ["Keep current", "Patch (0.0.X) - Bug fixes", "Minor (0.X.0) - New features", "Major (X.0.0) - Breaking changes"],
                        key="version_action"
                    )
                    version_notes = None
                    if version_action != "Keep current":
                        version_notes = st.text_area(
                            "Version Notes",
                            placeholder="Describe what changed in this version...",
                            key="version_notes",
                            height=60
                        )

                with v_col2:
                    current_status = full_panel.get('status', 'draft')
                    st.caption(f"Current Status: {current_status.upper()}")

                    # Define valid status transitions
                    status_transitions = {
                        'draft': ['draft', 'validated', 'archived'],
                        'validated': ['validated', 'active', 'draft', 'archived'],
                        'active': ['active', 'deprecated', 'archived'],
                        'deprecated': ['deprecated', 'archived', 'active'],
                        'archived': ['archived']
                    }

                    valid_statuses = status_transitions.get(current_status, ['draft', 'validated', 'active', 'deprecated', 'archived'])
                    new_status = st.selectbox(
                        "Status",
                        valid_statuses,
                        index=valid_statuses.index(current_status) if current_status in valid_statuses else 0,
                        key="new_status"
                    )

                    status_reason = None
                    if new_status != current_status:
                        status_reason = st.text_input(
                            "Reason for status change",
                            placeholder="Why is the status changing?",
                            key="status_reason"
                        )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    save_clicked = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
                with col_btn2:
                    cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)

            if save_clicked:
                # Handle version update
                from datetime import datetime
                import uuid as uuid_module

                current_version = full_panel.get('version', '1.0.0')
                new_version = current_version

                if version_action != "Keep current":
                    # Parse current version
                    try:
                        major, minor, patch = map(int, current_version.split('.'))

                        if "Patch" in version_action:
                            patch += 1
                        elif "Minor" in version_action:
                            minor += 1
                            patch = 0
                        elif "Major" in version_action:
                            major += 1
                            minor = 0
                            patch = 0

                        new_version = f"{major}.{minor}.{patch}"

                        # Record version history
                        query_panels("""
                            INSERT INTO panel_versions (id, panel_id, version, previous_version, status, changes_summary, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(uuid_module.uuid4()),
                            panel_id,
                            new_version,
                            current_version,
                            new_status,
                            version_notes or '',
                            datetime.utcnow().isoformat()
                        ), commit=True)

                        # Update panel version
                        query_panels("UPDATE panels SET version = ?, updated_at = ? WHERE id = ?",
                                   (new_version, datetime.utcnow().isoformat(), panel_id), commit=True)

                    except ValueError:
                        st.error("Invalid version format")

                # Handle status change
                if new_status != current_status:
                    query_panels("""
                        INSERT INTO panel_status_history (id, panel_id, from_status, to_status, reason, changed_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid_module.uuid4()),
                        panel_id,
                        current_status,
                        new_status,
                        status_reason or '',
                        datetime.utcnow().isoformat()
                    ), commit=True)

                    # Update panel status
                    query_panels("UPDATE panels SET status = ?, updated_at = ? WHERE id = ?",
                               (new_status, datetime.utcnow().isoformat(), panel_id), commit=True)

                # Update metadata (protocols are not editable here)
                success, message = update_panel_metadata(
                    panel_id, new_name, new_description, new_sample_type, new_sample_volume,
                    1 if new_washed_sample else 0, new_clinical_indication
                )

                if success:
                    if new_version != current_version:
                        st.success(f"✅ Panel updated to version {new_version}")
                    if new_status != current_status:
                        st.success(f"✅ Panel status changed to {new_status}")
                    st.success(message)
                    st.session_state["panel_mode"] = "view"
                    st.rerun()
                else:
                    st.error(message)

            if cancel_clicked:
                st.session_state["panel_mode"] = "view"
                st.rerun()

        # =============================================================
        # MODIFY MODE (Edit reagent composition)
        # =============================================================
        elif st.session_state["panel_mode"] == "modify":
            st.markdown(f"## 🔧 Modify Panel Contents: {panel['name']}")

            # Load current reagents
            panel_reagents = query_panels("""
                SELECT
                    pr.id as panel_reagent_id,
                    pr.display_name,
                    pr.channel_display_name as channel,
                    pr.volume_used
                FROM panel_reagents pr
                WHERE pr.panel_id = ?
                ORDER BY pr.channel_display_name
            """, (panel_id,))

            if not panel_reagents.empty:
                st.markdown("### Current Reagents")

                # Make dataframe selectable
                selected_reagents = st.dataframe(
                    panel_reagents[["channel", "display_name", "volume_used"]].rename(columns={
                        "channel": "Channel",
                        "display_name": "Marker",
                        "volume_used": "Vol (µL)"
                    }),
                    use_container_width=True,
                    selection_mode="multi-row",
                    on_select="rerun",
                    hide_index=True
                )

                # Remove button
                if selected_reagents and selected_reagents.get("selection", {}).get("rows"):
                    if st.button("Remove Selected Reagents", type="secondary"):
                        for idx in selected_reagents["selection"]["rows"]:
                            reagent_id = panel_reagents.iloc[idx]["panel_reagent_id"]
                            success, msg = remove_reagent_from_panel(reagent_id)
                            if not success:
                                st.error(msg)
                        st.success("Selected reagents removed")
                        st.rerun()

            else:
                st.info("This panel has no reagents. Use Panel Builder to add reagents.")

            st.markdown("---")

            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                if st.button("🔧 Edit in Panel Builder", use_container_width=True, type="primary",
                           help="Open this panel in Panel Builder to add/modify reagents"):
                    # Set editing mode in session state
                    st.session_state["editing_panel_id"] = panel_id
                    st.session_state["panel_draft_reagents"] = []  # Will be loaded in Panel Builder
                    st.session_state["panel_mode"] = "view"

                    # Force navigation to Panel Builder (will need app.py integration)
                    st.info("✓ Panel loaded into Panel Builder. Navigate to 'Panel Builder' tab to continue editing.")
                    st.success(f"Panel '{panel['name']}' is ready for editing in Panel Builder")

            with col_btn2:
                st.caption("💡 Use Panel Builder to add reagents")

            with col_btn3:
                if st.button("✓ Done", use_container_width=True):
                    st.session_state["panel_mode"] = "view"
                    st.rerun()

        # =============================================================
        # DELETE CONFIRMATION
        # =============================================================
        elif st.session_state["panel_mode"] == "delete_confirm":
            st.markdown(f"## ⚠️ Delete Panel: {panel['name']}?")

            st.error(f"""
                **WARNING:** You are about to permanently delete this panel.

                This will remove:
                - Panel metadata
                - All reagent assignments
                - Protocol references

                **This action cannot be undone.**
            """)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Yes, Delete Panel", type="primary", use_container_width=True):
                    success, message = delete_panel(panel_id)
                    if success:
                        st.success(message)
                        st.session_state["panel_mode"] = "view"
                        st.session_state["panel_selected_id"] = None
                        st.rerun()
                    else:
                        st.error(message)

            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state["panel_mode"] = "view"
                    st.rerun()
