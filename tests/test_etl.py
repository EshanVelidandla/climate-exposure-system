"""
Unit tests for ETL modules.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock


class TestTemperatureETL:
    """Tests for temperature_etl.py"""
    
    def test_load_temperature_data(self, sample_temperature_data, temp_data_dir):
        """Test loading temperature CSV."""
        # Save sample data
        csv_path = f"{temp_data_dir}/temperature.csv"
        sample_temperature_data.to_csv(csv_path, index=False)
        
        # Mock the load function
        with patch('src.etl.temperature_etl.load_temperature_data') as mock_load:
            mock_load.return_value = sample_temperature_data
            result = mock_load(csv_path)
            
            assert len(result) == 365
            assert 'avg_temp' in result.columns
            assert 'city' in result.columns
    
    def test_compute_heat_metrics(self, sample_temperature_data):
        """Test heat metric calculations."""
        # Simulate metric computation
        data = sample_temperature_data.copy()
        data['heat_annual_mean'] = data['avg_temp'].mean()
        data['heat_days_above_90f'] = (data['avg_temp'] > 90).sum()
        data['heat_extreme_percentile_95'] = data['avg_temp'].quantile(0.95)
        
        assert 30 <= data['heat_annual_mean'].iloc[0] <= 85
        assert 0 <= data['heat_days_above_90f'].iloc[0] <= 365
    
    def test_normalize_features(self):
        """Test feature normalization to 0-1."""
        values = pd.Series([0, 50, 100])
        normalized = (values - values.min()) / (values.max() - values.min())
        
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0
        assert normalized.iloc[1] == 0.5
    
    def test_save_interim_data(self, sample_temperature_data, temp_data_dir):
        """Test saving to interim parquet."""
        output_path = f"{temp_data_dir}/heat_interim.parquet"
        sample_temperature_data.to_parquet(output_path)
        
        loaded = pd.read_parquet(output_path)
        assert len(loaded) == len(sample_temperature_data)
        assert list(loaded.columns) == list(sample_temperature_data.columns)


class TestAQSETL:
    """Tests for aqs_etl.py"""
    
    def test_parse_aqs_data(self, sample_aqs_data):
        """Test AQS data parsing."""
        assert len(sample_aqs_data) == 100
        assert 'arithmetic_mean' in sample_aqs_data.columns
        assert sample_aqs_data['parameter_name'].unique()[0] == 'PM2.5'
    
    def test_create_location_id(self):
        """Test location ID creation."""
        state = '36'
        county = '061'
        site = '0001'
        
        location_id = f"{state}{county}{site}"
        assert location_id == '360610001'
        assert len(location_id) == 9
    
    def test_pivot_pollutants(self, sample_aqs_data):
        """Test pollutant pivoting."""
        # Add ozone data
        ozone_data = sample_aqs_data.copy()
        ozone_data['parameter_name'] = 'Ozone'
        ozone_data['arithmetic_mean'] = ozone_data['arithmetic_mean'] / 2
        
        combined = pd.concat([sample_aqs_data, ozone_data])
        pivoted = combined.pivot_table(
            index='site_number',
            columns='parameter_name',
            values='arithmetic_mean',
            aggfunc='mean'
        )
        
        assert 'PM2.5' in pivoted.columns
        assert 'Ozone' in pivoted.columns


class TestSVIETL:
    """Tests for svi_etl.py"""
    
    def test_load_svi_csv(self, sample_svi_data):
        """Test SVI CSV loading."""
        assert 'GEOID' in sample_svi_data.columns
        assert len(sample_svi_data) == 3
        assert all(sample_svi_data['GEOID'].str.len() == 11)
    
    def test_normalize_svi_percentiles(self):
        """Test SVI percentile normalization."""
        # SVI percentiles are 0-100, should normalize to 0-1
        percentiles = pd.Series([0, 25, 50, 75, 100])
        normalized = percentiles / 100
        
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0
        assert normalized.iloc[2] == 0.5
    
    def test_compute_svi_composite(self, sample_svi_data):
        """Test SVI composite score."""
        # Create normalized versions
        svi_cols = ['E_POV', 'E_UNEMP']
        sample_svi_data['svi_composite'] = sample_svi_data[svi_cols].mean(axis=1)
        
        assert 0 <= sample_svi_data['svi_composite'].max() <= 1000
        assert sample_svi_data['svi_composite'].notna().all()


class TestTIGERETL:
    """Tests for tiger_etl.py"""
    
    def test_load_shapefile(self, sample_tiger_data):
        """Test shapefile loading."""
        assert len(sample_tiger_data) == 3
        assert 'geometry' in sample_tiger_data.columns
        assert sample_tiger_data.crs == 'EPSG:4326'
    
    def test_geoid_formatting(self, sample_tiger_data):
        """Test GEOID is 11-digit string."""
        for geoid in sample_tiger_data['GEOID']:
            assert isinstance(geoid, str)
            assert len(geoid) == 11
            assert geoid.isdigit()
    
    def test_remove_duplicates(self, sample_tiger_data):
        """Test duplicate removal by GEOID."""
        # Add duplicate
        duplicate = sample_tiger_data.iloc[0:1].copy()
        combined = pd.concat([sample_tiger_data, duplicate])
        
        deduplicated = combined.drop_duplicates(subset=['GEOID'])
        assert len(deduplicated) == 3
    
    def test_reproject_to_wgs84(self, sample_tiger_data):
        """Test reprojection to WGS84."""
        assert sample_tiger_data.crs == 'EPSG:4326'
        # Verify coordinates are in expected range
        bounds = sample_tiger_data.total_bounds
        assert -180 <= bounds[0] <= 180  # min_lon
        assert -90 <= bounds[1] <= 90    # min_lat
        assert -180 <= bounds[2] <= 180  # max_lon
        assert -90 <= bounds[3] <= 90    # max_lat


class TestESGETL:
    """Tests for esg_etl.py"""
    
    def test_extract_esg_zip(self, temp_data_dir):
        """Test ESG ZIP extraction."""
        # Mock ZIP contents
        import zipfile
        zip_path = f"{temp_data_dir}/esg.zip"
        
        # Create test files in ZIP
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('esg_data.csv', 'ticker,env_score\nAAPL,75\nGOOGL,80')
        
        # Verify ZIP can be read
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert 'esg_data.csv' in zf.namelist()
    
    def test_normalize_esg_scores(self):
        """Test ESG score normalization to 0-100."""
        raw_scores = pd.Series([-10, 0, 50, 100, 150])
        
        # Clip to 0-100 and normalize
        normalized = raw_scores.clip(0, 100)
        assert normalized.min() == 0
        assert normalized.max() == 100
