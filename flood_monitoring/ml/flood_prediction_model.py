"""Flood Prediction Machine Learning Model

This module provides functions for training and using machine learning models to predict flood
events based on environmental sensor data, historical patterns, and geographic information.

The model primarily uses rainfall, water level, soil saturation, and elevation data to predict
flood probabilities, timing, and potential impact.

Example usage:
    - Train the model: train_flood_prediction_model(historical_data)
    - Make predictions: predict_flood_probability(current_data)
"""

import os
import datetime
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, mean_squared_error
from sklearn.pipeline import Pipeline
import joblib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths for saving/loading models
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

CLASSIFICATION_MODEL_PATH = os.path.join(MODEL_DIR, 'flood_classification_model.joblib')
REGRESSION_MODEL_PATH = os.path.join(MODEL_DIR, 'flood_time_prediction_model.joblib')
FEATURE_SCALER_PATH = os.path.join(MODEL_DIR, 'feature_scaler.joblib')

# Features used for prediction
FEATURES = [
    'rainfall_24h', 'rainfall_48h', 'rainfall_7d',
    'water_level', 'water_level_change_24h',
    'temperature', 'humidity',
    'elevation', 'soil_saturation',
    'month', 'day_of_year', 'historical_floods_count'
]

# Thresholds for flood severity classification
FLOOD_THRESHOLDS = {
    'advisory': 30,     # 30% probability
    'watch': 50,       # 50% probability
    'warning': 70,     # 70% probability
    'emergency': 85,   # 85% probability
    'catastrophic': 95 # 95% probability
}


def preprocess_data(data):
    """Preprocess input data for the flood prediction model.
    
    Args:
        data (dict or pandas.DataFrame): Raw input data with sensor readings and geographical info
        
    Returns:
        pandas.DataFrame: Preprocessed data ready for the model
    """
    # Convert to DataFrame if it's a dictionary
    if isinstance(data, dict):
        df = pd.DataFrame([data])
    else:
        df = data.copy()
    
    # Extract temporal features if timestamp is available
    if 'timestamp' in df.columns:
        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Extract date features
        df['month'] = df['timestamp'].dt.month
        df['day_of_year'] = df['timestamp'].dt.dayofyear
    else:
        # Use current date if no timestamp provided
        now = datetime.datetime.now()
        df['month'] = now.month
        df['day_of_year'] = now.timetuple().tm_yday
    
    # Fill missing values with appropriate defaults
    for feature in FEATURES:
        if feature not in df.columns:
            if feature == 'soil_saturation':
                # Estimate soil saturation from rainfall data if available
                if 'rainfall_24h' in df.columns and 'rainfall_48h' in df.columns:
                    df[feature] = (df['rainfall_24h'] * 2 + df['rainfall_48h']) / 3 * 10  # Simple estimation
                else:
                    df[feature] = 50  # Default mid-range value
            elif feature == 'historical_floods_count':
                df[feature] = 0  # Default to zero historical floods
            elif 'rainfall' in feature and 'rainfall_24h' in df.columns:
                df[feature] = df['rainfall_24h']  # Use 24h rainfall as a fallback
            elif feature == 'water_level_change_24h' and 'water_level' in df.columns:
                df[feature] = 0  # Default to no change
            else:
                df[feature] = 0  # Default for other missing features
    
    # Ensure all required features are in the DataFrame
    for feature in FEATURES:
        if feature not in df.columns:
            logger.warning(f"Missing feature: {feature}. Using default value.")
            df[feature] = 0
    
    return df[FEATURES]


def train_flood_prediction_model(historical_data):
    """Train machine learning models for flood prediction.
    
    This function trains two models:
    1. A classification model to predict flood probability
    2. A regression model to predict time until flooding
    
    Args:
        historical_data (pandas.DataFrame): Historical data with sensor readings and flood outcomes
        
    Returns:
        tuple: (classification_model, regression_model, feature_scaler)
    """
    logger.info("Starting flood prediction model training...")
    
    # Preprocess data
    X = preprocess_data(historical_data)
    y_flood = historical_data['flood_occurred']  # Binary: Did flooding occur?
    y_time = historical_data['hours_to_flood']   # Regression: Hours until flooding
    
    # Split data into training and testing sets
    X_train, X_test, y_flood_train, y_flood_test = train_test_split(
        X, y_flood, test_size=0.2, random_state=42
    )
    
    # Create feature scaler
    scaler = StandardScaler()
    
    # Train classification model (flood probability)
    logger.info("Training classification model...")
    classification_model = Pipeline([
        ('scaler', scaler),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    classification_model.fit(X_train, y_flood_train)
    
    # Evaluate classification model
    y_flood_pred = classification_model.predict(X_test)
    logger.info("Classification model evaluation:")
    logger.info(classification_report(y_flood_test, y_flood_pred))
    
    # Train regression model (time until flooding) - only on data where flooding occurred
    logger.info("Training regression model...")
    flood_mask = historical_data['flood_occurred'] == 1
    if flood_mask.sum() > 0:
        X_flood = X[flood_mask]
        y_time_flood = y_time[flood_mask]
        
        X_time_train, X_time_test, y_time_train, y_time_test = train_test_split(
            X_flood, y_time_flood, test_size=0.2, random_state=42
        )
        
        regression_model = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', GradientBoostingRegressor(n_estimators=100, random_state=42))
        ])
        regression_model.fit(X_time_train, y_time_train)
        
        # Evaluate regression model
        y_time_pred = regression_model.predict(X_time_test)
        mse = mean_squared_error(y_time_test, y_time_pred)
        logger.info(f"Regression model MSE: {mse:.2f}")
    else:
        logger.warning("No flood events in training data. Regression model not trained.")
        regression_model = None
    
    # Save models
    logger.info("Saving models...")
    joblib.dump(classification_model, CLASSIFICATION_MODEL_PATH)
    if regression_model is not None:
        joblib.dump(regression_model, REGRESSION_MODEL_PATH)
    
    return classification_model, regression_model, scaler


def load_models():
    """Load trained models from disk.
    
    Returns:
        tuple: (classification_model, regression_model)
    """
    classification_model = None
    regression_model = None
    
    try:
        if os.path.exists(CLASSIFICATION_MODEL_PATH):
            logger.info("Loading flood classification model...")
            classification_model = joblib.load(CLASSIFICATION_MODEL_PATH)
        
        if os.path.exists(REGRESSION_MODEL_PATH):
            logger.info("Loading flood timing regression model...")
            regression_model = joblib.load(REGRESSION_MODEL_PATH)
    except Exception as e:
        logger.error(f"Error loading models: {e}")
    
    return classification_model, regression_model


def predict_flood_probability(data):
    """Predict flood probability based on current sensor data.
    
    Args:
        data (dict or pandas.DataFrame): Current sensor readings and geographical info
        
    Returns:
        dict: Prediction results including probability, severity, time to flood, etc.
    """
    # Load models
    classification_model, regression_model = load_models()
    
    # Initialize result dictionary
    result = {
        'probability': 0,
        'severity_level': 0,
        'severity_text': 'Normal',
        'hours_to_flood': None,
        'contributing_factors': [],
        'last_updated': datetime.datetime.now().isoformat()
    }
    
    if classification_model is None:
        logger.warning("Classification model not found. Using default prediction.")
        # Generate synthetic prediction based on rainfall and water level manually
        if isinstance(data, dict):
            rainfall_24h = data.get('rainfall_24h', 0)
            water_level = data.get('water_level', 0)
            water_level_threshold = 1.5  # Example threshold
            rainfall_threshold = 50      # Example threshold (mm in 24h)
            
            rainfall_factor = min(100, (rainfall_24h / rainfall_threshold) * 100) if rainfall_threshold > 0 else 0
            water_level_factor = min(100, (water_level / water_level_threshold) * 100) if water_level_threshold > 0 else 0
            
            # Weighted average of factors
            probability = (rainfall_factor * 0.6) + (water_level_factor * 0.4)  # 60% rainfall, 40% water level
            result['probability'] = int(probability)
        else:
            result['probability'] = 15  # Default low probability
    else:
        # Preprocess input data
        X = preprocess_data(data)
        
        # Predict flood probability
        probability = classification_model.predict_proba(X)[0, 1] * 100  # Convert to percentage
        result['probability'] = int(probability)
        
        # If flooding is likely, predict time until flood
        if probability > 50 and regression_model is not None:
            hours_to_flood = regression_model.predict(X)[0]
            result['hours_to_flood'] = max(0, float(hours_to_flood))  # Ensure non-negative
            
            # Calculate predicted flood time
            now = datetime.datetime.now()
            flood_time = now + datetime.timedelta(hours=result['hours_to_flood'])
            result['flood_time'] = flood_time.isoformat()
    
    # Determine severity level based on probability
    for level, threshold in sorted(FLOOD_THRESHOLDS.items(), key=lambda x: x[1]):
        if result['probability'] >= threshold:
            result['severity_text'] = level.capitalize()
            if level == 'advisory':
                result['severity_level'] = 1
            elif level == 'watch':
                result['severity_level'] = 2
            elif level == 'warning':
                result['severity_level'] = 3
            elif level == 'emergency':
                result['severity_level'] = 4
            elif level == 'catastrophic':
                result['severity_level'] = 5
    
    # Generate impact assessment based on severity
    if result['severity_level'] <= 1:
        result['impact'] = "No significant flooding expected."
    elif result['severity_level'] == 2:
        result['impact'] = "Possible minor flooding in low-lying areas."
    elif result['severity_level'] == 3:
        result['impact'] = "Moderate flooding likely. Some roads may be impassable."
    elif result['severity_level'] == 4:
        result['impact'] = "Severe flooding expected with significant infrastructure impact."
    else:
        result['impact'] = "Catastrophic flooding expected. Immediate evacuation recommended."
    
    # Identify contributing factors (for example purposes)
    if isinstance(data, dict):
        # Check rainfall
        if data.get('rainfall_24h', 0) > 30:
            result['contributing_factors'].append(f"Heavy rainfall in the last 24 hours ({data.get('rainfall_24h', 0):.1f}mm)")
        
        # Check water level
        if data.get('water_level', 0) > 1.0:
            result['contributing_factors'].append(f"Elevated water level ({data.get('water_level', 0):.2f}m)")
        
        # Check soil saturation if available
        if data.get('soil_saturation', 0) > 80:
            result['contributing_factors'].append("High soil saturation limiting water absorption")
        
        # Check historical context
        if data.get('historical_floods_count', 0) > 3:
            result['contributing_factors'].append("Area has history of frequent flooding")
        
        # If no factors but high probability
        if not result['contributing_factors'] and result['probability'] > 30:
            result['contributing_factors'].append("Multiple minor factors contributing to flood risk")
    
    return result


def get_affected_barangays(municipality_id=None, probability_threshold=50):
    """Get list of barangays likely to be affected by flooding.
    
    Args:
        municipality_id (int, optional): Filter by municipality ID
        probability_threshold (int, optional): Minimum flood probability threshold
        
    Returns:
        list: Barangays with flood risk above threshold
    """
    # This would typically query the database for barangays and their risk factors
    # For now, we'll return a simulated list based on the parameters
    
    # In a real implementation, you would:
    # 1. Query the database for barangays (filtered by municipality_id if provided)
    # 2. For each barangay, collect its relevant sensor data
    # 3. Run the prediction model for each barangay
    # 4. Filter the results by probability_threshold
    # 5. Return the list of affected barangays with their risk assessment
    
    from core.models import Barangay
    from django.db.models import Q
    
    # Start with a base query for barangays
    barangay_query = Barangay.objects.all()
    
    # Filter by municipality if provided
    if municipality_id is not None:
        barangay_query = barangay_query.filter(municipality_id=municipality_id)
    
    # Get all barangays
    barangays = list(barangay_query)
    affected_barangays = []
    
    # For each barangay, make a prediction
    for barangay in barangays:
        # Get the latest sensor data for this barangay
        # (In a real implementation, you would query the sensor data related to this barangay)
        
        # For now, generate some test data based on barangay ID
        # This ensures deterministic but varied results per barangay
        barangay_data = {
            'rainfall_24h': (barangay.id * 3.5) % 50,  # 0-50mm
            'water_level': ((barangay.id * 2.7) % 20) / 10,  # 0-2.0m
            'elevation': ((barangay.id * 4.1) % 100) + 10,  # 10-110m
            'soil_saturation': (barangay.id * 1.8) % 100,  # 0-100%
            'historical_floods_count': (barangay.id * 1.3) % 5  # 0-4 past floods
        }
        
        # Make prediction
        prediction = predict_flood_probability(barangay_data)
        
        # Include barangay if probability exceeds threshold
        if prediction['probability'] >= probability_threshold:
            affected_barangays.append({
                'id': barangay.id,
                'name': barangay.name,
                'population': barangay.population,
                'risk_level': "High" if prediction['probability'] >= 70 else 
                             "Moderate" if prediction['probability'] >= 50 else "Low",
                'probability': prediction['probability'],
                'evacuation_centers': (barangay.id % 3) + 1  # 1-3 evacuation centers
            })
    
    # Sort by risk (highest first)
    affected_barangays.sort(key=lambda x: x['probability'], reverse=True)
    
    return affected_barangays
