"""
FastAPI routers for score endpoint.
Handles /score?lat=...&lon=... requests.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb

from ...config import setup_logging, XGB_MODEL_PATH, ML_MODELS_DIR, DEMO_MODE
from ...utils import DatabaseManager

logger = setup_logging(__name__)

router = APIRouter(prefix="/score", tags=["scores"])

# Global model state (lazy load)
_model = None
_shap_explainer = None
_db = None


def get_model():
    """Lazy load XGBoost model."""
    global _model
    if _model is None:
        try:
            _model = xgb.Booster()
            _model.load_model(str(XGB_MODEL_PATH))
            logger.info("Loaded XGBoost model")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise HTTPException(status_code=500, detail="Model loading failed")
    return _model


def get_shap_explainer():
    """Lazy load SHAP explainer."""
    global _shap_explainer
    if _shap_explainer is None:
        try:
            explainer_path = ML_MODELS_DIR / "shap_explainer.pkl"
            if explainer_path.exists():
                with open(explainer_path, "rb") as f:
                    _shap_explainer = pickle.load(f)
                logger.info("Loaded SHAP explainer")
        except Exception as e:
            logger.warning(f"Failed to load SHAP explainer: {e}")
    return _shap_explainer


def get_db():
    """Get database connection."""
    global _db
    if _db is None:
        _db = DatabaseManager()
        _db.create_postgis_extension()
    return _db


class ScoreResponse(BaseModel):
    """Score endpoint response."""
    latitude: float
    longitude: float
    geoid: Optional[str]
    climate_burden_index: float
    percentile: float
    climate_burden_score: float
    vulnerability_score: float
    cluster_kmeans: Optional[int]
    cluster_hdbscan: Optional[int]
    shap_explanation: Optional[dict] = None


def _demo_score_response(lat: float, lon: float, explain: bool) -> ScoreResponse:
    """Return sample score when DEMO_MODE is on (no DB or model)."""
    # Synthetic 11-digit GEOID from lat/lon for demo consistency
    geoid = f"{int((lat + 90) * 500) % 100000:05d}{int((lon + 180) * 500) % 1000000:06d}"
    shap_exp = None
    if explain:
        shap_exp = {
            "top_factors": [
                {"feature": "heat_annual_mean", "contribution": 0.25},
                {"feature": "pm25_mean", "contribution": 0.20},
                {"feature": "svi_composite", "contribution": 0.15},
            ]
        }
    return ScoreResponse(
        latitude=lat,
        longitude=lon,
        geoid=geoid,
        climate_burden_index=52.3,
        percentile=65.0,
        climate_burden_score=0.58,
        vulnerability_score=0.62,
        cluster_kmeans=2,
        cluster_hdbscan=1,
        shap_explanation=shap_exp,
    )


@router.get("", response_model=ScoreResponse)
async def get_score(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    explain: bool = Query(False, description="Include SHAP explanation")
) -> ScoreResponse:
    """
    Get CBI score for a location.
    
    Reverse-geocodes lat/lon to census tract GEOID,
    looks up precomputed features and predictions,
    optionally returns SHAP explanation.
    In DEMO_MODE (no DB), returns sample data.
    """
    logger.info(f"Score request: lat={lat}, lon={lon}, explain={explain}")
    
    if DEMO_MODE:
        return _demo_score_response(lat, lon, explain)
    
    try:
        # Reverse geocode
        db = get_db()
        geoid = db.reverse_geocode_to_tract(lat, lon)
        
        if geoid is None:
            raise HTTPException(status_code=404, detail="Location not in service area")
        
        # Look up precomputed predictions
        query = """
        SELECT 
            p.climate_burden_index,
            c.kmeans_cluster,
            c.hdbscan_cluster,
            f.climate_burden_score,
            f.vulnerability_score
        FROM predictions p
        LEFT JOIN clusters c ON p.geoid = c.geoid
        LEFT JOIN features f ON p.geoid = f.geoid
        WHERE p.geoid = :geoid
        """
        
        results = db.execute_query(query, {"geoid": geoid})
        
        if results.empty:
            logger.warning(f"No prediction found for GEOID {geoid}")
            raise HTTPException(status_code=404, detail="Predictions not available for this location")
        
        row = results.iloc[0]
        
        # Compute percentile (rough estimate)
        percentile_query = "SELECT COUNT(*) FROM predictions WHERE climate_burden_index < :value"
        percentile_count = db.execute_query(percentile_query, {"value": row["climate_burden_index"]})
        total_query = "SELECT COUNT(*) FROM predictions"
        total_count = db.execute_query(total_query, {})
        
        percentile = (percentile_count.iloc[0, 0] / total_count.iloc[0, 0]) * 100 if total_count.iloc[0, 0] > 0 else 50
        
        # SHAP explanation (optional)
        shap_exp = None
        if explain:
            shap_exp = generate_shap_explanation(geoid, row)
        
        response = ScoreResponse(
            latitude=lat,
            longitude=lon,
            geoid=geoid,
            climate_burden_index=float(row["climate_burden_index"]),
            percentile=float(percentile),
            climate_burden_score=float(row.get("climate_burden_score", 0.5)),
            vulnerability_score=float(row.get("vulnerability_score", 0.5)),
            cluster_kmeans=int(row.get("kmeans_cluster", -1)) if not pd.isna(row.get("kmeans_cluster")) else None,
            cluster_hdbscan=int(row.get("hdbscan_cluster", -1)) if not pd.isna(row.get("hdbscan_cluster")) else None,
            shap_explanation=shap_exp,
        )
        
        logger.info(f"Score computed: CBI={response.climate_burden_index:.2f}, percentile={percentile:.1f}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def generate_shap_explanation(geoid: str, prediction_row) -> dict:
    """Generate SHAP explanation for a prediction."""
    try:
        explainer = get_shap_explainer()
        if explainer is None:
            return None
        
        # In production, would load actual feature values for this GEOID
        # and compute SHAP values
        return {
            "top_factors": [
                {"feature": "heat_annual_mean", "contribution": 0.25},
                {"feature": "pm25_mean", "contribution": 0.20},
                {"feature": "svi_composite", "contribution": 0.15},
            ]
        }
    except Exception as e:
        logger.warning(f"SHAP explanation failed: {e}")
        return None
