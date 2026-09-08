"""
RetailOS Edge Orchestrator — the autonomous closed-loop brain.

Pipeline: SEE → UNDERSTAND → PREDICT → DECIDE → ACT → VERIFY

This service consumes the current store state (from event stream / metrics)
and drives the full loop, returning a structured LoopSnapshot for the
Operations Center dashboard.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.prediction.queue_predictor import QueuePredictor
from app.services.prediction.inventory_predictor import InventoryPredictor
from app.services.decision.priority_engine import PriorityEngine
from app.services.actions.action_manager import ActionManager

logger = logging.getLogger(__name__)


class LoopStage:
    """Represents one stage of the autonomous loop with status + data."""

    def __init__(self, name: str, status: str = "idle", data: dict | None = None):
        self.name = name
        self.status = status  # idle | running | completed | error
        self.data = data or {}
        self.timestamp: str = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class LoopSnapshot:
    """Full snapshot of one autonomous loop cycle."""

    def __init__(self):
        self.cycle_id = str(uuid.uuid4())[:8]
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.stages: list[dict] = []
        self.incidents: list[dict] = []
        self.actions: list[dict] = []
        self.verifications: list[dict] = []
        self.summary: dict = {}

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "stages": self.stages,
            "incidents": self.incidents,
            "actions": self.actions,
            "verifications": self.verifications,
            "summary": self.summary,
        }


class EdgeOrchestrator:
    """
    Runs one cycle of the autonomous loop against the current store state.

    Usage:
        orchestrator = EdgeOrchestrator()
        snapshot = orchestrator.run_cycle(store_state)
    """

    def __init__(self):
        self.queue_predictor = QueuePredictor()
        self.inventory_predictor = InventoryPredictor()
        self.priority_engine = PriorityEngine()
        self.action_manager = ActionManager()
        self._last_snapshot: LoopSnapshot | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_cycle(self, store_state: dict[str, Any]) -> dict:
        """Execute one full SEE→UNDERSTAND→PREDICT→DECIDE→ACT→VERIFY cycle."""
        snapshot = LoopSnapshot()

        # ── STAGE 1: SEE ──
        see_data = self._stage_see(store_state)
        snapshot.stages.append(
            LoopStage("SEE", "completed", see_data).to_dict()
        )

        # ── STAGE 2: UNDERSTAND ──
        understand_data = self._stage_understand(see_data)
        snapshot.stages.append(
            LoopStage("UNDERSTAND", "completed", understand_data).to_dict()
        )

        # ── STAGE 3: PREDICT ──
        predictions = self._stage_predict(understand_data)
        snapshot.stages.append(
            LoopStage("PREDICT", "completed", predictions).to_dict()
        )

        # ── STAGE 4: DECIDE ──
        incidents = self._stage_decide(predictions)
        snapshot.incidents = incidents
        snapshot.stages.append(
            LoopStage("DECIDE", "completed", {"incident_count": len(incidents)}).to_dict()
        )

        # ── STAGE 5: ACT ──
        actions = self._stage_act(incidents)
        snapshot.actions = actions
        snapshot.stages.append(
            LoopStage("ACT", "completed", {"action_count": len(actions)}).to_dict()
        )

        # ── STAGE 6: VERIFY ──
        verifications = self._stage_verify(store_state)
        snapshot.verifications = verifications
        snapshot.stages.append(
            LoopStage("VERIFY", "completed", {"verified": len(verifications)}).to_dict()
        )

        # Build summary
        snapshot.summary = {
            "total_incidents": len(incidents),
            "critical_incidents": sum(1 for i in incidents if i.get("priority_level") == "CRITICAL"),
            "actions_dispatched": len(actions),
            "actions_verified": sum(1 for v in verifications if v.get("verified")),
            "queue_status": predictions.get("queue", {}).get("status", "UNKNOWN"),
            "inventory_alerts": len(predictions.get("inventory_alerts", [])),
        }

        self._last_snapshot = snapshot
        logger.info(
            "loop_cycle_complete",
            cycle_id=snapshot.cycle_id,
            incidents=len(incidents),
            actions=len(actions),
        )
        return snapshot.to_dict()

    def get_last_snapshot(self) -> dict | None:
        """Return the most recent loop snapshot, if any."""
        if self._last_snapshot:
            return self._last_snapshot.to_dict()
        return None

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _stage_see(self, store_state: dict) -> dict:
        """Extract raw signals from the store state."""
        return {
            "visitors_inside": store_state.get("visitors_inside", 0),
            "queues": store_state.get("queues", []),
            "shelves": store_state.get("shelves", []),
            "zones": store_state.get("zones", []),
            "staff_count": store_state.get("staff_count", 0),
            "cameras_active": store_state.get("cameras_active", 0),
        }

    def _stage_understand(self, see_data: dict) -> dict:
        """Derive context from raw signals."""
        queues = see_data.get("queues", [])
        total_queue = sum(q.get("depth", 0) for q in queues)
        max_queue = max((q.get("depth", 0) for q in queues), default=0)
        avg_queue = total_queue / len(queues) if queues else 0

        shelves = see_data.get("shelves", [])
        low_stock_count = sum(
            1 for s in shelves if s.get("units", 10) <= 4
        )
        empty_count = sum(
            1 for s in shelves if s.get("units", 10) == 0
        )

        return {
            "visitors_inside": see_data["visitors_inside"],
            "total_queue_depth": total_queue,
            "max_queue_depth": max_queue,
            "avg_queue_depth": round(avg_queue, 1),
            "active_queues": len(queues),
            "low_stock_shelves": low_stock_count,
            "empty_shelves": empty_count,
            "total_shelves": len(shelves),
            "staff_count": see_data["staff_count"],
            "cameras_active": see_data["cameras_active"],
            "queues": queues,
            "shelves": shelves,
        }

    def _stage_predict(self, understood: dict) -> dict:
        """Run prediction models on understood data."""
        # Queue prediction
        queue_pred = {"status": "NORMAL", "message": "No queues active."}
        queues = understood.get("queues", [])
        if queues:
            # Use the longest queue for prediction
            longest = max(queues, key=lambda q: q.get("depth", 0))
            queue_pred = self.queue_predictor.predict_congestion(
                current_queue_length=longest.get("depth", 0),
                arrival_rate_per_min=longest.get("arrival_rate", 2.0),
                service_rate_per_min=longest.get("service_rate", 1.5),
                active_counters=longest.get("counters", 1),
            )

        # Inventory predictions
        inventory_alerts = []
        shelves = understood.get("shelves", [])
        for shelf in shelves:
            pred = self.inventory_predictor.predict_stockout(
                sku=shelf.get("sku", "UNKNOWN"),
                current_visible_units=shelf.get("units", 10),
                consumption_rate_per_min=shelf.get("consumption_rate", 0.1),
            )
            if pred["status"] in ("CRITICAL", "LOW", "OUT_OF_STOCK"):
                inventory_alerts.append(pred)

        return {
            "queue": queue_pred,
            "inventory_alerts": inventory_alerts,
        }

    def _stage_decide(self, predictions: dict) -> list[dict]:
        """Build and prioritize incidents from predictions."""
        incidents = []

        # Queue incident
        queue_pred = predictions.get("queue", {})
        if queue_pred.get("status") in ("WARNING", "CRITICAL"):
            incidents.append({
                "type": "queue_congestion",
                "urgency": 1.0 if queue_pred["status"] == "CRITICAL" else 0.7,
                "confidence": 0.9,
                "affected_customers": 8 if queue_pred["status"] == "CRITICAL" else 4,
                "detail": queue_pred.get("message", ""),
                "time_to_critical_mins": queue_pred.get("time_to_critical_mins"),
            })

        # Inventory incidents
        for alert in predictions.get("inventory_alerts", []):
            incidents.append({
                "type": "stockout",
                "urgency": 1.0 if alert["status"] in ("CRITICAL", "OUT_OF_STOCK") else 0.6,
                "confidence": 0.85,
                "affected_customers": 3,
                "sku": alert.get("sku"),
                "detail": alert.get("message", ""),
                "time_to_stockout_mins": alert.get("time_to_stockout_mins"),
            })

        # Rank by priority
        if incidents:
            incidents = self.priority_engine.rank_incidents(incidents)

        return incidents

    def _stage_act(self, incidents: list[dict]) -> list[dict]:
        """Generate recommended actions for top incidents."""
        actions = []
        for incident in incidents[:5]:  # Cap at 5 concurrent actions
            action = self.action_manager.recommend_action(incident)
            actions.append(action)
        return actions

    def _stage_verify(self, store_state: dict) -> list[dict]:
        """Verify outstanding actions against current state."""
        verifications = []
        for task_id, task in list(self.action_manager.active_tasks.items()):
            if task.get("status") == "COMPLETED":
                continue
            verified = self.action_manager.verify_action(task_id, store_state)
            verifications.append({
                "task_id": task_id,
                "action_type": task.get("action_type"),
                "verified": verified,
                "status": "VERIFIED" if verified else "PENDING",
            })
        return verifications
