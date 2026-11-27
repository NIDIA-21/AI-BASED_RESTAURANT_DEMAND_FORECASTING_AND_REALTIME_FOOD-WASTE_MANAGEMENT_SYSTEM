"""
Flask Application Factory:
Initializes database connections, registers blueprints, injects template context,
and provides startup lifecycle hooks for automatic DB table creation, seeding, and ML model training.
"""

import os
from pathlib import Path
from flask import Flask, session, request
from backend.config import Config
from backend.models import db, User, ProductMenu, InventoryStock, SurplusRedistribution

def create_app(config_class=Config):
    """
    Constructs and configures the Flask application.
    """
    base_dir = Path(__file__).resolve().parent.parent
    template_dir = base_dir / 'templates'
    static_dir = base_dir / 'static'

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )
    app.config.from_object(config_class)

    # Initialize SQLAlchemy
    db.init_app(app)

    # Register Blueprints
    from backend.auth import auth_bp
    from backend.routes_dashboard import dashboard_bp
    from backend.routes_orders import orders_bp
    from backend.routes_inventory import inventory_bp
    from backend.routes_forecast import forecast_bp
    from backend.routes_surplus import surplus_bp
    from backend.routes_api import api_bp
    from backend.routes_menu import menu_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(surplus_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(menu_bp)

    # Custom Jinja filters
    @app.template_filter('currency')
    def format_currency(value):
        try:
            return f"{Config.CURRENCY_SYMBOL}{float(value):,.2f}"
        except (ValueError, TypeError):
            return f"{Config.CURRENCY_SYMBOL}0.00"

    # Global context processors for templates
    @app.context_processor
    def inject_global_variables():
        user_id = session.get('user_id')
        current_user_obj = None
        if user_id:
            current_user_obj = db.session.get(User, user_id)

        # Count active available surplus items for navigation badge
        available_surplus_badge = SurplusRedistribution.query.filter_by(
            status='available_for_ngo'
        ).count()

        # Count low stock alerts for inventory badge
        low_stock_badge = InventoryStock.query.filter(
            InventoryStock.current_stock_qty <= InventoryStock.min_threshold_qty
        ).count()

        return {
            'current_user': current_user_obj,
            'active_role': session.get('role', 'guest'),
            'restaurant_name': Config.RESTAURANT_NAME,
            'currency_symbol': Config.CURRENCY_SYMBOL,
            'available_surplus_badge': available_surplus_badge,
            'low_stock_badge': low_stock_badge
        }

    # Startup lifecycle hooks: create tables, seed, train ML model
    with app.app_context():
        try:
            # Create tables if not existing
            db.create_all()

            # Seed initial menu & synthetic history only when the database has no menu items yet
            # (preserves manager-added or deleted dishes across server restarts)
            if ProductMenu.query.count() == 0:
                print("[STARTUP] Seeding database with initial Indian Menu Items & Food Waste schema...")
                from database.seed_data import seed_all_data
                seed_all_data(days_of_history=90, force=True)
                from ml_model.train import train_demand_forecasting_model
                train_demand_forecasting_model()
            elif not Config.MODEL_FILE_PATH.exists():
                print("[STARTUP] ML model artifact not found. Triggering initial model training...")
                from ml_model.train import train_demand_forecasting_model
                train_demand_forecasting_model()

        except Exception as e:
            print(f"[STARTUP EXCEPTION] Initial setup notice: {e}")

    return app
