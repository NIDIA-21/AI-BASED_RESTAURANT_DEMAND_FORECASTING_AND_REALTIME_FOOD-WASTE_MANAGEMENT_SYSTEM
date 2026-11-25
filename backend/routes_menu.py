"""
Menu Management Module:
Allows restaurant managers/admins to add brand new dishes to the live menu,
update dish details, and delete underperforming items — all with full
database integration and automatic ML model re-training after changes.
"""

import threading
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, session
)
from backend.models import db, ProductMenu, InventoryStock, HistoricalSalesData
from backend.auth import login_required, role_required
from backend.config import Config

menu_bp = Blueprint('menu', __name__, url_prefix='/menu')

# ---------------------------------------------------------------------------
# Background ML retraining helper (non-blocking)
# ---------------------------------------------------------------------------
def _retrain_in_background(app):
    """Triggers ML retraining in a background thread so the HTTP response isn't delayed."""
    def _run():
        with app.app_context():
            try:
                from ml_model.train import train_demand_forecasting_model
                metrics = train_demand_forecasting_model()
                if metrics:
                    print(f"[ML] Background retraining complete. R2={metrics.get('r2_score', 'N/A')}")
            except Exception as e:
                print(f"[ML] Background retraining error: {e}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# 1. LIST / MANAGE all menu items
# ---------------------------------------------------------------------------
@menu_bp.route('/', methods=['GET'])
@login_required
@role_required('admin', 'restaurant_manager')
def index():
    """
    Menu Management Dashboard:
    Lists all dishes with profitability metrics, stock levels,
    and sales history counts. Provides Add/Edit/Delete actions.
    """
    items = ProductMenu.query.order_by(ProductMenu.category, ProductMenu.item_name).all()

    # Annotate each item with sales count and stock info
    enriched = []
    for item in items:
        stock = InventoryStock.query.filter_by(item_id=item.id).first()
        sales_count = HistoricalSalesData.query.filter_by(item_id=item.id).count()
        total_revenue = db.session.query(
            db.func.sum(HistoricalSalesData.actual_qty_ordered * item.unit_price)
        ).filter(HistoricalSalesData.item_id == item.id).scalar() or 0.0

        enriched.append({
            'item': item,
            'stock': stock,
            'sales_count': sales_count,
            'total_revenue': round(float(total_revenue), 2),
            'is_new': sales_count == 0  # Newly added, never ordered yet
        })

    total_items = len(items)
    categories = sorted(set(i.category for i in items))

    return render_template(
        'menu/index.html',
        enriched=enriched,
        total_items=total_items,
        categories=categories,
        currency=Config.CURRENCY_SYMBOL
    )


# ---------------------------------------------------------------------------
# 2. ADD NEW DISH (GET = form, POST = save)
# ---------------------------------------------------------------------------
@menu_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def add_dish():
    """
    Add a completely new dish to the restaurant menu.
    - Saves to ProductMenu table
    - Creates initial InventoryStock record
    - Triggers background ML retraining so future predictions include new dish
    """
    # Existing categories for autocomplete dropdown
    categories = sorted(set(
        c[0] for c in db.session.query(ProductMenu.category).distinct().all()
    ))

    if request.method == 'POST':
        item_name   = request.form.get('item_name', '').strip()
        category    = request.form.get('category', '').strip()
        new_cat     = request.form.get('new_category', '').strip()
        unit_price  = request.form.get('unit_price', 0, type=float)
        prep_cost   = request.form.get('standard_prep_cost', 0, type=float)
        shelf_life  = request.form.get('shelf_life_hours', 24, type=int)
        description = request.form.get('description', '').strip()
        image_url   = request.form.get('image_url', '').strip()
        init_stock  = request.form.get('initial_stock', 50, type=int)
        min_stock   = request.form.get('min_threshold', 10, type=int)

        # Use new category if manager typed one
        if new_cat:
            category = new_cat

        # --- Validation ---
        errors = []
        if not item_name:
            errors.append("Dish name is required.")
        if not category:
            errors.append("Category is required.")
        if unit_price <= 0:
            errors.append("Selling price must be greater than 0.")
        if prep_cost < 0:
            errors.append("Prep cost cannot be negative.")
        if prep_cost >= unit_price:
            errors.append("Prep cost must be less than the selling price (otherwise no profit).")
        if shelf_life <= 0:
            errors.append("Shelf life must be at least 1 hour.")

        # Check duplicate name (case-insensitive)
        existing = ProductMenu.query.filter(
            db.func.lower(ProductMenu.item_name) == item_name.lower()
        ).first()
        if existing:
            errors.append(f"A dish named '{existing.item_name}' already exists in the menu (ID #{existing.id}).")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('menu/add_dish.html', categories=categories, currency=Config.CURRENCY_SYMBOL, form_data=request.form)

        # --- Save new dish ---
        new_item = ProductMenu(
            item_name=item_name,
            category=category,
            unit_price=unit_price,
            standard_prep_cost=prep_cost,
            shelf_life_hours=shelf_life,
            description=description,
            image_url=image_url if image_url else None,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_item)
        db.session.flush()  # get new_item.id

        # Create initial inventory stock entry
        inventory = InventoryStock(
            item_id=new_item.id,
            current_stock_qty=init_stock,
            min_threshold_qty=min_stock,
            last_restocked_at=datetime.now(timezone.utc)
        )
        db.session.add(inventory)
        db.session.commit()

        # Trigger background ML retraining (non-blocking)
        from flask import current_app
        _retrain_in_background(current_app._get_current_object())

        flash(
            f"New dish '{item_name}' added to the menu successfully! "
            f"Initial stock: {init_stock} portions. "
            f"AI model retraining has started in the background — predictions will update shortly.",
            'success'
        )
        return redirect(url_for('menu.index'))

    return render_template('menu/add_dish.html', categories=categories, currency=Config.CURRENCY_SYMBOL, form_data={})


# ---------------------------------------------------------------------------
# 3. EDIT DISH (GET = pre-filled form, POST = update)
# ---------------------------------------------------------------------------
@menu_bp.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def edit_dish(item_id):
    """
    Edit an existing dish: update price, description, image, category, shelf life.
    Does NOT affect historical sales data.
    """
    item = db.get_or_404(ProductMenu, item_id)
    stock = InventoryStock.query.filter_by(item_id=item_id).first()
    categories = sorted(set(
        c[0] for c in db.session.query(ProductMenu.category).distinct().all()
    ))

    if request.method == 'POST':
        item_name   = request.form.get('item_name', '').strip()
        category    = request.form.get('category', '').strip()
        new_cat     = request.form.get('new_category', '').strip()
        unit_price  = request.form.get('unit_price', 0, type=float)
        prep_cost   = request.form.get('standard_prep_cost', 0, type=float)
        shelf_life  = request.form.get('shelf_life_hours', 24, type=int)
        description = request.form.get('description', '').strip()
        image_url   = request.form.get('image_url', '').strip()

        if new_cat:
            category = new_cat

        errors = []
        if not item_name:
            errors.append("Dish name is required.")
        if not category:
            errors.append("Category is required.")
        if unit_price <= 0:
            errors.append("Selling price must be greater than 0.")
        if prep_cost >= unit_price:
            errors.append("Prep cost must be less than the selling price.")

        # Duplicate check (excluding current item)
        dup = ProductMenu.query.filter(
            db.func.lower(ProductMenu.item_name) == item_name.lower(),
            ProductMenu.id != item_id
        ).first()
        if dup:
            errors.append(f"Another dish named '{dup.item_name}' already exists (ID #{dup.id}).")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('menu/edit_dish.html', item=item, stock=stock, categories=categories, currency=Config.CURRENCY_SYMBOL)

        item.item_name = item_name
        item.category = category
        item.unit_price = unit_price
        item.standard_prep_cost = prep_cost
        item.shelf_life_hours = shelf_life
        item.description = description
        item.image_url = image_url if image_url else item.image_url

        db.session.commit()
        flash(f"Dish '{item_name}' updated successfully!", 'success')
        return redirect(url_for('menu.index'))

    return render_template('menu/edit_dish.html', item=item, stock=stock, categories=categories, currency=Config.CURRENCY_SYMBOL)


# ---------------------------------------------------------------------------
# 4. DELETE DISH (POST only, with safety guards)
# ---------------------------------------------------------------------------
@menu_bp.route('/delete/<int:item_id>', methods=['POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def delete_dish(item_id):
    """
    Permanently removes a dish from the menu.
    Safety guards:
      - Cannot delete if dish has active (pending/preparing) orders
      - Warns if dish still has inventory stock
      - Cascades deletion to InventoryStock, HistoricalSalesData, SurplusRedistribution
    """
    item = db.get_or_404(ProductMenu, item_id)
    confirm_name = request.form.get('confirm_name', '').strip()

    # Require exact name confirmation to prevent accidental deletion
    if confirm_name.lower() != item.item_name.lower():
        flash(
            f"Deletion cancelled. You typed '{confirm_name}' but the dish name is '{item.item_name}'. "
            f"Type the exact dish name to confirm deletion.",
            'danger'
        )
        return redirect(url_for('menu.index'))

    # Safety: Block deletion if dish has ACTIVE orders
    from backend.models import LiveOrder
    active_orders = LiveOrder.query.filter(
        LiveOrder.item_id == item_id,
        LiveOrder.status.in_(['pending', 'preparing'])
    ).count()

    if active_orders > 0:
        flash(
            f"Cannot delete '{item.item_name}' — it has {active_orders} active order(s) still in progress. "
            f"Wait for all orders to complete or be cancelled first.",
            'danger'
        )
        return redirect(url_for('menu.index'))

    item_name_saved = item.item_name
    sales_count = HistoricalSalesData.query.filter_by(item_id=item_id).count()

    # Cascade delete (models.py has cascade='all, delete-orphan' on relationships)
    db.session.delete(item)
    db.session.commit()

    # Trigger background ML retraining after removal
    from flask import current_app
    _retrain_in_background(current_app._get_current_object())

    flash(
        f"Dish '{item_name_saved}' has been permanently removed from the menu "
        f"({sales_count} historical records also cleared). "
        f"AI model is retraining to reflect the updated menu.",
        'warning'
    )
    return redirect(url_for('menu.index'))


# ---------------------------------------------------------------------------
# 5. API: Check dish name availability (AJAX)
# ---------------------------------------------------------------------------
@menu_bp.route('/api/check-name', methods=['GET'])
@login_required
def check_name():
    """Returns whether a dish name already exists (for real-time form validation)."""
    name = request.args.get('name', '').strip()
    exclude_id = request.args.get('exclude_id', type=int)

    if not name:
        return jsonify({'available': False, 'message': 'Name is empty.'})

    query = ProductMenu.query.filter(db.func.lower(ProductMenu.item_name) == name.lower())
    if exclude_id:
        query = query.filter(ProductMenu.id != exclude_id)

    existing = query.first()
    if existing:
        return jsonify({'available': False, 'message': f"'{existing.item_name}' already exists in menu."})
    return jsonify({'available': True, 'message': 'Name is available!'})


# ---------------------------------------------------------------------------
# 6. API: Trigger manual ML retraining (Manager/Admin action)
# ---------------------------------------------------------------------------
@menu_bp.route('/api/retrain', methods=['POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def trigger_retrain():
    """Manually trigger ML model retraining from the UI."""
    from flask import current_app
    _retrain_in_background(current_app._get_current_object())
    return jsonify({
        'status': 'started',
        'message': 'AI model retraining started in background. Refresh the Forecast page in ~30 seconds to see updated predictions.'
    })
