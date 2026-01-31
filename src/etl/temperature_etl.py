"""
ETL for temperature data from city_temperature.csv
Computes heat exposure metrics (annual mean, percentiles, extreme days).
Saves to data/interim/heat_exposure.parquet
"""

import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..config import TEMP_CSV, HEAT_INTERIM, setup_logging, INTERIM_DATA_DIR

logger = setup_logging(__name__)


def load_temperature_data(csv_path: Path = TEMP_CSV) -> Optional[pd.DataFrame]:
    """Load temperature CSV with error handling."""
    if not csv_path.exists():
        logger.error(f"Temperature CSV not found at {csv_path}")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded temperature data: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Failed to load temperature data: {e}")
        return None


def compute_heat_exposure_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute heat exposure metrics from temperature data.
    
    Assumes columns: date, city, latitude, longitude, temperature (Celsius)
    
    Returns:
        DataFrame with GEOID, heat_annual_mean, heat_days_above_90f, heat_extreme_percentile_95
    """
    if df is None or df.empty:
        logger.warning("Empty temperature dataframe")
        return pd.DataFrame()
    
    # Standardize column names to lowercase
    df.columns = df.columns.str.lower()
    
    # Convert temperature to Fahrenheit if needed (assuming input is Celsius)
    if "temperature" in df.columns:
        df["temp_f"] = (df["temperature"] * 9/5) + 32
    elif "avg_temp" in df.columns:
        df["temp_f"] = (df["avg_temp"] * 9/5) + 32
    else:
        logger.error("No temperature column found")
        return pd.DataFrame()
    
    # Add date column
    if "date" not in df.columns:
        df["date"] = pd.to_datetime("2025-01-01")
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    # Group by location (use city + lat/lon as proxy for tract)
    # In production, this would be reverse-geocoded to census tract GEOID
    df["location_id"] = df.apply(
        lambda row: f"{row.get('city', 'unknown')}_{row.get('latitude', 0):.2f}_{row.get('longitude', 0):.2f}",
        axis=1
    )
    
    metrics = []
    for location_id in df["location_id"].unique():
        subset = df[df["location_id"] == location_id]
        
        # Annual mean temperature
        annual_mean = subset["temp_f"].mean()
        
        # Days above 90°F
        days_above_90 = (subset["temp_f"] > 90).sum()
        
        # 95th percentile
        percentile_95 = subset["temp_f"].quantile(0.95)
        
        metrics.append({
            "location_id": location_id,
            "heat_annual_mean": annual_mean,
            "heat_days_above_90f": days_above_90,
            "heat_extreme_percentile_95": percentile_95,
            "record_count": len(subset),
        })
    
    result = pd.DataFrame(metrics)
    logger.info(f"Computed heat metrics for {len(result)} locations")
    return result


def etl_temperature(output_path: Path = HEAT_INTERIM) -> Optional[pd.DataFrame]:
    """
    Full ETL pipeline for temperature data.
    
    Returns:
        DataFrame with heat exposure metrics
    """
    logger.info("Starting temperature ETL pipeline")
    
    # Load data
    df = load_temperature_data()
    if df is None:
        return None
    
    # Compute metrics
    metrics = compute_heat_exposure_metrics(df)
    
    # Save to interim
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_parquet(output_path, index=False)
    logger.info(f"Saved heat exposure metrics to {output_path}")
    
    return metrics


if __name__ == "__main__":
    result = etl_temperature()
    if result is not None:
        print(f"\n✓ Temperature ETL complete")
        print(f"  - Processed {len(result)} locations")
        print(f"  - Output: {HEAT_INTERIM}")
