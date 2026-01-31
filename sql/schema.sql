-- Climate Burden Index PostGIS Schema
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Census Tracts (TIGER/Line 2025)
CREATE TABLE IF NOT EXISTS census_tracts (
    geoid VARCHAR(11) PRIMARY KEY,
    statefp VARCHAR(2),
    countyfp VARCHAR(3),
    tractce VARCHAR(6),
    tract_name VARCHAR(255),
    aland BIGINT,
    awater BIGINT,
    geometry GEOMETRY(POLYGON, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tracts_geometry ON census_tracts USING GIST(geometry);
CREATE INDEX idx_tracts_state ON census_tracts(statefp);

-- Heat Exposure Data
CREATE TABLE IF NOT EXISTS heat_exposure (
    location_id VARCHAR(255) PRIMARY KEY,
    geoid VARCHAR(11),
    heat_annual_mean DECIMAL(10, 2),
    heat_days_above_90f INTEGER,
    heat_extreme_percentile_95 DECIMAL(10, 2),
    heat_annual_mean_normalized DECIMAL(5, 3),
    heat_days_above_90f_normalized DECIMAL(5, 3),
    heat_extreme_percentile_95_normalized DECIMAL(5, 3),
    record_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_heat_geoid ON heat_exposure(geoid);

-- Air Quality Data (EPA AQS)
CREATE TABLE IF NOT EXISTS aqs_metrics (
    location_id VARCHAR(255) PRIMARY KEY,
    geoid VARCHAR(11),
    pollutant VARCHAR(50),
    annual_mean_ppb DECIMAL(10, 3),
    percentile_95 DECIMAL(10, 3),
    high_days_above_threshold INTEGER,
    sample_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_aqs_geoid ON aqs_metrics(geoid);
CREATE INDEX idx_aqs_pollutant ON aqs_metrics(pollutant);

-- SVI (Social Vulnerability Index)
CREATE TABLE IF NOT EXISTS svi_indicators (
    geoid VARCHAR(11) PRIMARY KEY,
    svi_epl_pov DECIMAL(5, 3),
    svi_epl_unemp DECIMAL(5, 3),
    svi_epl_pci DECIMAL(5, 3),
    svi_epl_nohsdp DECIMAL(5, 3),
    svi_epl_age65 DECIMAL(5, 3),
    svi_epl_age17 DECIMAL(5, 3),
    svi_epl_disabl DECIMAL(5, 3),
    svi_epl_sngpnt DECIMAL(5, 3),
    svi_epl_minrty DECIMAL(5, 3),
    svi_epl_limeng DECIMAL(5, 3),
    svi_epl_munit DECIMAL(5, 3),
    svi_epl_mobile DECIMAL(5, 3),
    svi_epl_crowd DECIMAL(5, 3),
    svi_epl_noveh DECIMAL(5, 3),
    svi_epl_groupq DECIMAL(5, 3),
    svi_ep_socioec DECIMAL(5, 3),
    svi_ep_hshpd DECIMAL(5, 3),
    svi_ep_minrty DECIMAL(5, 3),
    svi_ep_houshtran DECIMAL(5, 3),
    svi_composite DECIMAL(5, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_svi_composite ON svi_indicators(svi_composite);

-- ESG Indicators (Environmental, Social, Governance)
CREATE TABLE IF NOT EXISTS esg_indicators (
    ticker VARCHAR(10),
    company VARCHAR(255),
    sector VARCHAR(100),
    esg_score DECIMAL(6, 2),
    e_score DECIMAL(6, 2),
    s_score DECIMAL(6, 2),
    g_score DECIMAL(6, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_esg_sector ON esg_indicators(sector);
CREATE INDEX idx_esg_score ON esg_indicators(esg_score);

-- Feature Vectors (merged/engineered)
CREATE TABLE IF NOT EXISTS features (
    geoid VARCHAR(11) PRIMARY KEY,
    heat_annual_mean DECIMAL(10, 2),
    heat_days_above_90f INTEGER,
    heat_extreme_percentile_95 DECIMAL(10, 2),
    pm25_mean DECIMAL(10, 3),
    pm25_95 DECIMAL(10, 3),
    ozone_mean DECIMAL(10, 3),
    ozone_high_days INTEGER,
    svi_composite DECIMAL(5, 3),
    climate_burden_score DECIMAL(5, 3),
    vulnerability_score DECIMAL(5, 3),
    climate_burden_index DECIMAL(10, 6),
    climate_burden_index_normalized DECIMAL(6, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_features_cbi ON features(climate_burden_index_normalized);

-- Cluster Assignments
CREATE TABLE IF NOT EXISTS clusters (
    geoid VARCHAR(11) PRIMARY KEY,
    hdbscan_cluster INTEGER,
    kmeans_cluster INTEGER,
    cluster_probability DECIMAL(5, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clusters_hdbscan ON clusters(hdbscan_cluster);
CREATE INDEX idx_clusters_kmeans ON clusters(kmeans_cluster);

-- Predictions (CBI scores per tract)
CREATE TABLE IF NOT EXISTS predictions (
    geoid VARCHAR(11) PRIMARY KEY,
    climate_burden_index DECIMAL(10, 6),
    climate_burden_index_normalized DECIMAL(6, 2),
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_predictions_cbi ON predictions(climate_burden_index_normalized);
CREATE INDEX idx_predictions_updated ON predictions(updated_at);

-- SHAP Explanations (feature importance per tract)
CREATE TABLE IF NOT EXISTS shap_explanations (
    id SERIAL PRIMARY KEY,
    geoid VARCHAR(11),
    feature_name VARCHAR(255),
    shap_value DECIMAL(10, 6),
    base_value DECIMAL(10, 6),
    feature_value DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shap_geoid ON shap_explanations(geoid);
CREATE INDEX idx_shap_feature ON shap_explanations(feature_name);

-- Data Quality Metrics
CREATE TABLE IF NOT EXISTS data_quality (
    metric_date DATE PRIMARY KEY,
    n_tracts_processed INTEGER,
    n_tracts_with_heat INTEGER,
    n_tracts_with_aqs INTEGER,
    n_tracts_with_svi INTEGER,
    missing_heat_percent DECIMAL(5, 2),
    missing_aqs_percent DECIMAL(5, 2),
    missing_svi_percent DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ETL Logs
CREATE TABLE IF NOT EXISTS etl_logs (
    id SERIAL PRIMARY KEY,
    pipeline VARCHAR(100),
    status VARCHAR(20),
    rows_processed INTEGER,
    rows_failed INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_etl_logs_pipeline ON etl_logs(pipeline);
CREATE INDEX idx_etl_logs_status ON etl_logs(status);
CREATE INDEX idx_etl_logs_date ON etl_logs(created_at);

-- Views

-- View: Tracts with all features
CREATE OR REPLACE VIEW vw_tract_features AS
SELECT 
    t.geoid,
    t.statefp,
    t.countyfp,
    t.tract_name,
    t.geometry,
    h.heat_annual_mean,
    h.heat_days_above_90f,
    a.pm25_mean,
    a.ozone_mean,
    s.svi_composite,
    f.climate_burden_score,
    f.vulnerability_score,
    p.climate_burden_index_normalized as cbi_normalized,
    c.kmeans_cluster,
    c.hdbscan_cluster
FROM census_tracts t
LEFT JOIN heat_exposure h ON t.geoid = h.geoid
LEFT JOIN aqs_metrics a ON t.geoid = a.geoid
LEFT JOIN svi_indicators s ON t.geoid = s.geoid
LEFT JOIN features f ON t.geoid = f.geoid
LEFT JOIN predictions p ON t.geoid = p.geoid
LEFT JOIN clusters c ON t.geoid = c.geoid;

-- View: Cluster statistics
CREATE OR REPLACE VIEW vw_cluster_statistics AS
SELECT 
    method,
    cluster_id,
    COUNT(*) as size,
    AVG(cbi_normalized) as avg_cbi,
    MIN(cbi_normalized) as min_cbi,
    MAX(cbi_normalized) as max_cbi,
    AVG(vulnerability_score) as avg_vulnerability,
    COUNT(DISTINCT statefp) as n_states
FROM (
    SELECT t.statefp, t.geoid, f.vulnerability_score, p.climate_burden_index_normalized as cbi_normalized, c.kmeans_cluster as cluster_id, 'kmeans' as method
    FROM census_tracts t
    LEFT JOIN features f ON t.geoid = f.geoid
    LEFT JOIN predictions p ON t.geoid = p.geoid
    LEFT JOIN clusters c ON t.geoid = c.geoid
    WHERE c.kmeans_cluster IS NOT NULL
    UNION ALL
    SELECT t.statefp, t.geoid, f.vulnerability_score, p.climate_burden_index_normalized as cbi_normalized, c.hdbscan_cluster as cluster_id, 'hdbscan' as method
    FROM census_tracts t
    LEFT JOIN features f ON t.geoid = f.geoid
    LEFT JOIN predictions p ON t.geoid = p.geoid
    LEFT JOIN clusters c ON t.geoid = c.geoid
    WHERE c.hdbscan_cluster IS NOT NULL
) clusters_combined
GROUP BY method, cluster_id;

-- Grant permissions (customize as needed)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO api_user;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA public TO api_user;
