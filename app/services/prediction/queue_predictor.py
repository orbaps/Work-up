from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class QueuePredictor:
    def __init__(self, critical_threshold: int = 8, warning_threshold: int = 5):
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold

    def predict_congestion(
        self, 
        current_queue_length: int, 
        arrival_rate_per_min: float, 
        service_rate_per_min: float, 
        active_counters: int
    ) -> dict:
        """
        Predicts if and when a queue will become congested.
        Returns a dictionary with prediction results.
        """
        if active_counters == 0:
            return {
                "status": "CRITICAL",
                "message": "No active counters. Queue will grow unbounded.",
                "time_to_critical_mins": 0
            }

        total_service_capacity = service_rate_per_min * active_counters
        net_growth_rate = arrival_rate_per_min - total_service_capacity

        if current_queue_length >= self.critical_threshold:
             return {
                 "status": "CRITICAL",
                 "message": f"Queue is already at critical level ({current_queue_length}).",
                 "time_to_critical_mins": 0
             }
             
        if current_queue_length >= self.warning_threshold and net_growth_rate <= 0:
             return {
                 "status": "WARNING",
                 "message": f"Queue is elevated ({current_queue_length}) but growth is stable/negative.",
                 "time_to_critical_mins": None
             }

        if net_growth_rate > 0:
            remaining_capacity = self.critical_threshold - current_queue_length
            time_to_critical = remaining_capacity / net_growth_rate
            
            status = "WARNING"
            if time_to_critical < 5:
                 status = "CRITICAL"
                 
            return {
                "status": status,
                "message": f"Queue is growing. Predicted to reach critical in {time_to_critical:.1f} minutes.",
                "time_to_critical_mins": round(time_to_critical, 1)
            }
            
        return {
            "status": "NORMAL",
            "message": "Queue is stable.",
            "time_to_critical_mins": None
        }
