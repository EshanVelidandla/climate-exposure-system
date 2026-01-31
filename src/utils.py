"""
Shared utilities for the Climate Burden Index system.
"""

import pandas as pd
import geopandas as gpd
from typing import Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from .config import DATABASE_URL, setup_logging

logger = setup_logging(__name__)

class DatabaseManager:
    """Manages connections to PostgreSQL with PostGIS."""
    
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def execute_query(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame."""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    
    def to_sql(self, df: pd.DataFrame, table_name: str, if_exists: str = "replace", 
               index: bool = False, method: str = "multi") -> None:
        """Save DataFrame to PostGIS table."""
        df.to_sql(table_name, self.engine, if_exists=if_exists, index=index, method=method)
        logger.info(f"Saved {len(df)} rows to table '{table_name}'")
    
    def from_sql(self, table_name: str) -> pd.DataFrame:
        """Read table from PostGIS."""
        query = f"SELECT * FROM {table_name}"
        return pd.read_sql(query, self.engine)
    
    def create_postgis_extension(self) -> None:
        """Enable PostGIS extension."""
        with self.engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.commit()
            logger.info("PostGIS extension enabled")
    
    def reverse_geocode_to_tract(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocode lat/lon to 11-digit GEOID using PostGIS.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            11-digit GEOID string or None if not found
        """
        query = """
        SELECT geoid FROM census_tracts
        WHERE ST_Contains(geometry, ST_Point(:lon, :lat, 4326))
        LIMIT 1
        """
        try:
            result = self.execute_query(query, {"lon": lon, "lat": lat})
            if not result.empty:
                return str(result.iloc[0, 0]).zfill(11)
        except Exception as e:
            logger.error(f"Reverse geocoding failed: {e}")
        return None
    
    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()


def validate_geoid(geoid: str) -> bool:
    """Validate that GEOID is 11-digit string."""
    return isinstance(geoid, str) and len(geoid) == 11 and geoid.isdigit()


def normalize_geoid(geoid) -> str:
    """Normalize GEOID to 11-digit string."""
    if isinstance(geoid, (int, float)):
        geoid = str(int(geoid))
    return str(geoid).zfill(11)


def merge_geojson_with_data(geojson_gdf: gpd.GeoDataFrame, 
                             data_df: pd.DataFrame, 
                             on: str = "GEOID") -> gpd.GeoDataFrame:
    """
    Merge GeoJSON (census tracts) with feature data.
    
    Args:
        geojson_gdf: GeoDataFrame with geometries
        data_df: DataFrame with features
        on: Column name to join on
        
    Returns:
        Merged GeoDataFrame
    """
    geojson_gdf[on] = geojson_gdf[on].apply(normalize_geoid)
    data_df[on] = data_df[on].apply(normalize_geoid)
    
    merged = geojson_gdf.merge(data_df, on=on, how="left")
    logger.info(f"Merged {len(merged)} tracts with feature data")
    return merged


def sample_for_shap(X: pd.DataFrame, n_samples: int = 1000) -> pd.DataFrame:
    """Sample data for SHAP analysis."""
    if len(X) > n_samples:
        return X.sample(n=n_samples, random_state=42)
    return X


def clip_to_us_bounds(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Clip geometries to continental US bounds.
    Uses rough bbox: (-125, 24) to (-66, 49)
    """
    bounds = "POLYGON((-125 24, -66 24, -66 49, -125 49, -125 24))"
    clipped = gdf[gdf.intersects(gpd.GeoSeries([bounds], crs="EPSG:4326")[0])]
    logger.info(f"Clipped to {len(clipped)} features within US bounds")
    return clipped
