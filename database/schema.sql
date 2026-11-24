-- =========================================================================
-- SMART RESTAURANT DEMAND FORECASTING & REAL-TIME FOOD WASTE MANAGEMENT SYSTEM
-- Production MySQL DDL Schema Definition & Analytical Views
-- Compatible with MySQL 8.0+ / MariaDB 10.5+ / SQLite
-- Menu: Customized for the 10 Indian Menu Items & Food Waste Tracking
-- =========================================================================

CREATE DATABASE IF NOT EXISTS restaurant_demand_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE restaurant_demand_db;

-- Step 1: Clean restart - drop tables in reverse foreign key order
DROP VIEW IF EXISTS vw_environmental_impact;
DROP VIEW IF EXISTS vw_expiring_soon_alert;
DROP VIEW IF EXISTS vw_overproduction_analysis;
DROP VIEW IF EXISTS vw_waste_by_reason;

DROP TABLE IF EXISTS food_donations;
DROP TABLE IF EXISTS food_waste_logs;
DROP TABLE IF EXISTS daily_food_prep;
DROP TABLE IF EXISTS menu_item_ingredients;
DROP TABLE IF EXISTS inventory_ingredients;
DROP TABLE IF EXISTS inventory_logs;
DROP TABLE IF EXISTS live_orders;
DROP TABLE IF EXISTS surplus_redistribution;
DROP TABLE IF EXISTS inventory_stock;
DROP TABLE IF EXISTS historical_sales_data;
DROP TABLE IF EXISTS product_menu;
DROP TABLE IF EXISTS users;

-- -------------------------------------------------------------------------
-- 1. Table: users
-- Role-based authentication (admin, restaurant_manager, inventory_staff, customer)
-- -------------------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'restaurant_manager', 'inventory_staff', 'customer') NOT NULL DEFAULT 'customer',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_role (role),
    INDEX idx_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 2. Table: product_menu
-- Master food & beverage items with cost, selling price, and shelf-life
-- -------------------------------------------------------------------------
CREATE TABLE product_menu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    standard_prep_cost DECIMAL(10, 2) NOT NULL,
    shelf_life_hours INT NOT NULL DEFAULT 24,
    description VARCHAR(255) NULL,
    image_url VARCHAR(500) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_category (category),
    INDEX idx_product_name (item_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 3. Table: inventory_ingredients
-- Raw ingredients, shelf-life, and expiry tracking to prevent raw spoilage
-- -------------------------------------------------------------------------
CREATE TABLE inventory_ingredients (
    ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
    ingredient_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    quantity_in_stock DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    cost_per_unit DECIMAL(10,2) NOT NULL,
    reorder_level DECIMAL(10,2) NOT NULL,
    expiry_date DATE NOT NULL,
    storage_location VARCHAR(50) DEFAULT 'Main Kitchen'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 4. Table: menu_item_ingredients (Recipe / Bill of Materials)
-- Maps each menu item to the exact raw ingredient quantities required
-- -------------------------------------------------------------------------
CREATE TABLE menu_item_ingredients (
    recipe_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    ingredient_id INT NOT NULL,
    quantity_required DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_recipe_item FOREIGN KEY (item_id)
        REFERENCES product_menu (id) ON DELETE CASCADE,
    CONSTRAINT fk_recipe_ingr FOREIGN KEY (ingredient_id)
        REFERENCES inventory_ingredients (ingredient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 5. Table: historical_sales_data
-- Time-series dataset for training ML demand forecasting models
-- -------------------------------------------------------------------------
CREATE TABLE historical_sales_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    item_id INT NOT NULL,
    day_type ENUM('weekday', 'weekend', 'festival', 'office_party', 'birthday_celebration') NOT NULL,
    customer_count INT NOT NULL,
    actual_qty_ordered INT NOT NULL,
    weather_condition ENUM('Sunny', 'Rainy', 'Cloudy', 'Stormy', 'Cold') NOT NULL DEFAULT 'Sunny',
    INDEX idx_hist_date (date),
    INDEX idx_hist_item_id (item_id),
    INDEX idx_hist_day_type (day_type),
    CONSTRAINT fk_hist_item FOREIGN KEY (item_id)
        REFERENCES product_menu (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 6. Table: inventory_stock
-- Current physical stock on hand and dynamic safety replenishment thresholds
-- -------------------------------------------------------------------------
CREATE TABLE inventory_stock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL UNIQUE,
    current_stock_qty INT NOT NULL DEFAULT 0,
    min_threshold_qty INT NOT NULL DEFAULT 10,
    last_restocked_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_inv_item (item_id),
    CONSTRAINT fk_inv_item FOREIGN KEY (item_id)
        REFERENCES product_menu (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 7. Table: live_orders
-- Real-time order capture with instant inventory deduction
-- -------------------------------------------------------------------------
CREATE TABLE live_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NULL,
    customer_name VARCHAR(100) NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    status ENUM('pending', 'preparing', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
    order_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_price DECIMAL(10, 2) NULL,
    INDEX idx_order_status (status),
    INDEX idx_order_time (order_time),
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id)
        REFERENCES users (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_order_item FOREIGN KEY (item_id)
        REFERENCES product_menu (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 8. Table: surplus_redistribution
-- Food waste minimization portal coordinating unsold surplus with local NGOs
-- -------------------------------------------------------------------------
CREATE TABLE surplus_redistribution (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    surplus_qty INT NOT NULL,
    status ENUM('available_for_ngo', 'claimed') NOT NULL DEFAULT 'available_for_ngo',
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    claimed_by_ngo VARCHAR(120) NULL,
    claimed_at DATETIME NULL,
    contact_phone VARCHAR(40) NULL,
    pickup_eta VARCHAR(60) NULL,
    notes VARCHAR(255) NULL,
    INDEX idx_surplus_status (status),
    INDEX idx_surplus_logged (logged_at),
    CONSTRAINT fk_surplus_item FOREIGN KEY (item_id)
        REFERENCES product_menu (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 9. Table: inventory_logs
-- Atomic transaction audit ledger tracking all inventory changes & stock safety
-- -------------------------------------------------------------------------
CREATE TABLE inventory_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    change_qty INT NOT NULL,
    previous_stock INT NOT NULL,
    new_stock INT NOT NULL,
    reason VARCHAR(60) NOT NULL,
    reference_id INT NULL,
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INT NULL,
    INDEX idx_log_item (item_id),
    INDEX idx_log_reason (reason),
    INDEX idx_log_time (logged_at),
    CONSTRAINT fk_log_item FOREIGN KEY (item_id)
        REFERENCES product_menu (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_log_user FOREIGN KEY (created_by_user_id)
        REFERENCES users (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 10. Table: daily_food_prep
-- Tracks batch cooking vs. actual sales to detect overproduction
-- -------------------------------------------------------------------------
CREATE TABLE daily_food_prep (
    prep_id INT AUTO_INCREMENT PRIMARY KEY,
    prep_date DATE NOT NULL,
    item_id INT NOT NULL,
    quantity_prepared INT NOT NULL,
    quantity_sold INT DEFAULT 0,
    CONSTRAINT fk_prep_item FOREIGN KEY (item_id)
        REFERENCES product_menu (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 11. Table: food_waste_logs
-- Core tracking table for food waste causes, volumes, and cost losses
-- -------------------------------------------------------------------------
CREATE TABLE food_waste_logs (
    waste_id INT AUTO_INCREMENT PRIMARY KEY,
    log_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    item_type ENUM('Prepared Food', 'Raw Ingredient') NOT NULL,
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
    disposal_method ENUM('Landfill', 'Composted', 'Animal Feed', 'Donation') DEFAULT 'Landfill'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 12. Table: food_donations
-- Tracks surplus food diverted to food banks/charities instead of landfill
-- -------------------------------------------------------------------------
CREATE TABLE food_donations (
    donation_id INT AUTO_INCREMENT PRIMARY KEY,
    donation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    recipient_organization VARCHAR(100) NOT NULL,
    food_description VARCHAR(150) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    driver_or_contact VARCHAR(50),
    donation_status ENUM('Scheduled', 'Picked Up', 'Delivered') DEFAULT 'Delivered'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- ANALYTICAL VIEWS FOR FOOD WASTE REDUCTION
-- -------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_waste_by_reason AS
SELECT 
    waste_reason,
    COUNT(waste_id) AS total_incidents,
    SUM(cost_loss) AS total_financial_loss,
    ROUND(SUM(cost_loss) * 100.0 / (SELECT SUM(cost_loss) FROM food_waste_logs), 2) AS percentage_of_total_loss
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
    (p.quantity_prepared - p.quantity_sold) AS quantity_surplus,
    ROUND(((p.quantity_prepared - p.quantity_sold) * 1.0 / p.quantity_prepared) * 100, 1) AS waste_risk_percentage
FROM daily_food_prep p
JOIN product_menu m ON p.item_id = m.id
WHERE (p.quantity_prepared - p.quantity_sold) > 0
ORDER BY p.prep_date DESC, quantity_surplus DESC;

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
