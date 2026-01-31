# Climate Burden Index - System Architecture

## Overview

The CBI system is a modular pipeline for quantifying environmental inequity at U.S. census-tract scale.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐
│  │ Temp CSV │ │ AQS ZIPs │ │ SVI CSV  │ │Tiger ZIPs│ │ ESG  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────┘
└─────────────────────────────────────────────────────────────┘
                         ↓ ETL
┌─────────────────────────────────────────────────────────────┐
│                      INTERIM TABLES                          │
│  ┌────────────┐ ┌────────┐ ┌──────┐ ┌──────────┐ ┌─────┐
│  │Heat Metrics│ │AQS Data│ │ SVI  │ │ Geometry │ │ ESG │
│  └────────────┘ └────────┘ └──────┘ └──────────┘ └─────┘
└─────────────────────────────────────────────────────────────┘
                    ↓ Feature Engineering
┌─────────────────────────────────────────────────────────────┐
│                    FEATURE VECTORS                           │
│  Climate Burden Score × Vulnerability Score = CBI           │
│  ┌──────────────────────────────────────────────────────┐
│  │ GEOID │ Heat │ PM2.5 │ SVI │ CBI │ Percentile      │
│  │ 11   │ vars │ vars  │vars │     │ Normalized      │
│  └──────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
        ↓ ML (Clustering)    ↓ ML (Supervised)
    ┌─────────────┐      ┌────────────┐
    │  HDBSCAN    │      │  XGBoost   │
    │  K-Means    │      │  + SHAP    │
    │  Labels     │      │  Predictions│
    └─────────────┘      └────────────┘
        ↓                   ↓
┌─────────────────────────────────────────────────────────────┐
│              POSTGIS DATABASE (Predictions)                 │
│  ┌──────────────────────────────────────────────────────┐
│  │ census_tracts │ heat_exposure │ aqs_metrics │ ...   │
│  │ predictions   │ clusters      │ shap_explns │       │
│  └──────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
      ↓ API                     ↓ Frontend
  ┌─────────────────┐    ┌──────────────────┐
  │  FastAPI        │    │  Next.js         │
  │  /score         │    │  Map              │
  │  /clusters      │    │  Dashboard        │
  │  /nlp-insights  │    │  Drill-down Panel │
  └─────────────────┘    └──────────────────┘
```

## Data Flow

### Stage 1: ETL
1. **Temperature ETL** (temperature_etl.py)
   - Load: city_temperature.csv
   - Transform: Aggregate to annual metrics (mean, days >90°F, percentile)
   - Output: data/interim/heat_exposure.parquet

2. **AQS ETL** (aqs_etl.py)
   - Load: Unzip EPA AQS files from data/raw/climate/epa_aqs/
   - Transform: Extract PM2.5 & ozone, compute statistics
   - Output: data/interim/aqs_metrics.parquet

3. **SVI ETL** (svi_etl.py)
   - Load: CDC SVI CSV from data/raw/socioeconomic/svi/
   - Transform: Normalize 15 variables (0-100 percentiles) to 0-1
   - Output: data/interim/svi_normalized.parquet

4. **TIGER ETL** (tiger_etl.py)
   - Load: Unzip all tl_2025_##_tract.zip files
   - Transform: Merge into national GeoDataFrame, standardize GEOID (11-digit)
   - Output: data/interim/tiger_tracts.parquet (GeoParquet)

5. **ESG ETL** (esg_etl.py)
   - Load: Unzip Kaggle ESG dataset
   - Transform: Normalize scores, aggregate by sector
   - Output: data/interim/esg_indicators.parquet

### Stage 2: Feature Engineering
- **Input:** All 5 interim datasets
- **Process:**
  - Merge by GEOID (SVI as base)
  - Compute Climate Burden Score = mean(heat, PM2.5, ozone indicators)
  - Compute Vulnerability Score = mean(SVI normalized variables)
  - Create CBI = Climate Burden × Vulnerability (0-1 range)
  - Normalize CBI to 0-100 scale
- **Output:** data/processed/features.parquet (~15K tracts, 50+ columns)

### Stage 3: Clustering
- **Input:** Numeric features (standardized)
- **HDBSCAN:**
  - Min samples = 10
  - Density-based, auto K selection
  - Identifies variable-density clusters
- **K-Means:**
  - K = 5 (configurable)
  - Partition into fixed segments
  - Better for stratified analysis
- **Output:** data/processed/clusters.parquet (cluster labels + probability)

### Stage 4: Supervised ML
- **Model:** XGBoost regressor
- **Target:** climate_burden_index_normalized (0-100)
- **Features:** All numeric features (auto-selected)
- **Train/Val Split:** 80/20
- **Evaluation:**
  - RMSE, MAE, R²
  - Residual analysis
- **Interpretability:** SHAP values for each prediction
- **Output:** 
  - src/ml/models/cbi_xgb.json (model)
  - src/ml/models/shap_explainer.pkl (explainer)
  - src/ml/models/model_summary.json (metrics)

### Stage 5: Database Loading
- **Tables Created:**
  - census_tracts (GEOID, geometry, state/county info)
  - heat_exposure, aqs_metrics, svi_indicators, esg_indicators
  - features (all merged features)
  - clusters (HDBSCAN + K-Means labels)
  - predictions (CBI per tract)
  - shap_explanations (feature importance per tract)
  - data_quality, etl_logs (monitoring)

- **Indices:** On GEOID, geometry, clustering labels, CBI scores
- **Views:** vw_tract_features, vw_cluster_statistics

### Stage 6: API Server
- **FastAPI** on port 8000
- **Endpoints:**
  - /score?lat&lon&explain - Reverse-geocode + lookup prediction + SHAP
  - /clusters?method - Cluster statistics
  - /nlp-insights?geoid - NLP-generated summaries
- **Database:** Async PostgreSQL queries with sqlalchemy
- **CORS:** Enabled for frontend

### Stage 7: Frontend
- **Next.js** on port 3000
- **Components:**
  - Map: Mapbox GL choropleth of CBI
  - Dashboard: Key metrics, charts, filters
  - ClusterExplorer: Compare clusters
  - DetailPanel: Tract details, SHAP plot, recommendations
- **State Management:** Zustand store
- **Styling:** Tailwind CSS

## Orchestration

### Airflow DAG (dags/cbi_pipeline_dag.py)

**Schedule:** Weekly (Sundays 2 AM UTC)

```
cbi_pipeline_v1
├── etl (TaskGroup)
│   ├── temperature_etl ──┐
│   ├── aqs_etl ──────────┤
│   ├── svi_etl ──────────├─→ feature_engineering
│   ├── tiger_etl ────────┤    ├─→ clustering ────┐
│   └── esg_etl ──────────┘    └─→ supervised_ml  ├─→ data_quality_check → load_to_database
                                                 │
                                                 └─ (runs in parallel)
```

## Configuration & Secrets

**Environment Variables** (.env):
```
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=climate_burden_index
DB_USER=postgres
DB_PASSWORD=your_password

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# ML
N_CLUSTERS_KMEANS=5
MIN_SAMPLES_HDBSCAN=10
TEST_SIZE=0.2
RANDOM_STATE=42

# Frontend
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Logging
LOG_LEVEL=INFO
```

## Monitoring & Observability

### Logging
- All modules use Python logging
- Logs to console + file (logs/ directory)
- Structured JSON logging for production

### Database Monitoring
```sql
-- Data quality checks
SELECT * FROM data_quality ORDER BY metric_date DESC;

-- ETL audit trail
SELECT * FROM etl_logs ORDER BY created_at DESC;
```

### API Metrics
- Prometheus endpoint: /metrics
- Request count, latency, errors
- Model inference time

## Security

### Database
- SSL/TLS for connections (production)
- Row-level security (RLS) on sensitive tables
- Audit logging for modifications

### API
- CORS restricted to frontend origins
- Rate limiting (future)
- JWT authentication (future)

### Data
- Raw data files gitignored
- Models not committed (load from model registry)
- Secrets in .env (not committed)

## Scalability Considerations

### Horizontal Scaling
- Stateless API (can run multiple workers)
- Database connection pooling
- Caching layer (Redis for cluster summaries)

### Vertical Scaling
- Batch prediction for all tracts (not real-time)
- Incremental feature computation (only new data)
- Model serving with ONNX Runtime (faster inference)

### Performance Optimization
- Spatial indices on geometry column
- Parquet compression (snappy)
- PostGIS materialized views for hot queries
- API response caching (30 min for /clusters)

## Disaster Recovery

### Backups
- Daily database backups to S3
- Git repo with full code history
- Model artifacts versioned (MLflow)

### Rollback
- API version endpoint for backwards compatibility
- Database migration scripts
- Blue-green deployment (future)

## Cost Estimation (AWS)

| Component | Estimate |
|-----------|----------|
| RDS (PostgreSQL) | $200-500/month |
| EC2 (API/frontend) | $100-300/month |
| S3 (data/backups) | $50-100/month |
| Data transfer | $20-50/month |
| **Total** | **$370-950/month** |

## Testing Strategy

### Unit Tests
- ETL data validation
- Feature computation correctness
- ML model metrics

### Integration Tests
- Full pipeline end-to-end
- Database read/write
- API endpoints

### Load Tests
- API concurrent requests
- Database query performance
- Frontend rendering

---

**Last Updated:** January 2025  
**Version:** 1.0.0
