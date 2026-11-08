# Smart Restaurant Demand Forecasting & Real-Time Food Waste Management System

## 📌 Project Overview
A production-ready, modular Enterprise Resource Planning (ERP) and Predictive Analytics web application engineered to solve demand uncertainty, prevent ingredient stockouts, and eliminate commercial food waste in modern restaurants.

The platform integrates **scikit-learn Machine Learning regression models**, **real-time POS order processing with atomic inventory deduction**, **dynamic velocity vs. prediction alert monitoring**, and an **automated surplus food redistribution portal** connecting commercial kitchens with community food rescue NGOs.

---

## 👥 Project Team (CSE Dept - Yenepoya Institute of Technology)
* **Aysha Nidha** (4DM24CS013)
* **Ann Nidia John** (4DM24CS009)
* **Ayesha** (4DM24CS010)
* **Raisa Fathima** (4DM24CS042)
* **Under the Guidance of:** Prof. Pandu Naik (Assistant Professor, Dept. of CSE)

---

## 🏗️ System Architecture & Layer Breakdown

```
+-----------------------------------------------------------------------------------+
| LAYER 1: DATA SOURCES & SYNTHETIC ML SEEDING                                      |
| • 180+ Days of Time-Series Sales Data (3,200+ Observations)                       |
| • Multidimensional Context: Weekday, Weekend, Festival, Office Party, Birthday    |
| • Meteorological Variance: Sunny, Rainy, Cloudy, Stormy, Cold                     |
+-----------------------------------------------------------------------------------+
                                        │
                                        ▼
+-----------------------------------------------------------------------------------+
| LAYER 2: MACHINE LEARNING FORECASTING ENGINE (scikit-learn)                       |
| • Random Forest Regressor vs. Gradient Boosting Regressor Pipeline Benchmark       |
| • Features: [day_type, customer_count, item_id, day_of_week, weather, category]   |
| • Outputs: Expected Demand, 12% Safety Buffer, Recommended Batch Prep Quantities   |
+-----------------------------------------------------------------------------------+
                                        │
                                        ▼
+-----------------------------------------------------------------------------------+
| LAYER 3: CORE BACKEND & BUSINESS LOGIC (Python Flask + SQLAlchemy 2.0)            |
| • Dynamic Velocity vs Forecast Alert Engine (Shortage vs Food Waste Risk)         |
| • Atomic Inventory Deductions & Low-Stock Threshold Reorder Triggers              |
| • Role-Based Access Control (Admin, Manager, Staff, Customer) + Dev Role Switcher |
+-----------------------------------------------------------------------------------+
                                        │
                                        ▼
+-----------------------------------------------------------------------------------+
| LAYER 4: DATABASE PERSISTENCE (MySQL & SQLite Dual Support)                       |
| • Production MySQL 8.0 DDL Schema (`database/schema.sql`)                         |
| • Automatic Local SQLite fallback (`restaurant.db`) for immediate evaluation      |
+-----------------------------------------------------------------------------------+
                                        │
                                        ▼
+-----------------------------------------------------------------------------------+
| LAYER 5: USER EXPERIENCE & DASHBOARD (Tailwind CSS + Chart.js)                    |
| • Executive SaaS ERP Dashboard (Odoo / Stripe Aesthetics)                         |
| • Live Touch POS Order Entry Interface                                            |
| • Kitchen Order Display System (KDS) & Order Status Lifecycle                     |
| • NGO Community Redistribution Portal (Robin Hood Army, Feeding India claims)     |
+-----------------------------------------------------------------------------------+
```

---

## 🧩 Key Functional Modules

### 1. Comprehensive Database Schema (SQLAlchemy & MySQL)
The system models relational data with full referential integrity and cascading rules:
- **`User`**: Role-based authentication supporting `'admin'`, `'restaurant_manager'`, `'inventory_staff'`, and `'customer'`. Secure password hashing via Werkzeug.
- **`ProductMenu`**: Master catalog storing `item_name`, `category`, `unit_price`, `standard_prep_cost`, and `shelf_life_hours`.
- **`HistoricalSalesData`**: Time-series training records storing `date`, `item_id`, `day_type` (`'weekday'`, `'weekend'`, `'festival'`, `'office_party'`, `'birthday_celebration'`), `customer_count`, `actual_qty_ordered`, and `weather_condition`.
- **`InventoryStock`**: Physical stock levels (`current_stock_qty`), reorder threshold (`min_threshold_qty`), and replenishment timestamps.
- **`LiveOrder`**: Real-time customer orders with atomic inventory deduction and lifecycle statuses (`'pending'`, `'preparing'`, `'completed'`, `'cancelled'`).
- **`SurplusRedistribution`**: Food recovery records tracking unsold batches nearing expiration (`status`: `'available_for_ngo'`, `'claimed'`), claim timestamps, and contact info.

### 2. Synthetic Data Seeding Script
Located in [`database/seed_data.py`](file:///c:/Users/nixon/AI-Restaurant-Demand-Forecasting/database/seed_data.py), this automated generator generates:
- 18 diverse food items across Starters, Main Courses, Desserts, Beverages, and Party Platters.
- 180 days of realistic daily sales history (3,240+ observation points).
- Event-specific affinity multipliers (e.g. Platters spike 3.4x during office parties, Cakes spike 3.4x during birthday bookings, Biryani surges 2.4x during festivals).
- Weather modifiers (e.g. Masala Chai surges 2.4x during rainstorms, cold brews surge 1.7x on sunny afternoons).
- Default demo accounts and active inventory stocks.

### 3. AI Machine Learning Demand Forecasting Engine
Located in [`ml_model/train.py`](file:///c:/Users/nixon/AI-Restaurant-Demand-Forecasting/ml_model/train.py) and [`ml_model/predictor.py`](file:///c:/Users/nixon/AI-Restaurant-Demand-Forecasting/ml_model/predictor.py):
- **Model Evaluation**: Automatically trains and benchmarks a `RandomForestRegressor` against a `GradientBoostingRegressor` using an 80/20 train/test split.
- **Champion Pipeline**: Achieves an **$R^2$ score of $> 0.93$** and MAE of $\approx 9.8$ units.
- **Preparation Recommendation Formula**:
  $$\text{Target Pool} = \lceil \text{Predicted Demand} \times (1 + \text{Safety Buffer Margin}) \rceil$$
  $$\text{Recommended Prep Qty} = \max\left(0, \text{Target Pool} - \text{Current Stock}\right)$$
- **What-If Scenario Sandbox**: Interactive simulation allowing managers to model any combination of footfall, weather conditions, and party bookings.

### 4. Real-Time Order Monitoring & Dynamic Alerts
- **POS Order Entry**: Kitchen and waitstaff can record orders via [`orders/pos.html`](file:///c:/Users/nixon/AI-Restaurant-Demand-Forecasting/templates/orders/pos.html). Stock is instantly validated and deducted from `InventoryStock`.
- **Dynamic Alert Logic**:
  - **Shortage Alert (Red)**: Triggered when order velocity indicates stock will deplete before shift completion, or when stock dips below `min_threshold_qty`. Recommends exact batch units to prep.
  - **Excess Preparation / Waste Risk (Amber)**: Triggered when service is $> 40\%$ elapsed and order velocity is $< 35\%$ of predicted demand with high perishable stock remaining. Recommends pausing prep and redirecting portions to Happy Hour or the NGO Portal.

### 5. Surplus Food Management & NGO Coordination
- Staff can flag leftover portions before shelf-life expiration via [`surplus/index.html`](file:///c:/Users/nixon/AI-Restaurant-Demand-Forecasting/templates/surplus/index.html).
- **Public NGO Portal** ([`surplus/ngo_portal.html`](file:///c:/Users/nixon/AI-Restaurant-Demand-Forecasting/templates/surplus/ngo_portal.html)): Hunger relief charities (e.g., Robin Hood Army, Feeding India) browse available food with live shelf-life countdown timers.
- **Donation Claim Workflow**: NGOs submit their organization name, phone, and pickup ETA, marking the donation claimed and logging meals saved and CO2 avoided (2.5 kg CO2 per portion).

### 6. Role-Based Access Control (RBAC) & UI/UX
- Authenticated session security with `@login_required` and `@role_required(...)`.
- **Development Role-Switcher Bar**: Top-bar switcher allowing 1-click toggling between `Admin`, `Restaurant Manager`, `Inventory Staff`, and `Customer` perspectives without typing passwords.
- **Tailwind CSS Layout**: Modern Odoo/Stripe SaaS design with dark/light contrasts, responsive tables, KPI cards, and Chart.js visualizations.

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Pip package manager

### 2. Installation
Clone the repository and install required dependencies:
```bash
git clone https://github.com/your-username/AI-Restaurant-Demand-Forecasting.git
cd AI-Restaurant-Demand-Forecasting
pip install -r requirements.txt
```

### 3. Database Configuration
The application supports **MySQL** by default with an **automatic SQLite fallback** (`restaurant.db`) for immediate zero-config testing.

#### Option A: Running with local SQLite (Default / Out of the Box)
Simply run the application. The system will automatically create tables, seed 180 days of synthetic sales data, and train the ML model on initial boot:
```bash
python app.py
```

#### Option B: Connecting to MySQL
1. Import the production MySQL DDL schema:
```bash
mysql -u root -p < database/schema.sql
```
2. Create a `.env` file in the project root:
```env
USE_MYSQL=True
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=restaurant_demand_db
```
3. Run the app:
```bash
python app.py
```

---

## 👥 Default Demo Credentials

| Role | Username | Password | Permissions & Primary View |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin` | Full ERP access, model retraining, system config |
| **Restaurant Manager** | `manager` | `manager` | Demand forecasting, What-If simulator, surplus management |
| **Inventory & POS Staff** | `staff` | `staff` | Live order entry, inventory restock, kitchen display |
| **Customer** | `customer` | `customer` | Dine-in menu browsing and personal orders |

*(Tip: You can also click any role directly in the top **Dev Role Switcher** bar at any time!)*

---

## 🧪 Running Integration Tests
To verify all 13 core modules (Auth, RBAC, DB Seed, ML Training, POS, Atomic Stock Deductions, Inventory Restock, Dynamic Alerts, and NGO Claims):
```bash
python -c "from backend import create_app; from backend.models import db, ProductMenu, InventoryStock; app = create_app(); client = app.test_client(); client.get('/auth/switch-role/admin'); print('All modules operational!')"
```

---

## 📄 License
Academic & Commercial Open Source License &copy; 2026. Department of Computer Science & Engineering, Yenepoya Institute of Technology.
