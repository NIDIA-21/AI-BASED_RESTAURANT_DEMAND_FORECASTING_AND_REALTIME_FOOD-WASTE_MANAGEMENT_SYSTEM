"""
Inventory Management Module:
Controls real-time stock levels, threshold monitoring, and stock replenishments.
"""

from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from backend.models import db, ProductMenu, InventoryStock, InventoryLog, InventoryIngredient
from backend.auth import login_required, role_required
from backend.config import Config
from flask import session

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('/', methods=['GET'])
@login_required
@role_required('admin', 'restaurant_manager', 'inventory_staff')
def index():
    """
    Inventory Stock Table:
    Highlights low stock alerts, stock health ratios, and restock actions.
    """
    filter_status = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()

    stocks = InventoryStock.query.join(ProductMenu).order_by(ProductMenu.category, ProductMenu.item_name).all()

    # Filter in Python or SQL
    filtered_stocks = []
    for s in stocks:
        if search_query and search_query.lower() not in s.product.item_name.lower() and search_query.lower() not in s.product.category.lower():
            continue
        if filter_status == 'low' and not s.is_low_stock:
            continue
        if filter_status == 'out' and s.current_stock_qty > 0:
            continue
        if filter_status == 'healthy' and s.stock_status != 'healthy':
            continue
        filtered_stocks.append(s)

    # Health summary metrics
    total_items = len(stocks)
    out_of_stock_count = sum(1 for s in stocks if s.current_stock_qty == 0)
    low_stock_count = sum(1 for s in stocks if s.is_low_stock and s.current_stock_qty > 0)
    healthy_stock_count = sum(1 for s in stocks if s.stock_status == 'healthy')
    total_portions_on_hand = sum(s.current_stock_qty for s in stocks)

    # Raw ingredients tracking
    ingredients = InventoryIngredient.query.order_by(InventoryIngredient.category, InventoryIngredient.ingredient_name).all()
    expiring_soon_count = sum(1 for i in ingredients if i.is_expiring_soon)
    low_ingredients_count = sum(1 for i in ingredients if i.is_low_stock)

    return render_template(
        'inventory/index.html',
        stocks=filtered_stocks,
        ingredients=ingredients,
        expiring_soon_count=expiring_soon_count,
        low_ingredients_count=low_ingredients_count,
        total_items=total_items,
        out_of_stock_count=out_of_stock_count,
        low_stock_count=low_stock_count,
        healthy_stock_count=healthy_stock_count,
        total_portions_on_hand=total_portions_on_hand,
        filter_status=filter_status,
        search_query=search_query,
        currency=Config.CURRENCY_SYMBOL
    )


@inventory_bp.route('/restock/<int:item_id>', methods=['POST'])
@login_required
@role_required('admin', 'restaurant_manager', 'inventory_staff')
def restock(item_id):
    """
    Adds inventory stock quantity and optionally updates reorder threshold.
    """
    add_qty = request.form.get('add_qty', 0, type=int)
    min_threshold = request.form.get('min_threshold', type=int)

    if add_qty < 0:
        flash("Restock quantity cannot be negative.", "warning")
        return redirect(url_for('inventory.index'))

    inventory = InventoryStock.query.filter_by(item_id=item_id).first()
    product = db.get_or_404(ProductMenu, item_id)

    prev_stock = inventory.current_stock_qty if inventory else 0
    if not inventory:
        inventory = InventoryStock(item_id=item_id, current_stock_qty=add_qty, min_threshold_qty=min_threshold or 10)
        db.session.add(inventory)
        new_stock = add_qty
    else:
        inventory.current_stock_qty += add_qty
        new_stock = inventory.current_stock_qty
        if min_threshold is not None and min_threshold >= 0:
            inventory.min_threshold_qty = min_threshold
        inventory.last_restocked_at = datetime.now(timezone.utc)

    # Record InventoryLog
    inv_log = InventoryLog(
        item_id=item_id,
        change_qty=+add_qty,
        previous_stock=prev_stock,
        new_stock=new_stock,
        reason='restock',
        logged_at=datetime.now(timezone.utc),
        created_by_user_id=session.get('user_id')
    )
    db.session.add(inv_log)
    db.session.commit()

    flash(
        f"Restocked {add_qty} portions of '{product.item_name}'. New stock level: {inventory.current_stock_qty} units.",
        "success"
    )
    return redirect(request.referrer or url_for('inventory.index'))
