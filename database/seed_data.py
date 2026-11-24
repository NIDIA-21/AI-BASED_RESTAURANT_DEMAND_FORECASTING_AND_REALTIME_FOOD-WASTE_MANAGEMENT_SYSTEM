"""
Database Seeding Script:
Customized exactly for the 10 specified Indian menu items & zero-password database schema.
Generates rich synthetic data with deep variance across:
- 10 Specific Menu Items:
  1. Masala Dosa
  2. Idli
  3. Poori
  4. Veg Meals
  5. Paneer Rice
  6. Samosa
  7. Veg Sandwich
  8. Coffee
  9. Tea
  10. Chapati and Curry
- 10 Raw Ingredients & Recipe Mappings (Bill of Materials)
- Day Types: 'weekday', 'weekend', 'festival', 'office_party', 'birthday_celebration'
- Customer Counts: 50 to 450
- Weather Conditions: 'Sunny', 'Rainy', 'Cloudy', 'Stormy', 'Cold'
- Realistic user accounts with hashed credentials
- Daily Food Preparation & Overproduction Records
- Food Waste Logs by Cause, Cost Loss & Disposal Method
- Surplus Food Donations to Community NGOs
"""

import random
from datetime import datetime, date, timedelta, timezone
from backend.models import (
    db, User, ProductMenu, HistoricalSalesData,
    InventoryStock, LiveOrder, SurplusRedistribution,
    InventoryIngredient, MenuItemIngredient, DailyFoodPrep,
    FoodWasteLog, FoodDonation
)

# Exactly the 10 specified menu items from user requirements
SAMPLE_MENU_ITEMS = [
    {
        "id": 1,
        "item_name": "Masala Dosa",
        "category": "Breakfast / Tiffin",
        "unit_price": 60.00,
        "standard_prep_cost": 20.00,
        "shelf_life_hours": 24,
        "description": "Crispy fermented crepe stuffed with spiced potato masala, served with coconut chutney & sambar.",
        "popularity_weight": 0.38,
        "event_affinity": {"weekday": 1.3, "weekend": 1.7, "festival": 1.8, "office_party": 1.1, "birthday_celebration": 1.2},
        "weather_affinity": {"Rainy": 1.35, "Cold": 1.3, "Sunny": 0.9, "Cloudy": 1.1, "Stormy": 1.25}
    },
    {
        "id": 2,
        "item_name": "Idli",
        "category": "Breakfast / Tiffin",
        "unit_price": 40.00,
        "standard_prep_cost": 12.00,
        "shelf_life_hours": 24,
        "description": "Steamed soft, fluffy fermented rice and black gram cakes with fresh coconut chutney & hot sambar.",
        "popularity_weight": 0.35,
        "event_affinity": {"weekday": 1.4, "weekend": 1.5, "festival": 1.6, "office_party": 1.0, "birthday_celebration": 1.1},
        "weather_affinity": {"Rainy": 1.25, "Cold": 1.3, "Sunny": 0.95, "Cloudy": 1.05, "Stormy": 1.15}
    },
    {
        "id": 3,
        "item_name": "Poori",
        "category": "Breakfast / Tiffin",
        "unit_price": 50.00,
        "standard_prep_cost": 15.00,
        "shelf_life_hours": 24,
        "description": "Golden puffed whole-wheat fried breads served with mildly spiced potato sagu and onion relish.",
        "popularity_weight": 0.30,
        "event_affinity": {"weekend": 1.9, "festival": 2.1, "birthday_celebration": 1.5, "office_party": 1.2, "weekday": 0.9},
        "weather_affinity": {"Rainy": 1.4, "Cold": 1.35, "Sunny": 0.85, "Cloudy": 1.1, "Stormy": 1.3}
    },
    {
        "id": 4,
        "item_name": "Veg Meals",
        "category": "Lunch",
        "unit_price": 120.00,
        "standard_prep_cost": 45.00,
        "shelf_life_hours": 24,
        "description": "Traditional full South Indian vegetarian thali with rice, sambar, rasam, kootu, poriyal, curd & appalam.",
        "popularity_weight": 0.42,
        "event_affinity": {"weekday": 1.5, "weekend": 1.6, "office_party": 1.7, "festival": 2.2, "birthday_celebration": 1.3},
        "weather_affinity": {"Rainy": 1.2, "Cold": 1.2, "Sunny": 1.0, "Cloudy": 1.05, "Stormy": 1.1}
    },
    {
        "id": 5,
        "item_name": "Paneer Rice",
        "category": "Lunch / Dinner",
        "unit_price": 130.00,
        "standard_prep_cost": 50.00,
        "shelf_life_hours": 24,
        "description": "Fragrant basmati rice tossed with spiced golden paneer cubes, whole herbs, and caramelized onions.",
        "popularity_weight": 0.32,
        "event_affinity": {"weekend": 1.8, "festival": 2.2, "office_party": 1.8, "birthday_celebration": 2.0, "weekday": 0.9},
        "weather_affinity": {"Rainy": 1.3, "Cold": 1.35, "Sunny": 0.9, "Cloudy": 1.1, "Stormy": 1.25}
    },
    {
        "id": 6,
        "item_name": "Samosa",
        "category": "Snacks",
        "unit_price": 25.00,
        "standard_prep_cost": 8.00,
        "shelf_life_hours": 24,
        "description": "Crispy flaky crust pastry filled with crushed spiced potatoes and peas with sweet tamarind chutney.",
        "popularity_weight": 0.45,
        "event_affinity": {"office_party": 2.5, "weekend": 1.6, "festival": 1.5, "birthday_celebration": 1.7, "weekday": 1.2},
        "weather_affinity": {"Rainy": 2.2, "Cold": 1.9, "Stormy": 2.1, "Cloudy": 1.4, "Sunny": 0.75}
    },
    {
        "id": 7,
        "item_name": "Veg Sandwich",
        "category": "Snacks",
        "unit_price": 60.00,
        "standard_prep_cost": 20.00,
        "shelf_life_hours": 24,
        "description": "Grilled sandwich with crisp cucumber, tomato, potato, green chutney, and seasoned butter.",
        "popularity_weight": 0.28,
        "event_affinity": {"office_party": 1.8, "weekday": 1.3, "weekend": 1.2, "birthday_celebration": 1.3, "festival": 0.9},
        "weather_affinity": {"Sunny": 1.2, "Cloudy": 1.05, "Rainy": 0.9, "Cold": 0.85, "Stormy": 0.85}
    },
    {
        "id": 8,
        "item_name": "Coffee",
        "category": "Beverages",
        "unit_price": 25.00,
        "standard_prep_cost": 8.00,
        "shelf_life_hours": 24,
        "description": "Traditional South Indian filter coffee frothed in authentic brass davara tumbler with hot boiled milk.",
        "popularity_weight": 0.40,
        "event_affinity": {"weekday": 1.5, "office_party": 1.6, "weekend": 1.3, "festival": 1.1, "birthday_celebration": 1.0},
        "weather_affinity": {"Rainy": 1.8, "Cold": 2.0, "Stormy": 1.9, "Cloudy": 1.3, "Sunny": 0.8}
    },
    {
        "id": 9,
        "item_name": "Tea",
        "category": "Beverages",
        "unit_price": 20.00,
        "standard_prep_cost": 6.00,
        "shelf_life_hours": 24,
        "description": "Fresh hot ginger cardamom milk tea brewed with Assam CTC tea leaves.",
        "popularity_weight": 0.48,
        "event_affinity": {"weekday": 1.6, "office_party": 1.8, "weekend": 1.2, "festival": 1.2, "birthday_celebration": 1.0},
        "weather_affinity": {"Rainy": 2.2, "Cold": 2.4, "Stormy": 2.3, "Cloudy": 1.4, "Sunny": 0.7}
    },
    {
        "id": 10,
        "item_name": "Chapati and Curry",
        "category": "Dinner",
        "unit_price": 70.00,
        "standard_prep_cost": 25.00,
        "shelf_life_hours": 24,
        "description": "Soft golden whole-wheat tawa chapatis served with hearty homestyle vegetable kurma.",
        "popularity_weight": 0.34,
        "event_affinity": {"weekday": 1.3, "weekend": 1.4, "festival": 1.6, "office_party": 1.2, "birthday_celebration": 1.2},
        "weather_affinity": {"Rainy": 1.3, "Cold": 1.35, "Sunny": 0.95, "Cloudy": 1.05, "Stormy": 1.2}
    }
]

# 10 Raw Ingredients matching database schema
RAW_INGREDIENTS = [
    (1, 'Rice & Urad Dal Batter', 'Prepared Batter', 25.0, 'kg', 35.00, 8.0, '2026-11-26', 'Refrigerator'),
    (2, 'Potatoes', 'Produce', 40.0, 'kg', 25.00, 10.0, '2026-12-10', 'Dry Pantry'),
    (3, 'Wheat Flour (Atta)', 'Dry Goods', 50.0, 'kg', 38.00, 15.0, '2027-02-15', 'Dry Storage'),
    (4, 'Fresh Paneer', 'Dairy', 12.0, 'kg', 280.00, 4.0, '2026-11-27', 'Cold Storage'),
    (5, 'Basmati Rice', 'Dry Goods', 60.0, 'kg', 75.00, 20.0, '2027-05-01', 'Dry Storage'),
    (6, 'Bread Slices', 'Bakery', 15.0, 'packets', 40.00, 5.0, '2026-11-26', 'Pantry'),
    (7, 'Fresh Milk', 'Dairy', 30.0, 'liters', 55.00, 10.0, '2026-11-25', 'Refrigerator'),
    (8, 'Coffee Powder & Tea Leaves', 'Dry Goods', 10.0, 'kg', 400.00, 3.0, '2027-04-10', 'Pantry Shelf'),
    (9, 'Cooking Oil', 'Dry Goods', 40.0, 'liters', 130.00, 12.0, '2027-06-30', 'Storage Room'),
    (10, 'Mixed Vegetables (Carrot, Beans, Peas)', 'Produce', 25.0, 'kg', 45.00, 8.0, '2026-11-26', 'Cold Storage')
]

# Recipe mappings (item_id, ingredient_id, quantity_required)
RECIPE_MAPPINGS = [
    (1, 1, 0.20), (1, 2, 0.10),
    (2, 1, 0.25),
    (3, 3, 0.15), (3, 2, 0.10),
    (4, 5, 0.25), (4, 10, 0.20),
    (5, 4, 0.15), (5, 5, 0.20),
    (6, 2, 0.12),
    (7, 6, 0.20), (7, 10, 0.10),
    (8, 7, 0.15),
    (9, 7, 0.15),
    (10, 3, 0.18), (10, 10, 0.15)
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
    Automated seed script generating rich historical records and context data for the 10 menu items.
    """
    # Check if database already seeded with exactly 10 items
    existing_items = ProductMenu.query.count()
    if existing_items == 10 and not force:
        print(f"[SEED] Database already contains the 10 menu items. Skipping seed.")
        return

    print("[SEED] Starting comprehensive database seeding for 10 Indian Menu Items...")

    # Clear existing tables if forced or count differs
    print("[SEED] Clearing existing records for a fresh synchronization...")
    FoodDonation.query.delete()
    FoodWasteLog.query.delete()
    DailyFoodPrep.query.delete()
    MenuItemIngredient.query.delete()
    InventoryIngredient.query.delete()
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
        user = User(
            username=u['username'],
            email=u['email'],
            role=u['role']
        )
        user.set_password(u['password'])
        db.session.add(user)
        user_objects[u['username']] = user
    db.session.commit()

    # 2. Seed Raw Ingredients
    print(f"[SEED] Inserting {len(RAW_INGREDIENTS)} raw ingredients...")
    for ingr_data in RAW_INGREDIENTS:
        ingr = InventoryIngredient(
            ingredient_id=ingr_data[0],
            ingredient_name=ingr_data[1],
            category=ingr_data[2],
            quantity_in_stock=ingr_data[3],
            unit=ingr_data[4],
            cost_per_unit=ingr_data[5],
            reorder_level=ingr_data[6],
            expiry_date=ingr_data[7],
            storage_location=ingr_data[8]
        )
        db.session.add(ingr)
    db.session.commit()

    # 3. Seed 10 Menu Items & Inventory
    print(f"[SEED] Inserting {len(SAMPLE_MENU_ITEMS)} menu items and initial stock levels...")
    menu_objects = []
    for item_data in SAMPLE_MENU_ITEMS:
        item = ProductMenu(
            id=item_data['id'],
            item_name=item_data['item_name'],
            category=item_data['category'],
            unit_price=item_data['unit_price'],
            standard_prep_cost=item_data['standard_prep_cost'],
            shelf_life_hours=item_data['shelf_life_hours'],
            description=item_data['description']
        )
        db.session.add(item)
        db.session.flush()
        menu_objects.append((item, item_data))

        # Initial finished dish inventory stock
        init_stock = random.randint(30, 70)
        min_thresh = random.randint(10, 20)
        inv = InventoryStock(
            item_id=item.id,
            current_stock_qty=init_stock,
            min_threshold_qty=min_thresh,
            last_restocked_at=datetime.now(timezone.utc)
        )
        db.session.add(inv)
    db.session.commit()

    # 4. Seed Recipe Mappings
    print(f"[SEED] Mapping recipes (Bill of Materials)...")
    for r in RECIPE_MAPPINGS:
        recipe_entry = MenuItemIngredient(
            item_id=r[0],
            ingredient_id=r[1],
            quantity_required=r[2]
        )
        db.session.add(recipe_entry)
    db.session.commit()

    # 5. Seed Historical Sales Data (180 days for all 10 items)
    print(f"[SEED] Generating {days_of_history} days of historical sales records for 10 menu items...")
    today = date.today()
    start_date = today - timedelta(days=days_of_history)

    weather_choices = ['Sunny', 'Rainy', 'Cloudy', 'Stormy', 'Cold']
    weather_weights = [0.45, 0.25, 0.15, 0.05, 0.10]

    historical_records = []
    total_sales_points = 0
    festival_offsets = {5, 6, 25, 26, 60, 61, 105, 120, 150}

    for d in range(days_of_history):
        current_date = start_date + timedelta(days=d)
        weekday_num = current_date.weekday()

        if (days_of_history - d) in festival_offsets:
            day_type = 'festival'
        elif weekday_num in (4, 5, 6):
            roll = random.random()
            if roll < 0.65:
                day_type = 'weekend'
            elif roll < 0.85:
                day_type = 'office_party' if weekday_num == 4 else 'birthday_celebration'
            else:
                day_type = 'birthday_celebration'
        else:
            roll = random.random()
            if roll < 0.75:
                day_type = 'weekday'
            elif roll < 0.92:
                day_type = 'office_party'
            else:
                day_type = 'birthday_celebration'

        if day_type == 'weekday':
            customer_count = random.randint(70, 130)
        elif day_type == 'weekend':
            customer_count = random.randint(180, 310)
        elif day_type == 'office_party':
            customer_count = random.randint(150, 260)
        elif day_type == 'birthday_celebration':
            customer_count = random.randint(130, 220)
        else:
            customer_count = random.randint(280, 460)

        weather = random.choices(weather_choices, weights=weather_weights, k=1)[0]

        for item, item_meta in menu_objects:
            base_pop = item_meta['popularity_weight']
            event_mult = item_meta['event_affinity'].get(day_type, 1.0)
            weather_mult = item_meta['weather_affinity'].get(weather, 1.0)

            expected_demand = customer_count * base_pop * event_mult * weather_mult
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

            if len(historical_records) >= 500:
                db.session.bulk_save_objects(historical_records)
                db.session.commit()
                historical_records = []

    if historical_records:
        db.session.bulk_save_objects(historical_records)
        db.session.commit()

    print(f"[SEED] Successfully generated {total_sales_points} historical sales data points!")

    # 6. Seed Daily Food Prep Records
    print("[SEED] Creating daily food prep records...")
    prep_data = [
        ('2026-11-23', 2, 50, 42),  # Idli
        ('2026-11-23', 4, 40, 31),  # Veg Meals
        ('2026-11-23', 6, 60, 48),  # Samosa
        ('2026-11-24', 1, 45, 43),  # Masala Dosa
        ('2026-11-24', 4, 35, 30),  # Veg Meals
        ('2026-11-24', 10, 40, 34)  # Chapati & Curry
    ]
    for p in prep_data:
        daily_p = DailyFoodPrep(
            prep_date=p[0],
            item_id=p[1],
            quantity_prepared=p[2],
            quantity_sold=p[3]
        )
        db.session.add(daily_p)
    db.session.commit()

    # 7. Seed Food Waste Logs
    print("[SEED] Creating food waste logs...")
    waste_logs = [
        (datetime(2026, 11, 23, 15, 30), 'Prepared Food', 'Veg Meals', 6.0, 'portions', 'Overproduction / Unsold', 270.00, 'Head Chef Ramesh', 'Composted'),
        (datetime(2026, 11, 23, 18, 0), 'Prepared Food', 'Samosa', 8.0, 'pieces', 'Overproduction / Unsold', 64.00, 'Cook Suresh', 'Animal Feed'),
        (datetime(2026, 11, 23, 20, 30), 'Prepared Food', 'Masala Dosa', 3.0, 'plates', 'Kitchen Error / Burnt', 60.00, 'Tiffin Master Anand', 'Landfill'),
        (datetime(2026, 11, 24, 14, 15), 'Prepared Food', 'Veg Meals (Leftover Rice)', 2.5, 'kg', 'Plate Waste (Leftover by customer)', 90.00, 'Kitchen Busser', 'Composted'),
        (datetime(2026, 11, 24, 16, 0), 'Raw Ingredient', 'Fresh Milk', 3.0, 'liters', 'Expired / Spoiled', 165.00, 'Storekeeper Priya', 'Landfill'),
        (datetime(2026, 11, 24, 21, 30), 'Prepared Food', 'Chapati and Curry', 5.0, 'portions', 'Overproduction / Unsold', 125.00, 'Head Chef Ramesh', 'Donation')
    ]
    for w in waste_logs:
        waste_entry = FoodWasteLog(
            log_date=w[0],
            item_type=w[1],
            item_name=w[2],
            quantity_wasted=w[3],
            unit=w[4],
            waste_reason=w[5],
            cost_loss=w[6],
            recorded_by=w[7],
            disposal_method=w[8]
        )
        db.session.add(waste_entry)
    db.session.commit()

    # 8. Seed Food Donations
    print("[SEED] Creating community food donation logs...")
    donations = [
        (datetime(2026, 11, 23, 22, 30), 'Robin Hood Army Food Drive', 'Untouched surplus Chapatis and Vegetable Curry', 15.0, 'packets', 'Vikram Volunteer', 'Delivered'),
        (datetime(2026, 11, 24, 22, 0), 'Sneha Orphanage & Care Home', 'Freshly packed Idlis and Samosas', 20.0, 'portions', 'Kavita Coordinator', 'Delivered')
    ]
    for don in donations:
        donation_entry = FoodDonation(
            donation_date=don[0],
            recipient_organization=don[1],
            food_description=don[2],
            quantity=don[3],
            unit=don[4],
            driver_or_contact=don[5],
            donation_status=don[6]
        )
        db.session.add(donation_entry)
    db.session.commit()

    # 9. Seed Active Live Orders for Today
    print("[SEED] Creating initial live orders for the current service shift...")
    customer_user = User.query.filter_by(role='customer').first()
    customer_id = customer_user.id if customer_user else None

    sample_orders = [
        (1, 2, 'completed', "Table 3 - Dine In"),  # Masala Dosa
        (2, 2, 'completed', "Table 5 - Dine In"),  # Idli
        (8, 2, 'completed', "Table 3 - Dine In"),  # Coffee
        (4, 2, 'preparing', "Table 2 - Family"),   # Veg Meals
        (6, 4, 'preparing', "Walk-in Takeaway"),  # Samosa
        (9, 2, 'pending', "Table 8 - Tea Order"),  # Tea
        (5, 3, 'pending', "Table 11 - Evening"),   # Paneer Rice
        (10, 2, 'preparing', "Table 4 - Dinner"),  # Chapati & Curry
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

    # 10. Seed Surplus Food & NGO Redistribution records
    print("[SEED] Creating surplus food redistribution records for NGO coordination...")
    surplus_records = [
        SurplusRedistribution(
            item_id=4, # Veg Meals
            surplus_qty=9,
            status='available_for_ngo',
            logged_at=datetime.now(timezone.utc) - timedelta(hours=2),
            notes="Untouched surplus afternoon Veg Meals packed in clean food-grade foil containers."
        ),
        SurplusRedistribution(
            item_id=6, # Samosa
            surplus_qty=12,
            status='available_for_ngo',
            logged_at=datetime.now(timezone.utc) - timedelta(hours=1, minutes=15),
            notes="Freshly prepared evening batch samosas ready for NGO dispatch."
        ),
        SurplusRedistribution(
            item_id=10, # Chapati and Curry
            surplus_qty=15,
            status='claimed',
            logged_at=datetime.now(timezone.utc) - timedelta(hours=4),
            claimed_by_ngo="Robin Hood Army - Mangalore Chapter",
            claimed_at=datetime.now(timezone.utc) - timedelta(hours=2),
            contact_phone="+91 98765 43210",
            pickup_eta="Picked up at 8:30 PM",
            notes="Distributed to local shelter."
        )
    ]
    db.session.add_all(surplus_records)
    db.session.commit()

    print("[SEED] Database seeding completed successfully with 10 menu items and full tracking schema!")
