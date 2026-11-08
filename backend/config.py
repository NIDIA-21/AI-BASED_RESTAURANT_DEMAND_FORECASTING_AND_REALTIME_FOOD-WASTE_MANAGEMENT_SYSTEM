import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-restaurant-demand-forecast-secret-key-2026')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    
    # Database configuration: MySQL by default with graceful SQLite fallback
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'restaurant_demand_db')
    
    # Priority: explicit DATABASE_URL -> MySQL connection -> local SQLite
    ENV_DATABASE_URL = os.environ.get('DATABASE_URL')
    SQLITE_PATH = BASE_DIR / 'restaurant.db'
    
    if ENV_DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = ENV_DATABASE_URL
    else:
        # Check if MySQL credentials were explicitly given or default to SQLite fallback
        use_mysql = os.environ.get('USE_MYSQL', 'False').lower() in ('true', '1', 'yes')
        if use_mysql:
            if MYSQL_PASSWORD:
                SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
            else:
                SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
        else:
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{SQLITE_PATH}"
            
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ML Model directory
    ML_MODEL_DIR = BASE_DIR / 'ml_model'
    MODEL_FILE_PATH = ML_MODEL_DIR / 'demand_model.joblib'
    METRICS_FILE_PATH = ML_MODEL_DIR / 'metrics.json'
    
    # App Settings
    RESTAURANT_NAME = "GreenBite Smart Bistro & ERP"
    CURRENCY_SYMBOL = "₹"
    SAFETY_BUFFER_PERCENT = 0.12  # 12% safety buffer for preparation recommendation
