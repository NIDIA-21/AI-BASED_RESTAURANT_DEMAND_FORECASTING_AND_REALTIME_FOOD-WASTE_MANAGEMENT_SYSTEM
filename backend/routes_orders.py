"""
Real-Time Order Monitoring & POS Module:
Handles live order taking, atomic inventory stock deduction,
audit logging via InventoryLog, and reactive Kitchen Display System (KDS) lifecycle.
"""

from datetime import datetime, timezone, date
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, current_app
)
from backend.models import db, ProductMenu, InventoryStock, LiveOrder, User, InventoryLog, HistoricalSalesData
from backend.auth import login_required, role_required
from backend.config import Config
from ml_model.train import trigger_async_retrain

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


def _sync_order_to_historical_sales(item_id: int, delta_qty: int, order_date: date = None):
    """
    Records or adjusts today's live order volume inside HistoricalSalesData so
    every order for existing or newly added dishes feeds into AI retraining.
    """
    target_date = order_date or date.today()
    day_type = 'weekend' if target_date.weekday() in (4, 5, 6) else 'weekday'
    baseline_footfall = 210 if day_type == 'weekend' else 85

    day_start = datetime.combine(target_date, datetime.min.time())
    day_orders_count = LiveOrder.query.filter(
        LiveOrder.order_time >= day_start,
        LiveOrder.status != 'cancelled'
    ).count()
    estimated_customer_count = max(baseline_footfall, day_orders_count * 3)

    existing_hist = HistoricalSalesData.query.filter_by(
        date=target_date,
        item_id=item_id
    ).first()

    if existing_hist:
        updated_qty = (existing_hist.actual_qty_ordered or 0) + delta_qty
        if updated_qty <= 0:
            db.session.delete(existing_hist)
        else:
            existing_hist.actual_qty_ordered = updated_qty
            existing_hist.customer_count = max(existing_hist.customer_count or 0, estimated_customer_count)
    elif delta_qty > 0:
        hist_record = HistoricalSalesData(
            date=target_date,
            item_id=item_id,
            day_type=day_type,
            customer_count=estimated_customer_count,
            actual_qty_ordered=delta_qty,
            weather_condition='Sunny'
        )
        db.session.add(hist_record)


@orders_bp.route('/pos', methods=['GET'])
@login_required
def pos_view():
    """
    Live Order Entry Screen & Customer Visual Menu:
    Interactive POS / order taking interface with category filters,
    high-resolution dish photography, real-time stock availability, and instant ordering.
    """
    category_filter = request.args.get('category', 'all')
    search_query = request.args.get('q', '').strip()

    query = ProductMenu.query
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    if search_query:
        query = query.filter(ProductMenu.item_name.ilike(f"%{search_query}%"))

    menu_items = query.order_by(ProductMenu.category, ProductMenu.item_name).all()
    categories = [c[0] for c in db.session.query(ProductMenu.category).distinct().all()]

    # Customers list for table / customer assignment (Staff/Manager/Admin)
    customers = User.query.filter_by(role='customer').order_by(User.username).all()

    # Calculate today's sales summary
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_orders = LiveOrder.query.filter(LiveOrder.order_time >= today_start).all()
    today_total_sales = sum((o.total_price or 0.0) for o in today_orders if o.status != 'cancelled')
    today_orders_count = len([o for o in today_orders if o.status != 'cancelled'])

    return render_template(
        'orders/pos.html',
        menu_items=menu_items,
        categories=categories,
        selected_category=category_filter,
        search_query=search_query,
        customers=customers,
        currency=Config.CURRENCY_SYMBOL,
        today_total_sales=today_total_sales,
        today_orders_count=today_orders_count
    )


@orders_bp.route('/create', methods=['POST'])
@login_required
def create_order():
    """
    Submits a live customer/POS order safely wrapped in an atomic transaction:
    (a) Creating the LiveOrder
    (b) Decrementing physical InventoryStock
    (c) Writing an audit record to InventoryLog
    Guarantees all three succeed together or rolls back cleanly to prevent partial state corruption.
    """
    # Accept both Form encoded and JSON payload
    data = request.get_json(silent=True) or request.form

    item_id = data.get('item_id', type=int)
    quantity = data.get('quantity', 1, type=int)
    customer_id = data.get('customer_id', type=int)
    customer_name = (data.get('customer_name') or '').strip()
    status = data.get('status') or 'preparing'

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    if not item_id or quantity <= 0:
        if is_ajax:
            return jsonify({'status': 'error', 'message': 'Invalid menu item or quantity specified.'}), 400
        flash("Invalid menu item or quantity specified.", "danger")
        return redirect(url_for('orders.pos_view'))

    product = db.get_or_404(ProductMenu, item_id)

    # Wrap in atomic transaction
    try:
        inventory = InventoryStock.query.filter_by(item_id=item_id).first()

        if not inventory:
            inventory = InventoryStock(item_id=item_id, current_stock_qty=0, min_threshold_qty=10)
            db.session.add(inventory)
            db.session.flush()

        if inventory.current_stock_qty < quantity:
            msg = f"Insufficient Stock! Only {inventory.current_stock_qty} portions of '{product.item_name}' available. Requested: {quantity}."
            if is_ajax:
                return jsonify({'status': 'error', 'message': msg}), 400
            flash(msg, "danger")
            return redirect(url_for('orders.pos_view'))

        prev_stock = inventory.current_stock_qty
        new_stock = prev_stock - quantity

        # (b) Decrement physical inventory
        inventory.current_stock_qty = new_stock

        # Auto-assign customer from session if customer role
        if session.get('role') == 'customer':
            customer_id = session.get('user_id')
            customer_name = session.get('username')

        total_price = round(quantity * product.unit_price, 2)

        # (a) Create LiveOrder
        order = LiveOrder(
            customer_id=customer_id,
            customer_name=customer_name or (session.get('username') if session.get('role') == 'customer' else "Table Guest"),
            item_id=item_id,
            quantity=quantity,
            status=status,
            total_price=total_price,
            order_time=datetime.now(timezone.utc)
        )
        db.session.add(order)
        db.session.flush()

        # (c) Write to InventoryLog audit ledger
        inv_log = InventoryLog(
            item_id=item_id,
            change_qty=-quantity,
            previous_stock=prev_stock,
            new_stock=new_stock,
            reason='pos_order',
            reference_id=order.id,
            logged_at=datetime.now(timezone.utc),
            created_by_user_id=session.get('user_id')
        )
        db.session.add(inv_log)

        # (d) Record to HistoricalSalesData — feeds AI model with live order data
        # Ensures every customer order (old & new dishes) updates the training dataset immediately.
        _sync_order_to_historical_sales(item_id, +quantity, date.today())

        # Commit entire atomic transaction safely
        db.session.commit()

        # (e) Retrain AI demand forecasting model automatically on every customer order
        trigger_async_retrain(current_app._get_current_object(), reason=f"order:{product.item_name}")

        success_msg = f"Order #{order.id} for {quantity}x '{product.item_name}' ({Config.CURRENCY_SYMBOL}{total_price:.2f}) confirmed and deducted from stock!"
        
        if is_ajax:
            return jsonify({
                'status': 'success',
                'order_id': order.id,
                'item_name': product.item_name,
                'quantity': quantity,
                'remaining_stock': inventory.current_stock_qty,
                'is_low_stock': inventory.is_low_stock,
                'message': success_msg
            }), 201

        if inventory.is_low_stock:
            flash(
                f"Order #{order.id} placed! Note: Stock for '{product.item_name}' is now LOW ({inventory.current_stock_qty} left, below threshold {inventory.min_threshold_qty}).",
                "warning"
            )
        else:
            flash(success_msg, "success")

        return redirect(url_for('orders.pos_view'))

    except Exception as e:
        db.session.rollback()
        err_msg = f"Database transaction failed during POS checkout: {str(e)}"
        if is_ajax:
            return jsonify({'status': 'error', 'message': err_msg}), 500
        flash(err_msg, "danger")
        return redirect(url_for('orders.pos_view'))


@orders_bp.route('/list', methods=['GET'])
@login_required
def orders_list():
    """
    Live Kitchen Display System (KDS) & Order Monitor:
    Real-time kitchen order tracking and state management.
    """
    status_filter = request.args.get('status', 'all')
    query = LiveOrder.query

    # If role is customer, show only their orders
    if session.get('role') == 'customer':
        query = query.filter_by(customer_id=session.get('user_id'))
    elif status_filter != 'all':
        query = query.filter_by(status=status_filter)

    orders = query.order_by(LiveOrder.order_time.desc()).limit(100).all()

    # Count by status for header counters
    status_counts = {
        'all': LiveOrder.query.count(),
        'pending': LiveOrder.query.filter_by(status='pending').count(),
        'preparing': LiveOrder.query.filter_by(status='preparing').count(),
        'completed': LiveOrder.query.filter_by(status='completed').count(),
        'cancelled': LiveOrder.query.filter_by(status='cancelled').count()
    }

    return render_template(
        'orders/list.html',
        orders=orders,
        selected_status=status_filter,
        status_counts=status_counts,
        currency=Config.CURRENCY_SYMBOL
    )


@orders_bp.route('/update-status/<int:order_id>/<new_status>', methods=['POST', 'GET'])
@login_required
@role_required('admin', 'restaurant_manager', 'inventory_staff')
def update_status(order_id, new_status):
    """
    REACTIVE KDS WORKFLOW ENDPOINT:
    Transitions order lifecycle: PENDING -> PREPARING -> COMPLETED or CANCELLED.
    - When marked 'completed': updates DB, dynamically updates header counters, and allows action button removal.
    - When marked 'cancelled': automatically returns items to InventoryStock and records an InventoryLog audit entry.
    Supports both instant AJAX fetch calls (returning JSON) and traditional redirects.
    """
    new_status = new_status.lower().strip()
    valid_statuses = ['pending', 'preparing', 'completed', 'cancelled']
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or 'application/json' in request.headers.get('Accept', '')

    if new_status not in valid_statuses:
        if is_ajax:
            return jsonify({'status': 'error', 'message': f"Invalid status '{new_status}'."}), 400
        flash(f"Invalid status '{new_status}'.", "danger")
        return redirect(url_for('orders.orders_list'))

    order = db.get_or_404(LiveOrder, order_id)
    prev_status = order.status

    try:
        # If cancelling an active order, restore inventory and log audit entry
        if new_status == 'cancelled' and prev_status != 'cancelled':
            inventory = InventoryStock.query.filter_by(item_id=order.item_id).first()
            if inventory:
                prev_stock = inventory.current_stock_qty
                inventory.current_stock_qty += order.quantity
                new_stock = inventory.current_stock_qty

                # Record restoration audit entry
                inv_log = InventoryLog(
                    item_id=order.item_id,
                    change_qty=+order.quantity,
                    previous_stock=prev_stock,
                    new_stock=new_stock,
                    reason='cancellation_restore',
                    reference_id=order.id,
                    logged_at=datetime.now(timezone.utc),
                    created_by_user_id=session.get('user_id')
                )
                db.session.add(inv_log)

            # Revert historical count if cancelled on the order's date
            order_dt = order.order_time.date() if order.order_time else date.today()
            _sync_order_to_historical_sales(order.item_id, -order.quantity, order_dt)

        # If un-cancelling, deduct stock back
        elif prev_status == 'cancelled' and new_status != 'cancelled':
            inventory = InventoryStock.query.filter_by(item_id=order.item_id).first()
            if inventory:
                prev_stock = inventory.current_stock_qty
                inventory.current_stock_qty = max(0, inventory.current_stock_qty - order.quantity)
                new_stock = inventory.current_stock_qty

                inv_log = InventoryLog(
                    item_id=order.item_id,
                    change_qty=-order.quantity,
                    previous_stock=prev_stock,
                    new_stock=new_stock,
                    reason='pos_order',
                    reference_id=order.id,
                    logged_at=datetime.now(timezone.utc),
                    created_by_user_id=session.get('user_id')
                )
                db.session.add(inv_log)

            order_dt = order.order_time.date() if order.order_time else date.today()
            _sync_order_to_historical_sales(order.item_id, +order.quantity, order_dt)

        order.status = new_status
        db.session.commit()

        if new_status == 'cancelled' or prev_status == 'cancelled':
            trigger_async_retrain(current_app._get_current_object(), reason=f"order_status:{new_status}")

        # Recalculate live status counts for dynamic header updates
        status_counts = {
            'all': LiveOrder.query.count(),
            'pending': LiveOrder.query.filter_by(status='pending').count(),
            'preparing': LiveOrder.query.filter_by(status='preparing').count(),
            'completed': LiveOrder.query.filter_by(status='completed').count(),
            'cancelled': LiveOrder.query.filter_by(status='cancelled').count()
        }

        action_label = {
            'completed': 'Ready & Completed',
            'preparing': 'Now Cooking (Preparing)',
            'cancelled': 'Cancelled (Stock Restored)',
            'pending': 'Pending'
        }.get(new_status, new_status.title())

        msg = f"Order #{order.id} marked as {action_label}!"

        if is_ajax:
            return jsonify({
                'status': 'success',
                'order_id': order.id,
                'new_status': new_status,
                'prev_status': prev_status,
                'message': msg,
                'status_counts': status_counts
            }), 200

        flash(msg, "success")
        return redirect(request.referrer or url_for('orders.orders_list'))

    except Exception as e:
        db.session.rollback()
        err_msg = f"Failed to update order #{order_id}: {str(e)}"
        if is_ajax:
            return jsonify({'status': 'error', 'message': err_msg}), 500
        flash(err_msg, "danger")
        return redirect(url_for('orders.orders_list'))


@orders_bp.route('/api/live', methods=['GET'])
def get_live_kds_feed():
    """
    REAL-TIME POS-TO-KITCHEN STATE SYNCHRONIZATION ENDPOINT:
    Polled every 2.5 - 3 seconds by the Kitchen Order Monitor and Dashboard
    so newly placed orders appear instantly without requiring browser reloads.
    """
    status_filter = request.args.get('status', 'all')
    query = LiveOrder.query

    if session.get('role') == 'customer':
        query = query.filter_by(customer_id=session.get('user_id'))
    elif status_filter != 'all':
        query = query.filter_by(status=status_filter)

    orders = query.order_by(LiveOrder.order_time.desc()).limit(80).all()

    status_counts = {
        'all': LiveOrder.query.count(),
        'pending': LiveOrder.query.filter_by(status='pending').count(),
        'preparing': LiveOrder.query.filter_by(status='preparing').count(),
        'completed': LiveOrder.query.filter_by(status='completed').count(),
        'cancelled': LiveOrder.query.filter_by(status='cancelled').count()
    }

    orders_data = []
    for o in orders:
        product = o.product
        orders_data.append({
            'id': o.id,
            'item_id': o.item_id,
            'item_name': product.item_name if product else 'Unknown Item',
            'category': product.category if product else '',
            'display_image': product.display_image if product else '',
            'quantity': o.quantity,
            'customer_name': o.customer_name or 'Walk-in Guest',
            'status': o.status,
            'total_price': float(o.total_price) if o.total_price else 0.0,
            'order_time': o.order_time.strftime('%I:%M %p') if o.order_time else '',
            'raw_timestamp': o.order_time.isoformat() if o.order_time else ''
        })

    return jsonify({
        'status': 'success',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'status_counts': status_counts,
        'orders': orders_data
    })
