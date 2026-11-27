from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """
    User Model:
    Role-based authentication supporting:
    - 'admin': Full ERP administrative privileges & system config
    - 'restaurant_manager': Demand forecasting, prep planning, surplus coordination
    - 'inventory_staff': Order fulfillment, POS entry, stock adjustments
    - 'customer': Dine-in / online order viewing
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='customer')  # 'admin', 'restaurant_manager', 'inventory_staff', 'customer'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    orders = db.relationship('LiveOrder', backref='customer', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def display_role(self) -> str:
        role_map = {
            'admin': 'Administrator',
            'restaurant_manager': 'Restaurant Manager',
            'inventory_staff': 'Inventory & POS Staff',
            'customer': 'Customer'
        }
        return role_map.get(self.role, self.role.title())

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'display_role': self.display_role
        }

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"


class ProductMenu(db.Model):
    """
    ProductMenu Model:
    Item master catalog with financial metrics and shelf life specifications.
    """
    __tablename__ = 'product_menu'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_name = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(60), nullable=False, index=True)  # e.g., 'Starters', 'Main Course', 'Desserts', 'Beverages', 'Party Platters'
    unit_price = db.Column(db.Float, nullable=False)                 # Selling price per portion
    standard_prep_cost = db.Column(db.Float, nullable=False)         # Ingredient + preparation cost
    shelf_life_hours = db.Column(db.Integer, nullable=False, default=12) # Shelf life before waste/spoilage
    description = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    inventory = db.relationship('InventoryStock', backref='product', uselist=False, cascade='all, delete-orphan')
    historical_sales = db.relationship('HistoricalSalesData', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    live_orders = db.relationship('LiveOrder', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    surplus_records = db.relationship('SurplusRedistribution', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def display_image(self) -> str:
        """High-resolution appetizing food photography for every menu item."""
        if self.image_url and self.image_url.strip():
            return self.image_url.strip()

        name_lower = self.item_name.lower()
        # Verified dish images (local curated photos for key Indian menu items + verified URLs)
        if 'poori' in name_lower or 'puri' in name_lower:
            return "/static/images/dishes/poori.jpg"
        elif 'chapati' in name_lower or 'chapathi' in name_lower or 'roti' in name_lower:
            return "/static/images/dishes/chapati_curry.jpg"
        elif 'veg meals' in name_lower or 'meals' in name_lower or 'thali' in name_lower:
            return "/static/images/dishes/veg_meals.jpg"
        elif 'paneer rice' in name_lower or ('paneer' in name_lower and ('rice' in name_lower or 'pulao' in name_lower or 'biryani' in name_lower)):
            return "/static/images/dishes/paneer_rice.jpg"
        elif 'masala dosa' in name_lower or 'dosa' in name_lower:
            return "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=600&auto=format&fit=crop&q=80"
        elif 'idli' in name_lower:
            return "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&auto=format&fit=crop&q=80"
        elif 'paneer' in name_lower:
            return "/static/images/dishes/paneer_rice.jpg"
        elif 'samosa' in name_lower:
            return "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop&q=80"
        elif 'sandwich' in name_lower:
            return "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80"
        elif 'coffee' in name_lower:
            return "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80"
        elif 'tea' in name_lower or 'chai' in name_lower:
            return "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80"
        elif 'rice' in name_lower or 'biryani' in name_lower or 'pulao' in name_lower:
            return "/static/images/dishes/paneer_rice.jpg"
        elif 'curry' in name_lower or 'kurma' in name_lower or 'gravy' in name_lower:
            return "/static/images/dishes/chapati_curry.jpg"

        cat_lower = self.category.lower()
        if 'breakfast' in cat_lower or 'tiffin' in cat_lower:
            return "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=600&auto=format&fit=crop&q=80"
        elif 'lunch' in cat_lower:
            return "/static/images/dishes/veg_meals.jpg"
        elif 'snack' in cat_lower:
            return "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop&q=80"
        elif 'beverage' in cat_lower:
            return "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80"
        elif 'dinner' in cat_lower:
            return "/static/images/dishes/chapati_curry.jpg"
        return "/static/images/dishes/veg_meals.jpg"

    @property
    def profit_margin(self) -> float:
        """Contribution margin per unit."""
        return round(self.unit_price - self.standard_prep_cost, 2)

    @property
    def margin_percentage(self) -> float:
        """Percentage gross margin."""
        if self.unit_price > 0:
            return round(((self.unit_price - self.standard_prep_cost) / self.unit_price) * 100, 1)
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'item_name': self.item_name,
            'category': self.category,
            'unit_price': float(self.unit_price),
            'standard_prep_cost': float(self.standard_prep_cost),
            'shelf_life_hours': self.shelf_life_hours,
            'profit_margin': self.profit_margin,
            'margin_percentage': self.margin_percentage,
            'description': self.description or '',
            'image_url': self.image_url or ''
        }

    def __repr__(self):
        return f"<ProductMenu #{self.id} {self.item_name} (${self.unit_price})>"


class HistoricalSalesData(db.Model):
    """
    HistoricalSalesData Model:
    Training dataset records linking context features (day_type, customer_count, weather)
    with actual units demanded for ML regression models.
    """
    __tablename__ = 'historical_sales_data'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('product_menu.id', ondelete='CASCADE'), nullable=False, index=True)
    day_type = db.Column(db.String(40), nullable=False, index=True) # 'weekday', 'weekend', 'festival', 'office_party', 'birthday_celebration'
    customer_count = db.Column(db.Integer, nullable=False)
    actual_qty_ordered = db.Column(db.Integer, nullable=False)
    weather_condition = db.Column(db.String(40), nullable=False)   # 'Sunny', 'Rainy', 'Cloudy', 'Stormy', 'Cold'

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'item_id': self.item_id,
            'item_name': self.product.item_name if self.product else None,
            'day_type': self.day_type,
            'customer_count': self.customer_count,
            'actual_qty_ordered': self.actual_qty_ordered,
            'weather_condition': self.weather_condition
        }

    def __repr__(self):
        return f"<HistoricalSale {self.date} Item:{self.item_id} Day:{self.day_type} Qty:{self.actual_qty_ordered}>"


class InventoryStock(db.Model):
    """
    InventoryStock Model:
    Real-time inventory levels, reorder thresholds, and stock replenishment tracking.
    """
    __tablename__ = 'inventory_stock'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey('product_menu.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    current_stock_qty = db.Column(db.Integer, nullable=False, default=0)
    min_threshold_qty = db.Column(db.Integer, nullable=False, default=10)
    last_restocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock_qty <= self.min_threshold_qty

    @property
    def stock_status(self) -> str:
        if self.current_stock_qty == 0:
            return 'out_of_stock'
        elif self.current_stock_qty <= self.min_threshold_qty:
            return 'low_stock'
        return 'healthy'

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.product.item_name if self.product else None,
            'category': self.product.category if self.product else None,
            'current_stock_qty': self.current_stock_qty,
            'min_threshold_qty': self.min_threshold_qty,
            'is_low_stock': self.is_low_stock,
            'stock_status': self.stock_status,
            'last_restocked_at': self.last_restocked_at.strftime('%Y-%m-%d %H:%M') if self.last_restocked_at else None
        }

    def __repr__(self):
        return f"<InventoryStock Item:{self.item_id} Qty:{self.current_stock_qty} Min:{self.min_threshold_qty}>"


class LiveOrder(db.Model):
    """
    LiveOrder Model:
    Real-time order entries placed by staff or customers with instant inventory deduction.
    """
    __tablename__ = 'live_orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    customer_name = db.Column(db.String(100), nullable=True) # Useful for walk-ins or table identifiers
    item_id = db.Column(db.Integer, db.ForeignKey('product_menu.id', ondelete='CASCADE'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True) # 'pending', 'preparing', 'completed', 'cancelled'
    order_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    total_price = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name or (self.customer.username if self.customer else 'Walk-in Guest'),
            'item_id': self.item_id,
            'item_name': self.product.item_name if self.product else None,
            'quantity': self.quantity,
            'unit_price': float(self.product.unit_price) if self.product else 0.0,
            'total_price': float(self.total_price) if self.total_price else (self.quantity * (self.product.unit_price if self.product else 0.0)),
            'status': self.status,
            'order_time': self.order_time.strftime('%Y-%m-%d %H:%M:%S') if self.order_time else None
        }

    def __repr__(self):
        return f"<LiveOrder #{self.id} Item:{self.item_id} Qty:{self.quantity} Status:{self.status}>"


class SurplusRedistribution(db.Model):
    """
    SurplusRedistribution Model:
    Food waste prevention tracking surplus batches nearing expiration and coordinating with NGOs.
    """
    __tablename__ = 'surplus_redistribution'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey('product_menu.id', ondelete='CASCADE'), nullable=False, index=True)
    surplus_qty = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='available_for_ngo', index=True) # 'available_for_ngo', 'claimed'
    logged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    claimed_by_ngo = db.Column(db.String(120), nullable=True)
    claimed_at = db.Column(db.DateTime, nullable=True)
    contact_phone = db.Column(db.String(40), nullable=True)
    pickup_eta = db.Column(db.String(60), nullable=True)
    notes = db.Column(db.String(255), nullable=True)

    @property
    def hours_since_logged(self) -> float:
        if not self.logged_at:
            return 0.0
        now = datetime.now(timezone.utc)
        logged = self.logged_at
        if logged.tzinfo is None:
            logged = logged.replace(tzinfo=timezone.utc)
        delta = now - logged
        return round(delta.total_seconds() / 3600.0, 1)

    @property
    def hours_remaining(self) -> float:
        shelf_life = self.product.shelf_life_hours if self.product else 12
        remaining = shelf_life - self.hours_since_logged
        return round(max(0.0, remaining), 1)

    @property
    def is_expired(self) -> bool:
        return self.hours_remaining <= 0.0

    @property
    def co2_kg_saved(self) -> float:
        """Estimated 2.5 kg CO2 avoided per standard prepared meal portion saved."""
        return round(self.surplus_qty * 2.5, 1)

    @property
    def estimated_value_recovered(self) -> float:
        if self.product:
            return round(self.surplus_qty * self.product.standard_prep_cost, 2)
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.product.item_name if self.product else None,
            'category': self.product.category if self.product else None,
            'surplus_qty': self.surplus_qty,
            'status': self.status,
            'logged_at': self.logged_at.strftime('%Y-%m-%d %H:%M:%S') if self.logged_at else None,
            'claimed_by_ngo': self.claimed_by_ngo,
            'claimed_at': self.claimed_at.strftime('%Y-%m-%d %H:%M:%S') if self.claimed_at else None,
            'contact_phone': self.contact_phone,
            'pickup_eta': self.pickup_eta,
            'notes': self.notes,
            'hours_remaining': self.hours_remaining,
            'is_expired': self.is_expired,
            'co2_kg_saved': self.co2_kg_saved,
            'estimated_value_recovered': self.estimated_value_recovered
        }

    def __repr__(self):
        return f"<SurplusRedistribution #{self.id} Item:{self.item_id} Qty:{self.surplus_qty} Status:{self.status}>"


class InventoryLog(db.Model):
    """
    InventoryLog Model:
    Atomic transaction audit ledger tracking all inventory state shifts:
    - POS checkout deductions
    - Order cancellation stock returns
    - Physical kitchen restocks
    - Surplus food redirection deductions
    """
    __tablename__ = 'inventory_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey('product_menu.id', ondelete='CASCADE'), nullable=False, index=True)
    change_qty = db.Column(db.Integer, nullable=False) # Negative for deduction, positive for replenishment
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(60), nullable=False, index=True) # 'pos_order', 'restock', 'cancellation_restore', 'surplus_deduction'
    reference_id = db.Column(db.Integer, nullable=True) # Linked LiveOrder.id or SurplusRedistribution.id
    logged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    product = db.relationship('ProductMenu', backref='stock_audit_logs')
    user = db.relationship('User', backref='stock_operations')

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.product.item_name if self.product else None,
            'change_qty': self.change_qty,
            'previous_stock': self.previous_stock,
            'new_stock': self.new_stock,
            'reason': self.reason,
            'reference_id': self.reference_id,
            'logged_at': self.logged_at.strftime('%Y-%m-%d %H:%M:%S') if self.logged_at else None,
            'performed_by': self.user.username if self.user else 'System'
        }

    def __repr__(self):
        return f"<InventoryLog #{self.id} Item:{self.item_id} Change:{self.change_qty} Reason:{self.reason}>"


class InventoryIngredient(db.Model):
    """
    InventoryIngredient Model:
    Raw ingredients, shelf-life, and expiry tracking to prevent raw material spoilage.
    """
    __tablename__ = 'inventory_ingredients'

    ingredient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ingredient_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # 'Prepared Batter', 'Produce', 'Dry Goods', 'Dairy', 'Bakery'
    quantity_in_stock = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False) # 'kg', 'liters', 'packets'
    cost_per_unit = db.Column(db.Float, nullable=False)
    reorder_level = db.Column(db.Float, nullable=False)
    expiry_date = db.Column(db.String(20), nullable=False) # 'YYYY-MM-DD'
    storage_location = db.Column(db.String(50), default='Main Kitchen')

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_in_stock <= self.reorder_level

    @property
    def days_until_expiry(self) -> int:
        try:
            exp = datetime.strptime(self.expiry_date.strip(), '%Y-%m-%d').date()
            today = datetime.now(timezone.utc).date()
            return (exp - today).days
        except Exception:
            return 999

    @property
    def is_expiring_soon(self) -> bool:
        return self.days_until_expiry <= 5

    def to_dict(self):
        return {
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient_name,
            'category': self.category,
            'quantity_in_stock': self.quantity_in_stock,
            'unit': self.unit,
            'cost_per_unit': self.cost_per_unit,
            'reorder_level': self.reorder_level,
            'expiry_date': self.expiry_date,
            'storage_location': self.storage_location,
            'is_low_stock': self.is_low_stock,
            'days_until_expiry': self.days_until_expiry,
            'is_expiring_soon': self.is_expiring_soon
        }

    def __repr__(self):
        return f"<InventoryIngredient #{self.ingredient_id} {self.ingredient_name} ({self.quantity_in_stock} {self.unit})>"


class MenuItemIngredient(db.Model):
    """
    MenuItemIngredient Model (Recipe / Bill of Materials):
    Maps each of the 10 menu items to exact raw ingredient quantities required.
    """
    __tablename__ = 'menu_item_ingredients'

    recipe_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey('product_menu.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('inventory_ingredients.ingredient_id', ondelete='CASCADE'), nullable=False)
    quantity_required = db.Column(db.Float, nullable=False)

    # Relationships
    product = db.relationship('ProductMenu', backref='recipe_mappings')
    ingredient = db.relationship('InventoryIngredient', backref='menu_usages')

    def to_dict(self):
        return {
            'recipe_id': self.recipe_id,
            'item_id': self.item_id,
            'item_name': self.product.item_name if self.product else None,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.ingredient_name if self.ingredient else None,
            'quantity_required': self.quantity_required,
            'unit': self.ingredient.unit if self.ingredient else ''
        }

    def __repr__(self):
        return f"<MenuItemIngredient Recipe #{self.recipe_id} Item:{self.item_id} -> Ingr:{self.ingredient_id} ({self.quantity_required})>"


class DailyFoodPrep(db.Model):
    """
    DailyFoodPrep Model:
    Tracks batch cooking vs. actual sales to detect overproduction and food waste risks.
    """
    __tablename__ = 'daily_food_prep'

    prep_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prep_date = db.Column(db.String(20), nullable=False) # 'YYYY-MM-DD'
    item_id = db.Column(db.Integer, db.ForeignKey('product_menu.id', ondelete='CASCADE'), nullable=False)
    quantity_prepared = db.Column(db.Integer, nullable=False)
    quantity_sold = db.Column(db.Integer, default=0)

    # Relationships
    product = db.relationship('ProductMenu', backref='prep_records')

    @property
    def quantity_surplus(self) -> int:
        return max(0, self.quantity_prepared - (self.quantity_sold or 0))

    @property
    def waste_risk_percentage(self) -> float:
        if self.quantity_prepared > 0:
            return round((self.quantity_surplus / self.quantity_prepared) * 100.0, 1)
        return 0.0

    def to_dict(self):
        return {
            'prep_id': self.prep_id,
            'prep_date': self.prep_date,
            'item_id': self.item_id,
            'item_name': self.product.item_name if self.product else None,
            'category': self.product.category if self.product else None,
            'quantity_prepared': self.quantity_prepared,
            'quantity_sold': self.quantity_sold,
            'quantity_surplus': self.quantity_surplus,
            'waste_risk_percentage': self.waste_risk_percentage
        }

    def __repr__(self):
        return f"<DailyFoodPrep #{self.prep_id} Date:{self.prep_date} Item:{self.item_id} Prep:{self.quantity_prepared} Sold:{self.quantity_sold}>"


class FoodWasteLog(db.Model):
    """
    FoodWasteLog Model:
    Core tracking table for food waste causes, volumes, and cost losses.
    """
    __tablename__ = 'food_waste_logs'

    waste_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    log_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    item_type = db.Column(db.String(50), nullable=False) # 'Prepared Food', 'Raw Ingredient'
    item_name = db.Column(db.String(100), nullable=False)
    quantity_wasted = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False) # 'portions', 'pieces', 'plates', 'kg', 'liters'
    waste_reason = db.Column(db.String(100), nullable=False) # 'Expired / Spoiled', 'Overproduction / Unsold', 'Kitchen Error / Burnt', etc.
    cost_loss = db.Column(db.Float, nullable=False)
    recorded_by = db.Column(db.String(50), default='Kitchen Supervisor')
    disposal_method = db.Column(db.String(50), default='Landfill') # 'Landfill', 'Composted', 'Animal Feed', 'Donation'

    def to_dict(self):
        return {
            'waste_id': self.waste_id,
            'log_date': self.log_date.strftime('%Y-%m-%d %H:%M') if self.log_date else None,
            'item_type': self.item_type,
            'item_name': self.item_name,
            'quantity_wasted': self.quantity_wasted,
            'unit': self.unit,
            'waste_reason': self.waste_reason,
            'cost_loss': self.cost_loss,
            'recorded_by': self.recorded_by,
            'disposal_method': self.disposal_method
        }

    def __repr__(self):
        return f"<FoodWasteLog #{self.waste_id} {self.item_name} ({self.quantity_wasted} {self.unit}) Reason:{self.waste_reason}>"


class FoodDonation(db.Model):
    """
    FoodDonation Model:
    Tracks surplus food diverted to food banks and charities instead of landfill.
    """
    __tablename__ = 'food_donations'

    donation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    donation_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    recipient_organization = db.Column(db.String(100), nullable=False)
    food_description = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False) # 'packets', 'portions', 'kg'
    driver_or_contact = db.Column(db.String(50), nullable=True)
    donation_status = db.Column(db.String(30), default='Delivered') # 'Scheduled', 'Picked Up', 'Delivered'

    def to_dict(self):
        return {
            'donation_id': self.donation_id,
            'donation_date': self.donation_date.strftime('%Y-%m-%d %H:%M') if self.donation_date else None,
            'recipient_organization': self.recipient_organization,
            'food_description': self.food_description,
            'quantity': self.quantity,
            'unit': self.unit,
            'driver_or_contact': self.driver_or_contact,
            'donation_status': self.donation_status
        }

    def __repr__(self):
        return f"<FoodDonation #{self.donation_id} To:{self.recipient_organization} ({self.quantity} {self.unit}) Status:{self.donation_status}>"


