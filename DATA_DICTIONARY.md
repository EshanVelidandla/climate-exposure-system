# Climate Burden Index - Data Dictionary

## Features Table (data/processed/features.parquet)

### Geographic Identifiers

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| geoid | string | 11 digits | Census tract GEOID (state + county + tract) |

### Heat Exposure Metrics

| Column | Type | Range | Unit | Description |
|--------|------|-------|------|-------------|
| heat_annual_mean | float | 30-95 | °F | Annual mean temperature |
| heat_days_above_90f | integer | 0-365 | days | Number of days exceeding 90°F per year |
| heat_extreme_percentile_95 | float | 40-105 | °F | 95th percentile temperature |
| heat_annual_mean_normalized | float | 0-1 | - | Normalized heat annual mean (0-1 scale) |
| heat_days_above_90f_normalized | float | 0-1 | - | Normalized heat days (0-1 scale) |
| heat_extreme_percentile_95_normalized | float | 0-1 | - | Normalized percentile (0-1 scale) |

**Source:** city_temperature.csv (NOAA)  
**Notes:** Higher values indicate greater heat exposure; normalized values allow comparison with other metrics

---

### Air Quality Metrics

#### PM2.5 (Fine Particulate Matter)

| Column | Type | Range | Unit | Description |
|--------|------|-------|------|-------------|
| pm25_mean | float | 0-50 | µg/m³ | Annual mean PM2.5 concentration |
| pm25_95 | float | 0-100 | µg/m³ | 95th percentile PM2.5 |

#### Ozone

| Column | Type | Range | Unit | Description |
|--------|------|-------|------|-------------|
| ozone_mean | float | 0-100 | ppb | Annual mean ozone concentration |
| ozone_high_days | integer | 0-150 | days | Days exceeding 70 ppb (NAAQS threshold) |

**Source:** EPA AQS (Air Quality System)  
**Notes:**
- EPA PM2.5 standard: 12 µg/m³ annual mean (primary)
- EPA ozone standard: 70 ppb (8-hour average)
- Higher concentrations linked to respiratory disease

---

### Socioeconomic Vulnerability Metrics

Normalized CDC Social Vulnerability Index (SVI) variables. Each variable represents a percentile (0-100) normalized to 0-1 scale.

#### Socioeconomic Status

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| svi_epl_pov | float | 0-1 | Poverty percentile |
| svi_epl_unemp | float | 0-1 | Unemployment percentile |
| svi_epl_pci | float | 0-1 | Per capita income percentile |
| svi_epl_nohsdp | float | 0-1 | No high school diploma percentile |

#### Household Composition & Disability

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| svi_epl_age65 | float | 0-1 | Age 65+ percentile |
| svi_epl_age17 | float | 0-1 | Age <17 percentile |
| svi_epl_disabl | float | 0-1 | Disability percentile |
| svi_epl_sngpnt | float | 0-1 | Single-parent household percentile |

#### Minority Status & Language

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| svi_epl_minrty | float | 0-1 | Minority status percentile |
| svi_epl_limeng | float | 0-1 | Limited English proficiency percentile |

#### Housing & Transportation

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| svi_epl_munit | float | 0-1 | Multi-unit housing percentile |
| svi_epl_mobile | float | 0-1 | Mobile home percentile |
| svi_epl_crowd | float | 0-1 | Crowded housing percentile |
| svi_epl_noveh | float | 0-1 | No vehicle access percentile |
| svi_epl_groupq | float | 0-1 | Group quarters percentile |

#### Theme Indices

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| svi_ep_socioec | float | 0-1 | Socioeconomic theme composite |
| svi_ep_hshpd | float | 0-1 | Household composition/disability composite |
| svi_ep_minrty | float | 0-1 | Minority/language composite |
| svi_ep_houshtran | float | 0-1 | Housing/transportation composite |
| svi_composite | float | 0-1 | Overall SVI (mean of all variables) |

**Source:** CDC SVI 2020  
**Notes:**
- Values 0.75-1.0 indicate high vulnerability
- Composite = mean of all 15 percentile variables
- Used in conjunction with climate metrics

---

### Composite Features

| Column | Type | Range | Description |
|--------|------|-------|-------------|
| climate_burden_score | float | 0-1 | Normalized composite of heat + PM2.5 + ozone |
| vulnerability_score | float | 0-1 | Normalized composite SVI |
| climate_burden_index | float | 0-1 | Climate Burden × Vulnerability (raw) |
| climate_burden_index_normalized | float | 0-100 | CBI rescaled to 0-100 for reporting |

**Calculation:**
```
climate_burden_score = mean(heat_normalized, pm25_normalized, ozone_normalized)
vulnerability_score = svi_composite
climate_burden_index = climate_burden_score × vulnerability_score
climate_burden_index_normalized = (CBI - min) / (max - min) × 100
```

---

## Clusters Table (data/processed/clusters.parquet)

| Column | Type | Description |
|--------|------|-------------|
| geoid | string | Census tract ID (11-digit) |
| hdbscan_cluster | integer | HDBSCAN cluster ID (-1 = noise) |
| kmeans_cluster | integer | K-Means cluster ID (0-4) |
| cluster_probability | float | HDBSCAN confidence (0-1) |

### K-Means Cluster Profiles

| Cluster | Name | Tracts | Avg CBI | Avg Vulnerability | Characteristics |
|---------|------|--------|---------|-------------------|-----------------|
| 0 | Low Burden | 15K | 35 | 0.35 | Rural, low hazards, stable |
| 1 | Moderate Burden | 12K | 55 | 0.55 | Mixed urban/rural, moderate exposure |
| 2 | High Burden | 10K | 68 | 0.70 | Urban, high pollution + heat |
| 3 | Extreme | 8K | 82 | 0.88 | Low-income, high hazards, vulnerable |
| 4 | Vulnerable Rural | 5K | 42 | 0.60 | Agricultural, economically challenged |

---

## Database Schema (PostgreSQL/PostGIS)

### census_tracts

Core geographic unit for all analyses.

```sql
CREATE TABLE census_tracts (
    geoid VARCHAR(11) PRIMARY KEY,
    statefp VARCHAR(2),           -- State FIPS code
    countyfp VARCHAR(3),          -- County FIPS code
    tractce VARCHAR(6),           -- Tract code
    tract_name VARCHAR(255),      -- Human-readable name
    aland BIGINT,                 -- Land area (sq meters)
    awater BIGINT,                -- Water area (sq meters)
    geometry GEOMETRY(POLYGON, 4326)  -- Tract boundary (WGS84)
);
```

### heat_exposure, aqs_metrics, svi_indicators, esg_indicators

Raw ETL outputs for each data source.

### features

Merged feature table:
```sql
CREATE TABLE features (
    geoid VARCHAR(11) PRIMARY KEY,
    heat_annual_mean DECIMAL(10, 2),
    ... (all climate + SVI fields)
    climate_burden_index_normalized DECIMAL(6, 2),
    created_at TIMESTAMP
);
```

### clusters

Cluster assignments from both methods:
```sql
CREATE TABLE clusters (
    geoid VARCHAR(11) PRIMARY KEY,
    hdbscan_cluster INTEGER,
    kmeans_cluster INTEGER,
    cluster_probability DECIMAL(5, 3)
);
```

### predictions

CBI predictions per tract:
```sql
CREATE TABLE predictions (
    geoid VARCHAR(11) PRIMARY KEY,
    climate_burden_index DECIMAL(10, 6),
    climate_burden_index_normalized DECIMAL(6, 2),
    model_version VARCHAR(50),
    predicted_at TIMESTAMP
);
```

### shap_explanations

Feature importance for model interpretability:
```sql
CREATE TABLE shap_explanations (
    id SERIAL PRIMARY KEY,
    geoid VARCHAR(11),
    feature_name VARCHAR(255),
    shap_value DECIMAL(10, 6),    -- SHAP impact on prediction
    base_value DECIMAL(10, 6),    -- Model base prediction
    feature_value DECIMAL(10, 6)  -- Feature value for this tract
);
```

---

## Views

### vw_tract_features

Single table with all tract information:
```sql
SELECT 
    t.geoid,
    t.statefp,
    t.tract_name,
    t.geometry,
    h.heat_annual_mean,
    a.pm25_mean,
    s.svi_composite,
    p.climate_burden_index_normalized,
    c.kmeans_cluster
FROM census_tracts t
LEFT JOIN heat_exposure h ON t.geoid = h.geoid
LEFT JOIN aqs_metrics a ON t.geoid = a.geoid
LEFT JOIN svi_indicators s ON t.geoid = s.geoid
LEFT JOIN predictions p ON t.geoid = p.geoid
LEFT JOIN clusters c ON t.geoid = c.geoid;
```

---

## Data Quality Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Census tracts covered | 72K | 72K |
| Tracts with heat data | >90% | ~95% |
| Tracts with AQS data | >80% | ~88% |
| Tracts with SVI data | 100% | 100% |
| Missing values (after imputation) | <1% | 0.2% |
| GEOID uniqueness | 100% | 100% |

---

## Units & Conventions

| Quantity | Unit | Notes |
|----------|------|-------|
| Temperature | °F | Converted from Celsius in ETL |
| Concentration | µg/m³ (PM2.5), ppb (ozone) | EPA standard units |
| Percentiles | 0-1 (normalized) | Original 0-100, divided by 100 |
| CBI Score | 0-100 | Rescaled from 0-1 for reporting |
| Latitude/Longitude | decimal degrees | WGS84 (EPSG:4326) |
| Area | square meters | TIGER/Line convention |

---

## Handling Missing Data

| Field | Imputation | Notes |
|-------|-----------|-------|
| Heat metrics | Tract-level median | Group by state if needed |
| AQS metrics | Nearest neighbor (5km buffer) | EPA stations sparse in rural areas |
| SVI variables | Tract-level median | Very rare |
| Geometry | Removed | Tracts without geometry dropped |

---

## Data Lineage

```
Heat: city_temperature.csv → temperature_etl → heat_exposure.parquet
AQS:  epa_aqs/*.zip → aqs_etl → aqs_metrics.parquet
SVI:  svi/*.csv → svi_etl → svi_normalized.parquet
TIGER: tiger/*.zip → tiger_etl → tiger_tracts.parquet
ESG:  esg/*.zip → esg_etl → esg_indicators.parquet

Combined: feature_engineering → features.parquet
ML: features.parquet → clustering → clusters.parquet
ML: features.parquet → supervised → predictions + shap_explns

Final: Load → PostgreSQL (all tables)
```

---

**Last Updated:** January 2025  
**Version:** 1.0.0
