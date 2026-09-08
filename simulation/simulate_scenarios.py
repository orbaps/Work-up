import asyncio
import httpx
import uuid
from datetime import datetime, timedelta
import random

BASE_URL = "http://localhost:8000/v1/events/ingest"
STORE_ID = "S-101"
CAMERA_ID = "CAM-01"

async def send_events(events):
    async with httpx.AsyncClient() as client:
        payload = {
            "batch_id": str(uuid.uuid4()),
            "events": events
        }
        try:
            response = await client.post(BASE_URL, json=payload, timeout=5.0)
            if response.status_code == 200:
                print(f"✅ Ingested {len(events)} events.")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"⚠️ Connection error: {e}")

def create_event(event_type, payload):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "store_id": STORE_ID,
        "camera_id": CAMERA_ID,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "confidence": 0.95,
        "payload": payload
    }

async def scenario_1_queue_spike():
    print("🚀 Running Scenario 1: Queue Spike...")
    events = []
    # Simulate a sudden increase in queue depth
    for depth in [1, 2, 4, 6, 8, 10]:
        events.append(create_event("queue_depth", {"queue_id": "Q-checkout-1", "depth": depth}))
        events.append(create_event("queue_warning", {"queue_id": "Q-checkout-1", "depth": depth, "message": f"Queue growing ({depth})"}))
        if depth >= 8:
            events.append(create_event("queue_critical", {"queue_id": "Q-checkout-1", "depth": depth, "message": f"Queue critical ({depth}) - Needs staff"}))
    await send_events(events)

async def scenario_2_stockout():
    print("🚀 Running Scenario 2: Inventory Stockout...")
    events = []
    events.append(create_event("shelf_low", {"zone_id": "Z-Electronics", "sku": "SKU-HEADPHONES", "remaining": 3}))
    events.append(create_event("stockout_predicted", {"zone_id": "Z-Electronics", "sku": "SKU-HEADPHONES", "time_to_empty_mins": 15}))
    events.append(create_event("shelf_empty", {"zone_id": "Z-Electronics", "sku": "SKU-HEADPHONES"}))
    events.append(create_event("restock_required", {"zone_id": "Z-Electronics", "sku": "SKU-HEADPHONES", "priority": "CRITICAL"}))
    await send_events(events)

async def scenario_3_spillage():
    print("🚀 Running Scenario 3: Anomalous Event (Spillage / Misplaced Item)...")
    events = []
    events.append(create_event("sku_misplaced", {"zone_id": "Z-Apparel", "sku": "SKU-TSHIRT", "confidence": 0.85}))
    events.append(create_event("staff_action", {"zone_id": "Z-Apparel", "action_id": "TASK-123", "status": "assigned"}))
    await send_events(events)

async def main():
    print("RetailOS Edge - Event Simulator")
    await scenario_1_queue_spike()
    await asyncio.sleep(2)
    await scenario_2_stockout()
    await asyncio.sleep(2)
    await scenario_3_spillage()

if __name__ == "__main__":
    asyncio.run(main())
