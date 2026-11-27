"""
AI Machine Learning Demand Forecasting Training Pipeline:
Trains and benchmarks RandomForestRegressor and GradientBoostingRegressor models
to predict daily food item order demand and recommend initial preparation quantities.
Supports continuous online learning as new dishes are added and new customer orders arrive.
"""

import os
import json
import joblib
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timezone

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

# Thread-safe coalescing state for non-blocking background retraining
_retrain_lock = threading.Lock()
_retrain_running = False
_retrain_pending = False


def load_training_dataset():
    """
    Extract historical sales joined with product menu metadata from database.
    Includes all historical records for both original and newly added dishes.
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
            'day_of_week': date_obj.weekday(),  # 0=Monday, 6=Sunday
            'month': date_obj.month,
            'actual_qty_ordered': r.actual_qty_ordered
        })

    return pd.DataFrame(data)


def _compute_item_sample_weights(series: pd.Series) -> np.ndarray:
    """
    Balance per-dish learning weight across items (capped at 90x) so newly
    added dishes with just 1-5 live orders strongly guide the trained model
    without losing accuracy on established high-history dishes.
    """
    counts = series.value_counts()
    max_count = float(counts.max()) if len(counts) > 0 else 1.0
    weights = series.map(
        lambda item_id: min(90.0, max(1.0, max_count / max(1, counts.get(item_id, 1))))
    )
    return weights.to_numpy(dtype=float)


def _build_preprocessor(categorical_features, numeric_features):
    """Creates the ColumnTransformer used across benchmark and final models."""
    return ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
            ('num', StandardScaler(), numeric_features)
        ]
    )


def _build_candidate_models():
    """Returns fresh estimator instances for benchmarking and full-data fitting."""
    return {
        'Random Forest Regressor': lambda: RandomForestRegressor(
            n_estimators=100,
            max_depth=14,
            min_samples_split=3,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=1  # Single-process avoids Windows joblib worker spawn overhead (~1.4s total)
        ),
        'Gradient Boosting Regressor': lambda: GradientBoostingRegressor(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=5,
            min_samples_leaf=1,
            subsample=0.85,
            random_state=42
        )
    }


def _atomic_write_joblib(pipeline, target_path):
    tmp_path = target_path.with_suffix('.joblib.tmp')
    joblib.dump(pipeline, tmp_path)
    os.replace(tmp_path, target_path)


def _atomic_write_json(payload, target_path):
    tmp_path = target_path.with_suffix('.json.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, target_path)


def train_demand_forecasting_model():
    """
    Executes training workflow:
    1. Benchmarks RandomForest & GradientBoosting on an 80/20 split for honest accuracy metrics.
    2. Refits the winning champion pipeline on 100% of current database sales records
       (with rarity balancing) so every existing AND newly ordered dish is learned immediately.
    3. Saves the champion pipeline + metrics atomically to disk.
    """
    print("[ML] Initializing AI Demand Forecasting Model Training...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = load_training_dataset()
    if df is None or len(df) < 10:
        print("[ML WARNING] Insufficient historical data found in database. Please seed database first.")
        return None

    distinct_items = int(df['item_id'].nunique())
    print(f"[ML] Training dataset loaded: {len(df)} historical observations across {distinct_items} dishes.")

    categorical_features = ['day_type', 'item_id', 'weather_condition', 'category']
    numeric_features = ['customer_count', 'day_of_week', 'month', 'unit_price']

    X = df[categorical_features + numeric_features]
    y = df['actual_qty_ordered']

    # Stratify by item_id when every item has at least 5 observations for clean validation split
    item_counts = df['item_id'].value_counts()
    stratify_col = df['item_id'] if (len(item_counts) > 1 and item_counts.min() >= 5) else None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, shuffle=True, stratify=stratify_col
    )

    candidate_factories = _build_candidate_models()
    best_model_name = None
    best_r2 = -float('inf')
    model_evaluations = {}

    for name, regressor_factory in candidate_factories.items():
        print(f"[ML] Benchmarking candidate model: {name}...")
        eval_pipeline = Pipeline(steps=[
            ('preprocessor', _build_preprocessor(categorical_features, numeric_features)),
            ('regressor', regressor_factory())
        ])

        eval_pipeline.fit(X_train, y_train)
        y_pred = eval_pipeline.predict(X_test)

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

    print(f"[ML] Champion Model Selected: {best_model_name} (R2 = {best_r2:.4f})")

    # Fit final deployed champion on 100% of data so newly ordered dishes with >=1 record are always learned
    full_weights = _compute_item_sample_weights(df['item_id'])
    final_pipeline = Pipeline(steps=[
        ('preprocessor', _build_preprocessor(categorical_features, numeric_features)),
        ('regressor', candidate_factories[best_model_name]())
    ])
    final_pipeline.fit(X, y, regressor__sample_weight=full_weights)

    _atomic_write_joblib(final_pipeline, MODEL_PATH)
    print(f"[ML] Champion pipeline fitted on all {len(df)} records and saved to: {MODEL_PATH}")

    # Calculate Feature Importances from final deployed pipeline
    feature_importances = []
    try:
        fitted_preprocessor = final_pipeline.named_steps['preprocessor']
        fitted_regressor = final_pipeline.named_steps['regressor']

        encoded_cat_names = list(
            fitted_preprocessor.named_transformers_['cat'].get_feature_names_out(categorical_features)
        )
        all_feature_names = encoded_cat_names + numeric_features

        if hasattr(fitted_regressor, 'feature_importances_'):
            importances = fitted_regressor.feature_importances_
            feature_imp_pairs = sorted(
                zip(all_feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )[:15]
            feature_importances = [
                {'feature': str(f), 'importance': round(float(imp) * 100, 2)}
                for f, imp in feature_imp_pairs
            ]
    except Exception as e:
        print(f"[ML Notice] Feature importance extraction skipped: {e}")

    metrics_report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'champion_model': best_model_name,
        'r2_score': model_evaluations[best_model_name]['r2_score'],
        'mae': model_evaluations[best_model_name]['mae'],
        'rmse': model_evaluations[best_model_name]['rmse'],
        'mape_percent': model_evaluations[best_model_name]['mape_percent'],
        'training_samples': int(len(df)),
        'dishes_learned': distinct_items,
        'train_samples': int(len(X_train)),
        'test_samples': int(len(X_test)),
        'models_compared': model_evaluations,
        'feature_importances': feature_importances,
        'required_features': ['day_type', 'customer_count', 'item_id', 'day_of_week'],
        'extended_features': ['weather_condition', 'category', 'month', 'unit_price']
    }

    _atomic_write_json(metrics_report, METRICS_PATH)
    print(f"[ML] Metrics report written to: {METRICS_PATH}")
    return metrics_report


def trigger_async_retrain(app, reason: str = "data_update"):
    """
    Coalescing background ML retrain helper shared by orders and menu routes.
    Immediately retrains and reloads DemandPredictor in memory without blocking HTTP requests;
    if new updates arrive while training runs, queues exactly one follow-up pass.
    """
    global _retrain_running, _retrain_pending

    with _retrain_lock:
        if _retrain_running:
            _retrain_pending = True
            return
        _retrain_running = True

    def _worker():
        global _retrain_running, _retrain_pending
        while True:
            try:
                with app.app_context():
                    metrics = train_demand_forecasting_model()
                    from ml_model.predictor import DemandPredictor
                    DemandPredictor.reload_pipeline()
                    if metrics:
                        print(
                            f"[ML AUTO-RETRAIN:{reason}] Complete -> "
                            f"samples={metrics['training_samples']}, dishes={metrics['dishes_learned']}, R2={metrics['r2_score']}"
                        )
            except Exception as e:
                print(f"[ML AUTO-RETRAIN:{reason}] Error: {e}")

            with _retrain_lock:
                if _retrain_pending:
                    _retrain_pending = False
                    continue
                _retrain_running = False
                break

    threading.Thread(target=_worker, daemon=True).start()


if __name__ == '__main__':
    from backend import create_app
    app = create_app()
    with app.app_context():
        train_demand_forecasting_model()
