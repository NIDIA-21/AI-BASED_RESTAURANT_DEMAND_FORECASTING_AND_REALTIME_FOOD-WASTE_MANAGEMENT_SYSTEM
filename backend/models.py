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
        if 'paneer tikka' in name_lower:
            return "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?w=600&auto=format&fit=crop&q=80"
        elif 'honey chilli chicken' in name_lower or 'crispy' in name_lower:
            return "https://images.unsplash.com/photo-1562967914-608f82629710?w=600&auto=format&fit=crop&q=80"
        elif 'fries' in name_lower:
            return "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600&auto=format&fit=crop&q=80"
        elif 'calamari' in name_lower or 'squid' in name_lower:
            return "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=600&auto=format&fit=crop&q=80"
        elif 'biryani' in name_lower:
            return "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&auto=format&fit=crop&q=80"
        elif 'butter masala' in name_lower or 'naan' in name_lower:
            return "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&auto=format&fit=crop&q=80"
        elif 'salmon' in name_lower or 'fish' in name_lower:
            return "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=600&auto=format&fit=crop&q=80"
        elif 'risotto' in name_lower or 'mushroom' in name_lower:
            return "https://images.unsplash.com/photo-1633964913295-ceb43826e7c9?w=600&auto=format&fit=crop&q=80"
        elif 'rogan josh' in name_lower or 'lamb' in name_lower:
            return "https://images.unsplash.com/photo-1545247181-516773cae754?w=600&auto=format&fit=crop&q=80"
        elif 'lava cake' in name_lower or 'chocolate' in name_lower:
            return "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=600&auto=format&fit=crop&q=80"
        elif 'cheesecake' in name_lower or 'rasmalai' in name_lower:
            return "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=600&auto=format&fit=crop&q=80"
        elif 'brownie' in name_lower:
            return "https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=600&auto=format&fit=crop&q=80"
        elif 'cold brew' in name_lower or 'coffee' in name_lower:
            return "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=600&auto=format&fit=crop&q=80"
        elif 'mojito' in name_lower or 'passionfruit' in name_lower:
            return "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&auto=format&fit=crop&q=80"
        elif 'chai' in name_lower or 'tea' in name_lower:
            return "https://images.unsplash.com/photo-1561336313-0bd5e0b27ec8?w=600&auto=format&fit=crop&q=80"
        elif 'tandoori feast' in name_lower or 'mixed grill' in name_lower:
            return "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&auto=format&fit=crop&q=80"
        elif 'mezze' in name_lower or 'mediterranean' in name_lower:
            return "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=600&auto=format&fit=crop&q=80"
        elif 'slider' in name_lower or 'burger' in name_lower:
            return "https://images.unsplash.com/photo-1550547660-d9450f859349?w=600&auto=format&fit=crop&q=80"

        cat_lower = self.category.lower()
        if 'starter' in cat_lower:
            return "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=600&auto=format&fit=crop&q=80"
        elif 'main' in cat_lower:
            return "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80"
        elif 'dessert' in cat_lower:
            return "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=600&auto=format&fit=crop&q=80"
        elif 'beverage' in cat_lower or 'drink' in cat_lower:
            return "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&auto=format&fit=crop&q=80"
        return "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&auto=format&fit=crop&q=80"

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

