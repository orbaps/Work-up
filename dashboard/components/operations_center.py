"""
RetailOS Edge — Operations Center Dashboard Page.

This page visualizes the autonomous SEE→UNDERSTAND→PREDICT→DECIDE→ACT→VERIFY loop
with real-time cycle execution against demo scenarios.

Run: streamlit run dashboard/streamlit_app.py (this page loaded via sidebar nav)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

OPS_CSS = """
<style>
    .loop-stage {
        text-align: center;
        padding: 16px 10px;
        border-radius: 12px;
        border: 1px solid #2d3548;
        background: linear-gradient(145deg, #1a1f2e 0%, #12151c 100%);
    }
    .loop-stage-active {
        border-color: #3dd68c;
        box-shadow: 0 0 12px rgba(61, 214, 140, 0.25);
    }
    .loop-stage h4 { margin: 0 0 4px 0; color: #f0f3f7; font-size: 0.95rem; }
    .loop-stage p { margin: 0; color: #9aa4b2; font-size: 0.75rem; }
    .stage-icon { font-size: 1.6rem; margin-bottom: 4px; }

    .incident-row {
        padding: 10px 14px;
        margin-bottom: 6px;
        border-radius: 8px;
        border-left: 4px solid #64748b;
        background: #1a1f2e;
    }
    .incident-critical { border-left-color: #ef4444; background: #1f1215; }
    .incident-high { border-left-color: #f59e0b; background: #1f1a12; }
    .incident-medium { border-left-color: #3b82f6; }
    .incident-low { border-left-color: #64748b; }

    .action-card {
        padding: 12px 14px;
        margin-bottom: 6px;
        border-radius: 8px;
        background: #12151c;
        border: 1px solid #2d3548;
    }
    .action-verified { border-color: #3dd68c; }
    .action-pending { border-color: #f59e0b; }

    .kpi-big {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f0f3f7;
        line-height: 1;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #9aa4b2;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
"""

STAGE_META = [
    ("👁️", "SEE", "Sensor data"),
    ("🧠", "UNDERSTAND", "Context"),
    ("🔮", "PREDICT", "Forecast"),
    ("⚖️", "DECIDE", "Prioritize"),
    ("⚡", "ACT", "Dispatch"),
    ("✅", "VERIFY", "Confirm"),
]


# ---------------------------------------------------------------------------
# API helper (talks to /operations endpoints)
# ---------------------------------------------------------------------------


def _fetch_scenarios(api_url: str) -> list[dict]:
    """Get available demo scenarios from the operations API."""
    import httpx
    try:
        r = httpx.get(f"{api_url}/operations/loop/demo/scenarios", timeout=3.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return [
            {"id": "normal", "name": "Normal Operations", "description": "Stable store"},
            {"id": "queue_spike", "name": "Queue Spike", "description": "Checkout rush"},
            {"id": "stockout", "name": "Inventory Stockout", "description": "Low stock"},
            {"id": "combined", "name": "Combined Crisis", "description": "Everything at once"},
        ]


def _run_demo_cycle(api_url: str, scenario: str) -> dict | None:
    """Execute a demo loop cycle via POST."""
    import httpx
    try:
        r = httpx.post(
            f"{api_url}/operations/loop/demo",
            json={"scenario": scenario},
            timeout=5.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _get_snapshot(api_url: str) -> dict | None:
    """Fetch the last loop snapshot."""
    import httpx
    try:
        r = httpx.get(f"{api_url}/operations/loop/snapshot", timeout=3.0)
        r.raise_for_status()
        data = r.json()
        if "message" in data:
            return None
        return data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# UI components
# ---------------------------------------------------------------------------


def _render_loop_pipeline(stages: list[dict]) -> None:
    """Render the 6-stage pipeline as a horizontal flow."""
    cols = st.columns(6)
    stage_map = {s["name"]: s for s in stages}

    for i, (icon, name, label) in enumerate(STAGE_META):
        stage = stage_map.get(name, {})
        is_done = stage.get("status") == "completed"
        css_class = "loop-stage loop-stage-active" if is_done else "loop-stage"
        check = "✓" if is_done else "…"

        with cols[i]:
            st.markdown(
                f"""
                <div class="{css_class}">
                    <div class="stage-icon">{icon}</div>
                    <h4>{name} {check}</h4>
                    <p>{label}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_summary_kpis(summary: dict) -> None:
    """KPI row from loop summary."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Incidents", summary.get("total_incidents", 0))
    c2.metric("Critical", summary.get("critical_incidents", 0))
    c3.metric("Actions", summary.get("actions_dispatched", 0))
    c4.metric("Verified", summary.get("actions_verified", 0))
    c5.metric("Queue Status", summary.get("queue_status", "—"))
    c6.metric("Inventory Alerts", summary.get("inventory_alerts", 0))


def _render_incidents(incidents: list[dict]) -> None:
    """Render prioritized incident list."""
    st.subheader("🚨 Prioritized Incidents")
    if not incidents:
        st.success("No incidents detected — store operating normally.")
        return

    for inc in incidents:
        level = inc.get("priority_level", "LOW")
        css = f"incident-{level.lower()}"
        score = inc.get("priority_score", 0)
        inc_type = inc.get("type", "unknown")
        detail = inc.get("detail", "")

        st.markdown(
            f"""
            <div class="incident-row {css}">
                <strong>{inc_type.replace('_', ' ').title()}</strong>
                &nbsp;·&nbsp; {level} &nbsp;·&nbsp; Score: {score:.2f}<br/>
                <span style="color:#cbd5e1; font-size:0.9rem;">{detail}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_actions(actions: list[dict]) -> None:
    """Render dispatched actions."""
    st.subheader("⚡ Dispatched Actions")
    if not actions:
        st.info("No actions to dispatch.")
        return

    for act in actions:
        status = act.get("status", "RECOMMENDED")
        css = "action-verified" if status == "COMPLETED" else "action-pending"
        badge = "✅" if status == "COMPLETED" else "🔄"

        st.markdown(
            f"""
            <div class="action-card {css}">
                {badge} <strong>{act.get('action_type', 'UNKNOWN')}</strong>
                &nbsp;→&nbsp; {act.get('target', '—')}<br/>
                <span style="color:#cbd5e1; font-size:0.9rem;">{act.get('description', '')}</span><br/>
                <span style="color:#94a3b8; font-size:0.8rem;">
                    💡 {act.get('explanation', '')}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_prediction_chart(snapshot: dict) -> None:
    """Visualize predictions from the loop."""
    predict_stage = next(
        (s for s in snapshot.get("stages", []) if s["name"] == "PREDICT"), None
    )
    if not predict_stage:
        return

    data = predict_stage.get("data", {})
    queue = data.get("queue", {})
    inv_alerts = data.get("inventory_alerts", [])

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("##### Queue Forecast")
        q_status = queue.get("status", "NORMAL")
        color_map = {"CRITICAL": "🔴", "WARNING": "🟡", "NORMAL": "🟢"}
        st.markdown(f"{color_map.get(q_status, '⚪')} **{q_status}** — {queue.get('message', '')}")
        ttc = queue.get("time_to_critical_mins")
        if ttc is not None and ttc > 0:
            st.warning(f"⏱️ Time to critical: **{ttc} minutes**")

    with col_b:
        st.markdown("##### Inventory Alerts")
        if not inv_alerts:
            st.success("All shelves healthy")
        else:
            for alert in inv_alerts:
                status = alert.get("status", "")
                icon = {"OUT_OF_STOCK": "🔴", "CRITICAL": "🟠", "LOW": "🟡"}.get(status, "⚪")
                st.markdown(f"{icon} **{alert['sku']}** — {alert['message']}")


def _render_verification(verifications: list[dict]) -> None:
    """Render verification results."""
    st.subheader("✅ Verification Loop")
    if not verifications:
        st.info("No actions pending verification in this cycle.")
        return

    for v in verifications:
        icon = "✅" if v.get("verified") else "⏳"
        st.markdown(
            f"{icon} `{v.get('task_id', '?')[:8]}` — "
            f"**{v.get('action_type', '?')}** → {v.get('status', '?')}"
        )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def render_operations_center(api_url: str) -> None:
    """Render the full Operations Center page."""
    st.markdown(OPS_CSS, unsafe_allow_html=True)

    st.title("🎯 Operations Center")
    st.markdown("Autonomous Edge AI Loop — **SEE → UNDERSTAND → PREDICT → DECIDE → ACT → VERIFY**")

    # Controls
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Operations")

    scenarios = _fetch_scenarios(api_url)
    scenario_names = {s["id"]: s["name"] for s in scenarios}
    selected = st.sidebar.selectbox(
        "Demo Scenario",
        options=list(scenario_names.keys()),
        format_func=lambda x: scenario_names[x],
    )

    if st.sidebar.button("▶️ Run Loop Cycle", type="primary", use_container_width=True):
        with st.spinner("Running autonomous loop..."):
            result = _run_demo_cycle(api_url, selected)
            if result:
                st.session_state["ops_snapshot"] = result
                st.rerun()

    # Show description for selected scenario
    desc = next((s["description"] for s in scenarios if s["id"] == selected), "")
    st.sidebar.caption(desc)

    # Load snapshot
    snapshot = st.session_state.get("ops_snapshot") or _get_snapshot(api_url)

    if snapshot is None:
        st.info("👆 Select a scenario and click **Run Loop Cycle** to start the autonomous loop.")
        # Show the empty pipeline
        _render_loop_pipeline([])
        return

    # Pipeline visualization
    _render_loop_pipeline(snapshot.get("stages", []))

    st.divider()

    # Summary KPIs
    _render_summary_kpis(snapshot.get("summary", {}))

    st.divider()

    # Predictions
    _render_prediction_chart(snapshot)

    st.divider()

    # Incidents and Actions side by side
    left, right = st.columns(2)
    with left:
        _render_incidents(snapshot.get("incidents", []))
    with right:
        _render_actions(snapshot.get("actions", []))

    st.divider()

    # Verification
    _render_verification(snapshot.get("verifications", []))

    # Metadata footer
    st.caption(
        f"Cycle: `{snapshot.get('cycle_id', '?')}` · "
        f"Started: {snapshot.get('started_at', '?')}"
    )
