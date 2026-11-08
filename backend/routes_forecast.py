"""
AI Demand Forecasting & Prep Planning Module:
Calculates daily kitchen preparation recommendations, what-if simulations, and model retraining.
"""

from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from backend.auth import login_required, role_required
from backend.models import ProductMenu
from backend.config import Config
from ml_model.predictor import DemandPredictor
from ml_model.train import train_demand_forecasting_model

forecast_bp = Blueprint('forecast', __name__, url_prefix='/forecast')


@forecast_bp.route('/', methods=['GET'])
@login_required
@role_required('admin', 'restaurant_manager')
def index():
    """
    Daily Preparation Recommendations Dashboard:
    Computes expected demand and optimal batch preparation quantities for today.
    """
    # Optional URL params to forecast for custom date/scenario
    date_str = request.args.get('date')
    day_type = request.args.get('day_type')
    weather = request.args.get('weather', 'Sunny')
    customer_count = request.args.get('customers', type=int)

    target_date = date.today()
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = date.today()

    data = DemandPredictor.get_daily_preparation_recommendations(
        target_date=target_date,
        day_type=day_type,
        customer_count=customer_count,
        weather_condition=weather
    )

    metrics = DemandPredictor.get_model_metrics()

    return render_template(
        'forecast/index.html',
        recommendations=data['recommendations'],
        summary=data['summary'],
        metadata=data['metadata'],
        metrics=metrics,
        currency=Config.CURRENCY_SYMBOL
    )


@forecast_bp.route('/simulator', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def simulator():
    """
    Interactive 'What-If' Scenario Planning Sandbox:
    Allows managers to simulate potential party bookings, festivals, and rainstorms.
    """
    day_type = request.values.get('day_type', 'office_party')
    customer_count = request.values.get('customer_count', 180, type=int)
    weather = request.values.get('weather', 'Rainy')
    safety_buffer = request.values.get('safety_buffer', 12, type=int) / 100.0

    simulation = DemandPredictor.get_daily_preparation_recommendations(
        target_date=date.today(),
        day_type=day_type,
        customer_count=customer_count,
        weather_condition=weather,
        safety_buffer_pct=safety_buffer
    )

    metrics = DemandPredictor.get_model_metrics()

    return render_template(
        'forecast/simulator.html',
        recommendations=simulation['recommendations'],
        summary=simulation['summary'],
        metadata=simulation['metadata'],
        metrics=metrics,
        currency=Config.CURRENCY_SYMBOL
    )


@forecast_bp.route('/retrain', methods=['POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def retrain():
    """
    Triggers model training workflow on demand with current database records.
    """
    try:
        report = train_demand_forecasting_model()
        DemandPredictor.reload_pipeline()
        if report:
            flash(
                f"AI Demand Forecasting Model retrained successfully! Champion: {report['champion_model']} "
                f"| R2: {report['r2_score']} | MAE: {report['mae']} units.",
                "success"
            )
        else:
            flash("Retraining completed, but dataset was too small for high-confidence metrics.", "warning")
    except Exception as e:
        flash(f"Error during model retraining: {str(e)}", "danger")

    return redirect(request.referrer or url_for('forecast.index'))
