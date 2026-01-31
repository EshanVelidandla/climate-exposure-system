"""
ETL for ESG (Environmental, Social, Governance) dataset.
Loads Kaggle ESG ZIP and extracts company/sector ESG scores.
Saves to data/interim/esg_indicators.parquet
"""

import pandas as pd
import numpy as np
import logging
import zipfile
import io
from pathlib import Path
from typing import Optional

from ..config import ESG_ZIP_DIR, ESG_INTERIM, setup_logging

logger = setup_logging(__name__)


def find_esg_zip_file(esg_dir: Path = ESG_ZIP_DIR) -> Optional[Path]:
    """Find ESG ZIP file in directory."""
    if not esg_dir.exists():
        logger.error(f"ESG directory not found: {esg_dir}")
        return None
    
    zips = list(esg_dir.glob("*.zip"))
    if not zips:
        logger.warning("No ESG ZIP files found")
        return None
    
    logger.info(f"Found ESG ZIP: {zips[0].name}")
    return zips[0]


def extract_esg_from_zip(zip_path: Path) -> Optional[pd.DataFrame]:
    """
    Extract ESG data from Kaggle ZIP.
    
    Assumes structure: ZIP contains CSV(s) with columns like:
    Ticker, Company, Sector, ESG Score, E Score, S Score, G Score, etc.
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                logger.warning(f"No CSV files found in {zip_path.name}")
                return None
            
            # Read first CSV
            csv_file = csv_files[0]
            with z.open(csv_file) as f:
                df = pd.read_csv(f)
                logger.info(f"Extracted {csv_file} from {zip_path.name}: {len(df)} rows")
                return df
    except Exception as e:
        logger.error(f"Failed to extract ESG data: {e}")
        return None


def normalize_esg_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize ESG scores to 0-100 range and compute aggregates.
    
    Handles various ESG score naming conventions.
    """
    if df is None or df.empty:
        logger.warning("Empty ESG dataframe")
        return pd.DataFrame()
    
    df.columns = df.columns.str.strip().str.upper()
    
    # Create output with company/sector
    output = pd.DataFrame()
    
    if "TICKER" in df.columns:
        output["ticker"] = df["TICKER"]
    if "COMPANY" in df.columns:
        output["company"] = df["COMPANY"]
    if "SECTOR" in df.columns:
        output["sector"] = df["SECTOR"]
    
    # Normalize ESG component scores
    score_mappings = {
        "ESG_SCORE": ["ESG SCORE", "ESG_SCORE", "ESGSCORE"],
        "E_SCORE": ["E SCORE", "E_SCORE", "ENVIRONMENTAL"],
        "S_SCORE": ["S SCORE", "S_SCORE", "SOCIAL"],
        "G_SCORE": ["G SCORE", "G_SCORE", "GOVERNANCE"],
    }
    
    for output_col, input_cols in score_mappings.items():
        for input_col in input_cols:
            if input_col in df.columns:
                values = pd.to_numeric(df[input_col], errors="coerce")
                # Normalize to 0-100 if needed
                if values.max() <= 1:
                    values = values * 100
                output[output_col.lower()] = values.clip(0, 100)
                logger.info(f"Extracted {input_col}")
                break
    
    # Compute composite if not already present
    if "esg_score" not in output.columns:
        component_cols = [c for c in output.columns if c in ["e_score", "s_score", "g_score"]]
        if component_cols:
            output["esg_score"] = output[component_cols].mean(axis=1)
            logger.info(f"Computed composite ESG score from components")
    
    logger.info(f"Normalized ESG scores for {len(output)} companies/sectors")
    return output


def aggregate_esg_by_sector(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate ESG scores by sector for geographic analysis.
    
    This allows mapping sector-level ESG to census tracts with major employers.
    """
    if "sector" not in df.columns or df.empty:
        logger.warning("Cannot aggregate without sector column")
        return df
    
    agg_dict = {}
    for col in ["esg_score", "e_score", "s_score", "g_score"]:
        if col in df.columns:
            agg_dict[col] = ["mean", "median", "std"]
    
    if not agg_dict:
        logger.warning("No numeric ESG scores to aggregate")
        return df
    
    sector_agg = df.groupby("sector").agg(agg_dict).reset_index()
    sector_agg.columns = ["_".join(col).strip("_") for col in sector_agg.columns.values]
    
    logger.info(f"Aggregated ESG scores by {len(sector_agg)} sectors")
    return sector_agg


def etl_esg(esg_dir: Path = ESG_ZIP_DIR, output_path: Path = ESG_INTERIM) -> Optional[pd.DataFrame]:
    """
    Full ETL pipeline for Kaggle ESG dataset.
    
    Returns:
        DataFrame with normalized ESG scores
    """
    logger.info("Starting ESG ETL pipeline")
    
    # Find ZIP file
    zip_path = find_esg_zip_file(esg_dir)
    if zip_path is None:
        logger.warning("ESG ZIP file not found")
        return None
    
    # Extract data
    df = extract_esg_from_zip(zip_path)
    if df is None:
        return None
    
    # Normalize scores
    normalized = normalize_esg_scores(df)
    
    # Aggregate by sector
    sector_agg = aggregate_esg_by_sector(normalized)
    
    # Save to interim
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_parquet(output_path, index=False)
    logger.info(f"Saved ESG data to {output_path}")
    
    # Also save sector aggregates
    sector_output = output_path.parent / "esg_by_sector.parquet"
    sector_agg.to_parquet(sector_output, index=False)
    logger.info(f"Saved sector ESG aggregates to {sector_output}")
    
    return normalized


if __name__ == "__main__":
    result = etl_esg()
    if result is not None:
        print(f"\n✓ ESG ETL complete")
        print(f"  - Processed {len(result)} companies")
        if "sector" in result.columns:
            print(f"  - Sectors: {result['sector'].nunique()}")
        print(f"  - Output: {ESG_INTERIM}")
