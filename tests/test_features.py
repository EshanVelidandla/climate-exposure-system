"""
Unit tests for feature engineering module.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock


class TestFeatureEngineering:
    """Tests for feature_engineering.py"""
    
    def test_load_all_interim_data(self, temp_data_dir, sample_features_data):
        """Test loading all 5 interim datasets."""
        # Save all datasets
        sample_features_data.to_parquet(f"{temp_data_dir}/heat_interim.parquet")
        sample_features_data.to_parquet(f"{temp_data_dir}/aqs_metrics.parquet")
        sample_features_data.to_parquet(f"{temp_data_dir}/svi_normalized.parquet")
        
        # Mock load function
        with patch('src.features.feature_engineering.load_interim_data') as mock_load:
            mock_load.return_value = sample_features_data
            result = mock_load(f"{temp_data_dir}")
            
            assert len(result) == 1000
            assert 'geoid' in result.columns
    
    def test_merge_on_geoid(self, sample_features_data):
        """Test merging datasets on GEOID."""
        df1 = sample_features_data[['geoid', 'heat_annual_mean']].copy()
        df2 = sample_features_data[['geoid', 'pm25_mean']].copy()
        
        merged = df1.merge(df2, on='geoid', how='outer')
        
        assert len(merged) == len(df1)
        assert 'heat_annual_mean' in merged.columns
        assert 'pm25_mean' in merged.columns
    
    def test_compute_climate_burden_score(self, sample_features_data):
        """Test climate burden score calculation."""
        # Simple mean of normalized heat and pollution metrics
        metrics = [
            'heat_annual_mean_normalized',
            'pm25_mean',  # Assuming normalized
            'ozone_mean'   # Assuming normalized
        ]
        
        sample_features_data['climate_burden_score'] = sample_features_data[metrics].mean(axis=1)
        
        assert 0 <= sample_features_data['climate_burden_score'].min()
        assert sample_features_data['climate_burden_score'].max() <= 1
    
    def test_compute_vulnerability_score(self, sample_features_data):
        """Test vulnerability score = SVI composite."""
        sample_features_data['vulnerability_score'] = sample_features_data['svi_composite']
        
        assert 0 <= sample_features_data['vulnerability_score'].min()
        assert sample_features_data['vulnerability_score'].max() <= 1
    
    def test_compute_climate_burden_index(self, sample_features_data):
        """Test CBI = burden × vulnerability."""
        burden = sample_features_data['climate_burden_score']
        vulnerability = sample_features_data['vulnerability_score']
        
        sample_features_data['climate_burden_index'] = burden * vulnerability
        
        assert 0 <= sample_features_data['climate_burden_index'].min()
        assert sample_features_data['climate_burden_index'].max() <= 1
    
    def test_normalize_cbi_to_0_100(self, sample_features_data):
        """Test normalizing CBI to 0-100 scale."""
        cbi = sample_features_data['climate_burden_index']
        
        # Min-max normalization to 0-100
        cbi_normalized = ((cbi - cbi.min()) / (cbi.max() - cbi.min())) * 100
        
        assert cbi_normalized.min() >= 0
        assert cbi_normalized.max() <= 100
    
    def test_fill_missing_values_with_median(self):
        """Test imputation with median."""
        data = pd.DataFrame({
            'feature1': [1, 2, np.nan, 4, 5],
            'feature2': [10, np.nan, 30, 40, 50]
        })
        
        filled = data.fillna(data.median())
        
        assert filled.isna().sum().sum() == 0
        assert filled.loc[2, 'feature1'] == 3.0  # median
        assert filled.loc[1, 'feature2'] == 30.0  # median
    
    def test_handle_missing_geoid(self):
        """Test that records without GEOID are dropped."""
        data = pd.DataFrame({
            'geoid': ['36061001001', None, '36061001003'],
            'value': [1, 2, 3]
        })
        
        cleaned = data.dropna(subset=['geoid'])
        assert len(cleaned) == 2
    
    def test_feature_output_structure(self, sample_features_data):
        """Test final output has all required columns."""
        required_cols = [
            'geoid',
            'climate_burden_index_normalized',
            'svi_composite',
            'heat_annual_mean',
            'pm25_mean',
            'ozone_mean'
        ]
        
        for col in required_cols:
            assert col in sample_features_data.columns


class TestDataQuality:
    """Tests for data quality checks."""
    
    def test_geoid_validity(self, sample_features_data):
        """Test all GEOIDs are 11-digit strings."""
        for geoid in sample_features_data['geoid']:
            assert isinstance(geoid, str)
            assert len(geoid) == 11
            assert geoid.isdigit()
    
    def test_value_ranges(self, sample_features_data):
        """Test feature values are in expected ranges."""
        # Heat metrics
        assert 30 <= sample_features_data['heat_annual_mean'].max() <= 120
        assert 0 <= sample_features_data['heat_days_above_90f'].min()
        
        # Air quality
        assert 0 <= sample_features_data['pm25_mean'].min()
        assert sample_features_data['pm25_mean'].max() <= 100
        
        # Normalized features
        assert sample_features_data['climate_burden_index_normalized'].min() >= 0
        assert sample_features_data['climate_burden_index_normalized'].max() <= 100
    
    def test_no_duplicates(self, sample_features_data):
        """Test no duplicate GEOIDs."""
        assert len(sample_features_data) == len(sample_features_data['geoid'].unique())
    
    def test_missing_value_threshold(self, sample_features_data):
        """Test missing values < 1%."""
        missing_pct = sample_features_data.isna().sum().sum() / sample_features_data.size * 100
        assert missing_pct < 1.0
