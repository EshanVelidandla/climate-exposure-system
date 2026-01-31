"""
ETL for EPA AQS (Air Quality System) data.
Extracts PM2.5 and ozone metrics from zipped AQS files.
Saves to data/interim/aqs_metrics.parquet
"""

import pandas as pd
import logging
import zipfile
import io
from pathlib import Path
from typing import Optional, List

from ..config import AQS_ZIP_DIR, AQS_INTERIM, setup_logging

logger = setup_logging(__name__)


def find_aqs_zip_files(zip_dir: Path = AQS_ZIP_DIR) -> List[Path]:
    """Find all AQS ZIP files in directory."""
    if not zip_dir.exists():
        logger.error(f"AQS directory not found: {zip_dir}")
        return []
    
    zips = list(zip_dir.glob("*.zip"))
    logger.info(f"Found {len(zips)} AQS ZIP files")
    return zips


def extract_aqs_from_zip(zip_path: Path) -> Optional[pd.DataFrame]:
    """
    Extract AQS CSV from ZIP file.
    Assumes structure: ZIP contains CSV with columns like:
    State Code, County Code, Site Num, Parameter Name, Datetime, Sample Measurement, etc.
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                logger.warning(f"No CSV files found in {zip_path.name}")
                return None
            
            # Read first CSV found (typically daily or hourly data)
            csv_file = csv_files[0]
            with z.open(csv_file) as f:
                df = pd.read_csv(f)
                logger.info(f"Extracted {csv_file} from {zip_path.name}: {len(df)} rows")
                return df
    except Exception as e:
        logger.error(f"Failed to extract AQS from {zip_path.name}: {e}")
        return None


def compute_aqs_metrics(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Compute PM2.5 and ozone metrics from AQS data.
    
    Processes daily/hourly data and returns aggregated metrics by location.
    """
    if not dfs or all(df is None or df.empty for df in dfs):
        logger.warning("No AQS data to process")
        return pd.DataFrame()
    
    # Combine all dataframes
    combined = pd.concat([df for df in dfs if df is not None], ignore_index=True)
    combined.columns = combined.columns.str.lower().str.replace(" ", "_")
    
    # Standardize parameter names
    if "parameter_name" in combined.columns:
        combined["parameter"] = combined["parameter_name"].str.lower()
    elif "pollutant" in combined.columns:
        combined["parameter"] = combined["pollutant"].str.lower()
    else:
        logger.warning("Could not identify parameter column")
        combined["parameter"] = "unknown"
    
    # Extract numeric measurement
    if "sample_measurement" in combined.columns:
        combined["measurement"] = pd.to_numeric(combined["sample_measurement"], errors="coerce")
    elif "concentration" in combined.columns:
        combined["measurement"] = pd.to_numeric(combined["concentration"], errors="coerce")
    else:
        combined["measurement"] = np.nan
    
    # Create location ID from state/county/site
    if all(col in combined.columns for col in ["state_code", "county_code", "site_num"]):
        combined["location_id"] = (
            combined["state_code"].astype(str).str.zfill(2) +
            combined["county_code"].astype(str).str.zfill(3) +
            combined["site_num"].astype(str).str.zfill(4)
        )
    else:
        combined["location_id"] = combined.get("site_id", "unknown")
    
    # Aggregate metrics by location and parameter
    metrics = []
    for location in combined["location_id"].unique():
        loc_data = combined[combined["location_id"] == location]
        
        # PM2.5 metrics
        pm25_data = loc_data[loc_data["parameter"].str.contains("pm2.5|pm 2.5|fine", case=False, na=False)]
        if not pm25_data.empty:
            pm25_mean = pm25_data["measurement"].mean()
            pm25_95 = pm25_data["measurement"].quantile(0.95)
            metrics.append({
                "location_id": location,
                "pollutant": "PM2.5",
                "annual_mean_ppb": pm25_mean,
                "percentile_95": pm25_95,
                "sample_count": len(pm25_data),
            })
        
        # Ozone metrics
        oz_data = loc_data[loc_data["parameter"].str.contains("ozone|o3", case=False, na=False)]
        if not oz_data.empty:
            oz_mean = oz_data["measurement"].mean()
            oz_high_days = (oz_data["measurement"] > 70).sum()  # ppb threshold
            metrics.append({
                "location_id": location,
                "pollutant": "Ozone",
                "annual_mean_ppb": oz_mean,
                "high_days_above_threshold": oz_high_days,
                "sample_count": len(oz_data),
            })
    
    result = pd.DataFrame(metrics)
    logger.info(f"Computed AQS metrics for {len(result)} location-pollutant pairs")
    return result


def etl_aqs(zip_dir: Path = AQS_ZIP_DIR, output_path: Path = AQS_INTERIM) -> Optional[pd.DataFrame]:
    """
    Full ETL pipeline for EPA AQS data.
    
    Returns:
        DataFrame with AQS metrics (PM2.5, Ozone)
    """
    logger.info("Starting EPA AQS ETL pipeline")
    
    # Find ZIP files
    zips = find_aqs_zip_files(zip_dir)
    if not zips:
        logger.warning("No AQS ZIP files found")
        return None
    
    # Extract from each ZIP
    dfs = [extract_aqs_from_zip(z) for z in zips]
    
    # Compute metrics
    metrics = compute_aqs_metrics(dfs)
    
    # Save to interim
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_parquet(output_path, index=False)
    logger.info(f"Saved AQS metrics to {output_path}")
    
    return metrics


if __name__ == "__main__":
    import numpy as np
    result = etl_aqs()
    if result is not None:
        print(f"\n✓ AQS ETL complete")
        print(f"  - Processed {result['location_id'].nunique()} locations")
        print(f"  - Pollutants: {', '.join(result['pollutant'].unique())}")
        print(f"  - Output: {AQS_INTERIM}")
