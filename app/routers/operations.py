"""Operations Center API — exposes the autonomous loop to the dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.orchestrator import EdgeOrchestrator

router = APIRouter(prefix="/operations", tags=["operations"])

# Singleton orchestrator instance (in production, use DI)
_orchestrator = EdgeOrchestrator()


class StoreStateRequest(BaseModel):
    """Payload describing current store state for a loop cycle."""

    store_id: str = "S-101"
    visitors_inside: int = 0
    staff_count: int = 3
    cameras_active: int = 4
    queues: list[dict[str, Any]] = Field(default_factory=list)
    shelves: list[dict[str, Any]] = Field(default_factory=list)
    zones: list[dict[str, Any]] = Field(default_factory=list)


class DemoScenario(BaseModel):
    """Pre-built scenario for demo/showcase."""

    scenario: str = "normal"  # normal | queue_spike | stockout | combined


# ---------------------------------------------------------------------------
# Demo state builders
# ---------------------------------------------------------------------------

def _build_demo_state(scenario: str) -> dict:
    """Build a realistic store state for demo scenarios."""
    base = {
        "visitors_inside": 24,
        "staff_count": 3,
        "cameras_active": 4,
        "queues": [
            {"queue_id": "Q-checkout-1", "depth": 3, "arrival_rate": 1.5, "service_rate": 2.0, "counters": 2},
            {"queue_id": "Q-checkout-2", "depth": 1, "arrival_rate": 0.8, "service_rate": 1.5, "counters": 1},
        ],
        "shelves": [
            {"sku": "SKU-HEADPHONES", "zone": "Z-Electronics", "units": 12, "consumption_rate": 0.05},
            {"sku": "SKU-CHARGER", "zone": "Z-Electronics", "units": 8, "consumption_rate": 0.08},
            {"sku": "SKU-TSHIRT", "zone": "Z-Apparel", "units": 20, "consumption_rate": 0.03},
            {"sku": "SKU-JEANS", "zone": "Z-Apparel", "units": 6, "consumption_rate": 0.04},
        ],
        "zones": [
            {"zone_id": "Z-Electronics", "visitors": 8},
            {"zone_id": "Z-Apparel", "visitors": 6},
            {"zone_id": "Z-Grocery", "visitors": 5},
            {"zone_id": "Z-Checkout", "visitors": 5},
        ],
    }

    if scenario == "queue_spike":
        base["visitors_inside"] = 42
        base["queues"] = [
            {"queue_id": "Q-checkout-1", "depth": 11, "arrival_rate": 4.5, "service_rate": 1.5, "counters": 1},
            {"queue_id": "Q-checkout-2", "depth": 7, "arrival_rate": 3.0, "service_rate": 1.5, "counters": 1},
        ]

    elif scenario == "stockout":
        base["shelves"] = [
            {"sku": "SKU-HEADPHONES", "zone": "Z-Electronics", "units": 1, "consumption_rate": 0.3},
            {"sku": "SKU-CHARGER", "zone": "Z-Electronics", "units": 0, "consumption_rate": 0.2},
            {"sku": "SKU-TSHIRT", "zone": "Z-Apparel", "units": 3, "consumption_rate": 0.15},
            {"sku": "SKU-JEANS", "zone": "Z-Apparel", "units": 15, "consumption_rate": 0.02},
        ]

    elif scenario == "combined":
        base["visitors_inside"] = 50
        base["queues"] = [
            {"queue_id": "Q-checkout-1", "depth": 9, "arrival_rate": 3.8, "service_rate": 1.5, "counters": 1},
            {"queue_id": "Q-checkout-2", "depth": 6, "arrival_rate": 2.5, "service_rate": 1.5, "counters": 1},
        ]
        base["shelves"] = [
            {"sku": "SKU-HEADPHONES", "zone": "Z-Electronics", "units": 2, "consumption_rate": 0.25},
            {"sku": "SKU-CHARGER", "zone": "Z-Electronics", "units": 0, "consumption_rate": 0.2},
            {"sku": "SKU-TSHIRT", "zone": "Z-Apparel", "units": 4, "consumption_rate": 0.12},
            {"sku": "SKU-JEANS", "zone": "Z-Apparel", "units": 18, "consumption_rate": 0.02},
        ]

    return base


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/loop/run",
    summary="Run one autonomous loop cycle",
    description="Execute SEE→UNDERSTAND→PREDICT→DECIDE→ACT→VERIFY on the given store state.",
)
async def run_loop_cycle(body: StoreStateRequest) -> dict:
    state = body.model_dump()
    return _orchestrator.run_cycle(state)


@router.post(
    "/loop/demo",
    summary="Run a demo scenario",
    description="Run the autonomous loop with a pre-built demo scenario.",
)
async def run_demo_scenario(body: DemoScenario) -> dict:
    state = _build_demo_state(body.scenario)
    return _orchestrator.run_cycle(state)


@router.get(
    "/loop/snapshot",
    summary="Get the last loop snapshot",
    description="Returns the most recent autonomous loop cycle result.",
)
async def get_last_snapshot() -> dict:
    snapshot = _orchestrator.get_last_snapshot()
    if snapshot is None:
        return {"message": "No loop cycle has been run yet. POST to /operations/loop/demo to start."}
    return snapshot


@router.get(
    "/loop/demo/scenarios",
    summary="List available demo scenarios",
)
async def list_scenarios() -> list[dict]:
    return [
        {
            "id": "normal",
            "name": "Normal Operations",
            "description": "Store running smoothly. No incidents expected.",
        },
        {
            "id": "queue_spike",
            "name": "Queue Spike",
            "description": "Sudden rush at checkout. Queue depths exceed critical thresholds.",
        },
        {
            "id": "stockout",
            "name": "Inventory Stockout",
            "description": "Multiple SKUs running critically low. Immediate restock needed.",
        },
        {
            "id": "combined",
            "name": "Combined Crisis",
            "description": "Queue spike + stockout happening simultaneously. Maximum stress test.",
        },
    ]
