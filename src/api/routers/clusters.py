"""
FastAPI routers for clusters endpoint.
Returns cluster assignments and metadata.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...config import setup_logging, CLUSTERS_OUTPUT, DEMO_MODE
from ...utils import DatabaseManager

logger = setup_logging(__name__)

router = APIRouter(prefix="/clusters", tags=["clusters"])

_db = None


def get_db():
    """Get database connection."""
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db


class ClusterSummary(BaseModel):
    """Cluster summary statistics."""
    cluster_id: int
    method: str  # "kmeans" or "hdbscan"
    size: int
    avg_climate_burden_index: float
    avg_vulnerability_score: float
    geographic_distribution: Optional[dict]


class ClustersResponse(BaseModel):
    """Clusters endpoint response."""
    method: str
    n_clusters: int
    summaries: List[ClusterSummary]


def _demo_clusters_response(method: str) -> ClustersResponse:
    """Return sample cluster summaries when DEMO_MODE is on (no DB)."""
    summaries = [
        ClusterSummary(cluster_id=0, method=method, size=18000, avg_climate_burden_index=28.5, avg_vulnerability_score=0.32, geographic_distribution=None),
        ClusterSummary(cluster_id=1, method=method, size=22000, avg_climate_burden_index=45.2, avg_vulnerability_score=0.48, geographic_distribution=None),
        ClusterSummary(cluster_id=2, method=method, size=15000, avg_climate_burden_index=58.1, avg_vulnerability_score=0.61, geographic_distribution=None),
        ClusterSummary(cluster_id=3, method=method, size=12000, avg_climate_burden_index=72.0, avg_vulnerability_score=0.74, geographic_distribution=None),
        ClusterSummary(cluster_id=4, method=method, size=8000, avg_climate_burden_index=85.3, avg_vulnerability_score=0.82, geographic_distribution=None),
    ]
    return ClustersResponse(method=method, n_clusters=5, summaries=summaries)


@router.get("", response_model=ClustersResponse)
async def get_clusters(
    method: str = Query("kmeans", regex="^(kmeans|hdbscan)$", description="Clustering method")
) -> ClustersResponse:
    """
    Get cluster assignments and summaries.
    
    Returns statistics for each cluster including size,
    average CBI, and vulnerability scores.
    In DEMO_MODE (no DB), returns sample data.
    """
    logger.info(f"Clusters request: method={method}")
    
    if DEMO_MODE:
        return _demo_clusters_response(method)
    
    try:
        db = get_db()
        
        # Get cluster assignments and metrics
        cluster_col = f"{method}_cluster" if method == "kmeans" else "hdbscan_cluster"
        
        query = f"""
        SELECT 
            {cluster_col} as cluster_id,
            COUNT(*) as size,
            AVG(p.climate_burden_index) as avg_cbi,
            AVG(f.vulnerability_score) as avg_vuln
        FROM clusters c
        LEFT JOIN predictions p ON c.geoid = p.geoid
        LEFT JOIN features f ON c.geoid = f.geoid
        WHERE {cluster_col} >= 0
        GROUP BY {cluster_col}
        ORDER BY {cluster_col}
        """
        
        results = db.execute_query(query, {})
        
        if results.empty:
            logger.warning("No cluster data found")
            raise HTTPException(status_code=404, detail="No cluster data available")
        
        summaries = []
        for _, row in results.iterrows():
            summary = ClusterSummary(
                cluster_id=int(row["cluster_id"]),
                method=method,
                size=int(row["size"]),
                avg_climate_burden_index=float(row.get("avg_cbi", 0)),
                avg_vulnerability_score=float(row.get("avg_vuln", 0)),
                geographic_distribution=None,  # Could include state distribution, etc.
            )
            summaries.append(summary)
        
        response = ClustersResponse(
            method=method,
            n_clusters=len(summaries),
            summaries=summaries,
        )
        
        logger.info(f"Returned {len(summaries)} cluster summaries for {method}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching clusters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hdbscan", response_model=ClustersResponse)
async def get_hdbscan_clusters() -> ClustersResponse:
    """Get HDBSCAN clusters."""
    return await get_clusters(method="hdbscan")


@router.get("/kmeans", response_model=ClustersResponse)
async def get_kmeans_clusters() -> ClustersResponse:
    """Get K-Means clusters."""
    return await get_clusters(method="kmeans")
