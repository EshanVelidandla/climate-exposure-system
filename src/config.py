"""
Configuration management for Climate Burden Index system.
Loads from environment variables with sensible defaults.
"""

import os
from pathlib import Path
import logging

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Data paths
TEMP_CSV = RAW_DATA_DIR / "climate" / "city_temperature.csv"
AQS_ZIP_DIR = RAW_DATA_DIR / "climate" / "epa_aqs"
SVI_CSV_DIR = RAW_DATA_DIR / "socioeconomic" / "svi"
TIGER_ZIP_DIR = RAW_DATA_DIR / "geography" / "tiger"
ESG_ZIP_DIR = RAW_DATA_DIR / "esg"

# Output paths
HEAT_INTERIM = INTERIM_DATA_DIR / "heat_exposure.parquet"
AQS_INTERIM = INTERIM_DATA_DIR / "aqs_metrics.parquet"
SVI_INTERIM = INTERIM_DATA_DIR / "svi_normalized.parquet"
TIGER_INTERIM = INTERIM_DATA_DIR / "tiger_tracts.parquet"
ESG_INTERIM = INTERIM_DATA_DIR / "esg_indicators.parquet"
FEATURES_OUTPUT = PROCESSED_DATA_DIR / "features.parquet"
CLUSTERS_OUTPUT = PROCESSED_DATA_DIR / "clusters.parquet"

# ML Models
ML_MODELS_DIR = PROJECT_ROOT / "src" / "ml" / "models"
XGB_MODEL_PATH = ML_MODELS_DIR / "cbi_xgb.json"
KMEANS_MODEL_PATH = ML_MODELS_DIR / "kmeans_model.pkl"
HDBSCAN_MODEL_PATH = ML_MODELS_DIR / "hdbscan_model.pkl"

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "climate_burden_index")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Airflow configuration
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", str(PROJECT_ROOT / "airflow"))
DAGS_FOLDER = PROJECT_ROOT / "dags"

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_WORKERS = int(os.getenv("API_WORKERS", 4))

# Demo mode: run API without PostgreSQL/Docker/API keys (returns sample data)
_demo = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
DEMO_MODE = _demo

# ML configuration
TEST_SIZE = 0.2
RANDOM_STATE = 42
N_CLUSTERS_KMEANS = 5
MIN_SAMPLES_HDBSCAN = 10
SHAP_SAMPLE_SIZE = 1000

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logging(name: str) -> logging.Logger:
    """Setup logging for a module."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Create directories if they don't exist
for directory in [RAW_DATA_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, ML_MODELS_DIR, DAGS_FOLDER]:
    directory.mkdir(parents=True, exist_ok=True)
