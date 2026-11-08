"""
Database Seeding Script:
Generates rich synthetic data with deep variance across:
- Day Types: 'weekday', 'weekend', 'festival', 'office_party', 'birthday_celebration'
- Customer Counts: 50 to 450
- Weather Conditions: 'Sunny', 'Rainy', 'Cloudy', 'Stormy', 'Cold'
- Menu Categories: Starters, Main Course, Desserts, Beverages, Party Platters
- Realistic user accounts with hashed credentials
- Initial inventory stock and active sample orders & surplus listings
"""

import random
from datetime import datetime, date, timedelta, timezone
from backend.models import (
    db, User, ProductMenu, HistoricalSalesData,
    InventoryStock, LiveOrder, SurplusRedistribution
)

# Seed menu catalog definitions
SAMPLE_MENU_ITEMS = [
    # Starters
    {
        "item_name": "Paneer Tikka Kebabs",
        "category": "Starters",
        "unit_price": 280.0,
        "standard_prep_cost": 110.0,
        "shelf_life_hours": 8,
        "description": "Clay-oven roasted cottage cheese skewers with bell peppers and mint chutney.",
        "popularity_weight": 0.28,
        "event_affinity": {"office_party": 1.7, "birthday_celebration": 1.4, "festival": 1.5, "weekend": 1.3, "weekday": 1.0},
        "weather_affinity": {"Rainy": 1.3, "Cold": 1.25, "Sunny": 0.95, "Cloudy": 1.05, "Stormy": 1.15}
    },
    {
        "item_name": "Crispy Honey Chilli Chicken",
        "category": "Starters",
        "unit_price": 340.0,
        "standard_prep_cost": 140.0,
        "shelf_life_hours": 6,
        "description": "Crispy chicken strips tossed in ginger honey glaze and toasted sesame.",
        "popularity_weight": 0.32,
        "event_affinity": {"office_party": 2.1, "birthday_celebration": 1.6, "festival": 1.4, "weekend": 1.4, "weekday": 1.0},
        "weather_affinity": {"Rainy": 1.35, "Cold": 1.2, "Sunny": 0.9, "Cloudy": 1.1, "Stormy": 1.25}
    },
    {
        "item_name": "Truffle Loaded Fries",
        "category": "Starters",
        "unit_price": 220.0,
        "standard_prep_cost": 75.0,
        "shelf_life_hours": 5,
        "description": "Hand-cut potato frites with white truffle oil, parmesan, and garlic aioli.",
        "popularity_weight": 0.30,
        "event_affinity": {"office_party": 2.3, "birthday_celebration": 1.8, "festival": 1.2, "weekend": 1.5, "weekday": 1.0},
        "weather_affinity": {"Rainy": 1.2, "Cold": 1.1, "Sunny": 1.0, "Cloudy": 1.0, "Stormy": 1.1}
    },
    {
        "item_name": "Peri Peri Calamari Rings",
        "category": "Starters",
        "unit_price": 390.0,
        "standard_prep_cost": 170.0,
        "shelf_life_hours": 5,
        "description": "Golden crispy squid rings spiced with African bird's eye chilli and lemon zest.",
        "popularity_weight": 0.18,
        "event_affinity": {"office_party": 1.8, "birthday_celebration": 1.3, "festival": 1.2, "weekend": 1.4, "weekday": 0.9},
        "weather_affinity": {"Rainy": 1.15, "Cold": 1.05, "Sunny": 1.0, "Cloudy": 1.0, "Stormy": 1.1}
    },

    # Main Courses
    {
        "item_name": "Royal Dum Chicken Biryani",
        "category": "Main Course",
        "unit_price": 380.0,
        "standard_prep_cost": 150.0,
        "shelf_life_hours": 10,
        "description": "Slow dum-cooked basmati rice with fragrant spices, marinated chicken, and saffron.",
        "popularity_weight": 0.45,
        "event_affinity": {"festival": 2.4, "weekend": 1.8, "office_party": 1.5, "birthday_celebration": 1.5, "weekday": 1.0},
        "weather_affinity": {"Rainy": 1.4, "Cold": 1.35, "Sunny": 0.9, "Cloudy": 1.1, "Stormy": 1.3}
    },
    {
        "item_name": "Paneer Butter Masala & Naan",
        "category": "Main Course",
        "unit_price": 320.0,
        "standard_prep_cost": 120.0,
        "shelf_life_hours": 10,
        "description": "Cottage cheese in rich tomato-cashew satin gravy served with garlic butter naan.",
        "popularity_weight": 0.35,
        "event_affinity": {"festival": 2.1, "weekend": 1.6, "office_party": 1.4, "birthday_celebration": 1.4, "weekday": 1.0},
        "weather_affinity": {"Rainy": 1.3, "Cold": 1.3, "Sunny": 0.95, "Cloudy": 1.05, "Stormy": 1.2}
    },
    {
        "item_name": "Grilled Herb Butter Salmon",
        "category": "Main Course",
        "unit_price": 580.0,
        "standard_prep_cost": 260.0,
        "shelf_life_hours": 6,
        "description": "Pan-seared Atlantic salmon fillet on crushed baby potatoes and asparagus spear.",
        "popularity_weight": 0.16,
        "event_affinity": {"festival": 1.5, "weekend": 1.7, "office_party": 1.2, "birthday_celebration": 1.5, "weekday": 0.9},
        "weather_affinity": {"Rainy": 0.95, "Cold": 1.0, "Sunny": 1.15, "Cloudy": 1.0, "Stormy": 0.9}
    },
    {
        "item_name": "Wild Mushroom Risotto",
        "category": "Main Course",
        "unit_price": 390.0,
        "standard_prep_cost": 145.0,
        "shelf_life_hours": 8,
        "description": "Creamy Arborio rice with porcini mushrooms, thyme, white wine, and aged parmesan.",
        "popularity_weight": 0.22,
        "event_affinity": {"festival": 1.3, "weekend": 1.4, "office_party": 1.1, "birthday_celebration": 1.3, "weekday": 1.0},
        "weather_affinity": {"Rainy": 1.25, "Cold": 1.35, "Sunny": 0.9, "Cloudy": 1.05, "Stormy": 1.15}
    },
    {
        "item_name": "Slow Cooked Rogan Josh",
        "category": "Main Course",
        "unit_price": 460.0,
        "standard_prep_cost": 190.0,
        "shelf_life_hours": 12,
        "description": "Kashmiri-style tender braised lamb shank in aromatic dried ginger and fennel gravy.",
        "popularity_weight": 0.24,
        "event_affinity": {"festival": 2.2, "weekend": 1.6, "office_party": 1.3, "birthday_celebration": 1.3, "weekday": 0.95},
        "weather_affinity": {"Rainy": 1.4, "Cold": 1.5, "Sunny": 0.85, "Cloudy": 1.1, "Stormy": 1.35}
    },

    # Desserts
    {
        "item_name": "Belgian Chocolate Lava Cake",
        "category": "Desserts",
        "unit_price": 240.0,
        "standard_prep_cost": 85.0,
        "shelf_life_hours": 24,
        "description": "Warm molten Callebaut chocolate center served with Madagascar vanilla bean gelato.",
        "popularity_weight": 0.38,
        "event_affinity": {"birthday_celebration": 3.4, "weekend": 1.8, "office_party": 1.5, "festival": 1.6, "weekday": 0.9},
        "weather_affinity": {"Rainy": 1.3, "Cold": 1.4, "Sunny": 0.9, "Cloudy": 1.05, "Stormy": 1.2}
    },
    {
        "item_name": "Saffron Rasmalai Cheesecake",
        "category": "Desserts",
        "unit_price": 260.0,
        "standard_prep_cost": 95.0,
        "shelf_life_hours": 36,
        "description": "Fusion baked cheesecake layered with saffron milk dumplings and pistachio dust.",
        "popularity_weight": 0.32,
        "event_affinity": {"festival": 2.8, "birthday_celebration": 2.9, "weekend": 1.7, "office_party": 1.3, "weekday": 0.9},
        "weather_affinity": {"Rainy": 1.1, "Cold": 1.05, "Sunny": 1.0, "Cloudy": 1.0, "Stormy": 1.05}
    },
    {
        "item_name": "Warm Walnut Brownie with Gelato",
        "category": "Desserts",
        "unit_price": 210.0,
        "standard_prep_cost": 70.0,
        "shelf_life_hours": 24,
        "description": "Fudgy roasted walnut brownie drizzled with hot salted caramel fudge.",
        "popularity_weight": 0.28,
        "event_affinity": {"birthday_celebration": 2.6, "office_party": 1.8, "weekend": 1.5, "festival": 1.4, "weekday": 1.0},
        "weather_affinity": {"Rainy": 1.25, "Cold": 1.3, "Sunny": 0.95, "Cloudy": 1.05, "Stormy": 1.15}
    },

    # Beverages
    {
        "item_name": "Cold Brew Cinnamon Tonic",
        "category": "Beverages",
        "unit_price": 180.0,
        "standard_prep_cost": 45.0,
        "shelf_life_hours": 12,
        "description": "18-hour single origin cold brew steeped with ceylon cinnamon and artisanal tonic.",
        "popularity_weight": 0.25,
        "event_affinity": {"weekday": 1.3, "office_party": 1.6, "weekend": 1.1, "birthday_celebration": 0.9, "festival": 0.9},
        "weather_affinity": {"Sunny": 1.7, "Cloudy": 1.1, "Rainy": 0.65, "Cold": 0.5, "Stormy": 0.6}
    },
    {
        "item_name": "Fresh Mint Passionfruit Mojito",
        "category": "Beverages",
        "unit_price": 190.0,
        "standard_prep_cost": 50.0,
        "shelf_life_hours": 8,
        "description": "Muddled garden mint, fresh passionfruit pulp, lime juice, and sparkling soda.",
        "popularity_weight": 0.35,
        "event_affinity": {"office_party": 2.2, "birthday_celebration": 2.0, "weekend": 1.6, "festival": 1.4, "weekday": 0.9},
        "weather_affinity": {"Sunny": 1.8, "Cloudy": 1.15, "Rainy": 0.7, "Cold": 0.55, "Stormy": 0.65}
    },
    {
        "item_name": "Spiced Masala Kulhad Chai",
        "category": "Beverages",
        "unit_price": 90.0,
        "standard_prep_cost": 20.0,
        "shelf_life_hours": 4,
        "description": "Traditional Assam CTC tea brewed with ginger, cardamom, and lemongrass in clay cup.",
        "popularity_weight": 0.40,
        "event_affinity": {"weekday": 1.4, "rainy_surge": 2.2, "office_party": 1.3, "weekend": 1.1, "festival": 1.2, "birthday_celebration": 0.8},
        "weather_affinity": {"Rainy": 2.4, "Cold": 2.5, "Stormy": 2.2, "Cloudy": 1.4, "Sunny": 0.7}
    },

    # Party & Office Sharing Platters
    {
        "item_name": "Grand Tandoori Feast Platter",
        "category": "Party Platters",
        "unit_price": 890.0,
        "standard_prep_cost": 380.0,
        "shelf_life_hours": 6,
        "description": "Assortment of seekh kebabs, malai tikka, tandoori prawns, spiced onions, and flatbreads.",
        "popularity_weight": 0.15,
        "event_affinity": {"office_party": 3.4, "birthday_celebration": 2.6, "festival": 2.5, "weekend": 1.8, "weekday": 0.6},
        "weather_affinity": {"Rainy": 1.2, "Cold": 1.2, "Sunny": 1.0, "Cloudy": 1.0, "Stormy": 1.1}
    },
    {
        "item_name": "Mediterranean Mezze Sharing Platter",
        "category": "Party Platters",
        "unit_price": 650.0,
        "standard_prep_cost": 240.0,
        "shelf_life_hours": 8,
        "description": "Smoky baba ganoush, classic hummus, muhammara, falafel, pickled vegetables, and warm pita.",
        "popularity_weight": 0.17,
        "event_affinity": {"office_party": 3.0, "birthday_celebration": 2.3, "festival": 1.9, "weekend": 1.6, "weekday": 0.7},
        "weather_affinity": {"Sunny": 1.2, "Cloudy": 1.0, "Rainy": 0.9, "Cold": 0.85, "Stormy": 0.9}
    },
    {
        "item_name": "Corporate Gourmet Slider Box",
        "category": "Party Platters",
        "unit_price": 720.0,
        "standard_prep_cost": 290.0,
        "shelf_life_hours": 6,
        "description": "12 artisanal mini brioche burgers (pulled barbecue chicken, grilled paneer, and smashed lamb).",
        "popularity_weight": 0.14,
        "event_affinity": {"office_party": 3.8, "birthday_celebration": 2.4, "festival": 1.5, "weekend": 1.4, "weekday": 0.7},
        "weather_affinity": {"Rainy": 1.1, "Cold": 1.1, "Sunny": 1.0, "Cloudy": 1.0, "Stormy": 1.05}
    }
]

DEFAULT_USERS = [
    {"username": "admin", "email": "admin@smartrestaurant.com", "password": "admin", "role": "admin"},
    {"username": "manager", "email": "manager@smartrestaurant.com", "password": "manager", "role": "restaurant_manager"},
    {"username": "staff", "email": "staff@smartrestaurant.com", "password": "staff", "role": "inventory_staff"},
    {"username": "customer", "email": "customer@gmail.com", "password": "customer", "role": "customer"},
    {"username": "rahul", "email": "rahul.sharma@example.com", "password": "password123", "role": "customer"},
    {"username": "priya", "email": "priya.nair@example.com", "password": "password123", "role": "customer"}
]


def seed_all_data(days_of_history: int = 180, force: bool = False):
    """
    Automated seed script generating rich historical records and context data.
    """
    # Check if database already seeded
    existing_items = ProductMenu.query.count()
    if existing_items > 0 and not force:
        print(f"[SEED] Database already contains {existing_items} menu items. Skipping seed.")
        return

    print("[SEED] Starting comprehensive database seeding...")

    # Clear existing tables if forced
    if force:
        print("[SEED] Clearing existing data...")
        LiveOrder.query.delete()
        SurplusRedistribution.query.delete()
        InventoryStock.query.delete()
        HistoricalSalesData.query.delete()
        ProductMenu.query.delete()
        User.query.delete()
        db.session.commit()

    # 1. Seed Users
    print("[SEED] Creating system users with role permissions...")
    user_objects = {}
    for u in DEFAULT_USERS:
        existing = User.query.filter_by(username=u['username']).first()
        if not existing:
            user = User(
                username=u['username'],
                email=u['email'],
                role=u['role']
            )
            user.set_password(u['password'])
            db.session.add(user)
            user_objects[u['username']] = user
        else:
            user_objects[u['username']] = existing
    db.session.commit()

    # 2. Seed Menu Items & Inventory
    print(f"[SEED] Inserting {len(SAMPLE_MENU_ITEMS)} menu items and initial stock levels...")
    menu_objects = []
    for item_data in SAMPLE_MENU_ITEMS:
        item = ProductMenu(
            item_name=item_data['item_name'],
            category=item_data['category'],
            unit_price=item_data['unit_price'],
            standard_prep_cost=item_data['standard_prep_cost'],
            shelf_life_hours=item_data['shelf_life_hours'],
            description=item_data['description']
        )
        db.session.add(item)
        db.session.flush() # Populate item.id
        menu_objects.append((item, item_data))

        # Initial inventory stock
        init_stock = random.randint(25, 60)
        min_thresh = random.randint(8, 18)
        inv = InventoryStock(
            item_id=item.id,
            current_stock_qty=init_stock,
            min_threshold_qty=min_thresh,
            last_restocked_at=datetime.now(timezone.utc)
        )
        db.session.add(inv)
    db.session.commit()

    # 3. Seed Historical Sales Data
    print(f"[SEED] Generating {days_of_history} days of historical sales records with multi-dimensional context...")
    today = date.today()
    start_date = today - timedelta(days=days_of_history)

    weather_choices = ['Sunny', 'Rainy', 'Cloudy', 'Stormy', 'Cold']
    weather_weights = [0.45, 0.25, 0.15, 0.05, 0.10]

    historical_records = []
    total_sales_points = 0

    # Specific calendar event dates (festivals)
    # E.g. Diwali, Eid, New Year, Christmas, etc. relative to current date
    festival_offsets = {5, 6, 25, 26, 60, 61, 105, 120, 150}

    for d in range(days_of_history):
        current_date = start_date + timedelta(days=d)
        weekday_num = current_date.weekday() # 0 = Monday, 6 = Sunday

        # Determine day_type
        if (days_of_history - d) in festival_offsets:
            day_type = 'festival'
        elif weekday_num in (4, 5, 6): # Fri, Sat, Sun
            roll = random.random()
            if roll < 0.65:
                day_type = 'weekend'
            elif roll < 0.85:
                day_type = 'office_party' if weekday_num == 4 else 'birthday_celebration'
            else:
                day_type = 'birthday_celebration'
        else: # Mon, Tue, Wed, Thu
            roll = random.random()
            if roll < 0.75:
                day_type = 'weekday'
            elif roll < 0.92:
                day_type = 'office_party'
            else:
                day_type = 'birthday_celebration'

        # Determine customer count based on day_type
        if day_type == 'weekday':
            customer_count = random.randint(65, 115)
        elif day_type == 'weekend':
            customer_count = random.randint(170, 290)
        elif day_type == 'office_party':
            customer_count = random.randint(140, 240)
        elif day_type == 'birthday_celebration':
            customer_count = random.randint(120, 205)
        else: # festival
            customer_count = random.randint(260, 440)

        # Weather selection
        weather = random.choices(weather_choices, weights=weather_weights, k=1)[0]

        # Generate sales for each menu item
        for item, item_meta in menu_objects:
            base_pop = item_meta['popularity_weight']
            event_mult = item_meta['event_affinity'].get(day_type, 1.0)
            weather_mult = item_meta['weather_affinity'].get(weather, 1.0)

            # Expected items ordered = customer_count * base_rate * event_mult * weather_mult
            expected_demand = customer_count * base_pop * event_mult * weather_mult
            # Add stochastic Gaussian noise
            actual_ordered = max(1, int(round(random.gauss(expected_demand, max(1.5, expected_demand * 0.12)))))

            record = HistoricalSalesData(
                date=current_date,
                item_id=item.id,
                day_type=day_type,
                customer_count=customer_count,
                actual_qty_ordered=actual_ordered,
                weather_condition=weather
            )
            historical_records.append(record)
            total_sales_points += 1

            # Batch commit every 500 records to keep memory lightweight
            if len(historical_records) >= 500:
                db.session.bulk_save_objects(historical_records)
                db.session.commit()
                historical_records = []

    if historical_records:
        db.session.bulk_save_objects(historical_records)
        db.session.commit()

    print(f"[SEED] Successfully generated {total_sales_points} historical sales data points!")

    # 4. Seed Some Active Live Orders for Today
    print("[SEED] Creating initial live orders for the current service shift...")
    customer_user = User.query.filter_by(role='customer').first()
    customer_id = customer_user.id if customer_user else None

    sample_orders = [
        (menu_objects[0][0].id, 3, 'completed', "Table 4 - Dine In"),
        (menu_objects[4][0].id, 4, 'preparing', "Table 8 - Family"),
        (menu_objects[1][0].id, 2, 'preparing', "Walk-in Takeaway"),
        (menu_objects[9][0].id, 3, 'pending', "Table 12 - Birthday"),
        (menu_objects[13][0].id, 4, 'completed', "Bar Counter"),
        (menu_objects[15][0].id, 1, 'preparing', "Table 2 - Corporate"),
    ]

    for item_id, qty, status, cust_name in sample_orders:
        item = db.session.get(ProductMenu, item_id)
        order = LiveOrder(
            customer_id=customer_id,
            customer_name=cust_name,
            item_id=item_id,
            quantity=qty,
            status=status,
            order_time=datetime.now(timezone.utc) - timedelta(minutes=random.randint(5, 120)),
            total_price=qty * item.unit_price if item else 0.0
        )
        db.session.add(order)
    db.session.commit()

    # 5. Seed Surplus Food & NGO Redistribution records
    print("[SEED] Creating surplus food redistribution records for NGO coordination...")
    # Record 1: Available for NGO
    surplus_biryani = SurplusRedistribution(
        item_id=menu_objects[4][0].id, # Dum Biryani
        surplus_qty=12,
        status='available_for_ngo',
        logged_at=datetime.now(timezone.utc) - timedelta(hours=2),
        notes="Freshly prepared evening batch. Packaged in sanitized foil containers."
    )
    # Record 2: Available for NGO
    surplus_kebabs = SurplusRedistribution(
        item_id=menu_objects[0][0].id, # Paneer Tikka
        surplus_qty=8,
        status='available_for_ngo',
        logged_at=datetime.now(timezone.utc) - timedelta(hours=1, minutes=20),
        notes="Portioned with mint chutney and lemon wedges."
    )
    # Record 3: Claimed by NGO
    surplus_cake = SurplusRedistribution(
        item_id=menu_objects[9][0].id, # Chocolate Lava Cake
        surplus_qty=15,
        status='claimed',
        logged_at=datetime.now(timezone.utc) - timedelta(hours=5),
        claimed_by_ngo="Robin Hood Army - Local Chapter",
        claimed_at=datetime.now(timezone.utc) - timedelta(hours=3),
        contact_phone="+91 98765 43210",
        pickup_eta="Picked up at 8:30 PM",
        notes="Distributed to community evening shelter."
    )
    db.session.add_all([surplus_biryani, surplus_kebabs, surplus_cake])
    db.session.commit()

    print("[SEED] Database seeding completed successfully with rich ML feature variance!")
