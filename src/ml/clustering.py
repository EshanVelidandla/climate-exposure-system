"""
Clustering module for Climate Burden Index.
Implements HDBSCAN + K-Means for tract segmentation.
Saves cluster labels and metrics to data/processed/clusters.parquet
"""

import pandas as pd
import numpy as np
import logging
import pickle
from pathlib import Path
from typing import Optional, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, silhouette_samples
import hdbscan
from sklearn.cluster import KMeans

from ...config import FEATURES_OUTPUT, CLUSTERS_OUTPUT, ML_MODELS_DIR, setup_logging
from ...config import N_CLUSTERS_KMEANS, MIN_SAMPLES_HDBSCAN

logger = setup_logging(__name__)


def load_features(features_path: Path = FEATURES_OUTPUT) -> Optional[pd.DataFrame]:
    """Load feature matrix for clustering."""
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


def prepare_clustering_data(df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Prepare data for clustering: select numeric features, standardize.
    
    Returns:
        (scaled_features, feature_dataframe)
    """
    # Select only numeric columns (exclude GEOID, geometry, etc.)
    numeric_df = df.select_dtypes(include=[np.number])
    
    # Remove any columns that are all NaN
    numeric_df = numeric_df.dropna(axis=1, how="all")
    
    # Fill remaining NaNs with median
    numeric_df = numeric_df.fillna(numeric_df.median())
    
    logger.info(f"Selected {numeric_df.shape[1]} numeric features for clustering")
    
    # Standardize
    scaler = StandardScaler()
    scaled = scaler.fit_transform(numeric_df)
    
    logger.info(f"Standardized features: shape {scaled.shape}")
    return scaled, numeric_df


def fit_hdbscan(X: np.ndarray, min_samples: int = MIN_SAMPLES_HDBSCAN) -> hdbscan.HDBSCAN:
    """
    Fit HDBSCAN for density-based clustering.
    
    HDBSCAN is robust to varying cluster densities and automatic K selection.
    """
    logger.info(f"Fitting HDBSCAN with min_samples={min_samples}")
    
    clusterer = hdbscan.HDBSCAN(min_samples=min_samples, min_cluster_size=20)
    clusterer.fit(X)
    
    n_clusters = len(set(clusterer.labels_)) - (1 if -1 in clusterer.labels_ else 0)
    n_noise = list(clusterer.labels_).count(-1)
    
    logger.info(f"HDBSCAN found {n_clusters} clusters, {n_noise} noise points")
    return clusterer


def fit_kmeans(X: np.ndarray, n_clusters: int = N_CLUSTERS_KMEANS) -> KMeans:
    """
    Fit K-Means for partition-based clustering.
    
    Provides fixed number of clusters for CBI segmentation.
    """
    logger.info(f"Fitting K-Means with k={n_clusters}")
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(X)
    
    silhouette = silhouette_score(X, kmeans.labels_)
    logger.info(f"K-Means silhouette score: {silhouette:.4f}")
    
    return kmeans


def evaluate_clustering(X: np.ndarray, labels: np.ndarray, 
                        method: str = "kmeans") -> dict:
    """Compute clustering evaluation metrics."""
    unique_labels = set(labels)
    unique_labels.discard(-1)  # Remove noise label if present
    
    n_clusters = len(unique_labels)
    
    metrics = {
        "method": method,
        "n_clusters": n_clusters,
    }
    
    # Silhouette score (only for valid clusters)
    if n_clusters > 1 and len(unique_labels) >= 2:
        try:
            silhouette = silhouette_score(X, labels)
            metrics["silhouette_score"] = silhouette
            logger.info(f"  Silhouette score: {silhouette:.4f}")
        except Exception as e:
            logger.warning(f"Could not compute silhouette score: {e}")
    
    # Cluster sizes
    unique, counts = np.unique(labels[labels != -1], return_counts=True)
    metrics["cluster_sizes"] = dict(zip(unique, counts))
    logger.info(f"  Cluster sizes: {metrics['cluster_sizes']}")
    
    return metrics


def clustering_pipeline() -> Optional[pd.DataFrame]:
    """
    Full clustering pipeline.
    
    Returns:
        DataFrame with cluster labels and metrics
    """
    logger.info("Starting clustering pipeline")
    
    # Load features
    df = load_features()
    if df is None:
        return None
    
    # Keep GEOID for output
    if "geoid" in df.columns:
        geoids = df["geoid"]
    else:
        geoids = pd.Series(range(len(df)))
    
    # Prepare clustering data
    X, feature_df = prepare_clustering_data(df)
    
    if X.shape[0] == 0:
        logger.error("No data for clustering")
        return None
    
    # Fit HDBSCAN
    hdbscan_model = fit_hdbscan(X)
    
    # Fit K-Means
    kmeans_model = fit_kmeans(X, n_clusters=N_CLUSTERS_KMEANS)
    
    # Evaluate
    hdbscan_metrics = evaluate_clustering(X, hdbscan_model.labels_, "hdbscan")
    kmeans_metrics = evaluate_clustering(X, kmeans_model.labels_, "kmeans")
    
    # Save models
    ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(ML_MODELS_DIR / "hdbscan_model.pkl", "wb") as f:
        pickle.dump(hdbscan_model, f)
    logger.info(f"Saved HDBSCAN model to {ML_MODELS_DIR / 'hdbscan_model.pkl'}")
    
    with open(ML_MODELS_DIR / "kmeans_model.pkl", "wb") as f:
        pickle.dump(kmeans_model, f)
    logger.info(f"Saved K-Means model to {ML_MODELS_DIR / 'kmeans_model.pkl'}")
    
    # Create output dataframe
    result = pd.DataFrame({
        "geoid": geoids.values,
        "hdbscan_cluster": hdbscan_model.labels_,
        "kmeans_cluster": kmeans_model.labels_,
        "cluster_probability": hdbscan_model.probabilities_,
    })
    
    # Save clusters
    CLUSTERS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(CLUSTERS_OUTPUT, index=False)
    logger.info(f"Saved cluster assignments to {CLUSTERS_OUTPUT}")
    
    # Log metrics
    logger.info(f"HDBSCAN metrics: {hdbscan_metrics}")
    logger.info(f"K-Means metrics: {kmeans_metrics}")
    
    return result


if __name__ == "__main__":
    result = clustering_pipeline()
    if result is not None:
        print(f"\n✓ Clustering complete")
        print(f"  - Samples: {len(result)}")
        print(f"  - HDBSCAN clusters: {result['hdbscan_cluster'].max() + 1}")
        print(f"  - K-Means clusters: {result['kmeans_cluster'].max() + 1}")
        print(f"  - Output: {CLUSTERS_OUTPUT}")
