-- =====================================================================
-- SAFE NON-DESTRUCTIVE MIGRATION SCRIPT FOR EXISTING MySQL DATABASES
-- Target Database: restaurant_management
-- Safety Guarantees:
--   * No DROP TABLE or DROP DATABASE statements
--   * No data deletion or silent overwriting of existing rows
--   * Uses INFORMATION_SCHEMA checks before running ALTER TABLE
--   * Tested for MySQL 8.0+ compatibility (MySQL Workbench Execute All)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS restaurant_management
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE restaurant_management;

-- ---------------------------------------------------------------------
-- PART 1: CREATE MISSING TABLES SAFELY (daily_sales & demand_forecasts)
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
-- PART 2: SAFE GUARDED ALTER TABLE MIGRATIONS FOR EXISTING TABLES
-- Note: MySQL 8.0 does not support "ALTER TABLE ... ADD COLUMN IF NOT EXISTS",
-- so temporary helper procedures check INFORMATION_SCHEMA safely first.
-- ---------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_mig_add_col_if_missing;
DROP PROCEDURE IF EXISTS sp_mig_add_fk_if_missing;
DROP PROCEDURE IF EXISTS sp_mig_run_safe_upgrades;

DELIMITER $$

CREATE PROCEDURE sp_mig_add_col_if_missing(
    IN p_table VARCHAR(64),
    IN p_col VARCHAR(64),
    IN p_alter_sql TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND COLUMN_NAME = p_col
    ) THEN
        SET @mig_sql = p_alter_sql;
        PREPARE stmt FROM @mig_sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

CREATE PROCEDURE sp_mig_add_fk_if_missing(
    IN p_table VARCHAR(64),
    IN p_constraint VARCHAR(64),
    IN p_alter_sql TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND CONSTRAINT_NAME = p_constraint
    ) THEN
        SET @mig_sql = p_alter_sql;
        PREPARE stmt FROM @mig_sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

CREATE PROCEDURE sp_mig_run_safe_upgrades()
BEGIN
    DECLARE v_invalid_order_types INT DEFAULT 0;
    DECLARE v_dup_prep_count INT DEFAULT 0;
    DECLARE v_neg_prep_count INT DEFAULT 0;
    DECLARE v_surplus_expr TEXT DEFAULT '';

    -- 1. orders: Add is_demo column if missing
    CALL sp_mig_add_col_if_missing(
        'orders',
        'is_demo',
        'ALTER TABLE orders ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE'
    );

    -- 1b. orders: Restrict order_type to Dine-In and Takeaway ONLY if no conflicting rows exist
    SELECT COUNT(*) INTO v_invalid_order_types
    FROM orders
    WHERE order_type IS NULL OR order_type NOT IN ('Dine-In', 'Takeaway');

    IF v_invalid_order_types = 0 THEN
        IF EXISTS (
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'orders'
              AND COLUMN_NAME = 'order_type'
              AND COLUMN_TYPE <> "enum('Dine-In','Takeaway')"
        ) THEN
            ALTER TABLE orders
                MODIFY COLUMN order_type ENUM('Dine-In', 'Takeaway') NOT NULL DEFAULT 'Dine-In';
        END IF;
    ELSE
        SELECT CONCAT(
            'WARNING: orders table has ', v_invalid_order_types,
            ' row(s) with order_type outside (Dine-In, Takeaway). Skipped ENUM conversion so no data is lost.'
        ) AS migration_notice;
    END IF;

    -- 2. daily_food_prep: Add quantity_wasted, quantity_donated, is_demo
    CALL sp_mig_add_col_if_missing(
        'daily_food_prep',
        'quantity_wasted',
        'ALTER TABLE daily_food_prep ADD COLUMN quantity_wasted INT NOT NULL DEFAULT 0 AFTER quantity_sold'
    );

    CALL sp_mig_add_col_if_missing(
        'daily_food_prep',
        'quantity_donated',
        'ALTER TABLE daily_food_prep ADD COLUMN quantity_donated INT NOT NULL DEFAULT 0 AFTER quantity_wasted'
    );

    CALL sp_mig_add_col_if_missing(
        'daily_food_prep',
        'is_demo',
        'ALTER TABLE daily_food_prep ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE'
    );

    -- 2b. daily_food_prep: Update quantity_surplus so it excludes wasted & donated and clamps at 0
    IF NOT EXISTS (
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'daily_food_prep'
          AND COLUMN_NAME = 'quantity_surplus'
    ) THEN
        ALTER TABLE daily_food_prep
            ADD COLUMN quantity_surplus INT GENERATED ALWAYS AS (
                GREATEST(0, quantity_prepared - quantity_sold - quantity_wasted - quantity_donated)
            ) STORED AFTER quantity_donated;
    ELSE
        SELECT COALESCE(GENERATION_EXPRESSION, '') INTO v_surplus_expr
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'daily_food_prep'
          AND COLUMN_NAME = 'quantity_surplus';

        IF v_surplus_expr NOT LIKE '%quantity_wasted%' OR v_surplus_expr NOT LIKE '%quantity_donated%' THEN
            ALTER TABLE daily_food_prep
                MODIFY COLUMN quantity_surplus INT GENERATED ALWAYS AS (
                    GREATEST(0, quantity_prepared - quantity_sold - quantity_wasted - quantity_donated)
                ) STORED;
        END IF;
    END IF;

    -- 2c. daily_food_prep: Add remaining_prepared_stock generated column if missing
    CALL sp_mig_add_col_if_missing(
        'daily_food_prep',
        'remaining_prepared_stock',
        'ALTER TABLE daily_food_prep ADD COLUMN remaining_prepared_stock INT GENERATED ALWAYS AS (GREATEST(0, quantity_prepared - quantity_sold - quantity_wasted - quantity_donated)) STORED AFTER quantity_surplus'
    );

    -- 2d. daily_food_prep: Add non-negative CHECK constraint if existing rows are valid
    SELECT COUNT(*) INTO v_neg_prep_count
    FROM daily_food_prep
    WHERE quantity_prepared < 0 OR quantity_sold < 0 OR quantity_wasted < 0 OR quantity_donated < 0;

    IF v_neg_prep_count = 0 THEN
        CALL sp_mig_add_fk_if_missing(
            'daily_food_prep',
            'chk_prep_non_negative',
            'ALTER TABLE daily_food_prep ADD CONSTRAINT chk_prep_non_negative CHECK (quantity_prepared >= 0 AND quantity_sold >= 0 AND quantity_wasted >= 0 AND quantity_donated >= 0)'
        );
    ELSE
        SELECT CONCAT(
            'WARNING: daily_food_prep has ', v_neg_prep_count,
            ' negative row(s). Skipped chk_prep_non_negative.'
        ) AS migration_notice;
    END IF;

    -- 2e. daily_food_prep: Add UNIQUE (prep_date, item_id) only if no duplicates exist
    IF NOT EXISTS (
        SELECT 1
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'daily_food_prep'
          AND INDEX_NAME = 'uq_prep_date_item'
    ) THEN
        SELECT COUNT(*) INTO v_dup_prep_count
        FROM (
            SELECT prep_date, item_id
            FROM daily_food_prep
            GROUP BY prep_date, item_id
            HAVING COUNT(*) > 1
        ) AS dups;

        IF v_dup_prep_count = 0 THEN
            ALTER TABLE daily_food_prep
                ADD UNIQUE KEY uq_prep_date_item (prep_date, item_id);
        ELSE
            SELECT CONCAT(
                'WARNING: daily_food_prep has ', v_dup_prep_count,
                ' duplicate (prep_date, item_id) pair(s). Review duplicates before adding uq_prep_date_item.'
            ) AS migration_notice;
        END IF;
    END IF;

    -- 3. food_waste_logs: Add optional item_id, ingredient_id, is_demo and foreign keys
    CALL sp_mig_add_col_if_missing(
        'food_waste_logs',
        'item_id',
        'ALTER TABLE food_waste_logs ADD COLUMN item_id INT NULL AFTER item_type'
    );

    CALL sp_mig_add_col_if_missing(
        'food_waste_logs',
        'ingredient_id',
        'ALTER TABLE food_waste_logs ADD COLUMN ingredient_id INT NULL AFTER item_id'
    );

    CALL sp_mig_add_col_if_missing(
        'food_waste_logs',
        'is_demo',
        'ALTER TABLE food_waste_logs ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE'
    );

    CALL sp_mig_add_fk_if_missing(
        'food_waste_logs',
        'fk_waste_menu_item',
        'ALTER TABLE food_waste_logs ADD CONSTRAINT fk_waste_menu_item FOREIGN KEY (item_id) REFERENCES menu_items(item_id) ON DELETE SET NULL ON UPDATE CASCADE'
    );

    CALL sp_mig_add_fk_if_missing(
        'food_waste_logs',
        'fk_waste_ingredient',
        'ALTER TABLE food_waste_logs ADD CONSTRAINT fk_waste_ingredient FOREIGN KEY (ingredient_id) REFERENCES inventory_ingredients(ingredient_id) ON DELETE SET NULL ON UPDATE CASCADE'
    );

    -- 4. food_donations: Add optional item_id, is_demo and foreign key
    CALL sp_mig_add_col_if_missing(
        'food_donations',
        'item_id',
        'ALTER TABLE food_donations ADD COLUMN item_id INT NULL AFTER recipient_organization'
    );

    CALL sp_mig_add_col_if_missing(
        'food_donations',
        'is_demo',
        'ALTER TABLE food_donations ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE'
    );

    CALL sp_mig_add_fk_if_missing(
        'food_donations',
        'fk_donation_menu_item',
        'ALTER TABLE food_donations ADD CONSTRAINT fk_donation_menu_item FOREIGN KEY (item_id) REFERENCES menu_items(item_id) ON DELETE SET NULL ON UPDATE CASCADE'
    );
END$$

DELIMITER ;

CALL sp_mig_run_safe_upgrades();

-- Remove only temporary migration helper procedures
DROP PROCEDURE IF EXISTS sp_mig_run_safe_upgrades;
DROP PROCEDURE IF EXISTS sp_mig_add_fk_if_missing;
DROP PROCEDURE IF EXISTS sp_mig_add_col_if_missing;

-- ---------------------------------------------------------------------
-- PART 3: SAFE ANALYTICAL VIEW UPDATES
-- ---------------------------------------------------------------------

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
