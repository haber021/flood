"""Advanced Machine Learning Algorithms for Flood Prediction

This module contains implementations of various machine learning algorithms for enhancing
flood prediction accuracy, including ensemble methods, neural networks, time series analysis,
and spatial analysis techniques.
"""

import numpy as np
import pandas as pd
import joblib
import os
import logging
from datetime import datetime, timedelta

# Scikit-learn imports
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import mean_squared_error, classification_report
from sklearn.model_selection import train_test_split, GridSearchCV

# Time series imports
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Neural network imports (if tensorflow is installed)
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, LSTM, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

# Constants
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/models')


class GradientBoostingFloodPredictor:
    """Gradient Boosting Machine for flood prediction
    
    This model uses gradient boosting to classify flood risk using multiple features
    including rainfall, water level, and soil saturation.
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.01, 0.1, 0.2],
            'max_depth': [3, 4, 5],
            'min_samples_split': [2, 5, 10],
            'subsample': [0.8, 0.9, 1.0]
        }
        
    def train(self, X, y):
        """Train the gradient boosting model with hyperparameter tuning"""
        logger.info("Training gradient boosting model with grid search...")
        X_scaled = self.scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        # Use GridSearchCV for hyperparameter tuning
        grid_search = GridSearchCV(GradientBoostingClassifier(), 
                                  self.param_grid, 
                                  cv=5, 
                                  scoring='f1',
                                  n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        # Get the best model
        self.model = grid_search.best_estimator_
        logger.info(f"Best parameters found: {grid_search.best_params_}")
        
        # Evaluate the model
        y_pred = self.model.predict(X_test)
        logger.info("\nGradient Boosting model evaluation:")
        logger.info(classification_report(y_test, y_pred))
        
        return self
    
    def predict(self, features):
        """Make flood predictions using the trained model"""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Make prediction
        prediction = self.model.predict(features_scaled)
        probability = self.model.predict_proba(features_scaled)[:, 1]  # Probability of positive class
        
        return prediction, probability
    
    def save(self, filename='gbm_flood_model.joblib'):
        """Save the model to disk"""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
            
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
            
        model_path = os.path.join(MODEL_DIR, filename)
        scaler_path = os.path.join(MODEL_DIR, 'gbm_scaler.joblib')
        
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"Model saved to {model_path}")
        
        return model_path
    
    def load(self, filename='gbm_flood_model.joblib'):
        """Load the model from disk"""
        model_path = os.path.join(MODEL_DIR, filename)
        scaler_path = os.path.join(MODEL_DIR, 'gbm_scaler.joblib')
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Model or scaler file not found at {model_path}")
            
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        logger.info(f"Model loaded from {model_path}")
        
        return self


class SVMFloodPredictor:
    """Support Vector Machine for flood classification
    
    This model uses SVM for binary classification of flood events.
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.param_grid = {
            'C': [0.1, 1, 10, 100],
            'gamma': ['scale', 'auto', 0.1, 0.01],
            'kernel': ['rbf', 'poly', 'sigmoid']
        }
        
    def train(self, X, y):
        """Train the SVM model with hyperparameter tuning"""
        logger.info("Training SVM model with grid search...")
        X_scaled = self.scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        # Use GridSearchCV for hyperparameter tuning
        grid_search = GridSearchCV(SVC(probability=True), 
                                  self.param_grid, 
                                  cv=5, 
                                  scoring='f1',
                                  n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        # Get the best model
        self.model = grid_search.best_estimator_
        logger.info(f"Best parameters found: {grid_search.best_params_}")
        
        # Evaluate the model
        y_pred = self.model.predict(X_test)
        logger.info("\nSVM model evaluation:")
        logger.info(classification_report(y_test, y_pred))
        
        return self
    
    def predict(self, features):
        """Make flood predictions using the trained model"""
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Make prediction
        prediction = self.model.predict(features_scaled)
        probability = self.model.predict_proba(features_scaled)[:, 1]  # Probability of positive class
        
        return prediction, probability
    
    def save(self, filename='svm_flood_model.joblib'):
        """Save the model to disk"""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
            
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
            
        model_path = os.path.join(MODEL_DIR, filename)
        scaler_path = os.path.join(MODEL_DIR, 'svm_scaler.joblib')
        
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"Model saved to {model_path}")
        
        return model_path
    
    def load(self, filename='svm_flood_model.joblib'):
        """Load the model from disk"""
        model_path = os.path.join(MODEL_DIR, filename)
        scaler_path = os.path.join(MODEL_DIR, 'svm_scaler.joblib')
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Model or scaler file not found at {model_path}")
            
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        logger.info(f"Model loaded from {model_path}")
        
        return self


class TimeSeriesForecaster:
    """Time Series Forecasting for flood prediction
    
    This class implements ARIMA and Exponential Smoothing for forecasting 
    time-dependent variables like water level and rainfall.
    """
    
    def __init__(self, method='arima'):
        """Initialize the time series forecaster
        
        Args:
            method (str): The forecasting method to use ('arima' or 'ets')
        """
        self.method = method.lower()
        self.model = None
        self.history = None
        self.frequency = None
        
        if self.method not in ['arima', 'ets']:
            raise ValueError("Method must be either 'arima' or 'ets'")
    
    def train(self, time_series, date_column, value_column, frequency='D'):
        """Train the time series model
        
        Args:
            time_series (pd.DataFrame): DataFrame containing time series data
            date_column (str): Name of the date column
            value_column (str): Name of the value column
            frequency (str): Frequency of the time series ('D' for daily, 'H' for hourly, etc.)
        """
        logger.info(f"Training {self.method.upper()} time series model...")
        
        # Convert to time series format
        df = time_series.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)
        
        # Set the date as index
        df = df.set_index(date_column)
        self.frequency = frequency
        
        # Extract the time series
        ts = df[value_column]
        self.history = ts
        
        if self.method == 'arima':
            # Fit ARIMA model (p,d,q) = (5,1,0) as starting point
            # These parameters should be tuned based on ACF/PACF plots
            self.model = ARIMA(ts, order=(5, 1, 0))
            self.model = self.model.fit()
            logger.info("ARIMA model summary:")
            logger.info(self.model.summary())
            
        elif self.method == 'ets':
            # Fit Exponential Smoothing model
            # seasonal_periods should be adjusted based on the data
            seasonal_periods = 7 if frequency == 'D' else 24  # Weekly or daily pattern
            self.model = ExponentialSmoothing(ts, 
                                             seasonal='add', 
                                             seasonal_periods=seasonal_periods)
            self.model = self.model.fit()
            logger.info("Exponential Smoothing model fitted")
        
        return self
    
    def forecast(self, steps=24):
        """Generate a forecast for future periods
        
        Args:
            steps (int): Number of periods to forecast
            
        Returns:
            pd.Series: Forecasted values with date index
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        if self.method == 'arima':
            forecast = self.model.forecast(steps=steps)
        elif self.method == 'ets':
            forecast = self.model.forecast(steps=steps)
        
        # Create a date range for the forecast
        last_date = self.history.index[-1]
        if self.frequency == 'D':
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=steps, freq='D')
        elif self.frequency == 'H':
            forecast_dates = pd.date_range(start=last_date + timedelta(hours=1), periods=steps, freq='H')
        else:
            # Default to daily
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=steps, freq=self.frequency)
        
        # Return forecast as a Series with date index
        forecast_series = pd.Series(forecast, index=forecast_dates)
        return forecast_series
    
    def save(self, filename=None):
        """Save the model to disk
        
        Note: For time series models, we save the model parameters and history
        """
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
            
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
        
        if filename is None:
            filename = f"{self.method}_model.joblib"
            
        model_path = os.path.join(MODEL_DIR, filename)
        history_path = os.path.join(MODEL_DIR, f"{self.method}_history.joblib")
        
        # Save the model and history
        joblib.dump(self.model, model_path)
        joblib.dump(self.history, history_path)
        logger.info(f"Time series model saved to {model_path}")
        
        return model_path
    
    def load(self, filename=None):
        """Load the model from disk"""
        if filename is None:
            filename = f"{self.method}_model.joblib"
            
        model_path = os.path.join(MODEL_DIR, filename)
        history_path = os.path.join(MODEL_DIR, f"{self.method}_history.joblib")
        
        if not os.path.exists(model_path) or not os.path.exists(history_path):
            raise FileNotFoundError(f"Model or history file not found at {model_path}")
            
        self.model = joblib.load(model_path)
        self.history = joblib.load(history_path)
        logger.info(f"Time series model loaded from {model_path}")
        
        return self


class SpatialAnalyzer:
    """Spatial analysis for flood risk zones
    
    This class implements K-means clustering and IDW interpolation for
    identifying flood risk zones and interpolating sensor readings.
    """
    
    def __init__(self, method='kmeans'):
        """Initialize the spatial analyzer
        
        Args:
            method (str): The spatial analysis method to use ('kmeans' or 'idw')
        """
        self.method = method.lower()
        self.model = None
        self.locations = None
        
        if self.method not in ['kmeans', 'idw']:
            raise ValueError("Method must be either 'kmeans' or 'idw'")
    
    def fit(self, locations, values=None, n_clusters=5):
        """Fit the spatial model
        
        Args:
            locations (pd.DataFrame): DataFrame with latitude and longitude columns
            values (pd.Series, optional): Series of values for each location (for IDW)
            n_clusters (int): Number of clusters for K-means
        """
        logger.info(f"Fitting {self.method.upper()} spatial model...")
        
        # Store locations
        self.locations = locations.copy()
        
        if self.method == 'kmeans':
            # Fit K-means clustering
            # We use lat/long as features for clustering
            coords = self.locations[['latitude', 'longitude']].values
            self.model = KMeans(n_clusters=n_clusters, random_state=42)
            self.model.fit(coords)
            
            # Add cluster labels to locations
            self.locations['cluster'] = self.model.labels_
            logger.info(f"K-means clustering completed with {n_clusters} clusters")
            
        elif self.method == 'idw':
            # For IDW, we just store the values with coordinates
            if values is None:
                raise ValueError("Values must be provided for IDW interpolation")
                
            self.locations['value'] = values
            logger.info("IDW interpolation prepared with locations and values")
        
        return self
    
    def predict(self, points):
        """Make predictions for new points
        
        Args:
            points (pd.DataFrame): DataFrame with latitude and longitude columns
            
        Returns:
            pd.Series: Predicted values or cluster assignments
        """
        if self.model is None and self.method == 'kmeans':
            raise ValueError("Model not fitted yet. Call fit() first.")
            
        if self.locations is None:
            raise ValueError("No location data available. Call fit() first.")
        
        if self.method == 'kmeans':
            # Predict cluster for new points
            coords = points[['latitude', 'longitude']].values
            clusters = self.model.predict(coords)
            return pd.Series(clusters, index=points.index)
            
        elif self.method == 'idw':
            # Implement Inverse Distance Weighting interpolation
            results = []
            
            for _, point in points.iterrows():
                # Calculate inverse squared distances to all known points
                distances = np.sqrt(((self.locations['latitude'] - point['latitude'])**2 + 
                                    (self.locations['longitude'] - point['longitude'])**2))
                
                # Avoid division by zero by setting a minimum distance
                min_dist = 1e-6
                distances = np.maximum(distances, min_dist)
                
                # Calculate weights as 1/d²
                weights = 1.0 / (distances**2)
                
                # Normalize weights
                weights /= np.sum(weights)
                
                # Calculate weighted average
                interpolated_value = np.sum(weights * self.locations['value'])
                results.append(interpolated_value)
            
            return pd.Series(results, index=points.index)
    
    def get_clusters(self):
        """Get the cluster assignments for all locations"""
        if self.method != 'kmeans' or self.model is None:
            raise ValueError("This method is only available for K-means clustering")
            
        return self.locations[['latitude', 'longitude', 'cluster']]
    
    def save(self, filename=None):
        """Save the model to disk"""
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
        
        if filename is None:
            filename = f"{self.method}_spatial_model.joblib"
            
        model_path = os.path.join(MODEL_DIR, filename)
        locations_path = os.path.join(MODEL_DIR, f"{self.method}_locations.joblib")
        
        # Save the model (if applicable) and locations
        if self.model is not None:
            joblib.dump(self.model, model_path)
        
        joblib.dump(self.locations, locations_path)
        logger.info(f"Spatial model saved to {model_path}")
        
        return model_path
    
    def load(self, filename=None):
        """Load the model from disk"""
        if filename is None:
            filename = f"{self.method}_spatial_model.joblib"
            
        model_path = os.path.join(MODEL_DIR, filename)
        locations_path = os.path.join(MODEL_DIR, f"{self.method}_locations.joblib")
        
        if self.method == 'kmeans' and not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
            
        if not os.path.exists(locations_path):
            raise FileNotFoundError(f"Locations file not found at {locations_path}")
        
        if self.method == 'kmeans':
            self.model = joblib.load(model_path)
        
        self.locations = joblib.load(locations_path)
        logger.info(f"Spatial model loaded from {model_path}")
        
        return self


class LSTMFloodPredictor:
    """LSTM Neural Network for time series flood prediction
    
    This model uses LSTM recurrent neural networks to predict flood events
    using time series data.
    """
    
    def __init__(self):
        """Initialize the LSTM flood predictor"""
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTM models but is not installed")
            
        self.model = None
        self.scaler = StandardScaler()
        self.sequence_length = 24  # Default to 24 hours of data
        self.input_features = None
        
    def _create_sequences(self, data, target_column):
        """Create sequences for LSTM training
        
        Args:
            data (pd.DataFrame): DataFrame with time series data
            target_column (str): Name of the target column
            
        Returns:
            tuple: (X, y) where X is sequence data and y is target values
        """
        sequences = []
        targets = []
        
        for i in range(len(data) - self.sequence_length):
            seq = data.iloc[i:i+self.sequence_length].drop(columns=[target_column])
            target = data.iloc[i+self.sequence_length][target_column]
            sequences.append(seq.values)
            targets.append(target)
            
        return np.array(sequences), np.array(targets)
        
    def train(self, data, target_column, sequence_length=24, epochs=50, batch_size=32):
        """Train the LSTM model for flood prediction
        
        Args:
            data (pd.DataFrame): DataFrame with features and target
            target_column (str): Name of the target column
            sequence_length (int): Number of time steps in each sequence
            epochs (int): Number of training epochs
            batch_size (int): Batch size for training
        """
        logger.info("Training LSTM neural network model...")
        
        self.sequence_length = sequence_length
        
        # Save feature names (excluding target)
        self.input_features = [col for col in data.columns if col != target_column]
        
        # Scale the data
        scaled_data = pd.DataFrame(
            self.scaler.fit_transform(data),
            columns=data.columns,
            index=data.index
        )
        
        # Create sequences for LSTM
        X, y = self._create_sequences(scaled_data, target_column)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Get the number of features (excluding target)
        n_features = X.shape[2]
        
        # Build LSTM model
        self.model = Sequential([
            LSTM(64, activation='relu', input_shape=(sequence_length, n_features), return_sequences=True),
            Dropout(0.2),
            LSTM(32, activation='relu'),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1, activation='sigmoid' if len(np.unique(y)) <= 2 else None)
        ])
        
        # Compile the model
        if len(np.unique(y)) <= 2:
            # Binary classification
            self.model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        else:
            # Regression
            self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        # Early stopping to prevent overfitting
        early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
        
        # Train the model
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            callbacks=[early_stopping],
            verbose=1
        )
        
        # Evaluate the model
        loss, metric = self.model.evaluate(X_test, y_test)
        
        if len(np.unique(y)) <= 2:
            logger.info(f"LSTM model trained - Test accuracy: {metric:.4f}")
            # Make predictions for classification report
            y_pred = (self.model.predict(X_test) > 0.5).astype(int)
            logger.info("\nLSTM model evaluation:")
            logger.info(classification_report(y_test, y_pred))
        else:
            logger.info(f"LSTM model trained - Test MAE: {metric:.4f}")
            # Calculate MSE for regression
            y_pred = self.model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            logger.info(f"Test MSE: {mse:.4f}")
        
        return self
    
    def predict(self, sequence_data):
        """Make predictions using the trained LSTM model
        
        Args:
            sequence_data (pd.DataFrame): DataFrame with sequence_length rows of features
            
        Returns:
            float: Prediction (probability for classification, value for regression)
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
            
        if len(sequence_data) != self.sequence_length:
            raise ValueError(f"Input must have exactly {self.sequence_length} time steps")
            
        # Ensure we have the correct features in the correct order
        if not all(feature in sequence_data.columns for feature in self.input_features):
            raise ValueError(f"Input must contain all features: {self.input_features}")
            
        sequence_data = sequence_data[self.input_features].copy()
        
        # Scale the data
        scaled_sequence = self.scaler.transform(sequence_data)
        
        # Reshape for LSTM input [samples, time steps, features]
        X = scaled_sequence.reshape(1, self.sequence_length, len(self.input_features))
        
        # Make prediction
        prediction = self.model.predict(X)[0, 0]
        
        return prediction
    
    def save(self, filename='lstm_flood_model'):
        """Save the LSTM model"""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
            
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
            
        model_path = os.path.join(MODEL_DIR, f"{filename}.h5")
        scaler_path = os.path.join(MODEL_DIR, f"{filename}_scaler.joblib")
        metadata_path = os.path.join(MODEL_DIR, f"{filename}_metadata.joblib")
        
        # Save the model in H5 format
        self.model.save(model_path)
        
        # Save the scaler
        joblib.dump(self.scaler, scaler_path)
        
        # Save metadata (sequence length and feature names)
        metadata = {
            'sequence_length': self.sequence_length,
            'input_features': self.input_features
        }
        joblib.dump(metadata, metadata_path)
        
        logger.info(f"LSTM model saved to {model_path}")
        
        return model_path
    
    def load(self, filename='lstm_flood_model'):
        """Load the LSTM model"""
        from tensorflow.keras.models import load_model
        
        model_path = os.path.join(MODEL_DIR, f"{filename}.h5")
        scaler_path = os.path.join(MODEL_DIR, f"{filename}_scaler.joblib")
        metadata_path = os.path.join(MODEL_DIR, f"{filename}_metadata.joblib")
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Model, scaler, or metadata file not found at {model_path}")
            
        # Load the model
        self.model = load_model(model_path)
        
        # Load the scaler
        self.scaler = joblib.load(scaler_path)
        
        # Load metadata
        metadata = joblib.load(metadata_path)
        self.sequence_length = metadata['sequence_length']
        self.input_features = metadata['input_features']
        
        logger.info(f"LSTM model loaded from {model_path}")
        
        return self
