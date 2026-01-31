"""
Airflow DAG for Climate Burden Index pipeline.
Orchestrates ETL, feature engineering, clustering, and supervised ML.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
import logging

logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    "owner": "climate-burden-team",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email": ["ops@climateburdentract.org"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# DAG
dag = DAG(
    "cbi_pipeline_v1",
    default_args=default_args,
    description="Climate Burden Index full pipeline",
    schedule_interval="0 2 * * 0",  # Weekly, Sundays at 2 AM UTC
    catchup=False,
    tags=["climate", "ml", "etl"],
)


def etl_temperature_task():
    """Run temperature ETL."""
    from src.etl.temperature_etl import etl_temperature
    return etl_temperature()


def etl_aqs_task():
    """Run AQS ETL."""
    from src.etl.aqs_etl import etl_aqs
    return etl_aqs()


def etl_svi_task():
    """Run SVI ETL."""
    from src.etl.svi_etl import etl_svi
    return etl_svi()


def etl_tiger_task():
    """Run TIGER/Line ETL."""
    from src.etl.tiger_etl import etl_tiger
    return etl_tiger()


def etl_esg_task():
    """Run ESG ETL."""
    from src.etl.esg_etl import etl_esg
    return etl_esg()


def feature_engineering_task():
    """Run feature engineering."""
    from src.features.feature_engineering import feature_engineering_pipeline
    return feature_engineering_pipeline()


def clustering_task():
    """Run clustering pipeline."""
    from src.ml.clustering import clustering_pipeline
    return clustering_pipeline()


def supervised_ml_task():
    """Run supervised ML pipeline."""
    from src.ml.supervised import supervised_ml_pipeline
    return supervised_ml_pipeline()


def data_quality_check_task():
    """Check data quality and log metrics."""
    from src.utils import DatabaseManager
    from datetime import date
    
    db = DatabaseManager()
    today = date.today()
    
    # Example quality checks
    check_query = """
    INSERT INTO data_quality (metric_date, n_tracts_processed)
    SELECT :date, COUNT(*) FROM features
    """
    db.execute_query(check_query, {"date": today})
    logger.info("Data quality checks completed")
    return True


def load_to_database_task():
    """Load processed data to PostGIS."""
    from src.utils import DatabaseManager
    import pandas as pd
    from pathlib import Path
    from src.config import FEATURES_OUTPUT, CLUSTERS_OUTPUT, PROCESSED_DATA_DIR
    
    db = DatabaseManager()
    
    # Load and save features
    if FEATURES_OUTPUT.exists():
        features = pd.read_parquet(FEATURES_OUTPUT)
        db.to_sql(features, "features", if_exists="replace")
        logger.info(f"Loaded {len(features)} feature vectors")
    
    # Load and save clusters
    if CLUSTERS_OUTPUT.exists():
        clusters = pd.read_parquet(CLUSTERS_OUTPUT)
        db.to_sql(clusters, "clusters", if_exists="replace")
        logger.info(f"Loaded {len(clusters)} cluster assignments")
    
    return True


# Task definitions
with TaskGroup("etl", tooltip="Extract, Transform, Load") as etl_group:
    temp_task = PythonOperator(
        task_id="temperature_etl",
        python_callable=etl_temperature_task,
        doc="Extract heat exposure metrics from temperature CSV",
    )
    
    aqs_task = PythonOperator(
        task_id="aqs_etl",
        python_callable=etl_aqs_task,
        doc="Extract PM2.5 and ozone from EPA AQS ZIPs",
    )
    
    svi_task = PythonOperator(
        task_id="svi_etl",
        python_callable=etl_svi_task,
        doc="Load and normalize CDC SVI",
    )
    
    tiger_task = PythonOperator(
        task_id="tiger_etl",
        python_callable=etl_tiger_task,
        doc="Merge TIGER/Line census tracts from all states",
    )
    
    esg_task = PythonOperator(
        task_id="esg_etl",
        python_callable=etl_esg_task,
        doc="Extract ESG scores from Kaggle data",
    )
    
    # ETL tasks in parallel
    [temp_task, aqs_task, svi_task, tiger_task, esg_task]


# Feature engineering
feature_task = PythonOperator(
    task_id="feature_engineering",
    python_callable=feature_engineering_task,
    doc="Merge all features and compute composite metrics",
)

# Clustering
cluster_task = PythonOperator(
    task_id="clustering",
    python_callable=clustering_task,
    doc="Run HDBSCAN and K-Means clustering",
)

# Supervised ML
ml_task = PythonOperator(
    task_id="supervised_ml",
    python_callable=supervised_ml_task,
    doc="Train XGBoost with SHAP explanations",
)

# Data quality
quality_task = PythonOperator(
    task_id="data_quality_check",
    python_callable=data_quality_check_task,
    doc="Log data quality metrics",
)

# Load to database
load_task = PythonOperator(
    task_id="load_to_database",
    python_callable=load_to_database_task,
    doc="Load processed data to PostGIS",
)

# Task dependencies
etl_group >> feature_task
feature_task >> [cluster_task, ml_task]
[cluster_task, ml_task] >> quality_task
quality_task >> load_task
