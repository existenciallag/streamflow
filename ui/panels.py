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


def delete_panel(panel_id):
    """Delete a panel and all its reagents"""
    try:
        # Delete panel reagents first (cascade)
        query_panels("DELETE FROM panel_reagents WHERE panel_id = ?", (panel_id,), commit=True)

        # Delete panel
        query_panels("DELETE FROM panels WHERE id = ?", (panel_id,), commit=True)

        return True, "Panel deleted successfully"
    except Exception as e:
        return False, f"Error deleting panel: {e}"


def update_panel_metadata(panel_id, name, description, sample_type, sample_volume, washed_sample,
                          clinical_indication, acquisition_protocol_name, acquisition_protocol_status,
                          compensation_protocol_name, compensation_protocol_status,
                          analysis_protocol_name, analysis_protocol_status):
    """Update panel metadata"""
    try:
        query_panels("""
            UPDATE panels SET
                name = ?,
                description = ?,
                sample_type = ?,
                sample_volume = ?,
                washed_sample = ?,
                clinical_indication = ?,
                acquisition_protocol_name = ?,
                acquisition_protocol_status = ?,
                compensation_name = ?,
                compensation_status = ?,
                analysis_protocol_name = ?,
                analysis_protocol_status = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            name, description, sample_type, sample_volume, washed_sample,
            clinical_indication, acquisition_protocol_name, acquisition_protocol_status,
            compensation_protocol_name, compensation_protocol_status,
            analysis_protocol_name, analysis_protocol_status,
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

    st.subheader("🔬 Panels")

    # Initialize session state
    if "panel_mode" not in st.session_state:
        st.session_state["panel_mode"] = "view"
    if "panel_selected_id" not in st.session_state:
        st.session_state["panel_selected_id"] = None

    # Load panels with semantic names
    if panels_df is None:
        panels = query_panels("""
            SELECT
                p.id,
                p.name,
                p.version,
                p.status,
                p.sample_type,
                p.sample_volume,
                p.clinical_indication,
                p.estimated_cost_per_test,
                c.name as cytometer_name,
                p.created_at
            FROM panels p
            LEFT JOIN cytometers c ON c.id = p.cytometer_id
            ORDER BY p.created_at DESC
        """)
    elif isinstance(panels_df, dict):
        panels = panels_df.get("panels")
    elif isinstance(panels_df, pd.DataFrame):
        panels = panels_df.copy()
    else:
        panels = None

    if panels is None or panels.empty:
        st.info("No panels found. Create one in Panel Builder.")
        return

    # Two-column layout
    col_list, col_detail = st.columns([1, 3])

    # =============================================================
    # LEFT PANEL: PANEL LIST
    # =============================================================
    with col_list:
        search = st.text_input("🔍 Search panels", key="panel_search")

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

        # Load full panel data
        panel = panels[panels["id"] == panel_id].iloc[0]

        # =============================================================
        # VIEW MODE
        # =============================================================
        if st.session_state["panel_mode"] == "view":
            # Header with action buttons
            col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1, 1, 1])

            with col_h1:
                st.markdown(f"## {panel['name']}")
                status_color = {"draft": "🟡", "validated": "🟢", "archived": "🔴"}.get(panel['status'], "⚪")
                st.caption(f"{status_color} {panel['status'].upper()} · v{panel['version']}")

            with col_h2:
                if st.button("✏️ Edit", use_container_width=True):
                    st.session_state["panel_mode"] = "edit"
                    st.rerun()

            with col_h3:
                if st.button("🔧 Modify", use_container_width=True, help="Modify panel contents"):
                    st.session_state["panel_mode"] = "modify"
                    st.rerun()

            with col_h4:
                if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                    st.session_state["panel_mode"] = "delete_confirm"
                    st.rerun()

            # Metadata display
            st.markdown("---")
            st.markdown("### 📋 Panel Information")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Sample Type", panel.get("sample_type") or "—")
            with col2:
                st.metric("Sample Volume", f"{panel.get('sample_volume') or '—'} µL")
            with col3:
                st.metric("Cost/Test", f"${panel.get('estimated_cost_per_test') or 0:.2f}")

            col4, col5, col6 = st.columns(3)
            with col4:
                st.metric("Cytometer", panel.get("cytometer_name") or "—")
            with col5:
                st.metric("Washed Sample", "Yes" if panel.get("washed_sample") else "No")
            with col6:
                st.metric("Created", panel.get("created_at", "—")[:10] if panel.get("created_at") else "—")

            if panel.get("clinical_indication"):
                st.markdown("**Clinical Indication:**")
                st.info(panel["clinical_indication"])

            # Protocols
            st.markdown("---")
            st.markdown("### 📑 Protocols")

            # Load full panel data for protocols
            full_panel = query_panels("SELECT * FROM panels WHERE id = ?", (panel_id,)).iloc[0]

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
            st.markdown("### 🧬 Panel Composition")

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
                    pr.cost_per_test,
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
                # Format for display
                display_reagents = panel_reagents[[
                    "channel", "display_name", "fluorochrome", "clone",
                    "brand", "volume_used", "staining_step", "is_intracellular", "cost_per_test"
                ]].copy()

                display_reagents["is_intracellular"] = display_reagents["is_intracellular"].apply(
                    lambda x: "✓" if x else ""
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
                    "cost_per_test": "Cost"
                })

                st.dataframe(display_reagents, use_container_width=True, hide_index=True)

                total_cost = panel_reagents["cost_per_test"].sum()
                st.markdown(f"### 💰 Total Cost: **${total_cost:.2f}** per test")

        # =============================================================
        # EDIT MODE
        # =============================================================
        elif st.session_state["panel_mode"] == "edit":
            st.markdown(f"## ✏️ Edit Panel: {panel['name']}")

            # Load full panel data
            full_panel = query_panels("SELECT * FROM panels WHERE id = ?", (panel_id,)).iloc[0]

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

                st.markdown("**Protocols**")
                p1, p2, p3 = st.columns(3)

                with p1:
                    st.caption("Acquisition")
                    new_acq_name = st.text_input(
                        "Name",
                        value=full_panel.get('acquisition_protocol_name') or "",
                        key="edit_acq_name"
                    )
                    new_acq_status = st.selectbox(
                        "Status",
                        ["draft", "validated", "archived"],
                        index=["draft", "validated", "archived"].index(full_panel.get('acquisition_protocol_status', 'draft'))
                        if full_panel.get('acquisition_protocol_status') in ["draft", "validated", "archived"] else 0,
                        key="edit_acq_status"
                    )

                with p2:
                    st.caption("Compensation")
                    new_comp_name = st.text_input(
                        "Name",
                        value=full_panel.get('compensation_name') or "",
                        key="edit_comp_name"
                    )
                    new_comp_status = st.selectbox(
                        "Status",
                        ["draft", "validated", "archived"],
                        index=["draft", "validated", "archived"].index(full_panel.get('compensation_status', 'draft'))
                        if full_panel.get('compensation_status') in ["draft", "validated", "archived"] else 0,
                        key="edit_comp_status"
                    )

                with p3:
                    st.caption("Analysis")
                    new_analysis_name = st.text_input(
                        "Name",
                        value=full_panel.get('analysis_protocol_name') or "",
                        key="edit_analysis_name"
                    )
                    new_analysis_status = st.selectbox(
                        "Status",
                        ["draft", "validated", "archived"],
                        index=["draft", "validated", "archived"].index(full_panel.get('analysis_protocol_status', 'draft'))
                        if full_panel.get('analysis_protocol_status') in ["draft", "validated", "archived"] else 0,
                        key="edit_analysis_status"
                    )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    save_clicked = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
                with col_btn2:
                    cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)

            if save_clicked:
                success, message = update_panel_metadata(
                    panel_id, new_name, new_description, new_sample_type, new_sample_volume,
                    1 if new_washed_sample else 0, new_clinical_indication,
                    new_acq_name, new_acq_status,
                    new_comp_name, new_comp_status,
                    new_analysis_name, new_analysis_status
                )

                if success:
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
                    pr.volume_used,
                    pr.cost_per_test
                FROM panel_reagents pr
                WHERE pr.panel_id = ?
                ORDER BY pr.channel_display_name
            """, (panel_id,))

            if not panel_reagents.empty:
                st.markdown("### Current Reagents")

                # Make dataframe selectable
                selected_reagents = st.dataframe(
                    panel_reagents[["channel", "display_name", "volume_used", "cost_per_test"]].rename(columns={
                        "channel": "Channel",
                        "display_name": "Marker",
                        "volume_used": "Vol (µL)",
                        "cost_per_test": "Cost"
                    }),
                    use_container_width=True,
                    selection_mode="multi-row",
                    on_select="rerun",
                    hide_index=True
                )

                # Remove button
                if selected_reagents and selected_reagents.get("selection", {}).get("rows"):
                    if st.button("🗑️ Remove Selected Reagents", type="secondary"):
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

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.info("💡 To add new reagents, use the Panel Builder")
            with col_btn2:
                if st.button("✓ Done", use_container_width=True, type="primary"):
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
                if st.button("🗑️ Yes, Delete Panel", type="primary", use_container_width=True):
                    success, message = delete_panel(panel_id)
                    if success:
                        st.success(message)
                        st.session_state["panel_mode"] = "view"
                        st.session_state["panel_selected_id"] = None
                        st.rerun()
                    else:
                        st.error(message)

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state["panel_mode"] = "view"
                    st.rerun()
