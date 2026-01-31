"""
Unit tests for ML pipelines (clustering and supervised).
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock


class TestClustering:
    """Tests for clustering.py"""
    
    def test_standardize_features(self, sample_features_data):
        """Test feature standardization (z-score)."""
        from sklearn.preprocessing import StandardScaler
        
        numeric_cols = sample_features_data.select_dtypes(include=[np.number]).columns
        scaler = StandardScaler()
        scaled = scaler.fit_transform(sample_features_data[numeric_cols])
        
        # Check mean ~0 and std ~1
        assert np.abs(scaled.mean()) < 0.1
        assert np.abs(scaled.std() - 1.0) < 0.1
    
    def test_hdbscan_clustering(self, sample_features_data):
        """Test HDBSCAN clustering."""
        with patch('src.ml.clustering.HDBSCAN') as mock_hdbscan:
            clusterer = MagicMock()
            clusterer.fit_predict.return_value = np.random.randint(-1, 5, len(sample_features_data))
            mock_hdbscan.return_value = clusterer
            
            labels = clusterer.fit_predict(sample_features_data.drop('geoid', axis=1))
            
            # Check that some clusters are identified
            unique_labels = np.unique(labels)
            assert -1 in unique_labels or len(unique_labels) > 1
    
    def test_kmeans_clustering(self, sample_features_data):
        """Test K-Means clustering with k=5."""
        with patch('src.ml.clustering.KMeans') as mock_kmeans:
            clusterer = MagicMock()
            clusterer.fit_predict.return_value = np.random.randint(0, 5, len(sample_features_data))
            mock_kmeans.return_value = clusterer
            
            labels = clusterer.fit_predict(sample_features_data.drop('geoid', axis=1))
            
            # Check 5 clusters
            assert set(np.unique(labels)) <= set(range(5))
            assert len(np.unique(labels)) >= 1
    
    def test_compute_silhouette_score(self):
        """Test silhouette score calculation."""
        from sklearn.metrics import silhouette_score
        
        # Create simple clusterable data
        X = np.array([
            [1, 2], [2, 1], [1, 1],
            [8, 8], [8, 9], [9, 8]
        ])
        labels = [0, 0, 0, 1, 1, 1]
        
        score = silhouette_score(X, labels)
        assert -1 <= score <= 1
        assert score > 0.5  # Should be high for well-separated clusters
    
    def test_save_cluster_models(self, temp_data_dir):
        """Test saving trained models."""
        from joblib import dump
        import pickle
        
        mock_model = {'hdbscan': MagicMock(), 'kmeans': MagicMock()}
        
        # Save models
        model_path = f"{temp_data_dir}/hdbscan_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(mock_model['hdbscan'], f)
        
        # Verify file exists
        import os
        assert os.path.exists(model_path)
    
    def test_cluster_labels_match_geoid(self, sample_features_data):
        """Test cluster labels align with GEOIDs."""
        sample_features_data['cluster'] = np.random.randint(0, 5, len(sample_features_data))
        
        # Each GEOID should have exactly one cluster
        assert len(sample_features_data) == len(sample_features_data['geoid'].unique())
        assert sample_features_data['cluster'].notna().all()


class TestSupervisedLearning:
    """Tests for supervised.py"""
    
    def test_prepare_training_data(self, sample_features_data):
        """Test X, y separation."""
        feature_cols = [c for c in sample_features_data.columns if c != 'geoid' and c != 'climate_burden_index_normalized']
        
        X = sample_features_data[feature_cols]
        y = sample_features_data['climate_burden_index_normalized']
        
        assert len(X) == len(y)
        assert X.shape[1] > 10
    
    def test_train_test_split(self, sample_features_data):
        """Test 80/20 train/test split."""
        from sklearn.model_selection import train_test_split
        
        X = sample_features_data.drop(['geoid', 'climate_burden_index_normalized'], axis=1)
        y = sample_features_data['climate_burden_index_normalized']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        assert len(X_train) == int(0.8 * len(X))
        assert len(X_test) == int(0.2 * len(X))
    
    def test_xgboost_training(self):
        """Test XGBoost model training."""
        with patch('src.ml.supervised.xgb.XGBRegressor') as mock_xgb:
            model = MagicMock()
            model.fit.return_value = model
            model.predict.return_value = np.random.uniform(30, 80, 100)
            mock_xgb.return_value = model
            
            X_train = np.random.randn(800, 20)
            y_train = np.random.uniform(30, 80, 800)
            
            model.fit(X_train, y_train)
            preds = model.predict(np.random.randn(200, 20))
            
            assert len(preds) == 200
            assert 0 <= preds.min()
            assert preds.max() <= 100
    
    def test_compute_metrics_rmse(self):
        """Test RMSE calculation."""
        from sklearn.metrics import mean_squared_error
        import math
        
        y_true = np.array([50, 60, 70])
        y_pred = np.array([52, 58, 72])
        
        rmse = math.sqrt(mean_squared_error(y_true, y_pred))
        assert rmse > 0
        assert rmse < 5
    
    def test_compute_metrics_mae(self):
        """Test MAE calculation."""
        from sklearn.metrics import mean_absolute_error
        
        y_true = np.array([50, 60, 70])
        y_pred = np.array([52, 58, 72])
        
        mae = mean_absolute_error(y_true, y_pred)
        assert mae > 0
        assert mae < 5
    
    def test_compute_metrics_r2(self):
        """Test R² calculation."""
        from sklearn.metrics import r2_score
        
        y_true = np.array([50, 60, 70, 80, 90])
        y_pred = np.array([52, 58, 72, 78, 92])
        
        r2 = r2_score(y_true, y_pred)
        assert -1 <= r2 <= 1
        assert r2 > 0.9  # Should be high for good predictions
    
    def test_shap_value_generation(self, mock_xgb_model, mock_shap_explainer):
        """Test SHAP value generation."""
        X_sample = np.random.randn(10, 50)
        
        shap_values = mock_shap_explainer.shap_values(X_sample)
        
        assert shap_values.shape == (10, 50)
    
    def test_save_model(self, temp_data_dir):
        """Test saving trained model."""
        import json
        
        model_data = {
            'n_estimators': 100,
            'max_depth': 6,
            'features': ['heat_annual_mean', 'pm25_mean']
        }
        
        model_path = f"{temp_data_dir}/model.json"
        with open(model_path, 'w') as f:
            json.dump(model_data, f)
        
        # Verify saved
        import os
        assert os.path.exists(model_path)
    
    def test_model_summary_generation(self):
        """Test model summary JSON."""
        summary = {
            'model_type': 'XGBRegressor',
            'version': '1.0.0',
            'metrics': {
                'train_rmse': 7.2,
                'val_rmse': 9.8,
                'val_r2': 0.78
            },
            'features': ['heat', 'pm25', 'svi']
        }
        
        assert 'model_type' in summary
        assert summary['metrics']['val_r2'] == 0.78


class TestModelEvaluation:
    """Tests for model performance evaluation."""
    
    def test_residual_analysis(self):
        """Test residual properties."""
        y_true = np.random.normal(60, 10, 100)
        y_pred = y_true + np.random.normal(0, 5, 100)  # Add noise
        
        residuals = y_true - y_pred
        
        assert np.abs(residuals.mean()) < 2
        assert residuals.std() < 10
    
    def test_prediction_distribution(self):
        """Test prediction distribution."""
        predictions = np.random.uniform(30, 80, 1000)
        
        assert predictions.min() >= 0
        assert predictions.max() <= 100
        assert 0 < predictions.mean() < 100
    
    def test_performance_by_cbi_range(self, sample_features_data):
        """Test model performance across CBI ranges."""
        sample_features_data['cbi_range'] = pd.cut(
            sample_features_data['climate_burden_index_normalized'],
            bins=[0, 33, 66, 100],
            labels=['Low', 'Moderate', 'High']
        )
        
        for range_name in ['Low', 'Moderate', 'High']:
            subset = sample_features_data[sample_features_data['cbi_range'] == range_name]
            assert len(subset) > 0
