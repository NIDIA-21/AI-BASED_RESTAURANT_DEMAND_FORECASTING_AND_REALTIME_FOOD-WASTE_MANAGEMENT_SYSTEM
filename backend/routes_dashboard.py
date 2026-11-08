"""
ERP Management Dashboard & Dynamic Alert System:
Aggregates high-level analytics, KPI summary cards, and calculates real-time
shortage versus food waste risk alerts comparing live order velocity against AI demand predictions.
"""

from datetime import datetime, date, timezone, timedelta
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from backend.models import (
    db, ProductMenu, InventoryStock, LiveOrder,
    HistoricalSalesData, SurplusRedistribution, User
)
from backend.auth import login_required
from backend.config import Config
from ml_model.predictor import DemandPredictor

dashboard_bp = Blueprint('dashboard', __name__)


def calculate_dynamic_alerts(target_date: date = None):
    """
    DYNAMIC ALERT ENGINE:
    Compares real-time live order velocity against AI-predicted demand curves.
    Generates actionable shortage alerts and excess preparation/waste risk warnings.
    """
    if target_date is None:
        target_date = date.today()

    # Get predictions for today
    prep_data = DemandPredictor.get_daily_preparation_recommendations(target_date=target_date)
    recommendations_map = {r['item_id']: r for r in prep_data['recommendations']}

    # Calculate actual orders placed today per item
    today_start = datetime.combine(target_date, datetime.min.time())
    today_orders = LiveOrder.query.filter(
        LiveOrder.order_time >= today_start,
        LiveOrder.status != 'cancelled'
    ).all()

    item_ordered_counts = {}
    for o in today_orders:
        item_ordered_counts[o.item_id] = item_ordered_counts.get(o.item_id, 0) + o.quantity

    # Operating shift progress (assuming a 12-hour dining window from 11:00 AM to 11:00 PM)
    now = datetime.now()
    hour = now.hour + (now.minute / 60.0)
    # Clamp fraction of day between 0.15 and 0.95 for realistic velocity extrapolation
    if hour < 11.0:
        day_progress_fraction = 0.20 # Early morning prep
    elif hour >= 23.0:
        day_progress_fraction = 0.95 # Closing service
    else:
        day_progress_fraction = max(0.15, min(0.95, (hour - 11.0) / 12.0))

    shortage_alerts = []
    waste_risk_alerts = []
    balanced_items = []

    for item_id, rec in recommendations_map.items():
        predicted = rec['predicted_demand']
        ordered_so_far = item_ordered_counts.get(item_id, 0)
        current_stock = rec['current_stock']
        min_threshold = rec['min_threshold']
        shelf_life = rec['shelf_life_hours']

        # Extrapolated daily order velocity
        projected_total_orders = int(round(ordered_so_far / day_progress_fraction))
        total_available = ordered_so_far + current_stock

        # 1. SHORTAGE RISK DETECTION:
        # If stock is critically depleted OR demand pace will exceed total prep before service ends
        is_stockout = current_stock == 0
        is_below_min = current_stock <= min_threshold
        is_velocity_surge = (ordered_so_far >= 0.70 * predicted and day_progress_fraction < 0.60) or (projected_total_orders > total_available)

        if is_stockout or is_below_min or is_velocity_surge:
            deficit = max(0, projected_total_orders - total_available)
            if deficit == 0 and is_below_min:
                deficit = min_threshold - current_stock + 5

            urgency = "CRITICAL" if (is_stockout or current_stock < 3) else "HIGH"
            shortage_alerts.append({
                'item_id': item_id,
                'item_name': rec['item_name'],
                'category': rec['category'],
                'urgency': urgency,
                'predicted_demand': predicted,
                'ordered_so_far': ordered_so_far,
                'current_stock': current_stock,
                'min_threshold': min_threshold,
                'projected_orders': projected_total_orders,
                'deficit_units': deficit,
                'message': (
                    f"Order velocity ({ordered_so_far} orders at {int(day_progress_fraction*100)}% shift) "
                    f"exceeds stock buffer. Current inventory ({current_stock}) will stock out soon!"
                ),
                'action_recommendation': f"Immediate Action: Kitchen prep batch of +{max(5, deficit)} portions recommended."
            })

        # 2. EXCESS PREPARATION / FOOD WASTE RISK DETECTION:
        # If time is past mid-shift (>= 40%), orders are significantly lower than predicted (< 35%),
        # and physical stock is high with short shelf-life
        elif (day_progress_fraction >= 0.40 and ordered_so_far < 0.35 * predicted and current_stock > 0.50 * predicted and shelf_life <= 12):
            excess_estimate = max(5, int(current_stock - (projected_total_orders - ordered_so_far)))
            waste_risk_alerts.append({
                'item_id': item_id,
                'item_name': rec['item_name'],
                'category': rec['category'],
                'severity': 'MODERATE' if shelf_life > 6 else 'HIGH',
                'predicted_demand': predicted,
                'ordered_so_far': ordered_so_far,
                'current_stock': current_stock,
                'shelf_life_hours': shelf_life,
                'excess_units': excess_estimate,
                'message': (
                    f"Low ordering velocity ({ordered_so_far}/{predicted} sold). "
                    f"High unconsumed stock ({current_stock} portions) nearing {shelf_life}h shelf-life."
                ),
                'action_recommendation': (
                    f"Waste Prevention: Halt kitchen prep. Log {min(current_stock, excess_estimate)} portions "
                    f"for Happy Hour promo or Surplus NGO Redistribution before expiry."
                )
            })
        else:
            balanced_items.append(rec['item_name'])

    return {
        'shortage_alerts': shortage_alerts,
        'waste_risk_alerts': waste_risk_alerts,
        'balanced_count': len(balanced_items),
        'shift_progress_percent': int(day_progress_fraction * 100),
        'total_alerts_count': len(shortage_alerts) + len(waste_risk_alerts)
    }


@dashboard_bp.route('/', methods=['GET'])
@login_required
def index():
    """
    Main SaaS ERP Dashboard:
    Odoo / Stripe style high-level analytics summary cards, dynamic alert banners,
    live sales counters, and demand comparison charts.
    """
    # Customer role is redirected to POS / Order view
    if session.get('role') == 'customer':
        return redirect(url_for('orders.pos_view'))

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    # 1. High-Level KPI Summary Metrics
    # Today's active orders
    today_orders = LiveOrder.query.filter(LiveOrder.order_time >= today_start).all()
    active_orders = [o for o in today_orders if o.status in ('pending', 'preparing')]
    completed_orders = [o for o in today_orders if o.status == 'completed']

    today_revenue = sum((o.total_price or 0.0) for o in today_orders if o.status != 'cancelled')
    total_orders_today = len([o for o in today_orders if o.status != 'cancelled'])

    # Inventory Health
    total_inventory_items = InventoryStock.query.count()
    low_stock_items = InventoryStock.query.filter(
        InventoryStock.current_stock_qty <= InventoryStock.min_threshold_qty
    ).count()

    # Surplus & NGO Food Recovery Impact
    surplus_records = SurplusRedistribution.query.all()
    total_portions_saved = sum(s.surplus_qty for s in surplus_records)
    active_available_surplus = SurplusRedistribution.query.filter_by(status='available_for_ngo').count()
    total_co2_kg = round(total_portions_saved * 2.5, 1)

    # 2. Dynamic Shortage vs Waste Risk Alerts
    alerts_data = calculate_dynamic_alerts(target_date=today)

    # 3. AI Prediction Summary
    prep_data = DemandPredictor.get_daily_preparation_recommendations(target_date=today)
    metrics = DemandPredictor.get_model_metrics()

    # 4. Top Demanded Items for Today
    top_recommendations = sorted(
        prep_data['recommendations'],
        key=lambda x: x['predicted_demand'],
        reverse=True
    )[:6]

    # 5. Recent Live Orders
    recent_orders = LiveOrder.query.order_by(LiveOrder.order_time.desc()).limit(8).all()

    return render_template(
        'dashboard/index.html',
        today_date=today.strftime('%A, %B %d, %Y'),
        today_revenue=today_revenue,
        total_orders_today=total_orders_today,
        active_orders_count=len(active_orders),
        completed_orders_count=len(completed_orders),
        total_inventory_items=total_inventory_items,
        low_stock_items=low_stock_items,
        total_portions_saved=total_portions_saved,
        active_available_surplus=active_available_surplus,
        total_co2_kg=total_co2_kg,
        alerts_data=alerts_data,
        prep_summary=prep_data['summary'],
        metadata=prep_data['metadata'],
        top_recommendations=top_recommendations,
        recent_orders=recent_orders,
        metrics=metrics,
        currency=Config.CURRENCY_SYMBOL
    )
