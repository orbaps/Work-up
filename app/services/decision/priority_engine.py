import logging
from enum import Enum

logger = logging.getLogger(__name__)

class PriorityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class PriorityEngine:
    def __init__(self):
        # Base impact scores
        self.impact_scores = {
            "queue_congestion": 0.9,
            "stockout": 0.8,
            "sku_misplaced": 0.4,
            "dead_zone": 0.5,
            "anomaly": 0.6
        }

    def calculate_priority_score(
        self,
        incident_type: str,
        urgency: float,
        confidence: float,
        affected_customers: int
    ) -> float:
        """
        Calculates priority score using the formula:
        priority = business_impact * urgency * confidence * affected_customers
        """
        impact = self.impact_scores.get(incident_type, 0.5)
        # Normalize affected customers to avoid unbounded scaling (e.g., max 20 for scaling)
        normalized_customers = min(affected_customers, 20) / 10.0 if affected_customers > 0 else 0.1
        
        return impact * urgency * confidence * normalized_customers

    def get_priority_level(self, score: float) -> PriorityLevel:
        if score >= 1.5:
            return PriorityLevel.CRITICAL
        elif score >= 1.0:
            return PriorityLevel.HIGH
        elif score >= 0.5:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW

    def rank_incidents(self, incidents: list) -> list:
        """
        Takes a list of incident dicts, calculates scores, and returns them sorted by priority.
        Expected keys in incident dict: 'type', 'urgency', 'confidence', 'affected_customers'.
        """
        scored_incidents = []
        for incident in incidents:
            score = self.calculate_priority_score(
                incident.get("type", "unknown"),
                incident.get("urgency", 0.5),
                incident.get("confidence", 0.8),
                incident.get("affected_customers", 1)
            )
            incident["priority_score"] = score
            incident["priority_level"] = self.get_priority_level(score).value
            scored_incidents.append(incident)
            
        return sorted(scored_incidents, key=lambda x: x["priority_score"], reverse=True)
