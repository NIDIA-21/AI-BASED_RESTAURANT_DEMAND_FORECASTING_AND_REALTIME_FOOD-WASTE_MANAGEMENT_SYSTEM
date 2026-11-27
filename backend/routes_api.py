"""
RESTful JSON API Module:
Supplies live data streams for AJAX charts, real-time metrics polling, and mobile/external integrations.
"""

from datetime import datetime, date, timedelta, timezone
from flask import Blueprint, jsonify, request
from backend.models import db, ProductMenu, InventoryStock, LiveOrder, SurplusRedistribution
from backend.routes_dashboard import calculate_dynamic_alerts
from ml_model.predictor import DemandPredictor
from backend.config import Config

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """Returns high-level KPI metrics in JSON format."""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    today_orders = LiveOrder.query.filter(LiveOrder.order_time >= today_start).all()
    today_revenue = sum((o.total_price or 0.0) for o in today_orders if o.status != 'cancelled')
    active_orders = len([o for o in today_orders if o.status in ('pending', 'preparing')])
    completed_orders = len([o for o in today_orders if o.status == 'completed'])

    low_stock_count = InventoryStock.query.filter(
        InventoryStock.current_stock_qty <= InventoryStock.min_threshold_qty
    ).count()

    alerts = calculate_dynamic_alerts(today)

    return jsonify({
        'status': 'success',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'metrics': {
            'today_revenue': round(today_revenue, 2),
            'currency': Config.CURRENCY_SYMBOL,
            'total_orders': len(today_orders),
            'active_orders': active_orders,
            'completed_orders': completed_orders,
            'low_stock_count': low_stock_count,
            'critical_shortage_alerts': len(alerts['shortage_alerts']),
            'waste_risk_alerts': len(alerts['waste_risk_alerts']),
            'shift_progress_percent': alerts['shift_progress_percent']
        }
    })


@api_bp.route('/charts/demand-vs-actual', methods=['GET'])
def chart_demand_vs_actual():
    """
    Feeds Chart.js grouped bar chart comparing AI Predicted Demand vs Live Actual Orders.
    """
    today = date.today()
    prep_data = DemandPredictor.get_daily_preparation_recommendations(target_date=today)
    recommendations = prep_data['recommendations']

    # Get today's actual orders per item
    today_start = datetime.combine(today, datetime.min.time())
    today_orders = LiveOrder.query.filter(
        LiveOrder.order_time >= today_start,
        LiveOrder.status != 'cancelled'
    ).all()

    actual_map = {}
    for o in today_orders:
        actual_map[o.item_id] = actual_map.get(o.item_id, 0) + o.quantity

    labels = []
    predicted_values = []
    actual_values = []
    current_stocks = []

    # Sort by predicted demand descending, include all active menu items (both existing and newly added dishes)
    sorted_recs = sorted(recommendations, key=lambda x: x['predicted_demand'], reverse=True)

    for r in sorted_recs:
        labels.append(r['item_name'])
        predicted_values.append(r['predicted_demand'])
        actual_values.append(actual_map.get(r['item_id'], 0))
        current_stocks.append(r['current_stock'])

    return jsonify({
        'labels': labels,
        'datasets': [
            {
                'label': 'AI Predicted Demand',
                'data': predicted_values,
                'backgroundColor': 'rgba(59, 130, 246, 0.75)', # Blue
                'borderColor': 'rgb(37, 99, 235)',
                'borderWidth': 1.5,
                'borderRadius': 4
            },
            {
                'label': 'Live Actual Orders',
                'data': actual_values,
                'backgroundColor': 'rgba(16, 185, 129, 0.85)', # Emerald Green
                'borderColor': 'rgb(5, 150, 105)',
                'borderWidth': 1.5,
                'borderRadius': 4
            },
            {
                'label': 'Current Stock on Hand',
                'data': current_stocks,
                'backgroundColor': 'rgba(245, 158, 11, 0.75)', # Amber
                'borderColor': 'rgb(217, 119, 6)',
                'borderWidth': 1.5,
                'borderRadius': 4
            }
        ]
    })


@api_bp.route('/charts/category-breakdown', methods=['GET'])
def chart_category_breakdown():
    """
    Feeds Chart.js Donut chart for category-wise demand distribution.
    """
    prep_data = DemandPredictor.get_daily_preparation_recommendations()
    cat_totals = {}
    for r in prep_data['recommendations']:
        cat = r['category']
        cat_totals[cat] = cat_totals.get(cat, 0) + r['predicted_demand']

    labels = list(cat_totals.keys())
    values = list(cat_totals.values())

    return jsonify({
        'labels': labels,
        'data': values
    })


@api_bp.route('/alerts/dynamic', methods=['GET'])
def get_dynamic_alerts():
    """Returns dynamic alerts list."""
    alerts = calculate_dynamic_alerts()
    return jsonify(alerts)
