"""
ETL for CDC SVI (Social Vulnerability Index) data.
Loads SVI CSV and normalizes 15 vulnerability variables.
Saves to data/interim/svi_normalized.parquet
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Optional

from ..config import SVI_CSV_DIR, SVI_INTERIM, setup_logging

logger = setup_logging(__name__)

# Standard SVI variables (15 + 4 themes)
SVI_VARIABLES = [
    "EPL_POV", "EPL_UNEMP", "EPL_PCI", "EPL_NOHSDP",  # Socioeconomic
    "EPL_AGE65", "EPL_AGE17", "EPL_DISABL", "EPL_SNGPNT",  # Household composition
    "EPL_MINRTY", "EPL_LIMENG",  # Minority status & language
    "EPL_MUNIT", "EPL_MOBILE", "EPL_CROWD", "EPL_NOVEH", "EPL_GROUPQ",  # Housing type/transportation
]

SVI_THEMES = [
    "EP_SOCIOEC", "EP_HSHPD", "EP_MINRTY", "EP_HOUSHTRAN"
]


def find_svi_csv_files(svi_dir: Path = SVI_CSV_DIR) -> list:
    """Find all SVI CSV files."""
    if not svi_dir.exists():
        logger.error(f"SVI directory not found: {svi_dir}")
        return []
    
    csvs = list(svi_dir.glob("*.csv"))
    logger.info(f"Found {len(csvs)} SVI CSV files")
    return csvs


def load_svi_data(csv_files: list) -> Optional[pd.DataFrame]:
    """Load and concatenate SVI CSV files."""
    if not csv_files:
        logger.error("No SVI CSV files provided")
        return None
    
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
            logger.info(f"Loaded {csv_file.name}: {len(df)} rows")
        except Exception as e:
            logger.error(f"Failed to load {csv_file.name}: {e}")
    
    if not dfs:
        return None
    
    combined = pd.concat(dfs, ignore_index=True)
    combined.columns = combined.columns.str.upper()
    logger.info(f"Combined SVI data: {len(combined)} rows")
    return combined


def normalize_svi_variables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize SVI percentile scores to 0-1 range.
    
    SVI variables are typically percentiles (0-100), so we divide by 100.
    Missing/invalid values are set to NaN.
    """
    if df is None or df.empty:
        logger.warning("Empty SVI dataframe")
        return pd.DataFrame()
    
    # Create output dataframe
    output = df[["GEOID"]].copy() if "GEOID" in df.columns else pd.DataFrame()
    
    # Normalize each variable
    for var in SVI_VARIABLES:
        if var in df.columns:
            # Convert to numeric, handle -999 or similar invalid codes
            values = pd.to_numeric(df[var], errors="coerce")
            values = values[(values >= 0) & (values <= 100)]  # Valid percentile range
            output[f"svi_{var.lower()}"] = values / 100.0  # Normalize to 0-1
        else:
            logger.warning(f"Variable {var} not found in SVI data")
    
    # Normalize theme percentiles if available
    for theme in SVI_THEMES:
        if theme in df.columns:
            values = pd.to_numeric(df[theme], errors="coerce")
            values = values[(values >= 0) & (values <= 100)]
            output[f"svi_{theme.lower()}"] = values / 100.0
    
    # Compute composite SVI (mean of all normalized variables)
    numeric_cols = output.select_dtypes(include=[np.number]).columns
    output["svi_composite"] = output[numeric_cols].mean(axis=1)
    
    logger.info(f"Normalized SVI variables for {len(output)} tracts")
    return output


def etl_svi(svi_dir: Path = SVI_CSV_DIR, output_path: Path = SVI_INTERIM) -> Optional[pd.DataFrame]:
    """
    Full ETL pipeline for CDC SVI data.
    
    Returns:
        DataFrame with normalized SVI variables
    """
    logger.info("Starting CDC SVI ETL pipeline")
    
    # Find CSV files
    csv_files = find_svi_csv_files(svi_dir)
    if not csv_files:
        logger.warning("No SVI CSV files found")
        return None
    
    # Load data
    df = load_svi_data(csv_files)
    if df is None:
        return None
    
    # Normalize
    normalized = normalize_svi_variables(df)
    
    # Save to interim
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_parquet(output_path, index=False)
    logger.info(f"Saved normalized SVI data to {output_path}")
    
    return normalized


if __name__ == "__main__":
    result = etl_svi()
    if result is not None:
        print(f"\n✓ SVI ETL complete")
        print(f"  - Processed {len(result)} census tracts")
        print(f"  - Variables: {result.shape[1] - 1} features")
        print(f"  - Output: {SVI_INTERIM}")
