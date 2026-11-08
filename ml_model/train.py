"""
AI Machine Learning Demand Forecasting Training Pipeline:
Trains and benchmarks RandomForestRegressor and GradientBoostingRegressor models
to predict daily food item order demand and recommend initial preparation quantities.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from backend.config import Config
from backend.models import db, HistoricalSalesData, ProductMenu

MODEL_DIR = Config.ML_MODEL_DIR
MODEL_PATH = Config.MODEL_FILE_PATH
METRICS_PATH = Config.METRICS_FILE_PATH


def load_training_dataset():
    """
    Extract historical sales joined with product menu metadata from database.
    """
    query = (
        db.session.query(
            HistoricalSalesData.date,
            HistoricalSalesData.item_id,
            HistoricalSalesData.day_type,
            HistoricalSalesData.customer_count,
            HistoricalSalesData.actual_qty_ordered,
            HistoricalSalesData.weather_condition,
            ProductMenu.item_name,
            ProductMenu.category,
            ProductMenu.unit_price,
            ProductMenu.standard_prep_cost,
            ProductMenu.shelf_life_hours
        )
        .join(ProductMenu, HistoricalSalesData.item_id == ProductMenu.id)
        .all()
    )

    if not query:
        return None

    # Convert to DataFrame
    data = []
    for r in query:
        date_obj = r.date
        data.append({
            'date': date_obj,
            'item_id': r.item_id,
            'item_name': r.item_name,
            'category': r.category,
            'day_type': r.day_type,
            'customer_count': r.customer_count,
            'weather_condition': r.weather_condition,
            'unit_price': float(r.unit_price),
            'standard_prep_cost': float(r.standard_prep_cost),
            'shelf_life_hours': r.shelf_life_hours,
            'day_of_week': date_obj.weekday(), # 0=Monday, 6=Sunday
            'month': date_obj.month,
            'actual_qty_ordered': r.actual_qty_ordered
        })

    df = pd.DataFrame(data)
    return df


def train_demand_forecasting_model():
    """
    Executes training workflow, compares models, saves champion pipeline & metrics.
    """
    print("[ML] Initializing AI Demand Forecasting Model Training...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = load_training_dataset()
    if df is None or len(df) < 50:
        print("[ML WARNING] Insufficient historical data found in database. Please seed database first.")
        return None

    print(f"[ML] Training dataset loaded successfully with {len(df)} historical observations.")

    # Feature definitions
    # Required core features: [day_type, customer_count, item_id, day_of_week]
    # Plus enriched features: [weather_condition, category, month, unit_price]
    categorical_features = ['day_type', 'item_id', 'weather_condition', 'category']
    numeric_features = ['customer_count', 'day_of_week', 'month', 'unit_price']

    X = df[categorical_features + numeric_features]
    y = df['actual_qty_ordered']

    # Train / Test split (80 / 20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, shuffle=True
    )

    # Feature preprocessor pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
            ('num', StandardScaler(), numeric_features)
        ]
    )

    # Candidate Models
    models = {
        'Random Forest Regressor': RandomForestRegressor(
            n_estimators=120,
            max_depth=14,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        ),
        'Gradient Boosting Regressor': GradientBoostingRegressor(
            n_estimators=120,
            learning_rate=0.08,
            max_depth=5,
            subsample=0.85,
            random_state=42
        )
    }

    best_model_name = None
    best_pipeline = None
    best_r2 = -float('inf')
    model_evaluations = {}

    for name, regressor in models.items():
        print(f"[ML] Training candidate model: {name}...")
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', regressor)
        ])

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        r2 = float(r2_score(y_test, y_pred))
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mape = float(np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100)

        print(f"[ML] {name} Performance -> R2: {r2:.4f} | MAE: {mae:.2f} | RMSE: {rmse:.2f} | MAPE: {mape:.2f}%")

        model_evaluations[name] = {
            'r2_score': round(r2, 4),
            'mae': round(mae, 2),
            'rmse': round(rmse, 2),
            'mape_percent': round(mape, 2)
        }

        if r2 > best_r2:
            best_r2 = r2
            best_model_name = name
            best_pipeline = pipeline

    print(f"[ML] Champion Model Selected: {best_model_name} (R2 = {best_r2:.4f})")

    # Save champion pipeline
    joblib.dump(best_pipeline, MODEL_PATH)
    print(f"[ML] Model pipeline successfully saved to: {MODEL_PATH}")

    # Calculate Feature Importances
    feature_importances = []
    try:
        fitted_preprocessor = best_pipeline.named_steps['preprocessor']
        fitted_regressor = best_pipeline.named_steps['regressor']
        
        encoded_cat_names = list(fitted_preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_features))
        all_feature_names = encoded_cat_names + numeric_features

        if hasattr(fitted_regressor, 'feature_importances_'):
            importances = fitted_regressor.feature_importances_
            feature_imp_pairs = sorted(
                zip(all_feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )[:15] # Top 15 features
            feature_importances = [
                {'feature': str(f), 'importance': round(float(imp) * 100, 2)}
                for f, imp in feature_imp_pairs
            ]
    except Exception as e:
        print(f"[ML Notice] Feature importance extraction skipped: {e}")

    # Build metrics report
    metrics_report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'champion_model': best_model_name,
        'r2_score': model_evaluations[best_model_name]['r2_score'],
        'mae': model_evaluations[best_model_name]['mae'],
        'rmse': model_evaluations[best_model_name]['rmse'],
        'mape_percent': model_evaluations[best_model_name]['mape_percent'],
        'training_samples': int(len(df)),
        'train_samples': int(len(X_train)),
        'test_samples': int(len(X_test)),
        'models_compared': model_evaluations,
        'feature_importances': feature_importances,
        'required_features': ['day_type', 'customer_count', 'item_id', 'day_of_week'],
        'extended_features': ['weather_condition', 'category', 'month', 'unit_price']
    }

    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics_report, f, indent=2)

    print(f"[ML] Metrics report written to: {METRICS_PATH}")
    return metrics_report


if __name__ == '__main__':
    from backend import create_app
    app = create_app()
    with app.app_context():
        train_demand_forecasting_model()
