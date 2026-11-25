"""
Restaurant Management & Food Waste Tracking
Zero-Password Database Setup Script (SQLite & MySQL compatible)

Generates a realistic 3-month (90-day) operational database spanning
2026-08-27 to 2026-11-24 based on the 10-item restaurant schema.

Run this script on ANY computer with:
    python setup_database.py

It requires NO root passwords, NO MySQL server, and works out-of-the-box
with Python's built-in sqlite3!
"""

import os
import random
import sqlite3
from datetime import date, datetime, timedelta

DB_NAME = "restaurant_waste.db"
DAYS_OF_HISTORY = 90  # ~3 months
END_DATE = date(2026, 11, 24)
START_DATE = END_DATE - timedelta(days=DAYS_OF_HISTORY - 1)


def init_db():
    random.seed(42)

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Removed existing {DB_NAME} to ensure a fresh start.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. MENU ITEMS
    cursor.execute("""
    CREATE TABLE menu_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        cost_price REAL NOT NULL,
        shelf_life_days INTEGER DEFAULT 1,
        is_available INTEGER DEFAULT 1
    );
    """)

    # 2. INVENTORY & INGREDIENTS
    cursor.execute("""
    CREATE TABLE inventory_ingredients (
        ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingredient_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity_in_stock REAL NOT NULL,
        unit TEXT NOT NULL,
        cost_per_unit REAL NOT NULL,
        reorder_level REAL NOT NULL,
        expiry_date TEXT NOT NULL,
        storage_location TEXT DEFAULT 'Main Kitchen'
    );
    """)

    # 3. RECIPE MAPPING
    cursor.execute("""
    CREATE TABLE menu_item_ingredients (
        recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        quantity_required REAL NOT NULL,
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id),
        FOREIGN KEY (ingredient_id) REFERENCES inventory_ingredients(ingredient_id)
    );
    """)

    # 4. ORDERS
    cursor.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_date TEXT DEFAULT CURRENT_TIMESTAMP,
        table_number INTEGER,
        order_type TEXT DEFAULT 'Dine-In',
        total_amount REAL DEFAULT 0.00,
        order_status TEXT DEFAULT 'Completed'
    );
    """)

    # 5. ORDER ITEMS
    cursor.execute("""
    CREATE TABLE order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
    );
    """)

    # 6. DAILY FOOD PREP
    cursor.execute("""
    CREATE TABLE daily_food_prep (
        prep_id INTEGER PRIMARY KEY AUTOINCREMENT,
        prep_date TEXT NOT NULL,
        item_id INTEGER NOT NULL,
        quantity_prepared INTEGER NOT NULL,
        quantity_sold INTEGER DEFAULT 0,
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
    );
    """)

    # 7. FOOD WASTE LOGS
    cursor.execute("""
    CREATE TABLE food_waste_logs (
        waste_id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT DEFAULT CURRENT_TIMESTAMP,
        item_type TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity_wasted REAL NOT NULL,
        unit TEXT NOT NULL,
        waste_reason TEXT NOT NULL,
        cost_loss REAL NOT NULL,
        recorded_by TEXT DEFAULT 'Kitchen Supervisor',
        disposal_method TEXT DEFAULT 'Landfill'
    );
    """)

    # 8. FOOD DONATIONS
    cursor.execute("""
    CREATE TABLE food_donations (
        donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        donation_date TEXT DEFAULT CURRENT_TIMESTAMP,
        recipient_organization TEXT NOT NULL,
        food_description TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL,
        driver_or_contact TEXT,
        donation_status TEXT DEFAULT 'Delivered'
    );
    """)

    # INSERT 10 INDIAN MENU ITEMS
    menu_items_data = [
        (1, 'Masala Dosa', 'Breakfast / Tiffin', 60.00, 20.00, 1, 1),
        (2, 'Idli', 'Breakfast / Tiffin', 40.00, 12.00, 1, 1),
        (3, 'Poori', 'Breakfast / Tiffin', 50.00, 15.00, 1, 1),
        (4, 'Veg Meals', 'Lunch', 120.00, 45.00, 1, 1),
        (5, 'Paneer Rice', 'Lunch / Dinner', 130.00, 50.00, 1, 1),
        (6, 'Samosa', 'Snacks', 25.00, 8.00, 1, 1),
        (7, 'Veg Sandwich', 'Snacks', 60.00, 20.00, 1, 1),
        (8, 'Coffee', 'Beverages', 25.00, 8.00, 1, 1),
        (9, 'Tea', 'Beverages', 20.00, 6.00, 1, 1),
        (10, 'Chapati and Curry', 'Dinner', 70.00, 25.00, 1, 1)
    ]
    cursor.executemany("""
    INSERT INTO menu_items (item_id, item_name, category, price, cost_price, shelf_life_days, is_available)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, menu_items_data)

    menu_lookup = {
        row[0]: {'name': row[1], 'category': row[2], 'price': row[3], 'cost': row[4]}
        for row in menu_items_data
    }

    # INSERT RAW INGREDIENTS
    ingredients_data = [
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
    cursor.executemany("""
    INSERT INTO inventory_ingredients (ingredient_id, ingredient_name, category, quantity_in_stock, unit, cost_per_unit, reorder_level, expiry_date, storage_location)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, ingredients_data)

    # INSERT RECIPE MAPPING
    cursor.executemany("""
    INSERT INTO menu_item_ingredients (item_id, ingredient_id, quantity_required)
    VALUES (?, ?, ?);
    """, [
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
    ])

    # GENERATE 3 MONTHS (90 DAYS) OF ORDERS, ORDER ITEMS, DAILY PREP, WASTE LOGS & DONATIONS
    meal_slot_items = {
        'breakfast': ([1, 2, 3, 8, 9], range(8, 11)),
        'lunch': ([4, 5, 8, 9], range(12, 15)),
        'snacks': ([6, 7, 8, 9], range(16, 19)),
        'dinner': ([5, 10, 1, 8, 9], range(19, 22))
    }

    orders_rows = []
    order_items_rows = []
    prep_rows = []
    waste_rows = []
    donation_rows = []

    order_id_seq = 1
    staff_members = ['Head Chef Ramesh', 'Cook Suresh', 'Tiffin Master Anand', 'Kitchen Busser', 'Storekeeper Priya']
    prepared_reasons = [
        ('Overproduction / Unsold', ['Composted', 'Animal Feed', 'Donation']),
        ('Kitchen Error / Burnt', ['Landfill', 'Composted']),
        ('Plate Waste (Leftover by customer)', ['Composted', 'Animal Feed']),
        ('Handling / Dropped', ['Landfill', 'Composted'])
    ]
    ngo_partners = [
        ('Robin Hood Army Food Drive', 'Vikram Volunteer'),
        ('Sneha Orphanage & Care Home', 'Kavita Coordinator'),
        ('Feeding India - Mangalore Chapter', 'Arjun Rao'),
        ('Karuna Shelter Home', 'Meera Nair')
    ]
    donation_descriptions = [
        'Untouched surplus Chapatis and Vegetable Curry',
        'Freshly packed Idlis and Samosas',
        'Surplus Veg Meals and Steamed Rice',
        'Packed Masala Dosa & Paneer Rice portions',
        'Evening batch Samosas and Veg Sandwiches'
    ]

    popularity_weights = {
        1: 0.38, 2: 0.35, 3: 0.30, 4: 0.42, 5: 0.32,
        6: 0.45, 7: 0.28, 8: 0.40, 9: 0.48, 10: 0.34
    }

    for day_offset in range(DAYS_OF_HISTORY):
        current_date = START_DATE + timedelta(days=day_offset)
        date_str = current_date.strftime('%Y-%m-%d')
        is_weekend = current_date.weekday() in (4, 5, 6)

        # Orders per day (higher on weekends)
        num_orders = random.randint(14, 22) if is_weekend else random.randint(9, 15)
        daily_sold_counts = {item_id: 0 for item_id in menu_lookup}

        for _ in range(num_orders):
            slot = random.choice(['breakfast', 'lunch', 'snacks', 'dinner'])
            candidate_items, hour_range = meal_slot_items[slot]
            order_hour = random.choice(list(hour_range))
            order_minute = random.choice([0, 10, 15, 25, 30, 40, 45, 50])
            order_dt = f"{date_str} {order_hour:02d}:{order_minute:02d}:00"

            order_type = random.choices(['Dine-In', 'Takeaway', 'Online Delivery'], weights=[0.65, 0.20, 0.15], k=1)[0]
            table_num = random.randint(1, 12) if order_type == 'Dine-In' else None

            chosen_items = random.sample(candidate_items, k=random.randint(1, min(3, len(candidate_items))))
            total_amt = 0.0
            for item_id in chosen_items:
                qty = random.randint(1, 3)
                subtotal = round(qty * menu_lookup[item_id]['price'], 2)
                total_amt += subtotal
                daily_sold_counts[item_id] += qty
                order_items_rows.append((order_id_seq, item_id, qty, subtotal))

            orders_rows.append((order_dt, table_num, order_type, round(total_amt, 2), 'Completed'))
            order_id_seq += 1

        # Daily food prep (tracked for 4-6 items per day, aligned with realistic volume)
        tracked_items = random.sample(list(menu_lookup.keys()), k=random.randint(4, 6))
        for item_id in tracked_items:
            base_sold = max(daily_sold_counts[item_id], int(round(random.gauss(50 * popularity_weights[item_id] * (2.6 if is_weekend else 2.0), 7))))
            surplus = random.randint(2, 12) if random.random() < 0.80 else 0
            prepared = base_sold + surplus
            prep_rows.append((date_str, item_id, prepared, base_sold))

        # Food waste logs (1-3 incidents per day)
        num_waste = random.choices([1, 2, 3], weights=[0.40, 0.45, 0.15], k=1)[0]
        for _ in range(num_waste):
            hour = random.randint(13, 21)
            minute = random.choice([0, 15, 30, 45])
            log_dt = f"{date_str} {hour:02d}:{minute:02d}:00"
            if random.random() < 0.80:
                item_id = random.choice(list(menu_lookup.keys()))
                item_info = menu_lookup[item_id]
                qty = float(random.randint(2, 9))
                reason, disposals = random.choice(prepared_reasons)
                cost_loss = round(qty * item_info['cost'], 2)
                unit = 'pieces' if item_info['name'] == 'Samosa' else ('plates' if 'Dosa' in item_info['name'] else 'portions')
                waste_rows.append((
                    log_dt, 'Prepared Food', item_info['name'], qty, unit,
                    reason, cost_loss, random.choice(staff_members), random.choice(disposals)
                ))
            else:
                ingr = random.choice(ingredients_data)
                qty = round(random.uniform(1.0, 4.0), 1)
                cost_loss = round(qty * ingr[5], 2)
                waste_rows.append((
                    log_dt, 'Raw Ingredient', ingr[1], qty, ingr[4],
                    'Expired / Spoiled', cost_loss, 'Storekeeper Priya', random.choice(['Landfill', 'Composted'])
                ))

        # Community food donations every 2 days
        if day_offset % 2 == 0:
            org, contact = random.choice(ngo_partners)
            don_dt = f"{date_str} {random.randint(21, 22):02d}:{random.choice([0, 30]):02d}:00"
            donation_rows.append((
                don_dt, org, random.choice(donation_descriptions),
                float(random.randint(10, 30)), random.choice(['packets', 'portions']),
                contact, 'Delivered'
            ))

    cursor.executemany("""
    INSERT INTO orders (order_date, table_number, order_type, total_amount, order_status)
    VALUES (?, ?, ?, ?, ?);
    """, orders_rows)

    cursor.executemany("""
    INSERT INTO order_items (order_id, item_id, quantity, subtotal)
    VALUES (?, ?, ?, ?);
    """, order_items_rows)

    cursor.executemany("""
    INSERT INTO daily_food_prep (prep_date, item_id, quantity_prepared, quantity_sold)
    VALUES (?, ?, ?, ?);
    """, prep_rows)

    cursor.executemany("""
    INSERT INTO food_waste_logs (log_date, item_type, item_name, quantity_wasted, unit, waste_reason, cost_loss, recorded_by, disposal_method)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, waste_rows)

    cursor.executemany("""
    INSERT INTO food_donations (donation_date, recipient_organization, food_description, quantity, unit, driver_or_contact, donation_status)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, donation_rows)

    # CREATE ANALYTICAL VIEWS
    cursor.execute("""
    CREATE VIEW IF NOT EXISTS vw_waste_by_reason AS
    SELECT 
        waste_reason,
        COUNT(waste_id) AS total_incidents,
        SUM(cost_loss) AS total_financial_loss,
        ROUND(SUM(cost_loss) * 100.0 / (SELECT SUM(cost_loss) FROM food_waste_logs), 2) AS percentage_of_total_loss
    FROM food_waste_logs
    GROUP BY waste_reason
    ORDER BY total_financial_loss DESC;
    """)

    cursor.execute("""
    CREATE VIEW IF NOT EXISTS vw_overproduction_analysis AS
    SELECT 
        p.prep_date,
        m.item_name,
        m.category,
        p.quantity_prepared,
        p.quantity_sold,
        (p.quantity_prepared - p.quantity_sold) AS quantity_surplus,
        ROUND(((p.quantity_prepared - p.quantity_sold) * 1.0 / p.quantity_prepared) * 100, 1) AS waste_risk_percentage
    FROM daily_food_prep p
    JOIN menu_items m ON p.item_id = m.item_id
    WHERE (p.quantity_prepared - p.quantity_sold) > 0
    ORDER BY p.prep_date DESC, quantity_surplus DESC;
    """)

    cursor.execute("""
    CREATE VIEW IF NOT EXISTS vw_expiring_soon_alert AS
    SELECT
        ingredient_id,
        ingredient_name,
        category,
        quantity_in_stock,
        unit,
        expiry_date,
        CAST(julianday(expiry_date) - julianday('2026-11-24') AS INTEGER) AS days_until_expiry,
        storage_location
    FROM inventory_ingredients
    WHERE julianday(expiry_date) <= julianday('2026-11-24', '+5 days')
    ORDER BY days_until_expiry ASC;
    """)

    cursor.execute("""
    CREATE VIEW IF NOT EXISTS vw_environmental_impact AS
    SELECT
        disposal_method,
        COUNT(*) AS incident_count,
        ROUND(SUM(quantity_wasted), 2) AS total_quantity,
        ROUND(SUM(cost_loss), 2) AS total_cost_value
    FROM food_waste_logs
    GROUP BY disposal_method;
    """)

    conn.commit()
    conn.close()
    print(
        f"SUCCESS! '{DB_NAME}' created with {DAYS_OF_HISTORY} days ({START_DATE} to {END_DATE}) "
        f"| Orders: {len(orders_rows)} | OrderItems: {len(order_items_rows)} "
        f"| DailyPrep: {len(prep_rows)} | WasteLogs: {len(waste_rows)} | Donations: {len(donation_rows)}"
    )


if __name__ == "__main__":
    init_db()
