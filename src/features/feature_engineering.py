"""
Feature engineering pipeline.
Merges all ETL outputs into a single modeling table.
Computes composite features for CBI prediction.
Saves to data/processed/features.parquet
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Optional

from ..config import (
    HEAT_INTERIM, AQS_INTERIM, SVI_INTERIM, TIGER_INTERIM, ESG_INTERIM,
    FEATURES_OUTPUT, setup_logging,
)
from ..utils import normalize_geoid

logger = setup_logging(__name__)


def load_all_interim_data() -> tuple:
    """Load all interim ETL outputs."""
    heat = None
    aqs = None
    svi = None
    tiger = None
    esg = None
    
    try:
        if HEAT_INTERIM.exists():
            heat = pd.read_parquet(HEAT_INTERIM)
            logger.info(f"Loaded heat data: {len(heat)} rows")
    except Exception as e:
        logger.warning(f"Could not load heat data: {e}")
    
    try:
        if AQS_INTERIM.exists():
            aqs = pd.read_parquet(AQS_INTERIM)
            logger.info(f"Loaded AQS data: {len(aqs)} rows")
    except Exception as e:
        logger.warning(f"Could not load AQS data: {e}")
    
    try:
        if SVI_INTERIM.exists():
            svi = pd.read_parquet(SVI_INTERIM)
            logger.info(f"Loaded SVI data: {len(svi)} rows")
    except Exception as e:
        logger.warning(f"Could not load SVI data: {e}")
    
    try:
        if TIGER_INTERIM.exists():
            import geopandas as gpd
            tiger = gpd.read_parquet(TIGER_INTERIM)
            logger.info(f"Loaded TIGER data: {len(tiger)} rows")
    except Exception as e:
        logger.warning(f"Could not load TIGER data: {e}")
    
    try:
        if ESG_INTERIM.exists():
            esg = pd.read_parquet(ESG_INTERIM)
            logger.info(f"Loaded ESG data: {len(esg)} rows")
    except Exception as e:
        logger.warning(f"Could not load ESG data: {e}")
    
    return heat, aqs, svi, tiger, esg


def prepare_heat_features(heat: pd.DataFrame) -> pd.DataFrame:
    """Prepare heat exposure features."""
    if heat is None or heat.empty:
        logger.warning("No heat data available")
        return pd.DataFrame()
    
    # Standardize columns
    heat = heat.copy()
    heat.columns = heat.columns.str.lower()
    
    # Ensure numeric types
    numeric_cols = ["heat_annual_mean", "heat_days_above_90f", "heat_extreme_percentile_95"]
    for col in numeric_cols:
        if col in heat.columns:
            heat[col] = pd.to_numeric(heat[col], errors="coerce")
    
    # Normalize to 0-1
    for col in numeric_cols:
        if col in heat.columns:
            min_val = heat[col].min()
            max_val = heat[col].max()
            if max_val > min_val:
                heat[f"{col}_normalized"] = (heat[col] - min_val) / (max_val - min_val)
            else:
                heat[f"{col}_normalized"] = 0
    
    logger.info(f"Prepared heat features for {len(heat)} locations")
    return heat


def prepare_aqs_features(aqs: pd.DataFrame) -> pd.DataFrame:
    """Prepare air quality features by pivoting pollutants."""
    if aqs is None or aqs.empty:
        logger.warning("No AQS data available")
        return pd.DataFrame()
    
    aqs = aqs.copy()
    aqs.columns = aqs.columns.str.lower()
    
    # Pivot by pollutant
    if "pollutant" in aqs.columns and "location_id" in aqs.columns:
        # PM2.5 metrics
        pm25 = aqs[aqs["pollutant"] == "PM2.5"].set_index("location_id")
        pm25 = pm25.rename(columns={
            "annual_mean_ppb": "pm25_mean",
            "percentile_95": "pm25_95",
        })
        
        # Ozone metrics
        oz = aqs[aqs["pollutant"] == "Ozone"].set_index("location_id")
        oz = oz.rename(columns={
            "annual_mean_ppb": "ozone_mean",
            "high_days_above_threshold": "ozone_high_days",
        })
        
        result = pd.concat([pm25, oz], axis=1).reset_index()
        
        # Fill missing
        for col in ["pm25_mean", "pm25_95", "ozone_mean", "ozone_high_days"]:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors="coerce")
                result[col] = result[col].fillna(result[col].median())
        
        logger.info(f"Prepared AQS features for {len(result)} locations")
        return result
    else:
        logger.warning("Cannot pivot AQS data: required columns missing")
        return aqs


def prepare_svi_features(svi: pd.DataFrame) -> pd.DataFrame:
    """Prepare SVI features (already normalized 0-1)."""
    if svi is None or svi.empty:
        logger.warning("No SVI data available")
        return pd.DataFrame()
    
    svi = svi.copy()
    svi.columns = svi.columns.str.lower()
    
    # Ensure GEOID is present
    if "geoid" not in svi.columns:
        logger.warning("GEOID not found in SVI data")
    
    logger.info(f"Prepared SVI features for {len(svi)} tracts")
    return svi


def merge_features(heat: pd.DataFrame, aqs: pd.DataFrame, svi: pd.DataFrame, 
                   tiger=None, esg: pd.DataFrame = None) -> pd.DataFrame:
    """
    Merge all features into a single modeling table.
    
    Strategy:
    1. Start with TIGER tracts (baseline)
    2. Join heat by location_id (reverse-geocoded from lat/lon)
    3. Join AQS by location_id
    4. Join SVI by GEOID
    5. Join ESG by sector (if available)
    """
    logger.info("Starting feature merge")
    
    # Initialize with SVI (has GEOID)
    if svi is not None and not svi.empty:
        merged = svi.copy()
        if "geoid" in merged.columns:
            merged["geoid"] = merged["geoid"].apply(normalize_geoid)
    else:
        logger.error("No SVI data to use as base table")
        return pd.DataFrame()
    
    # Join heat features
    if heat is not None and not heat.empty:
        # Map location_id to GEOID if possible
        # For now, use location_id as-is and merge on a common key
        if "location_id" in heat.columns and "geoid" not in heat.columns:
            # Create synthetic GEOID from location_id or skip
            logger.warning("Heat data lacks GEOID, attempting location-level match")
        elif "geoid" in heat.columns:
            heat["geoid"] = heat["geoid"].apply(normalize_geoid)
            merged = merged.merge(heat[["geoid", "heat_annual_mean", "heat_days_above_90f", 
                                        "heat_extreme_percentile_95", "heat_annual_mean_normalized",
                                        "heat_days_above_90f_normalized", "heat_extreme_percentile_95_normalized"]],
                                on="geoid", how="left")
    
    # Join AQS features
    if aqs is not None and not aqs.empty:
        if "location_id" in aqs.columns and "geoid" not in aqs.columns:
            logger.warning("AQS data lacks GEOID, skipping AQS join")
        elif "geoid" in aqs.columns:
            aqs["geoid"] = aqs["geoid"].apply(normalize_geoid)
            aqs_cols = [c for c in aqs.columns if c.startswith(("pm25", "ozone"))]
            merged = merged.merge(aqs[["geoid"] + aqs_cols], on="geoid", how="left")
    
    # Join ESG features (by sector, requires employment data)
    # Placeholder: would need sector employment data
    
    logger.info(f"Merged features for {len(merged)} tracts")
    return merged


def compute_composite_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute composite features for CBI prediction.
    
    - Climate Burden Score = f(heat, PM2.5, ozone)
    - Vulnerability Score = f(SVI metrics)
    - Environmental Inequity = Climate Burden × Vulnerability
    """
    df = df.copy()
    
    # Climate Burden Score
    climate_cols = [c for c in df.columns if c.startswith(("heat", "pm25", "ozone"))]
    numeric_climate = df[climate_cols].select_dtypes(include=[np.number]).columns
    if len(numeric_climate) > 0:
        df["climate_burden_score"] = df[numeric_climate].mean(axis=1)
        df["climate_burden_score"] = df["climate_burden_score"].fillna(df["climate_burden_score"].median())
    else:
        df["climate_burden_score"] = 0.5  # Default
    
    # Vulnerability Score (SVI composite)
    if "svi_composite" in df.columns:
        df["vulnerability_score"] = df["svi_composite"]
    else:
        svi_cols = [c for c in df.columns if c.startswith("svi_")]
        numeric_svi = df[svi_cols].select_dtypes(include=[np.number]).columns
        if len(numeric_svi) > 0:
            df["vulnerability_score"] = df[numeric_svi].mean(axis=1)
        else:
            df["vulnerability_score"] = 0.5
    
    # Environmental Inequity (interaction)
    df["climate_burden_index"] = (
        df["climate_burden_score"] * df["vulnerability_score"]
    )
    
    # Normalize CBI to 0-100 scale
    cbi_min = df["climate_burden_index"].min()
    cbi_max = df["climate_burden_index"].max()
    if cbi_max > cbi_min:
        df["climate_burden_index_normalized"] = (
            (df["climate_burden_index"] - cbi_min) / (cbi_max - cbi_min) * 100
        )
    else:
        df["climate_burden_index_normalized"] = 50
    
    logger.info("Computed composite features (CBI, Vulnerability, etc.)")
    return df


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing values with median/mode."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    return df


def feature_engineering_pipeline() -> Optional[pd.DataFrame]:
    """
    Full feature engineering pipeline.
    
    Returns:
        DataFrame with all features ready for ML
    """
    logger.info("Starting feature engineering pipeline")
    
    # Load all interim data
    heat, aqs, svi, tiger, esg = load_all_interim_data()
    
    # Prepare individual feature sets
    heat = prepare_heat_features(heat)
    aqs = prepare_aqs_features(aqs)
    svi = prepare_svi_features(svi)
    
    # Merge all features
    merged = merge_features(heat, aqs, svi, tiger, esg)
    
    if merged.empty:
        logger.error("Feature merge resulted in empty DataFrame")
        return None
    
    # Compute composite features
    features = compute_composite_features(merged)
    
    # Fill missing values
    features = fill_missing_values(features)
    
    # Save
    FEATURES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(FEATURES_OUTPUT, index=False)
    logger.info(f"Saved {len(features)} feature vectors to {FEATURES_OUTPUT}")
    
    return features


if __name__ == "__main__":
    result = feature_engineering_pipeline()
    if result is not None:
        print(f"\n✓ Feature engineering complete")
        print(f"  - Features: {len(result.columns)} columns")
        print(f"  - Rows: {len(result)} tracts")
        print(f"  - Output: {FEATURES_OUTPUT}")
