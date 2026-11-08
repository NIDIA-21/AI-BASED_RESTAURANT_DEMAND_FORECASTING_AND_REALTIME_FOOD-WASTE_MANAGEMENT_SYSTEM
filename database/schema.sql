-- =========================================================================
-- SMART RESTAURANT DEMAND FORECASTING & REAL-TIME FOOD WASTE MANAGEMENT SYSTEM
-- Production MySQL DDL Schema Definition
-- Compatible with MySQL 8.0+ / MariaDB 10.5+
-- =========================================================================

CREATE DATABASE IF NOT EXISTS restaurant_demand_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE restaurant_demand_db;

-- -------------------------------------------------------------------------
-- 1. Table: users
-- Role-based authentication (admin, restaurant_manager, inventory_staff, customer)
-- -------------------------------------------------------------------------
DROP TABLE IF EXISTS inventory_logs;
DROP TABLE IF EXISTS live_orders;
DROP TABLE IF EXISTS surplus_redistribution;
DROP TABLE IF EXISTS inventory_stock;
DROP TABLE IF EXISTS historical_sales_data;
DROP TABLE IF EXISTS product_menu;
DROP TABLE IF EXISTS users;

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
    shelf_life_hours INT NOT NULL DEFAULT 12,
    description VARCHAR(255) NULL,
    image_url VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_category (category),
    INDEX idx_product_name (item_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 3. Table: historical_sales_data
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
-- 4. Table: inventory_stock
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
-- 5. Table: live_orders
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
-- 6. Table: surplus_redistribution
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
-- 7. Table: inventory_logs
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
