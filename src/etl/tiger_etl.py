"""
ETL for TIGER/Line census tract boundaries (2025).
Loads all state ZIP files and merges into national GeoDataFrame.
Saves to data/interim/tiger_tracts.parquet
"""

import geopandas as gpd
import pandas as pd
import logging
import zipfile
from pathlib import Path
from typing import Optional
import tempfile

from ..config import TIGER_ZIP_DIR, TIGER_INTERIM, setup_logging

logger = setup_logging(__name__)


def find_tiger_zip_files(tiger_dir: Path = TIGER_ZIP_DIR) -> list:
    """Find all TIGER/Line tract ZIP files (tl_2025_##_tract.zip)."""
    if not tiger_dir.exists():
        logger.error(f"TIGER directory not found: {tiger_dir}")
        return []
    
    zips = list(tiger_dir.glob("tl_2025_*_tract.zip"))
    logger.info(f"Found {len(zips)} TIGER/Line ZIP files")
    return zips


def extract_shapefile_from_zip(zip_path: Path) -> Optional[gpd.GeoDataFrame]:
    """
    Extract shapefile from TIGER ZIP.
    
    ZIP typically contains:
    - .shp (geometry)
    - .shx (index)
    - .dbf (attributes)
    - .prj (projection)
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(tmpdir)
            
            # Find shapefile
            shp_files = list(Path(tmpdir).glob("*.shp"))
            if not shp_files:
                logger.warning(f"No shapefile found in {zip_path.name}")
                return None
            
            # Read shapefile
            gdf = gpd.read_file(shp_files[0])
            logger.info(f"Extracted {zip_path.name}: {len(gdf)} tracts, CRS={gdf.crs}")
            return gdf
    except Exception as e:
        logger.error(f"Failed to extract shapefile from {zip_path.name}: {e}")
        return None


def standardize_tiger_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Standardize column names across all TIGER files."""
    # TIGER standard columns: STATEFP, COUNTYFP, TRACTCE, GEOID, NAME, etc.
    gdf.columns = gdf.columns.str.upper()
    
    # Ensure GEOID is 11-digit string
    if "GEOID" in gdf.columns:
        gdf["GEOID"] = gdf["GEOID"].astype(str).str.zfill(11)
    elif "GEOID10" in gdf.columns:
        gdf["GEOID"] = gdf["GEOID10"].astype(str).str.zfill(11)
    else:
        logger.warning("GEOID column not found, attempting to construct")
        # Construct from STATEFP + COUNTYFP + TRACTCE
        if all(col in gdf.columns for col in ["STATEFP", "COUNTYFP", "TRACTCE"]):
            gdf["GEOID"] = (
                gdf["STATEFP"].astype(str).str.zfill(2) +
                gdf["COUNTYFP"].astype(str).str.zfill(3) +
                gdf["TRACTCE"].astype(str).str.zfill(6)
            )
    
    # Keep only essential columns
    keep_cols = ["GEOID", "geometry"]
    optional_cols = ["STATEFP", "COUNTYFP", "TRACTCE", "NAME", "ALAND", "AWATER"]
    
    cols_to_keep = [c for c in keep_cols + optional_cols if c in gdf.columns]
    gdf = gdf[cols_to_keep]
    
    # Ensure WGS84 (EPSG:4326)
    if gdf.crs is None:
        logger.warning("No CRS found, assuming EPSG:4326")
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs != "EPSG:4326":
        logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
        gdf = gdf.to_crs("EPSG:4326")
    
    return gdf


def merge_tiger_shapefiles(gdfs: list) -> Optional[gpd.GeoDataFrame]:
    """Merge multiple state TIGER shapefiles into national GeoDataFrame."""
    if not gdfs:
        logger.error("No GeoDataFrames to merge")
        return None
    
    # Remove None entries
    gdfs = [g for g in gdfs if g is not None and len(g) > 0]
    
    if not gdfs:
        logger.error("All GeoDataFrames are empty")
        return None
    
    # Concatenate
    national = gpd.GeoDataFrame(
        pd.concat(gdfs, ignore_index=True),
        crs=gdfs[0].crs
    )
    
    # Remove duplicates by GEOID
    national = national.drop_duplicates(subset=["GEOID"], keep="first")
    
    logger.info(f"Merged national TIGER data: {len(national)} unique census tracts")
    return national


def etl_tiger(tiger_dir: Path = TIGER_ZIP_DIR, output_path: Path = TIGER_INTERIM) -> Optional[gpd.GeoDataFrame]:
    """
    Full ETL pipeline for TIGER/Line census tracts.
    
    Returns:
        GeoDataFrame with national census tract geometries
    """
    logger.info("Starting TIGER/Line ETL pipeline")
    
    # Find ZIP files
    zips = find_tiger_zip_files(tiger_dir)
    if not zips:
        logger.warning("No TIGER ZIP files found")
        return None
    
    # Extract shapefiles
    gdfs = []
    for zip_path in zips:
        gdf = extract_shapefile_from_zip(zip_path)
        if gdf is not None:
            gdf = standardize_tiger_columns(gdf)
            gdfs.append(gdf)
    
    # Merge
    national = merge_tiger_shapefiles(gdfs)
    if national is None:
        return None
    
    # Save to interim (convert to Parquet with geometry as WKT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    national.to_parquet(output_path)
    logger.info(f"Saved TIGER tracts to {output_path}")
    
    return national


if __name__ == "__main__":
    result = etl_tiger()
    if result is not None:
        print(f"\n✓ TIGER/Line ETL complete")
        print(f"  - Processed {len(result)} census tracts")
        print(f"  - States: {result['STATEFP'].nunique() if 'STATEFP' in result.columns else 'N/A'}")
        print(f"  - CRS: {result.crs}")
        print(f"  - Output: {TIGER_INTERIM}")
