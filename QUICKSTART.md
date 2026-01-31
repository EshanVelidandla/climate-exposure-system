# Climate Burden Index - Quick Start Guide

Get the Climate Burden Index system running in minutes.

## 🚀 Fastest Path: Docker Compose

### Prerequisites
- Docker & Docker Compose installed
- 4GB free disk space

### Launch (30 seconds)

```bash
# Clone and navigate
git clone <repo> && cd climate-exposure-system

# Start all services
docker-compose up -d

# Verify services started
docker-compose ps
```

**Services running:**
- 🌐 API: http://localhost:8000
- 💻 Frontend: http://localhost:3000  
- 🗄️ Database: postgresql://localhost:5432
- 📊 Airflow: http://localhost:8080

---

## 📊 First Query

### Get CBI Score for a Location

```bash
# Query by latitude/longitude
curl -X GET "http://localhost:8000/score?lat=40.7128&lon=-74.0060&explain=false"

# Response
{
  "geoid": "36061001001",
  "climate_burden_index": 65.5,
  "percentile_rank": 78,
  "hdbscan_cluster": 2,
  "kmeans_cluster": 2
}
```

### Get All Clusters

```bash
curl -X GET "http://localhost:8000/clusters?method=kmeans"

# Response
[
  {
    "cluster_id": 0,
    "tract_count": 15000,
    "avg_cbi": 35,
    "characteristics": "Low burden, rural stable areas"
  },
  {
    "cluster_id": 1,
    "tract_count": 12000,
    "avg_cbi": 55,
    "characteristics": "Moderate burden, mixed urban/rural"
  }
  ...
]
```

### Get Explanation for Score

```bash
curl -X GET "http://localhost:8000/score?lat=40.7128&lon=-74.0060&explain=true"

# Response includes SHAP values
{
  "geoid": "36061001001",
  "climate_burden_index": 65.5,
  "explanation": {
    "base_value": 60.0,
    "features": [
      {"name": "heat_annual_mean", "contribution": 4.5},
      {"name": "pm25_mean", "contribution": -2.1},
      {"name": "svi_composite", "contribution": 3.1}
    ]
  }
}
```

---

## 📈 Run Analysis Pipeline

### Process All Data (One Command)

```bash
# Execute complete ETL → Features → ML → Load pipeline
docker-compose exec api python -m src.features.feature_engineering
docker-compose exec api python -m src.ml.clustering
docker-compose exec api python -m src.ml.supervised
```

### Or Use Airflow (Scheduled)

```bash
# Access Airflow UI
open http://localhost:8080

# Trigger pipeline manually
docker-compose exec airflow-webserver airflow dags trigger cbi_pipeline

# Monitor execution
docker-compose logs -f airflow-scheduler
```

---

## 🗄️ Database Access

### Connect to Database

```bash
# Via psql
docker-compose exec db psql -U cbi_user -d climate_burden_index

# Example queries
\dt                          # List all tables
SELECT COUNT(*) FROM features;
SELECT * FROM vw_cluster_statistics;
```

### Backup Data

```bash
docker-compose exec db pg_dump -U cbi_user climate_burden_index > backup.sql
```

---

## 🧪 Run Tests

```bash
# All tests
docker-compose exec api pytest tests/ -v

# Specific test suite
docker-compose exec api pytest tests/test_etl.py -v

# With coverage
docker-compose exec api pytest tests/ --cov=src --cov-report=html
```

---

## 📝 Explore API Documentation

```bash
# Interactive API docs
open http://localhost:8000/docs

# Alternative format
open http://localhost:8000/redoc
```

---

## 🔧 Local Development (Without Docker)

### Setup Python Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure Database

```bash
# Install PostgreSQL with PostGIS
# macOS: brew install postgresql postgis
# Ubuntu: sudo apt-get install postgresql postgresql-contrib postgis
# Windows: Download from postgresql.org

# Create database
createdb -U postgres climate_burden_index
psql -U postgres climate_burden_index < sql/schema.sql

# Update .env with your database connection
cp .env.example .env
```

### Run Services Locally

```bash
# Terminal 1: API Server
uvicorn src.api.main:app --reload

# Terminal 2: Frontend
cd src/frontend && npm install && npm run dev

# Terminal 3: Airflow (optional)
airflow webserver
# Terminal 4:
airflow scheduler
```

---

## 📁 Project Structure

```
climate-exposure-system/
├── data/
│   ├── raw/          # Original datasets
│   ├── interim/      # Processed intermediate files
│   └── processed/    # Final features & predictions
├── src/
│   ├── etl/          # Data loading & cleaning
│   ├── features/     # Feature engineering
│   ├── ml/           # ML pipelines & models
│   └── api/          # FastAPI backend
├── sql/              # Database schema
├── dags/             # Airflow orchestration
├── tests/            # Pytest test suite
├── docker-compose.yml  # Multi-container setup
└── requirements.txt  # Python dependencies
```

---

## 🌍 Deploy to Cloud

### AWS (ECS + RDS)
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#aws-deployment-recommended)

### Google Cloud (Cloud Run + Cloud SQL)
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#google-cloud-deployment)

### Azure (App Service + Database)
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#azure-deployment)

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design & data flow |
| [API_DOCS.md](API_DOCS.md) | Endpoint specifications |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Feature definitions |
| [ML_CARD.md](ML_CARD.md) | Model performance & fairness |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Production deployment |

---

## 🐛 Troubleshooting

**API won't start?**
```bash
docker-compose logs api  # Check error
docker-compose down && docker-compose up --build  # Rebuild
```

**Database connection error?**
```bash
docker-compose exec db psql -U cbi_user -d climate_burden_index -c "SELECT 1;"
```

**Tests failing?**
```bash
# Reset test database
docker-compose exec db dropdb -U cbi_user climate_burden_index_test
docker-compose exec db createdb -U cbi_user climate_burden_index_test
docker-compose exec api pytest
```

---

## 💡 Next Steps

1. **Load your data** - Place files in `data/raw/` directories
2. **Run ETL** - Process data through pipelines
3. **Train models** - Fit clustering & prediction models
4. **Query API** - Use endpoints to explore results
5. **Customize** - Modify ML hyperparameters in `src/config.py`

---

## 📞 Support

- **API Docs:** http://localhost:8000/docs
- **Issues:** GitHub Issues
- **Questions:** [Contact](mailto:team@example.com)

---

**Version:** 1.0.0 | **Last Updated:** January 2025
