"""
Pytest configuration and shared fixtures for Climate Burden Index testing.
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
from unittest.mock import MagicMock, patch
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_temperature_data():
    """Create sample temperature dataset."""
    return pd.DataFrame({
        'date': pd.date_range('2020-01-01', periods=365),
        'city': ['New York'] * 365,
        'year': [2020] * 365,
        'avg_temp': np.random.uniform(30, 85, 365),
        'state': ['NY'] * 365,
        'country': ['US'] * 365,
    })


@pytest.fixture
def sample_aqs_data():
    """Create sample EPA AQS data."""
    return pd.DataFrame({
        'state_code': ['36'] * 100,
        'county_code': ['061'] * 100,
        'site_number': ['0001'] * 100,
        'parameter_name': ['PM2.5'] * 100,
        'arithmetic_mean': np.random.uniform(5, 30, 100),
        'units_of_measure': ['Micrograms/cubic meter (LC)'] * 100,
    })


@pytest.fixture
def sample_svi_data():
    """Create sample SVI dataset."""
    return pd.DataFrame({
        'GEOID': ['36061001001', '36061001002', '36061001003'],
        'ST': ['36', '36', '36'],
        'COUNTY': ['061', '061', '061'],
        'TRACT': ['0001', '0002', '0003'],
        'E_TOTPOP': [3000, 2500, 4000],
        'M_TOTPOP': [100, 80, 120],
        'E_POV': [450, 375, 600],  # Poverty estimate
        'M_POV': [45, 38, 60],
        'E_UNEMP': [150, 125, 200],  # Unemployment
        'M_UNEMP': [15, 12, 20],
        'E_PCI': [35000, 40000, 30000],  # Per capita income
        'M_PCI': [3500, 4000, 3000],
        'E_NOHSDP': [600, 500, 800],  # No high school diploma
        'M_NOHSDP': [60, 50, 80],
    })


@pytest.fixture
def sample_tiger_data():
    """Create sample TIGER/Line GeoDataFrame."""
    try:
        import geopandas as gpd
        from shapely.geometry import Polygon
        
        geoms = [
            Polygon([(-74.0, 40.7), (-74.0, 40.75), (-73.95, 40.75), (-73.95, 40.7)]),
            Polygon([(-74.0, 40.75), (-74.0, 40.8), (-73.95, 40.8), (-73.95, 40.75)]),
            Polygon([(-74.0, 40.8), (-74.0, 40.85), (-73.95, 40.85), (-73.95, 40.8)]),
        ]
        
        return gpd.GeoDataFrame({
            'GEOID': ['36061001001', '36061001002', '36061001003'],
            'STATEFP': ['36', '36', '36'],
            'COUNTYFP': ['061', '061', '061'],
            'TRACTCE': ['0001', '0002', '0003'],
            'ALAND': [1000000, 1100000, 950000],
            'AWATER': [10000, 15000, 8000],
            'geometry': geoms
        }, crs='EPSG:4326')
    except ImportError:
        pytest.skip("GeoPandas not available")


@pytest.fixture
def sample_features_data():
    """Create complete features dataset."""
    np.random.seed(42)
    n_samples = 1000
    
    return pd.DataFrame({
        'geoid': [f'36061{i:06d}' for i in range(n_samples)],
        # Heat metrics
        'heat_annual_mean': np.random.uniform(45, 75, n_samples),
        'heat_days_above_90f': np.random.uniform(0, 200, n_samples),
        'heat_extreme_percentile_95': np.random.uniform(60, 95, n_samples),
        'heat_annual_mean_normalized': np.random.uniform(0, 1, n_samples),
        'heat_days_above_90f_normalized': np.random.uniform(0, 1, n_samples),
        'heat_extreme_percentile_95_normalized': np.random.uniform(0, 1, n_samples),
        # AQS metrics
        'pm25_mean': np.random.uniform(5, 35, n_samples),
        'pm25_95': np.random.uniform(10, 50, n_samples),
        'ozone_mean': np.random.uniform(30, 80, n_samples),
        'ozone_high_days': np.random.uniform(0, 100, n_samples),
        # SVI metrics
        'svi_composite': np.random.uniform(0, 1, n_samples),
        'svi_epl_pov': np.random.uniform(0, 1, n_samples),
        'svi_epl_unemp': np.random.uniform(0, 1, n_samples),
        'svi_epl_nohsdp': np.random.uniform(0, 1, n_samples),
        'svi_epl_minrty': np.random.uniform(0, 1, n_samples),
        # Composites
        'climate_burden_score': np.random.uniform(0, 1, n_samples),
        'vulnerability_score': np.random.uniform(0, 1, n_samples),
        'climate_burden_index': np.random.uniform(0, 1, n_samples),
        'climate_burden_index_normalized': np.random.uniform(0, 100, n_samples),
    })


@pytest.fixture
def mock_db_connection():
    """Create mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock query results
    mock_cursor.fetchone.return_value = ('36061001001',)  # GEOID
    mock_cursor.fetchall.return_value = [
        (0.5, 0.6, 0.7),  # climate, vulnerability, cbi
    ]
    
    return mock_conn


@pytest.fixture
def mock_xgb_model():
    """Create mock XGBoost model."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.random.uniform(30, 80, 100)
    return mock_model


@pytest.fixture
def mock_shap_explainer():
    """Create mock SHAP explainer."""
    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = np.random.uniform(-5, 5, (100, 50))
    return mock_explainer


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    from unittest.mock import MagicMock
    
    config = MagicMock()
    config.DATA_RAW_HEAT = '/tmp/heat/'
    config.DATA_INTERIM_HEAT = '/tmp/heat_interim.parquet'
    config.DB_CONNECTION_STRING = 'postgresql://user:pass@localhost/cbi'
    config.XGB_MODEL_PATH = '/tmp/cbi_xgb.json'
    config.SHAP_EXPLAINER_PATH = '/tmp/shap_explainer.pkl'
    
    return config
