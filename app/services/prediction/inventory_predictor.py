import logging

logger = logging.getLogger(__name__)

class InventoryPredictor:
    def __init__(self, low_stock_threshold: int = 4, critical_stock_threshold: int = 2):
        self.low_stock_threshold = low_stock_threshold
        self.critical_stock_threshold = critical_stock_threshold

    def predict_stockout(
        self,
        sku: str,
        current_visible_units: int,
        consumption_rate_per_min: float
    ) -> dict:
        """
        Predicts when a SKU will run out of stock based on current visible units and consumption rate.
        """
        if current_visible_units == 0:
            return {
                "sku": sku,
                "status": "OUT_OF_STOCK",
                "message": f"SKU {sku} is out of stock.",
                "time_to_stockout_mins": 0
            }

        if consumption_rate_per_min <= 0:
             status = "NORMAL"
             if current_visible_units <= self.critical_stock_threshold:
                 status = "CRITICAL"
             elif current_visible_units <= self.low_stock_threshold:
                 status = "LOW"
             
             return {
                 "sku": sku,
                 "status": status,
                 "message": f"SKU {sku} has {current_visible_units} units. No active consumption.",
                 "time_to_stockout_mins": None
             }

        time_to_stockout = current_visible_units / consumption_rate_per_min
        
        status = "NORMAL"
        if current_visible_units <= self.critical_stock_threshold or time_to_stockout < 10:
             status = "CRITICAL"
        elif current_visible_units <= self.low_stock_threshold or time_to_stockout < 30:
             status = "LOW"
             
        return {
            "sku": sku,
            "status": status,
            "message": f"SKU {sku} predicted to stock out in {time_to_stockout:.1f} minutes.",
            "time_to_stockout_mins": round(time_to_stockout, 1)
        }
