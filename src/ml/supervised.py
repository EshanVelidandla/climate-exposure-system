"""
Supervised ML module for Climate Burden Index prediction.
Trains XGBoost model with SHAP interpretability.
Saves model to src/ml/models/cbi_xgb.json
"""

import pandas as pd
import numpy as np
import logging
import json
import pickle
from pathlib import Path
from typing import Optional, Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import xgboost as xgb
import shap

from ...config import (
    FEATURES_OUTPUT, XGB_MODEL_PATH, ML_MODELS_DIR, 
    setup_logging, TEST_SIZE, RANDOM_STATE, SHAP_SAMPLE_SIZE
)

logger = setup_logging(__name__)


def load_features(features_path: Path = FEATURES_OUTPUT) -> Optional[pd.DataFrame]:
    """Load feature matrix for modeling."""
    if not features_path.exists():
        logger.error(f"Features file not found: {features_path}")
        return None
    
    try:
        df = pd.read_parquet(features_path)
        logger.info(f"Loaded {len(df)} feature vectors")
        return df
    except Exception as e:
        logger.error(f"Failed to load features: {e}")
        return None


def prepare_model_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare X and y for modeling.
    
    Target: climate_burden_index_normalized (or climate_burden_index)
    Features: all other numeric columns
    """
    # Target variable
    if "climate_burden_index_normalized" in df.columns:
        y = df["climate_burden_index_normalized"]
    elif "climate_burden_index" in df.columns:
        y = df["climate_burden_index"]
    else:
        logger.error("Target variable (climate_burden_index) not found")
        return None, None
    
    # Features (exclude target, GEOID, geometry-related)
    exclude_cols = {
        "geoid", "geometry", "climate_burden_index", 
        "climate_burden_index_normalized", "location_id"
    }
    exclude_cols = {c.lower() for c in exclude_cols}
    
    X = df.select_dtypes(include=[np.number]).copy()
    X.columns = X.columns.str.lower()
    
    # Drop excluded columns
    X = X[[c for c in X.columns if c not in exclude_cols]]
    
    # Drop columns with all NaN
    X = X.dropna(axis=1, how="all")
    
    # Fill remaining NaN with median
    X = X.fillna(X.median())
    
    logger.info(f"Selected {X.shape[1]} features for modeling")
    logger.info(f"Target shape: {y.shape}")
    
    return X, y


def train_xgboost_model(X_train: pd.DataFrame, y_train: pd.Series,
                       X_val: pd.DataFrame, y_val: pd.Series) -> xgb.XGBRegressor:
    """
    Train XGBoost regression model with validation.
    """
    logger.info("Training XGBoost model")
    
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=RANDOM_STATE,
        early_stopping_rounds=10,
        eval_metric="rmse",
    )
    
    # Train with early stopping
    eval_set = [(X_train, y_train), (X_val, y_val)]
    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        verbose=False
    )
    
    logger.info("Model training complete")
    return model


def evaluate_model(model: xgb.XGBRegressor, 
                  X_train: pd.DataFrame, y_train: pd.Series,
                  X_val: pd.DataFrame, y_val: pd.Series) -> dict:
    """Evaluate model performance."""
    # Predictions
    y_train_pred = model.predict(X_train)
    y_val_pred = model.predict(X_val)
    
    # Metrics
    metrics = {
        "train_rmse": float(np.sqrt(mean_squared_error(y_train, y_train_pred))),
        "val_rmse": float(np.sqrt(mean_squared_error(y_val, y_val_pred))),
        "train_mae": float(mean_absolute_error(y_train, y_train_pred)),
        "val_mae": float(mean_absolute_error(y_val, y_val_pred)),
        "train_r2": float(r2_score(y_train, y_train_pred)),
        "val_r2": float(r2_score(y_val, y_val_pred)),
    }
    
    logger.info(f"Model performance:")
    logger.info(f"  Train RMSE: {metrics['train_rmse']:.4f}")
    logger.info(f"  Val RMSE: {metrics['val_rmse']:.4f}")
    logger.info(f"  Train R²: {metrics['train_r2']:.4f}")
    logger.info(f"  Val R²: {metrics['val_r2']:.4f}")
    
    return metrics


def compute_shap_explanations(model: xgb.XGBRegressor,
                             X_sample: pd.DataFrame,
                             X_background: pd.DataFrame = None) -> Tuple[shap.Explainer, np.ndarray]:
    """
    Compute SHAP values for model interpretability.
    
    Args:
        model: Trained XGBoost model
        X_sample: Sample to explain (usually validation set)
        X_background: Background data for baseline (default: sample mean)
        
    Returns:
        (explainer, shap_values)
    """
    logger.info(f"Computing SHAP values for {len(X_sample)} samples")
    
    # Use TreeExplainer for XGBoost
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    logger.info(f"SHAP values shape: {shap_values.shape}")
    
    return explainer, shap_values


def generate_shap_report(explainer: shap.Explainer,
                        shap_values: np.ndarray,
                        X_sample: pd.DataFrame) -> dict:
    """Generate summary statistics for SHAP values."""
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    
    feature_importance = pd.DataFrame({
        "feature": X_sample.columns,
        "mean_abs_shap": mean_abs_shap
    }).sort_values("mean_abs_shap", ascending=False)
    
    logger.info("Top 10 most important features (by SHAP):")
    for idx, row in feature_importance.head(10).iterrows():
        logger.info(f"  {row['feature']}: {row['mean_abs_shap']:.4f}")
    
    return feature_importance.to_dict(orient="records")


def save_model(model: xgb.XGBRegressor, model_path: Path = XGB_MODEL_PATH) -> None:
    """Save XGBoost model to JSON."""
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.get_booster().save_model(str(model_path))
    logger.info(f"Saved model to {model_path}")


def supervised_ml_pipeline() -> Optional[dict]:
    """
    Full supervised ML pipeline.
    
    Returns:
        Dictionary with model, metrics, and SHAP explanations
    """
    logger.info("Starting supervised ML pipeline")
    
    # Load features
    df = load_features()
    if df is None:
        return None
    
    # Prepare X, y
    X, y = prepare_model_data(df)
    if X is None or y is None:
        return None
    
    # Train/val split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    
    logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}")
    
    # Train model
    model = train_xgboost_model(X_train, y_train, X_val, y_val)
    
    # Evaluate
    metrics = evaluate_model(model, X_train, y_train, X_val, y_val)
    
    # SHAP
    explainer, shap_values = compute_shap_explanations(model, X_val)
    shap_report = generate_shap_report(explainer, shap_values, X_val)
    
    # Save model
    save_model(model)
    
    # Save explainer
    with open(ML_MODELS_DIR / "shap_explainer.pkl", "wb") as f:
        pickle.dump(explainer, f)
    logger.info(f"Saved SHAP explainer to {ML_MODELS_DIR / 'shap_explainer.pkl'}")
    
    # Create summary
    result = {
        "model_path": str(XGB_MODEL_PATH),
        "metrics": metrics,
        "feature_importance": shap_report,
        "n_features": X.shape[1],
        "n_samples": len(df),
    }
    
    # Save summary to JSON
    summary_path = ML_MODELS_DIR / "model_summary.json"
    with open(summary_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved model summary to {summary_path}")
    
    return result


if __name__ == "__main__":
    result = supervised_ml_pipeline()
    if result is not None:
        print(f"\n✓ Supervised ML complete")
        print(f"  - Model: XGBoost")
        print(f"  - Val RMSE: {result['metrics']['val_rmse']:.4f}")
        print(f"  - Val R²: {result['metrics']['val_r2']:.4f}")
        print(f"  - Output: {XGB_MODEL_PATH}")
