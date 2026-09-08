import logging
import uuid
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ActionManager:
    def __init__(self):
        self.active_tasks = {}

    def generate_task_id(self) -> str:
        return str(uuid.uuid4())

    def recommend_action(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines the appropriate action based on incident type and context.
        """
        incident_type = incident.get("type")
        action = {
            "task_id": self.generate_task_id(),
            "incident_id": incident.get("incident_id"),
            "status": "RECOMMENDED",
            "created_at": datetime.utcnow().isoformat(),
            "verified_at": None,
            "verification_status": "PENDING"
        }

        if incident_type == "queue_congestion":
            current_queue = incident.get("current_queue_length", 0)
            arrival_rate = incident.get("arrival_rate", 0)
            service_capacity = incident.get("service_capacity", 0)
            
            action["action_type"] = "MOVE_STAFF"
            action["target"] = incident.get("zone_id", "CHECKOUT")
            action["description"] = "Open an additional checkout counter."
            action["explanation"] = f"Customer arrival rate is {arrival_rate:.1f}/min while service capacity is {service_capacity:.1f}/min. Queue is predicted to exceed critical limits."
            
        elif incident_type == "stockout":
            sku = incident.get("sku", "UNKNOWN")
            predicted_time = incident.get("time_to_stockout_mins", 0)
            
            action["action_type"] = "CREATE_RESTOCK_TASK"
            action["target"] = sku
            action["description"] = f"Restock {sku} immediately."
            action["explanation"] = f"{sku} is predicted to stock out in {predicted_time} minutes based on current consumption."

        else:
            action["action_type"] = "INVESTIGATE"
            action["description"] = "Investigate store anomaly."
            action["explanation"] = "An anomalous store condition was detected."

        self.active_tasks[action["task_id"]] = action
        return action

    def verify_action(self, task_id: str, new_state: Dict[str, Any]) -> bool:
        """
        Verifies if an action successfully resolved the underlying incident.
        Called by the event loop when state updates occur.
        """
        if task_id not in self.active_tasks:
            return False
            
        action = self.active_tasks[task_id]
        action_type = action.get("action_type")
        
        verified = False
        
        if action_type == "MOVE_STAFF":
            # Verification: did the queue length decrease?
            new_queue = new_state.get("queue_length", float('inf'))
            if new_queue < 5:  # threshold for returning to normal
                verified = True
                
        elif action_type == "CREATE_RESTOCK_TASK":
            # Verification: did shelf quantity increase?
            new_qty = new_state.get("shelf_quantity", 0)
            if new_qty > 4: # threshold for healthy stock
                verified = True
                
        if verified:
            action["status"] = "COMPLETED"
            action["verification_status"] = "VERIFIED"
            action["verified_at"] = datetime.utcnow().isoformat()
            
        return verified
