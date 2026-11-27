"""
AI Demand Predictor & Preparation Recommendation Engine:
Serves real-time demand inference and daily preparation recommendations for restaurant managers.
"""

import math
import json
import joblib
import pandas as pd
from datetime import datetime, date, timezone
from pathlib import Path

from backend.config import Config
from backend.models import db, ProductMenu, InventoryStock, HistoricalSalesData, LiveOrder

MODEL_PATH = Config.MODEL_FILE_PATH
METRICS_PATH = Config.METRICS_FILE_PATH


class DemandPredictor:
    """
    Inference engine for food demand prediction and inventory prep optimization.
    """
    _pipeline = None
    _model_mtime = None

    @classmethod
    def get_pipeline(cls):
        """Lazy load, auto-reload on disk updates, or train model pipeline."""
        if not MODEL_PATH.exists():
            print("[PREDICTOR] Model artifact not found. Triggering automated model training...")
            from ml_model.train import train_demand_forecasting_model
            train_demand_forecasting_model()

        if MODEL_PATH.exists():
            current_mtime = MODEL_PATH.stat().st_mtime
            if cls._pipeline is None or cls._model_mtime != current_mtime:
                cls._pipeline = joblib.load(MODEL_PATH)
                cls._model_mtime = current_mtime
                print(f"[PREDICTOR] Loaded model pipeline from {MODEL_PATH}")
        else:
            raise RuntimeError("Failed to load or generate ML model pipeline.")
        return cls._pipeline

    @classmethod
    def reload_pipeline(cls):
        """Forces reload of model pipeline from disk (useful after retraining)."""
        cls._pipeline = None
        cls._model_mtime = None
        return cls.get_pipeline()

    @classmethod
    def get_model_metrics(cls):
        """Retrieves trained model evaluation statistics and feature importances."""
        if METRICS_PATH.exists():
            try:
                with open(METRICS_PATH, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[PREDICTOR ERROR] Failed to read metrics JSON: {e}")
        return None

    @classmethod
    def predict_single_item(cls, item: ProductMenu, day_type: str, customer_count: int,
                            day_of_week: int, weather_condition: str = 'Sunny', month: int = None) -> int:
        """
        Predicts demand quantity for a single menu item.
        """
        pipeline = cls.get_pipeline()
        if month is None:
            month = datetime.now().month

        input_df = pd.DataFrame([{
            'day_type': str(day_type),
            'item_id': int(item.id),
            'weather_condition': str(weather_condition),
            'category': str(item.category),
            'customer_count': int(customer_count),
            'day_of_week': int(day_of_week),
            'month': int(month),
            'unit_price': float(item.unit_price)
        }])

        pred_val = pipeline.predict(input_df)[0]
        # Return non-negative rounded integer
        return max(1, int(round(pred_val)))

    @classmethod
    def get_daily_preparation_recommendations(
        cls,
        target_date: date = None,
        day_type: str = None,
        customer_count: int = None,
        weather_condition: str = 'Sunny',
        safety_buffer_pct: float = None
    ) -> dict:
        """
        Calculates optimized food prep quantities for all active menu items.
        Compares predicted demand + safety buffer against existing inventory stock.
        """
        pipeline = cls.get_pipeline()

        if target_date is None:
            target_date = date.today()

        day_of_week = target_date.weekday()
        month = target_date.month

        # Default day_type heuristic if not provided
        if day_type is None:
            if day_of_week in (4, 5, 6): # Fri, Sat, Sun
                day_type = 'weekend'
            else:
                day_type = 'weekday'

        # Default customer count heuristic if not provided
        if customer_count is None:
            default_counts = {
                'weekday': 85,
                'weekend': 210,
                'office_party': 175,
                'birthday_celebration': 150,
                'festival': 310
            }
            customer_count = default_counts.get(day_type, 100)

        if safety_buffer_pct is None:
            safety_buffer_pct = Config.SAFETY_BUFFER_PERCENT

        # Fetch all menu items with their inventory
        menu_items = ProductMenu.query.order_by(ProductMenu.category, ProductMenu.item_name).all()

        if not menu_items:
            return {
                'recommendations': [],
                'summary': {},
                'metadata': {}
            }

        # Build batch dataframe for efficient prediction
        # Also gather historical data count & live orders today per dish so we know
        # whether a dish is brand-new (0 sales history) vs actively learned by the AI model.
        hist_counts = dict(
            db.session.query(
                HistoricalSalesData.item_id,
                db.func.count(HistoricalSalesData.id)
            ).group_by(HistoricalSalesData.item_id).all()
        )
        today_start_dt = datetime.combine(date.today(), datetime.min.time())
        live_today_counts = dict(
            db.session.query(
                LiveOrder.item_id,
                db.func.coalesce(db.func.sum(LiveOrder.quantity), 0)
            ).filter(
                LiveOrder.order_time >= today_start_dt,
                LiveOrder.status != 'cancelled'
            ).group_by(LiveOrder.item_id).all()
        )

        batch_rows = []
        for item in menu_items:
            batch_rows.append({
                'day_type': str(day_type),
                'item_id': int(item.id),
                'weather_condition': str(weather_condition),
                'category': str(item.category),
                'customer_count': int(customer_count),
                'day_of_week': int(day_of_week),
                'month': int(month),
                'unit_price': float(item.unit_price)
            })

        batch_df = pd.DataFrame(batch_rows)
        raw_predictions = pipeline.predict(batch_df)

        recommendations = []
        total_predicted_demand = 0
        total_prep_units = 0
        total_prep_cost = 0.0
        total_expected_revenue = 0.0
        total_buffer_units = 0

        for i, item in enumerate(menu_items):
            hist_records = int(hist_counts.get(item.id, 0))
            live_today = int(live_today_counts.get(item.id, 0))
            pred_demand = max(1, int(round(raw_predictions[i])))
            # For brand-new dishes with zero historical orders yet, keep starter batch conservative
            # until real customer orders feed into the database and retrain the model.
            if hist_records == 0:
                starter_cap = max(5, int(round(customer_count * 0.12)))
                pred_demand = min(pred_demand, starter_cap)

            buffer_units = int(math.ceil(pred_demand * safety_buffer_pct))
            target_prep_pool = pred_demand + buffer_units

            current_stock = item.inventory.current_stock_qty if item.inventory else 0
            min_thresh = item.inventory.min_threshold_qty if item.inventory else 10

            # Prep recommendation = max(0, target_prep_pool - current_stock)
            rec_prep = max(0, target_prep_pool - current_stock)

            item_prep_cost = round(rec_prep * item.standard_prep_cost, 2)
            item_exp_rev = round(pred_demand * item.unit_price, 2)
            item_profit = round(item_exp_rev - item_prep_cost, 2)

            # Stock risk categorization
            if current_stock < min_thresh:
                stock_alert = "Critical Shortage Risk"
                badge_color = "red"
            elif current_stock < pred_demand:
                stock_alert = "Needs Fresh Batch Prep"
                badge_color = "amber"
            else:
                stock_alert = "Adequate Stock Available"
                badge_color = "green"

            # Shelf-life risk profile
            if item.shelf_life_hours <= 6:
                shelf_risk = "High Spoilage Risk (Cook in Batches)"
            elif item.shelf_life_hours <= 12:
                shelf_risk = "Moderate (Day Shift Prep)"
            else:
                shelf_risk = "Low Spoilage (Stable Prep)"

            recommendation_item = {
                'item_id': item.id,
                'item_name': item.item_name,
                'category': item.category,
                'unit_price': float(item.unit_price),
                'standard_prep_cost': float(item.standard_prep_cost),
                'shelf_life_hours': item.shelf_life_hours,
                'shelf_risk': shelf_risk,
                'current_stock': current_stock,
                'min_threshold': min_thresh,
                'predicted_demand': pred_demand,
                'safety_buffer_units': buffer_units,
                'target_total_pool': target_prep_pool,
                'recommended_prep_qty': rec_prep,
                'estimated_prep_cost': item_prep_cost,
                'expected_revenue': item_exp_rev,
                'projected_profit': item_profit,
                'stock_alert': stock_alert,
                'badge_color': badge_color,
                'historical_records': hist_records,
                'live_orders_today': live_today,
                'is_new_dish': hist_records == 0
            }

            recommendations.append(recommendation_item)

            total_predicted_demand += pred_demand
            total_buffer_units += buffer_units
            total_prep_units += rec_prep
            total_prep_cost += item_prep_cost
            total_expected_revenue += item_exp_rev

        projected_gross_margin = 0.0
        if total_expected_revenue > 0:
            projected_gross_margin = round(((total_expected_revenue - total_prep_cost) / total_expected_revenue) * 100, 1)

        summary = {
            'total_menu_items': len(menu_items),
            'total_predicted_demand': total_predicted_demand,
            'total_buffer_units': total_buffer_units,
            'total_prep_units': total_prep_units,
            'total_prep_cost': round(total_prep_cost, 2),
            'total_expected_revenue': round(total_expected_revenue, 2),
            'projected_gross_profit': round(total_expected_revenue - total_prep_cost, 2),
            'projected_margin_percent': projected_gross_margin
        }

        metadata = {
            'target_date': target_date.strftime('%Y-%m-%d'),
            'day_name': target_date.strftime('%A'),
            'day_type': day_type,
            'customer_count': customer_count,
            'weather_condition': weather_condition,
            'safety_buffer_percent': int(safety_buffer_pct * 100)
        }

        return {
            'recommendations': recommendations,
            'summary': summary,
            'metadata': metadata
        }
