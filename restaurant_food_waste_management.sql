-- =====================================================================
-- RESTAURANT MANAGEMENT & FOOD WASTE REDUCTION DATABASE SYSTEM (MySQL)
-- Database: restaurant_management
-- Scope: Physical Restaurant Operations Only (Dine-In & Takeaway)
-- Safety: Non-destructive DDL (No DROP TABLE / DROP DATABASE)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS restaurant_management
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE restaurant_management;

-- ---------------------------------------------------------------------
-- TABLE 1: menu_items
-- Master catalog of the 10 physical restaurant dishes
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS menu_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    cost_price DECIMAL(10,2) NOT NULL,
    shelf_life_days INT NOT NULL DEFAULT 1,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_menu_item_name (item_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 2: inventory_ingredients
-- Raw stock, shelf-life, and expiry tracking to prevent spoilage
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory_ingredients (
    ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
    ingredient_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    quantity_in_stock DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    unit VARCHAR(20) NOT NULL,
    cost_per_unit DECIMAL(10,2) NOT NULL,
    reorder_level DECIMAL(10,2) NOT NULL,
    expiry_date DATE NOT NULL,
    storage_location VARCHAR(50) DEFAULT 'Main Kitchen',
    UNIQUE KEY uq_ingredient_name (ingredient_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 3: menu_item_ingredients (Recipe / Bill of Materials)
-- Maps each menu item to the raw ingredient quantities required
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS menu_item_ingredients (
    recipe_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    ingredient_id INT NOT NULL,
    quantity_required DECIMAL(10,2) NOT NULL,
    UNIQUE KEY uq_recipe_item_ingredient (item_id, ingredient_id),
    CONSTRAINT fk_recipe_menu_item
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_recipe_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES inventory_ingredients(ingredient_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 4: orders
-- Customer orders for physical restaurant ONLY (Dine-In and Takeaway)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    table_number INT NULL,
    order_type ENUM('Dine-In', 'Takeaway') NOT NULL DEFAULT 'Dine-In',
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    order_status ENUM('Pending', 'Preparing', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Completed',
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_orders_date (order_date),
    INDEX idx_orders_type (order_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 5: order_items
-- Individual menu items inside each customer order
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    subtotal DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_order_items_menu_item
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 6: daily_food_prep
-- Tracks prepared, sold, wasted, and donated quantities separately.
-- Both quantity_surplus and remaining_prepared_stock exclude wasted and
-- donated food and are clamped at 0 to prevent negative stock.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_food_prep (
    prep_id INT AUTO_INCREMENT PRIMARY KEY,
    prep_date DATE NOT NULL,
    item_id INT NOT NULL,
    quantity_prepared INT NOT NULL,
    quantity_sold INT NOT NULL DEFAULT 0,
    quantity_wasted INT NOT NULL DEFAULT 0,
    quantity_donated INT NOT NULL DEFAULT 0,
    quantity_surplus INT GENERATED ALWAYS AS (
        GREATEST(0, quantity_prepared - quantity_sold - quantity_wasted - quantity_donated)
    ) STORED,
    remaining_prepared_stock INT GENERATED ALWAYS AS (
        GREATEST(0, quantity_prepared - quantity_sold - quantity_wasted - quantity_donated)
    ) STORED,
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE KEY uq_prep_date_item (prep_date, item_id),
    INDEX idx_prep_date (prep_date),
    CONSTRAINT chk_prep_non_negative CHECK (
        quantity_prepared >= 0
        AND quantity_sold >= 0
        AND quantity_wasted >= 0
        AND quantity_donated >= 0
    ),
    CONSTRAINT fk_prep_menu_item
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 7: daily_sales
-- Item-wise daily sales history (supports safe CSV import without duplicates)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_date DATE NOT NULL,
    item_id INT NOT NULL,
    day_type VARCHAR(30) NOT NULL DEFAULT 'weekday',
    customer_count INT NOT NULL DEFAULT 0,
    weather_condition VARCHAR(30) NOT NULL DEFAULT 'Sunny',
    quantity_sold INT NOT NULL DEFAULT 0,
    revenue DECIMAL(10,2) NULL,
    data_source VARCHAR(40) NOT NULL DEFAULT 'historical_csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_daily_sales_date_item (sale_date, item_id),
    INDEX idx_daily_sales_date (sale_date),
    INDEX idx_daily_sales_item (item_id),
    CONSTRAINT fk_daily_sales_item
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 8: demand_forecasts
-- Stores item-wise AI demand forecasts & recommended preparation qty
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS demand_forecasts (
    forecast_id INT AUTO_INCREMENT PRIMARY KEY,
    forecast_date DATE NOT NULL,
    item_id INT NOT NULL,
    day_type VARCHAR(30) NOT NULL DEFAULT 'weekday',
    expected_customers INT NOT NULL DEFAULT 0,
    weather_condition VARCHAR(30) NOT NULL DEFAULT 'Sunny',
    predicted_demand INT NOT NULL,
    safety_buffer_pct DECIMAL(5,2) NOT NULL DEFAULT 12.00,
    recommended_prep_qty INT NOT NULL,
    model_version VARCHAR(60) NOT NULL DEFAULT 'AI_MODEL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_forecast_date_item (forecast_date, item_id),
    INDEX idx_forecast_date (forecast_date),
    CONSTRAINT fk_forecast_menu_item
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 9: food_waste_logs
-- Tracks food waste causes, quantities, cost loss, disposal & item links
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS food_waste_logs (
    waste_id INT AUTO_INCREMENT PRIMARY KEY,
    log_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    item_type ENUM('Prepared Food', 'Raw Ingredient') NOT NULL,
    item_id INT NULL,
    ingredient_id INT NULL,
    item_name VARCHAR(100) NOT NULL,
    quantity_wasted DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    waste_reason ENUM(
        'Expired / Spoiled',
        'Overproduction / Unsold',
        'Kitchen Error / Burnt',
        'Plate Waste (Leftover by customer)',
        'Storage Malfunction',
        'Handling / Dropped'
    ) NOT NULL,
    cost_loss DECIMAL(10,2) NOT NULL,
    recorded_by VARCHAR(50) DEFAULT 'Kitchen Supervisor',
    disposal_method ENUM('Landfill', 'Composted', 'Animal Feed', 'Donation') DEFAULT 'Landfill',
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_waste_log_date (log_date),
    CONSTRAINT fk_waste_menu_item
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_waste_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES inventory_ingredients(ingredient_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- TABLE 10: food_donations
-- Tracks surplus food diverted to charities/shelters instead of landfill
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS food_donations (
    donation_id INT AUTO_INCREMENT PRIMARY KEY,
    donation_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recipient_organization VARCHAR(100) NOT NULL,
    item_id INT NULL,
    food_description VARCHAR(150) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    driver_or_contact VARCHAR(50),
    donation_status ENUM('Scheduled', 'Picked Up', 'Delivered') DEFAULT 'Delivered',
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_donation_date (donation_date),
    CONSTRAINT fk_donation_menu_item
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- STEP 2: SAFE MASTER DATA SEEDING (Never overwrites existing fixed IDs)
-- =====================================================================

-- Insert default menu items ONLY if neither item_id nor item_name already exists
INSERT INTO menu_items (item_id, item_name, category, price, cost_price, shelf_life_days, is_available)
SELECT src.item_id, src.item_name, src.category, src.price, src.cost_price, src.shelf_life_days, src.is_available
FROM (
    SELECT 1 AS item_id, 'Masala Dosa' AS item_name, 'Breakfast / Tiffin' AS category, 60.00 AS price, 20.00 AS cost_price, 1 AS shelf_life_days, TRUE AS is_available
    UNION ALL SELECT 2, 'Idli', 'Breakfast / Tiffin', 40.00, 12.00, 1, TRUE
    UNION ALL SELECT 3, 'Poori', 'Breakfast / Tiffin', 50.00, 15.00, 1, TRUE
    UNION ALL SELECT 4, 'Veg Meals', 'Lunch', 120.00, 45.00, 1, TRUE
    UNION ALL SELECT 5, 'Paneer Rice', 'Lunch / Dinner', 130.00, 50.00, 1, TRUE
    UNION ALL SELECT 6, 'Samosa', 'Snacks', 25.00, 8.00, 1, TRUE
    UNION ALL SELECT 7, 'Veg Sandwich', 'Snacks', 60.00, 20.00, 1, TRUE
    UNION ALL SELECT 8, 'Coffee', 'Beverages', 25.00, 8.00, 1, TRUE
    UNION ALL SELECT 9, 'Tea', 'Beverages', 20.00, 6.00, 1, TRUE
    UNION ALL SELECT 10, 'Chapati and Curry', 'Dinner', 70.00, 25.00, 1, TRUE
) AS src
WHERE NOT EXISTS (
    SELECT 1 FROM menu_items m
    WHERE m.item_id = src.item_id OR m.item_name = src.item_name
);

-- Insert default raw ingredients ONLY if neither ingredient_id nor ingredient_name exists
INSERT INTO inventory_ingredients (ingredient_id, ingredient_name, category, quantity_in_stock, unit, cost_per_unit, reorder_level, expiry_date, storage_location)
SELECT src.ingredient_id, src.ingredient_name, src.category, src.quantity_in_stock, src.unit, src.cost_per_unit, src.reorder_level, src.expiry_date, src.storage_location
FROM (
    SELECT 1 AS ingredient_id, 'Rice & Urad Dal Batter' AS ingredient_name, 'Prepared Batter' AS category, 25.0 AS quantity_in_stock, 'kg' AS unit, 35.00 AS cost_per_unit, 8.0 AS reorder_level, '2026-11-26' AS expiry_date, 'Refrigerator' AS storage_location
    UNION ALL SELECT 2, 'Potatoes', 'Produce', 40.0, 'kg', 25.00, 10.0, '2026-12-10', 'Dry Pantry'
    UNION ALL SELECT 3, 'Wheat Flour (Atta)', 'Dry Goods', 50.0, 'kg', 38.00, 15.0, '2027-02-15', 'Dry Storage'
    UNION ALL SELECT 4, 'Fresh Paneer', 'Dairy', 12.0, 'kg', 280.00, 4.0, '2026-11-27', 'Cold Storage'
    UNION ALL SELECT 5, 'Basmati Rice', 'Dry Goods', 60.0, 'kg', 75.00, 20.0, '2027-05-01', 'Dry Storage'
    UNION ALL SELECT 6, 'Bread Slices', 'Bakery', 15.0, 'packets', 40.00, 5.0, '2026-11-26', 'Pantry'
    UNION ALL SELECT 7, 'Fresh Milk', 'Dairy', 30.0, 'liters', 55.00, 10.0, '2026-11-25', 'Refrigerator'
    UNION ALL SELECT 8, 'Coffee Powder & Tea Leaves', 'Dry Goods', 10.0, 'kg', 400.00, 3.0, '2027-04-10', 'Pantry Shelf'
    UNION ALL SELECT 9, 'Cooking Oil', 'Dry Goods', 40.0, 'liters', 130.00, 12.0, '2027-06-30', 'Storage Room'
    UNION ALL SELECT 10, 'Mixed Vegetables (Carrot, Beans, Peas)', 'Produce', 25.0, 'kg', 45.00, 8.0, '2026-11-26', 'Cold Storage'
) AS src
WHERE NOT EXISTS (
    SELECT 1 FROM inventory_ingredients i
    WHERE i.ingredient_id = src.ingredient_id OR i.ingredient_name = src.ingredient_name
);

-- Insert recipes ONLY when both item_id+item_name and ingredient_id+ingredient_name match
INSERT IGNORE INTO menu_item_ingredients (item_id, ingredient_id, quantity_required)
SELECT m.item_id, i.ingredient_id, r.qty
FROM (
    SELECT 'Masala Dosa' AS item_name, 'Rice & Urad Dal Batter' AS ingr_name, 0.20 AS qty
    UNION ALL SELECT 'Masala Dosa', 'Potatoes', 0.10
    UNION ALL SELECT 'Idli', 'Rice & Urad Dal Batter', 0.25
    UNION ALL SELECT 'Poori', 'Wheat Flour (Atta)', 0.15
    UNION ALL SELECT 'Poori', 'Potatoes', 0.10
    UNION ALL SELECT 'Veg Meals', 'Basmati Rice', 0.25
    UNION ALL SELECT 'Veg Meals', 'Mixed Vegetables (Carrot, Beans, Peas)', 0.20
    UNION ALL SELECT 'Paneer Rice', 'Fresh Paneer', 0.15
    UNION ALL SELECT 'Paneer Rice', 'Basmati Rice', 0.20
    UNION ALL SELECT 'Samosa', 'Potatoes', 0.12
    UNION ALL SELECT 'Veg Sandwich', 'Bread Slices', 0.20
    UNION ALL SELECT 'Veg Sandwich', 'Mixed Vegetables (Carrot, Beans, Peas)', 0.10
    UNION ALL SELECT 'Coffee', 'Fresh Milk', 0.15
    UNION ALL SELECT 'Tea', 'Fresh Milk', 0.15
    UNION ALL SELECT 'Chapati and Curry', 'Wheat Flour (Atta)', 0.18
    UNION ALL SELECT 'Chapati and Curry', 'Mixed Vegetables (Carrot, Beans, Peas)', 0.15
) AS r
JOIN menu_items m ON m.item_name = r.item_name
JOIN inventory_ingredients i ON i.ingredient_name = r.ingr_name;

-- =====================================================================
-- STEP 3: SAMPLE / DEMO DATA ONLY (Fictional sample restaurant & NGOs)
-- All sample rows are flagged with is_demo = TRUE so real data stays separate.
-- Demo sample records are inserted ONLY when the target tables are empty.
-- =====================================================================

-- Demo Orders (Dine-In and Takeaway only; totals match order_items sums)
INSERT INTO orders (order_id, order_date, table_number, order_type, total_amount, order_status, is_demo)
SELECT src.order_id, src.order_date, src.table_number, src.order_type, src.total_amount, src.order_status, TRUE
FROM (
    SELECT 1 AS order_id, '2026-11-24 08:30:00' AS order_date, 3 AS table_number, 'Dine-In' AS order_type, 125.00 AS total_amount, 'Completed' AS order_status
    UNION ALL SELECT 2, '2026-11-24 09:15:00', 5, 'Dine-In', 75.00, 'Completed'
    UNION ALL SELECT 3, '2026-11-24 13:00:00', 2, 'Dine-In', 240.00, 'Completed'
    UNION ALL SELECT 4, '2026-11-24 17:30:00', NULL, 'Takeaway', 70.00, 'Completed'
) AS src
WHERE (SELECT COUNT(*) FROM orders) = 0
  AND EXISTS (SELECT 1 FROM menu_items WHERE item_id = 1 AND item_name = 'Masala Dosa')
  AND EXISTS (SELECT 1 FROM menu_items WHERE item_id = 2 AND item_name = 'Idli')
  AND EXISTS (SELECT 1 FROM menu_items WHERE item_id = 3 AND item_name = 'Poori')
  AND EXISTS (SELECT 1 FROM menu_items WHERE item_id = 4 AND item_name = 'Veg Meals')
  AND EXISTS (SELECT 1 FROM menu_items WHERE item_id = 6 AND item_name = 'Samosa')
  AND EXISTS (SELECT 1 FROM menu_items WHERE item_id = 8 AND item_name = 'Coffee')
  AND EXISTS (SELECT 1 FROM menu_items WHERE item_id = 9 AND item_name = 'Tea');

INSERT INTO order_items (order_item_id, order_id, item_id, quantity, subtotal)
SELECT src.order_item_id, src.order_id, src.item_id, src.quantity, src.subtotal
FROM (
    SELECT 1 AS order_item_id, 1 AS order_id, 1 AS item_id, 1 AS quantity, 60.00 AS subtotal
    UNION ALL SELECT 2, 1, 2, 1, 40.00
    UNION ALL SELECT 3, 1, 8, 1, 25.00
    UNION ALL SELECT 4, 2, 3, 1, 50.00
    UNION ALL SELECT 5, 2, 8, 1, 25.00
    UNION ALL SELECT 6, 3, 4, 2, 240.00
    UNION ALL SELECT 7, 4, 6, 2, 50.00
    UNION ALL SELECT 8, 4, 9, 1, 20.00
) AS src
WHERE (SELECT COUNT(*) FROM order_items) = 0
  AND EXISTS (SELECT 1 FROM orders o WHERE o.order_id = src.order_id AND o.is_demo = TRUE);

-- Demo Daily Food Prep (matches demo waste & donation quantities)
INSERT INTO daily_food_prep (prep_date, item_id, quantity_prepared, quantity_sold, quantity_wasted, quantity_donated, is_demo)
SELECT src.prep_date, m.item_id, src.quantity_prepared, src.quantity_sold, src.quantity_wasted, src.quantity_donated, TRUE
FROM (
    SELECT '2026-11-23' AS prep_date, 'Idli' AS item_name, 50 AS quantity_prepared, 42 AS quantity_sold, 0 AS quantity_wasted, 8 AS quantity_donated
    UNION ALL SELECT '2026-11-23', 'Veg Meals', 40, 31, 6, 0
    UNION ALL SELECT '2026-11-23', 'Samosa', 60, 48, 8, 4
    UNION ALL SELECT '2026-11-24', 'Masala Dosa', 45, 43, 2, 0
    UNION ALL SELECT '2026-11-24', 'Veg Meals', 35, 30, 0, 0
    UNION ALL SELECT '2026-11-24', 'Chapati and Curry', 40, 34, 5, 0
) AS src
JOIN menu_items m ON m.item_name = src.item_name
WHERE (SELECT COUNT(*) FROM daily_food_prep) = 0;

-- Demo Food Waste Logs (fictional demo staff labels; linked to item_id/ingredient_id)
INSERT INTO food_waste_logs (log_date, item_type, item_id, ingredient_id, item_name, quantity_wasted, unit, waste_reason, cost_loss, recorded_by, disposal_method, is_demo)
SELECT src.log_date, src.item_type, m.item_id, i.ingredient_id, src.item_name, src.quantity_wasted, src.unit, src.waste_reason, src.cost_loss, src.recorded_by, src.disposal_method, TRUE
FROM (
    SELECT '2026-11-23 15:30:00' AS log_date, 'Prepared Food' AS item_type, 'Veg Meals' AS ref_menu, NULL AS ref_ingr, 'Veg Meals' AS item_name, 6.0 AS quantity_wasted, 'portions' AS unit, 'Overproduction / Unsold' AS waste_reason, 270.00 AS cost_loss, 'Demo Staff - Kitchen Lead' AS recorded_by, 'Composted' AS disposal_method
    UNION ALL SELECT '2026-11-23 18:00:00', 'Prepared Food', 'Samosa', NULL, 'Samosa', 8.0, 'pieces', 'Overproduction / Unsold', 64.00, 'Demo Staff - Line Cook', 'Animal Feed'
    UNION ALL SELECT '2026-11-23 20:30:00', 'Prepared Food', 'Masala Dosa', NULL, 'Masala Dosa', 3.0, 'plates', 'Kitchen Error / Burnt', 60.00, 'Demo Staff - Tiffin Cook', 'Landfill'
    UNION ALL SELECT '2026-11-24 14:15:00', 'Prepared Food', 'Veg Meals', NULL, 'Veg Meals (Leftover Rice)', 2.5, 'kg', 'Plate Waste (Leftover by customer)', 90.00, 'Demo Staff - Busser', 'Composted'
    UNION ALL SELECT '2026-11-24 16:00:00', 'Raw Ingredient', NULL, 'Fresh Milk', 'Fresh Milk', 3.0, 'liters', 'Expired / Spoiled', 165.00, 'Demo Staff - Storekeeper', 'Landfill'
    UNION ALL SELECT '2026-11-24 21:30:00', 'Prepared Food', 'Chapati and Curry', NULL, 'Chapati and Curry', 5.0, 'portions', 'Overproduction / Unsold', 125.00, 'Demo Staff - Kitchen Lead', 'Donation'
) AS src
LEFT JOIN menu_items m ON m.item_name = src.ref_menu
LEFT JOIN inventory_ingredients i ON i.ingredient_name = src.ref_ingr
WHERE (SELECT COUNT(*) FROM food_waste_logs) = 0;

-- Demo Food Donations (fictional sample NGO names clearly marked as demo)
INSERT INTO food_donations (donation_date, recipient_organization, item_id, food_description, quantity, unit, driver_or_contact, donation_status, is_demo)
SELECT src.donation_date, src.recipient_organization, m.item_id, src.food_description, src.quantity, src.unit, src.driver_or_contact, src.donation_status, TRUE
FROM (
    SELECT '2026-11-23 22:30:00' AS donation_date, 'Sample NGO Partner A (Demo Only)' AS recipient_organization, 'Chapati and Curry' AS ref_menu, '[DEMO] Surplus Chapatis and Vegetable Curry' AS food_description, 15.0 AS quantity, 'packets' AS unit, 'Demo Volunteer Contact' AS driver_or_contact, 'Delivered' AS donation_status
    UNION ALL SELECT '2026-11-24 22:00:00', 'Sample Care Home B (Demo Only)', 'Idli', '[DEMO] Freshly packed Idlis and Samosas', 20.0, 'portions', 'Demo Coordinator Contact', 'Delivered'
) AS src
LEFT JOIN menu_items m ON m.item_name = src.ref_menu
WHERE (SELECT COUNT(*) FROM food_donations) = 0;

-- =====================================================================
-- STEP 4: ANALYTICAL VIEWS FOR FOOD WASTE REDUCTION
-- =====================================================================

CREATE OR REPLACE VIEW vw_waste_by_reason AS
SELECT
    waste_reason,
    COUNT(waste_id) AS total_incidents,
    SUM(cost_loss) AS total_financial_loss,
    ROUND(SUM(cost_loss) * 100.0 / NULLIF((SELECT SUM(cost_loss) FROM food_waste_logs), 0), 2) AS percentage_of_total_loss
FROM food_waste_logs
GROUP BY waste_reason
ORDER BY total_financial_loss DESC;

CREATE OR REPLACE VIEW vw_overproduction_analysis AS
SELECT
    p.prep_date,
    m.item_name,
    m.category,
    p.quantity_prepared,
    p.quantity_sold,
    p.quantity_wasted,
    p.quantity_donated,
    p.quantity_surplus,
    p.remaining_prepared_stock,
    ROUND((p.quantity_surplus / NULLIF(p.quantity_prepared, 0)) * 100, 1) AS waste_risk_percentage
FROM daily_food_prep p
JOIN menu_items m ON p.item_id = m.item_id
WHERE p.quantity_surplus > 0
ORDER BY p.prep_date DESC, p.remaining_prepared_stock DESC;

CREATE OR REPLACE VIEW vw_expiring_soon_alert AS
SELECT
    ingredient_id,
    ingredient_name,
    category,
    quantity_in_stock,
    unit,
    expiry_date,
    DATEDIFF(expiry_date, CURDATE()) AS days_until_expiry,
    storage_location
FROM inventory_ingredients
WHERE expiry_date <= DATE_ADD(CURDATE(), INTERVAL 5 DAY)
ORDER BY days_until_expiry ASC;

CREATE OR REPLACE VIEW vw_environmental_impact AS
SELECT
    disposal_method,
    COUNT(*) AS incident_count,
    SUM(quantity_wasted) AS total_quantity,
    SUM(cost_loss) AS total_cost_value
FROM food_waste_logs
GROUP BY disposal_method;

-- =====================================================================
-- STEP 5: NON-DESTRUCTIVE MASTER DATA CONFLICT CHECK (Read-Only)
-- Alerts you if fixed IDs 1..10 already existed with different names
-- =====================================================================
SELECT
    e.expected_id,
    e.expected_name,
    m.item_name AS actual_name_in_db
FROM (
    SELECT 1 AS expected_id, 'Masala Dosa' AS expected_name
    UNION ALL SELECT 2, 'Idli'
    UNION ALL SELECT 3, 'Poori'
    UNION ALL SELECT 4, 'Veg Meals'
    UNION ALL SELECT 5, 'Paneer Rice'
    UNION ALL SELECT 6, 'Samosa'
    UNION ALL SELECT 7, 'Veg Sandwich'
    UNION ALL SELECT 8, 'Coffee'
    UNION ALL SELECT 9, 'Tea'
    UNION ALL SELECT 10, 'Chapati and Curry'
) AS e
JOIN menu_items m ON m.item_id = e.expected_id
WHERE m.item_name <> e.expected_name;
