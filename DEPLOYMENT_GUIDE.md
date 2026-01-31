# Climate Burden Index - Deployment Guide

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Database Setup](#database-setup)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 14+ with PostGIS extension
- Node.js 18+
- Git
- 4GB RAM minimum (8GB recommended)

### Installation

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd climate-exposure-system
   ```

2. **Create Python Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize Database**
   ```bash
   psql -U postgres -d climate_burden_index -f sql/schema.sql
   ```

6. **Prepare Data**
   ```bash
   # Place data files in correct directories
   # See DATA_DIRECTORY_STRUCTURE.md for paths
   
   # Extract ZIP files if needed
   unzip data/raw/aqs/aqs_data.zip -d data/raw/aqs/
   unzip data/raw/tiger/*.zip -d data/raw/tiger/
   unzip data/raw/esg/esg_data.zip -d data/raw/esg/
   ```

7. **Run ETL Pipeline**
   ```bash
   # Run individual pipelines
   python -m src.etl.temperature_etl
   python -m src.etl.aqs_etl
   python -m src.etl.svi_etl
   python -m src.etl.tiger_etl
   python -m src.etl.esg_etl
   
   # Or run feature engineering (depends on all ETL)
   python -m src.features.feature_engineering
   ```

8. **Train ML Models**
   ```bash
   # Clustering
   python -m src.ml.clustering
   
   # Supervised Learning
   python -m src.ml.supervised
   ```

9. **Start API Server**
   ```bash
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
   API available at `http://localhost:8000`

10. **Setup Frontend (in new terminal)**
    ```bash
    cd src/frontend
    npm install
    npm run dev
    ```
    Frontend available at `http://localhost:3000`

---

## Docker Deployment

### Quick Start (All Services)

```bash
# Build and start all services
docker-compose up --build

# Run migrations
docker-compose exec db psql -U cbi_user -d climate_burden_index -f /docker-entrypoint-initdb.d/01-schema.sql

# Check service health
docker-compose ps
```

Services will be available at:
- **API:** http://localhost:8000
- **Frontend:** http://localhost:3000
- **Airflow:** http://localhost:8080
- **PostgreSQL:** localhost:5432

### Individual Service Management

```bash
# Start specific service
docker-compose up db api nginx

# Stop all services
docker-compose down

# View logs
docker-compose logs -f api

# Access PostgreSQL CLI
docker-compose exec db psql -U cbi_user -d climate_burden_index

# Run ETL in container
docker-compose exec api python -m src.etl.temperature_etl
```

### Volume Management

```bash
# List volumes
docker volume ls

# Clean up unused volumes
docker volume prune

# Backup PostgreSQL data
docker-compose exec db pg_dump -U cbi_user climate_burden_index > backup.sql

# Restore from backup
docker-compose exec db psql -U cbi_user climate_burden_index < backup.sql
```

---

## Production Deployment

### AWS Deployment (Recommended)

#### 1. RDS Database Setup

```bash
# Create RDS PostgreSQL with PostGIS
aws rds create-db-instance \
  --db-instance-identifier cbi-postgres \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 14.7 \
  --master-username cbi_admin \
  --master-user-password <secure-password> \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-xxxxxx \
  --publicly-accessible false

# Connect and enable PostGIS
psql -h cbi-postgres.xxxxx.rds.amazonaws.com -U cbi_admin -d postgres
CREATE EXTENSION postgis;
```

#### 2. ECS Deployment

```bash
# Create ECR repository
aws ecr create-repository --repository-name cbi-api

# Build and push image
docker build -t cbi-api .
docker tag cbi-api:latest <account-id>.dkr.ecr.<region>.amazonaws.com/cbi-api:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/cbi-api:latest

# Create ECS task definition (see ecs-task-definition.json)
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster cbi-cluster \
  --service-name cbi-api \
  --task-definition cbi-api:1 \
  --desired-count 3 \
  --launch-type FARGATE
```

#### 3. Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name cbi-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-zzzzz

# Create target group
aws elbv2 create-target-group \
  --name cbi-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx

# Register targets
aws elbv2 register-targets \
  --target-group-arn <target-group-arn> \
  --targets Id=i-xxxxx Id=i-yyyyy Id=i-zzzzz
```

#### 4. Auto Scaling

```bash
# Create Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name cbi-asg \
  --launch-configuration cbi-lc \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3 \
  --availability-zones us-east-1a us-east-1b

# Create scaling policy
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name cbi-asg \
  --policy-name scale-up \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration TargetValue=70
```

### Google Cloud Deployment

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/project-id/cbi-api

# Deploy to Cloud Run
gcloud run deploy cbi-api \
  --image gcr.io/project-id/cbi-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=<cloud-sql-url> \
  --memory 2Gi \
  --cpu 2

# Cloud SQL Database
gcloud sql instances create cbi-postgres \
  --database-version POSTGRES_14 \
  --tier db-n1-standard-1 \
  --region us-central1

# Enable PostGIS extension
gcloud sql databases create climate_burden_index --instance=cbi-postgres
```

### Azure Deployment

```bash
# Create resource group
az group create --name cbi-rg --location eastus

# Create PostgreSQL server
az postgres server create \
  --name cbi-postgres \
  --resource-group cbi-rg \
  --location eastus \
  --admin-user cbi_admin \
  --admin-password <secure-password>

# Deploy App Service
az appservice plan create \
  --name cbi-plan \
  --resource-group cbi-rg \
  --sku B2

az webapp create \
  --name cbi-api \
  --resource-group cbi-rg \
  --plan cbi-plan \
  --deployment-container-image-name-user <image-uri>
```

---

## Database Setup

### Initial Schema Creation

```bash
# From scratch
psql -U postgres
CREATE DATABASE climate_burden_index;
\c climate_burden_index
CREATE EXTENSION postgis;
\i sql/schema.sql
```

### Create API User

```sql
CREATE USER api_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE climate_burden_index TO api_user;
GRANT USAGE ON SCHEMA public TO api_user;

-- Grant specific permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO api_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO api_user;

-- For ETL operations (if same user)
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO api_user;
```

### Backup Strategy

```bash
# Daily full backup
pg_dump -h localhost -U cbi_user climate_burden_index > backup_$(date +%Y%m%d).sql

# Archive to S3
aws s3 cp backup_$(date +%Y%m%d).sql s3://cbi-backups/

# Automated backup (crontab)
0 2 * * * pg_dump -h localhost -U cbi_user climate_burden_index | gzip > /backups/cbi_$(date +\%Y\%m\%d).sql.gz
```

### Vacuum & Maintenance

```sql
-- Regular maintenance (weekly)
VACUUM ANALYZE;

-- Reindex tables (monthly)
REINDEX DATABASE climate_burden_index;

-- Check index health
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE tablename LIKE 'features%'
ORDER BY tablename, indexname;
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database connectivity
psql -h localhost -U cbi_user -d climate_burden_index -c "SELECT version();"

# Model files exist
ls -lh /models/
```

### Logging

```bash
# API logs
tail -f /var/log/cbi/api.log

# Database logs
tail -f /var/log/postgresql/postgresql.log

# Airflow logs
tail -f /opt/airflow/logs/
```

### Performance Monitoring

```bash
# Query performance
psql -c "EXPLAIN ANALYZE SELECT * FROM vw_tract_features LIMIT 10;"

# Index usage
SELECT * FROM pg_stat_user_indexes ORDER BY idx_blks_read DESC;

# Table size
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname = 'public' ORDER BY 3 DESC;
```

### Model Retraining

```bash
# Monthly retraining schedule (add to crontab)
0 3 1 * * cd /opt/cbi && python -m src.ml.clustering >> /var/log/cbi/retrain.log 2>&1
0 4 1 * * cd /opt/cbi && python -m src.ml.supervised >> /var/log/cbi/retrain.log 2>&1

# Validate model performance
python scripts/validate_model_performance.py
```

---

## Troubleshooting

### Common Issues

#### 1. PostGIS Extension Not Available

```sql
-- Check if installed
SELECT * FROM pg_extension WHERE extname = 'postgis';

-- If missing, install it
CREATE EXTENSION postgis;

-- Verify installation
SELECT PostGIS_version();
```

#### 2. Database Connection Refused

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify connection string in .env
psql -h localhost -U cbi_user -d climate_burden_index -c "SELECT 1;"

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql.log
```

#### 3. API 502 Bad Gateway (Docker)

```bash
# Check API service logs
docker-compose logs api

# Verify database connectivity from API container
docker-compose exec api python -c "
from src.config import DatabaseManager
db = DatabaseManager()
db.test_connection()
"
```

#### 4. Out of Memory

```bash
# Check resource usage
docker stats

# Increase Docker memory limit
# Edit docker-compose.yml:
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

#### 5. Slow Queries

```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1 second

-- View slow query log
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;

-- Create missing indices
CREATE INDEX idx_features_geoid ON features(geoid);
CREATE INDEX idx_predictions_geoid ON predictions(geoid);
CREATE INDEX idx_clusters_kmeans ON clusters(kmeans_cluster);
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug
uvicorn src.api.main:app --reload

# Enable SQL query logging
export SQLALCHEMY_ECHO=true

# Airflow debug
export AIRFLOW__CORE__LOAD_EXAMPLE_DAGS=True
airflow standalone
```

### Performance Optimization

```bash
# Increase connection pool size
# In config.py:
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 40

# Enable query result caching
REDIS_URL = "redis://localhost:6379/0"

# Batch API requests
# Send multiple GEOIDs in single request
curl -X POST http://localhost:8000/score/batch \
  -H "Content-Type: application/json" \
  -d '{"geoids": ["36061001001", "36061001002"]}'
```

---

**Last Updated:** January 2025  
**Maintainers:** Climate Burden Team
