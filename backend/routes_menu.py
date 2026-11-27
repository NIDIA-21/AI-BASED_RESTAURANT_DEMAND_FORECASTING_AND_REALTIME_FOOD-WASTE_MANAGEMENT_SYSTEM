"""
Menu Management Module:
Allows restaurant managers/admins to add brand-new dishes to the live menu,
update dish details/photos, and delete underperforming items — all with full
database integration and automatic ML model re-training after changes.
"""

import uuid
from pathlib import Path
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, current_app
)
from backend.models import (
    db, ProductMenu, InventoryStock, HistoricalSalesData,
    LiveOrder, SurplusRedistribution, InventoryLog,
    MenuItemIngredient, DailyFoodPrep
)
from backend.auth import login_required, role_required
from backend.config import Config
from ml_model.train import trigger_async_retrain

menu_bp = Blueprint('menu', __name__, url_prefix='/menu')

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}


def _save_uploaded_image(file_storage):
    """Stores an uploaded dish image safely under static/images/uploads and returns its web path."""
    if not file_storage or not file_storage.filename:
        return None
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None
    safe_stem = secure_filename(Path(file_storage.filename).stem)[:40] or 'dish'
    unique_name = f"{safe_stem}_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = Path(current_app.static_folder) / 'images' / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_storage.save(str(upload_dir / unique_name))
    return f"/static/images/uploads/{unique_name}"


@menu_bp.route('/', methods=['GET'])
@login_required
@role_required('admin', 'restaurant_manager')
def index():
    """
    Menu Management Dashboard:
    Lists all dishes with profitability metrics, stock levels, live/historical
    sales volume, and provides Add/Edit/Delete actions.
    """
    items = ProductMenu.query.order_by(ProductMenu.category, ProductMenu.item_name).all()

    enriched = []
    for item in items:
        stock = InventoryStock.query.filter_by(item_id=item.id).first()
        sales_count = HistoricalSalesData.query.filter_by(item_id=item.id).count()
        total_units_sold = db.session.query(
            db.func.coalesce(db.func.sum(HistoricalSalesData.actual_qty_ordered), 0)
        ).filter(HistoricalSalesData.item_id == item.id).scalar() or 0
        total_revenue = float(total_units_sold) * float(item.unit_price)
        total_profit = float(total_units_sold) * float(item.profit_margin)

        enriched.append({
            'item': item,
            'stock': stock,
            'sales_count': sales_count,
            'total_units_sold': int(total_units_sold),
            'total_revenue': round(total_revenue, 2),
            'total_profit': round(total_profit, 2),
            'is_new': sales_count == 0
        })

    categories = sorted(set(i.category for i in items))

    return render_template(
        'menu/index.html',
        enriched=enriched,
        total_items=len(items),
        categories=categories,
        currency=Config.CURRENCY_SYMBOL
    )


@menu_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def add_dish():
    """
    Add a completely new dish to the restaurant menu (not previously in database).
    - Saves to ProductMenu table
    - Creates initial InventoryStock record
    - Triggers background ML retraining & pipeline reload
    """
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

        if new_cat:
            category = new_cat

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

        existing = ProductMenu.query.filter(
            db.func.lower(ProductMenu.item_name) == item_name.lower()
        ).first()
        if existing:
            errors.append(f"A dish named '{existing.item_name}' already exists in the menu (ID #{existing.id}).")

        uploaded_file = request.files.get('image_file')
        if uploaded_file and uploaded_file.filename:
            ext = Path(uploaded_file.filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                errors.append("Uploaded image must be PNG, JPG, JPEG, WEBP, or GIF.")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('menu/add_dish.html', categories=categories, currency=Config.CURRENCY_SYMBOL, form_data=request.form)

        saved_upload_path = _save_uploaded_image(uploaded_file)
        final_image = saved_upload_path or (image_url if image_url else None)

        new_item = ProductMenu(
            item_name=item_name,
            category=category,
            unit_price=unit_price,
            standard_prep_cost=prep_cost,
            shelf_life_hours=shelf_life,
            description=description,
            image_url=final_image,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_item)
        db.session.flush()

        inventory = InventoryStock(
            item_id=new_item.id,
            current_stock_qty=max(0, init_stock),
            min_threshold_qty=max(0, min_stock),
            last_restocked_at=datetime.now(timezone.utc)
        )
        db.session.add(inventory)
        db.session.commit()

        trigger_async_retrain(current_app._get_current_object(), reason=f"add_dish:{new_item.item_name}")

        flash(
            f"New dish '{item_name}' added to the menu (ID #{new_item.id}) with {init_stock} portions in stock! "
            f"Place orders for it in POS/Customer Menu to feed live demand data straight into the AI forecasting model.",
            'success'
        )
        return redirect(url_for('menu.index'))

    return render_template('menu/add_dish.html', categories=categories, currency=Config.CURRENCY_SYMBOL, form_data={})


@menu_bp.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def edit_dish(item_id):
    """Edit an existing dish: update price, description, image, category, shelf life."""
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
        if prep_cost < 0 or prep_cost >= unit_price:
            errors.append("Prep cost must be >= 0 and less than the selling price.")

        dup = ProductMenu.query.filter(
            db.func.lower(ProductMenu.item_name) == item_name.lower(),
            ProductMenu.id != item_id
        ).first()
        if dup:
            errors.append(f"Another dish named '{dup.item_name}' already exists (ID #{dup.id}).")

        uploaded_file = request.files.get('image_file')
        if uploaded_file and uploaded_file.filename:
            ext = Path(uploaded_file.filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                errors.append("Uploaded image must be PNG, JPG, JPEG, WEBP, or GIF.")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('menu/edit_dish.html', item=item, stock=stock, categories=categories, currency=Config.CURRENCY_SYMBOL)

        saved_upload_path = _save_uploaded_image(uploaded_file)

        item.item_name = item_name
        item.category = category
        item.unit_price = unit_price
        item.standard_prep_cost = prep_cost
        item.shelf_life_hours = shelf_life
        item.description = description
        if saved_upload_path:
            item.image_url = saved_upload_path
        else:
            item.image_url = image_url or None

        db.session.commit()
        trigger_async_retrain(current_app._get_current_object(), reason=f"edit_dish:{item.item_name}")
        flash(f"Dish '{item_name}' updated successfully!", 'success')
        return redirect(url_for('menu.index'))

    return render_template('menu/edit_dish.html', item=item, stock=stock, categories=categories, currency=Config.CURRENCY_SYMBOL)


@menu_bp.route('/delete/<int:item_id>', methods=['POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def delete_dish(item_id):
    """
    Permanently removes an underperforming or unprofitable dish from the menu & database.
    Safety guards:
      - Requires matching dish name confirmation
      - Blocks deletion only if there are active (pending/preparing) kitchen orders
      - Cleans up all child rows (InventoryLog, MenuItemIngredient, DailyFoodPrep,
        InventoryStock, HistoricalSalesData, LiveOrder, SurplusRedistribution) atomically
      - Retrains AI model immediately in background
    """
    item = db.get_or_404(ProductMenu, item_id)
    confirm_name = request.form.get('confirm_name', '').strip()

    if confirm_name.lower() != item.item_name.lower():
        flash(
            f"Deletion cancelled. Please type '{item.item_name}' exactly to confirm.",
            'danger'
        )
        return redirect(url_for('menu.index'))

    active_orders = LiveOrder.query.filter(
        LiveOrder.item_id == item_id,
        LiveOrder.status.in_(['pending', 'preparing'])
    ).count()

    if active_orders > 0:
        flash(
            f"Cannot delete '{item.item_name}' — it has {active_orders} active order(s) currently in the kitchen. "
            f"Mark them Ready or Cancel in KDS first.",
            'danger'
        )
        return redirect(url_for('menu.index'))

    item_name_saved = item.item_name
    sales_count = HistoricalSalesData.query.filter_by(item_id=item_id).count()

    try:
        # Clean up all dependent foreign-key rows safely before deleting parent ProductMenu
        InventoryLog.query.filter_by(item_id=item_id).delete(synchronize_session=False)
        MenuItemIngredient.query.filter_by(item_id=item_id).delete(synchronize_session=False)
        DailyFoodPrep.query.filter_by(item_id=item_id).delete(synchronize_session=False)
        SurplusRedistribution.query.filter_by(item_id=item_id).delete(synchronize_session=False)
        LiveOrder.query.filter_by(item_id=item_id).delete(synchronize_session=False)
        HistoricalSalesData.query.filter_by(item_id=item_id).delete(synchronize_session=False)
        InventoryStock.query.filter_by(item_id=item_id).delete(synchronize_session=False)
        db.session.delete(item)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete '{item_name_saved}': {str(e)}", 'danger')
        return redirect(url_for('menu.index'))

    trigger_async_retrain(current_app._get_current_object(), reason=f"delete_dish:{item_name_saved}")

    flash(
        f"Dish '{item_name_saved}' permanently deleted from the menu and database "
        f"({sales_count} historical record(s) removed). AI model is retraining automatically.",
        'warning'
    )
    return redirect(url_for('menu.index'))


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


@menu_bp.route('/api/retrain', methods=['POST'])
@login_required
@role_required('admin', 'restaurant_manager')
def trigger_retrain():
    """Manually trigger AI model retraining and reload pipeline."""
    trigger_async_retrain(current_app._get_current_object(), reason="manual_button")
    return jsonify({
        'status': 'started',
        'message': 'AI model retraining started. Forecasts for all dishes (old & new) will update in a moment.'
    })
