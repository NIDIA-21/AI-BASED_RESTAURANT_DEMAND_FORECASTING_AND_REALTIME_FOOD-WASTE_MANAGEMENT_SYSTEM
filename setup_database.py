"""
Restaurant Management & Food Waste Tracking
Zero-Password Database Setup Script (SQLite & MySQL compatible)

Run this script on ANY computer with:
    python setup_database.py

It requires NO root passwords, NO MySQL server, and works out-of-the-box
with Python's built-in sqlite3!
"""

import sqlite3
import os

DB_NAME = "restaurant_waste.db"

def init_db():
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
    cursor.executemany("""
    INSERT INTO menu_items (item_id, item_name, category, price, cost_price, shelf_life_days, is_available)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, [
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
    ])

    # INSERT RAW INGREDIENTS
    cursor.executemany("""
    INSERT INTO inventory_ingredients (ingredient_id, ingredient_name, category, quantity_in_stock, unit, cost_per_unit, reorder_level, expiry_date, storage_location)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, [
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
    ])

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

    # INSERT ORDERS
    cursor.executemany("""
    INSERT INTO orders (order_date, table_number, order_type, total_amount, order_status)
    VALUES (?, ?, ?, ?, ?);
    """, [
        ('2026-11-24 08:30:00', 3, 'Dine-In', 125.00, 'Completed'),
        ('2026-11-24 09:15:00', 5, 'Dine-In', 85.00, 'Completed'),
        ('2026-11-24 13:00:00', 2, 'Dine-In', 250.00, 'Completed'),
        ('2026-11-24 17:30:00', None, 'Takeaway', 70.00, 'Completed')
    ])

    # INSERT ORDER ITEMS
    cursor.executemany("""
    INSERT INTO order_items (order_id, item_id, quantity, subtotal)
    VALUES (?, ?, ?, ?);
    """, [
        (1, 1, 1, 60.00),
        (1, 2, 1, 40.00),
        (1, 8, 1, 25.00),
        (2, 3, 1, 50.00),
        (2, 8, 1, 25.00),
        (3, 4, 2, 240.00),
        (4, 6, 2, 50.00),
        (4, 9, 1, 20.00)
    ])

    # INSERT DAILY FOOD PREP
    cursor.executemany("""
    INSERT INTO daily_food_prep (prep_date, item_id, quantity_prepared, quantity_sold)
    VALUES (?, ?, ?, ?);
    """, [
        ('2026-11-23', 2, 50, 42),
        ('2026-11-23', 4, 40, 31),
        ('2026-11-23', 6, 60, 48),
        ('2026-11-24', 1, 45, 43),
        ('2026-11-24', 4, 35, 30),
        ('2026-11-24', 10, 40, 34)
    ])

    # INSERT FOOD WASTE LOGS
    cursor.executemany("""
    INSERT INTO food_waste_logs (log_date, item_type, item_name, quantity_wasted, unit, waste_reason, cost_loss, recorded_by, disposal_method)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, [
        ('2026-11-23 15:30:00', 'Prepared Food', 'Veg Meals', 6.0, 'portions', 'Overproduction / Unsold', 270.00, 'Head Chef Ramesh', 'Composted'),
        ('2026-11-23 18:00:00', 'Prepared Food', 'Samosa', 8.0, 'pieces', 'Overproduction / Unsold', 64.00, 'Cook Suresh', 'Animal Feed'),
        ('2026-11-23 20:30:00', 'Prepared Food', 'Masala Dosa', 3.0, 'plates', 'Kitchen Error / Burnt', 60.00, 'Tiffin Master Anand', 'Landfill'),
        ('2026-11-24 14:15:00', 'Prepared Food', 'Veg Meals (Leftover Rice)', 2.5, 'kg', 'Plate Waste (Leftover by customer)', 90.00, 'Kitchen Busser', 'Composted'),
        ('2026-11-24 16:00:00', 'Raw Ingredient', 'Fresh Milk', 3.0, 'liters', 'Expired / Spoiled', 165.00, 'Storekeeper Priya', 'Landfill'),
        ('2026-11-24 21:30:00', 'Prepared Food', 'Chapati and Curry', 5.0, 'portions', 'Overproduction / Unsold', 125.00, 'Head Chef Ramesh', 'Donation')
    ])

    # INSERT FOOD DONATIONS
    cursor.executemany("""
    INSERT INTO food_donations (donation_date, recipient_organization, food_description, quantity, unit, driver_or_contact, donation_status)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, [
        ('2026-11-23 22:30:00', 'Robin Hood Army Food Drive', 'Untouched surplus Chapatis and Vegetable Curry', 15.0, 'packets', 'Vikram Volunteer', 'Delivered'),
        ('2026-11-24 22:00:00', 'Sneha Orphanage & Care Home', 'Freshly packed Idlis and Samosas', 20.0, 'portions', 'Kavita Coordinator', 'Delivered')
    ])

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

    conn.commit()
    conn.close()
    print("SUCCESS! 'restaurant_waste.db' created successfully with all 10 items and zero passwords!")

if __name__ == "__main__":
    init_db()
