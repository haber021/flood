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
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, mean_squared_error, mean_absolute_error, accuracy_score, f1_score
from sklearn.pipeline import Pipeline
import joblib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths for saving/loading models
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'models')
CLASSIFICATION_MODEL_PATH = os.path.join(MODEL_DIR, 'flood_classification_model.joblib')
REGRESSION_MODEL_PATH = os.path.join(MODEL_DIR, 'flood_timing_model.joblib')
SCALER_PATH = os.path.join(MODEL_DIR, 'feature_scaler.joblib')

# Try to import advanced algorithms (optional)
try:
    from flood_monitoring.ml.advanced_algorithms import (
        GradientBoostingFloodPredictor,
        SVMFloodPredictor,
        TimeSeriesForecaster,
        SpatialAnalyzer,
        LSTMFloodPredictor
    )
    ADVANCED_ALGORITHMS_AVAILABLE = True
    # Check if TensorFlow is available
    try:
        import tensorflow as tf
        TENSORFLOW_AVAILABLE = True
    except ImportError:
        TENSORFLOW_AVAILABLE = False
except ImportError:
    ADVANCED_ALGORITHMS_AVAILABLE = False
    TENSORFLOW_AVAILABLE = False

# Default algorithm to use
DEFAULT_CLASSIFICATION_ALGORITHM = 'random_forest'  # Options: 'random_forest', 'gradient_boosting', 'svm', 'lstm'
DEFAULT_REGRESSION_ALGORITHM = 'random_forest'      # Options: 'random_forest', 'gradient_boosting'
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


def train_flood_prediction_model(historical_data, classification_algorithm=DEFAULT_CLASSIFICATION_ALGORITHM, 
                            regression_algorithm=DEFAULT_REGRESSION_ALGORITHM, evaluate_only=False):
    """Train machine learning models for flood prediction.
    
    This function trains two models:
    1. A classification model to predict flood probability
    2. A regression model to predict time until flooding
    
    Args:
        historical_data (pandas.DataFrame): Historical data with sensor readings and flood outcomes
        classification_algorithm (str): Algorithm to use for flood classification
        regression_algorithm (str): Algorithm to use for flood timing regression
        evaluate_only (bool): If True, only evaluate existing models, don't train or save
        
    Returns:
        tuple: (classification_model, regression_model, feature_scaler) or metrics dict if evaluate_only=True
    """
    logger.info(f"Starting flood prediction model training using {classification_algorithm} for classification")
    
    # Preprocess data
    X = preprocess_data(historical_data)
    y_flood = historical_data['flood_occurred']  # Binary: Did flooding occur?
    y_time = historical_data['hours_to_flood']   # Regression: Hours until flooding
    
    # Split data into training and testing sets
    X_train, X_test, y_flood_train, y_flood_test = train_test_split(
        X, y_flood, test_size=0.2, random_state=42
    )
    
    # Create feature scaler for standard models
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train classification model (flood probability)
    logger.info(f"Training classification model using {classification_algorithm}...")
    classification_model = None
    metrics = {}
    
    # Select algorithm for classification
    if classification_algorithm == 'random_forest':
        classification_model = Pipeline([
            ('scaler', scaler),
            ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        classification_model.fit(X_train, y_flood_train)
    
    elif classification_algorithm == 'gradient_boosting' and ADVANCED_ALGORITHMS_AVAILABLE:
        # Use our GradientBoostingFloodPredictor
        classification_model = GradientBoostingFloodPredictor()
        classification_model.train(X_train, y_flood_train)
    
    elif classification_algorithm == 'svm' and ADVANCED_ALGORITHMS_AVAILABLE:
        # Use our SVMFloodPredictor
        classification_model = SVMFloodPredictor()
        classification_model.train(X_train, y_flood_train)
    
    elif classification_algorithm == 'lstm' and ADVANCED_ALGORITHMS_AVAILABLE:
        try:
            # Use our LSTMFloodPredictor
            # For LSTM, we need to prepare sequential data
            all_data = pd.concat([pd.DataFrame(X_train_scaled, columns=X.columns), 
                                 pd.Series(y_flood_train, name='flood_occurred')], axis=1)
            classification_model = LSTMFloodPredictor()
            classification_model.train(all_data, 'flood_occurred', sequence_length=10, epochs=20, batch_size=32)
        except Exception as e:
            logger.error(f"LSTM training failed: {str(e)}")
            # Fall back to Random Forest
            logger.info("Falling back to Random Forest classifier")
            classification_model = Pipeline([
                ('scaler', scaler),
                ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
            ])
            classification_model.fit(X_train, y_flood_train)
    else:
        # Default to Random Forest if algorithm not recognized
        logger.info("Using default Random Forest classifier")
        classification_model = Pipeline([
            ('scaler', scaler),
            ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        classification_model.fit(X_train, y_flood_train)
    
    # Evaluate classification model
    if classification_algorithm in ['gradient_boosting', 'svm'] and ADVANCED_ALGORITHMS_AVAILABLE:
        y_flood_pred, _ = classification_model.predict(X_test)
    elif classification_algorithm == 'lstm' and ADVANCED_ALGORITHMS_AVAILABLE:
        # Special evaluation for LSTM (simplified)
        try:
            test_data = pd.concat([pd.DataFrame(X_test_scaled, columns=X.columns), 
                                  pd.Series(y_flood_test, name='flood_occurred')], axis=1)
            y_flood_pred = []
            sequence_len = 10  # Should match training sequence length
            
            # Use a subset for demonstration if data is large
            test_subset = min(50, len(test_data) - sequence_len)
            for i in range(test_subset):
                seq = test_data.iloc[i:i+sequence_len].drop(columns=['flood_occurred'])
                y_flood_pred.append(int(classification_model.predict(seq) > 0.5))
                
            y_flood_test = y_flood_test[:test_subset]  # Match prediction length
        except Exception as e:
            logger.error(f"LSTM evaluation failed: {str(e)}")
            y_flood_pred = [0] * len(y_flood_test)  # Default predictions
    else:
        y_flood_pred = classification_model.predict(X_test)
    
    # Calculate metrics
    accuracy = accuracy_score(y_flood_test, y_flood_pred)
    f1 = f1_score(y_flood_test, y_flood_pred)
    logger.info("Classification model evaluation:")
    logger.info(f"Accuracy: {accuracy:.4f}, F1 Score: {f1:.4f}")
    logger.info(classification_report(y_flood_test, y_flood_pred))
    
    metrics['accuracy'] = accuracy
    metrics['f1_score'] = f1
    
    # Train regression model (time until flooding) - only on data where flooding occurred
    regression_model = None
    logger.info(f"Training regression model using {regression_algorithm}...")
    flood_mask = historical_data['flood_occurred'] == 1
    if flood_mask.sum() > 0:
        X_flood = X[flood_mask]
        y_time_flood = y_time[flood_mask]
        
        X_time_train, X_time_test, y_time_train, y_time_test = train_test_split(
            X_flood, y_time_flood, test_size=0.2, random_state=42
        )
        
        # Select algorithm for regression
        if regression_algorithm == 'random_forest':
            regression_model = Pipeline([
                ('scaler', StandardScaler()),
                ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
            ])
        elif regression_algorithm == 'gradient_boosting':
            regression_model = Pipeline([
                ('scaler', StandardScaler()),
                ('regressor', GradientBoostingRegressor(n_estimators=100, random_state=42))
            ])
        else:
            # Default to Gradient Boosting if not recognized
            regression_model = Pipeline([
                ('scaler', StandardScaler()),
                ('regressor', GradientBoostingRegressor(n_estimators=100, random_state=42))
            ])
        
        regression_model.fit(X_time_train, y_time_train)
        
        # Evaluate regression model
        y_time_pred = regression_model.predict(X_time_test)
        mse = mean_squared_error(y_time_test, y_time_pred)
        mae = mean_absolute_error(y_time_test, y_time_pred)
        logger.info(f"Regression model - MSE: {mse:.2f}, MAE: {mae:.2f}")
        
        metrics['regression_mse'] = mse
        metrics['regression_mae'] = mae
    else:
        logger.warning("No flood events in training data. Regression model not trained.")
    
    # Save models if not in evaluate_only mode
    if not evaluate_only:
        logger.info("Saving models...")
        # For advanced algorithm models that have their own save methods
        if classification_algorithm in ['gradient_boosting', 'svm', 'lstm'] and ADVANCED_ALGORITHMS_AVAILABLE:
            try:
                classification_model.save()
            except Exception as e:
                logger.error(f"Error saving advanced classification model: {str(e)}")
                # Consider saving model in another format if needed
        else:
            # Standard sklearn Pipeline models
            joblib.dump(classification_model, CLASSIFICATION_MODEL_PATH)
        
        if regression_model is not None:
            joblib.dump(regression_model, REGRESSION_MODEL_PATH)
    
    if evaluate_only:
        return metrics
    else:
        return classification_model, regression_model, scaler


def load_models(classification_algorithm=DEFAULT_CLASSIFICATION_ALGORITHM, regression_algorithm=DEFAULT_REGRESSION_ALGORITHM):
    """Load trained models from disk.
    
    Args:
        classification_algorithm (str): The algorithm used for classification
        regression_algorithm (str): The algorithm used for regression
    
    Returns:
        tuple: (classification_model, regression_model)
    """
    classification_model = None
    regression_model = None
    
    try:
        # Try to load the appropriate model based on the algorithm
        if classification_algorithm in ['gradient_boosting', 'svm', 'lstm'] and ADVANCED_ALGORITHMS_AVAILABLE:
            # Load the advanced model
            if classification_algorithm == 'gradient_boosting':
                logger.info("Loading Gradient Boosting classification model...")
                classification_model = GradientBoostingFloodPredictor()
                classification_model.load()
            elif classification_algorithm == 'svm':
                logger.info("Loading SVM classification model...")
                classification_model = SVMFloodPredictor()
                classification_model.load()
            elif classification_algorithm == 'lstm':
                logger.info("Loading LSTM classification model...")
                classification_model = LSTMFloodPredictor()
                classification_model.load()
        else:
            # Default to standard models
            if os.path.exists(CLASSIFICATION_MODEL_PATH):
                logger.info("Loading Random Forest classification model...")
                classification_model = joblib.load(CLASSIFICATION_MODEL_PATH)
        
        # Load regression model
        if os.path.exists(REGRESSION_MODEL_PATH):
            logger.info("Loading flood timing regression model...")
            regression_model = joblib.load(REGRESSION_MODEL_PATH)
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        # If advanced algorithm loading fails, try to fall back to standard model
        if classification_algorithm in ['gradient_boosting', 'svm', 'lstm'] and ADVANCED_ALGORITHMS_AVAILABLE:
            try:
                if os.path.exists(CLASSIFICATION_MODEL_PATH):
                    logger.info("Falling back to standard classification model...")
                    classification_model = joblib.load(CLASSIFICATION_MODEL_PATH)
            except Exception:
                pass
    
    return classification_model, regression_model


def predict_flood_probability(data, classification_algorithm=DEFAULT_CLASSIFICATION_ALGORITHM, 
                            regression_algorithm=DEFAULT_REGRESSION_ALGORITHM):
    """Predict flood probability based on current sensor data.
    
    Args:
        data (dict or pandas.DataFrame): Current sensor readings and geographical info
        classification_algorithm (str): Algorithm to use for classification
        regression_algorithm (str): Algorithm to use for regression
        
    Returns:
        dict: Prediction results including probability, severity, time to flood, etc.
    """
    # Load models with specified algorithms
    classification_model, regression_model = load_models(classification_algorithm, regression_algorithm)
    
    # Initialize result dictionary
    result = {
        'probability': 0,
        'severity_level': 0,
        'severity_text': 'Normal',
        'hours_to_flood': None,
        'contributing_factors': [],
        'model_used': classification_algorithm,
        'last_updated': datetime.datetime.now().isoformat()
    }
    
    if classification_model is None:
        logger.warning("Classification model not found. Using default prediction.")
        # Generate prediction based on rainfall and water level manually
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
            result['model_used'] = 'statistical_formula'  # Indicate we used a simple formula
        else:
            result['probability'] = 15  # Default low probability
            result['model_used'] = 'default_value'  # Indicate we used a default value
    else:
        # Preprocess input data
        X = preprocess_data(data)
        
        # Predict flood probability based on the model type
        if classification_algorithm in ['gradient_boosting', 'svm'] and ADVANCED_ALGORITHMS_AVAILABLE:
            # These advanced models return prediction and probability
            try:
                _, probability_array = classification_model.predict(X)
                probability = float(probability_array[0]) * 100  # Convert to percentage
            except Exception as e:
                logger.error(f"Error making prediction with advanced model: {str(e)}")
                probability = 15  # Default if prediction fails
        elif classification_algorithm == 'lstm' and ADVANCED_ALGORITHMS_AVAILABLE:
            # LSTM models may require sequential data
            try:
                # For real-time prediction, we need to handle sequences differently
                # For simplicity, we'll make a single prediction using the current data point
                # In a production system, you would maintain a queue of recent readings
                value = classification_model.predict(X)
                probability = float(value) * 100 if value is not None else 15
            except Exception as e:
                logger.error(f"Error making prediction with LSTM model: {str(e)}")
                probability = 15  # Default if prediction fails
        else:
            # Standard scikit-learn pipeline models
            try:
                probability = classification_model.predict_proba(X)[0, 1] * 100  # Convert to percentage
            except Exception as e:
                logger.error(f"Error making prediction with standard model: {str(e)}")
                probability = 15  # Default if prediction fails
        
        result['probability'] = int(probability)
        
        # If flooding is likely, predict time until flood
        if probability > 50 and regression_model is not None:
            try:
                hours_to_flood = regression_model.predict(X)[0]
                result['hours_to_flood'] = max(0, float(hours_to_flood))  # Ensure non-negative
                
                # Calculate predicted flood time
                now = datetime.datetime.now()
                flood_time = now + datetime.timedelta(hours=result['hours_to_flood'])
                result['flood_time'] = flood_time.isoformat()
            except Exception as e:
                logger.error(f"Error predicting flood timing: {str(e)}")
                # Don't set hours_to_flood if prediction fails
    
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


def get_affected_barangays(municipality_id=None, probability_threshold=50, 
                        classification_algorithm=DEFAULT_CLASSIFICATION_ALGORITHM,
                        compare_algorithms=False):
    """Get list of barangays likely to be affected by flooding.
    
    Args:
        municipality_id (int, optional): Filter by municipality ID
        probability_threshold (int, optional): Minimum flood probability threshold
        classification_algorithm (str): Algorithm to use for classification
        compare_algorithms (bool): If True, run predictions with multiple algorithms for comparison
        
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
    
    # Algorithms to use for prediction
    algorithms = ['random_forest']
    if compare_algorithms and ADVANCED_ALGORITHMS_AVAILABLE:
        algorithms = ['random_forest', 'gradient_boosting', 'svm']
        if TENSORFLOW_AVAILABLE:
            algorithms.append('lstm')
    elif classification_algorithm != 'random_forest':
        algorithms = [classification_algorithm]
    
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
        
        # Make predictions with the specified algorithm(s)
        predictions = {}
        best_prediction = None
        
        for algo in algorithms:
            try:
                pred = predict_flood_probability(barangay_data, classification_algorithm=algo)
                predictions[algo] = pred
                
                # For single algorithm mode, this is the only prediction
                # For comparison mode, we'll use the highest probability prediction
                if best_prediction is None or pred['probability'] > best_prediction['probability']:
                    best_prediction = pred
            except Exception as e:
                logger.error(f"Error making prediction with {algo} algorithm: {str(e)}")
        
        # Use the best prediction (highest probability)
        prediction = best_prediction
        
        # Skip if we couldn't make any predictions
        if prediction is None:
            logger.warning(f"Could not make predictions for barangay {barangay.name} with any algorithm")
            continue
        
        # Include barangay if probability exceeds threshold
        if prediction['probability'] >= probability_threshold:
            barangay_info = {
                'id': barangay.id,
                'name': barangay.name,
                'population': barangay.population,
                'risk_level': "High" if prediction['probability'] >= 70 else 
                             "Moderate" if prediction['probability'] >= 50 else "Low",
                'probability': prediction['probability'],
                'model_used': prediction['model_used'],
                'evacuation_centers': (barangay.id % 3) + 1  # 1-3 evacuation centers
            }
            
            # If comparing algorithms, include all predictions
            if compare_algorithms and len(predictions) > 1:
                barangay_info['algorithm_comparison'] = {
                    algo: {'probability': pred['probability'], 'severity_level': pred['severity_level']}
                    for algo, pred in predictions.items()
                }
            
            affected_barangays.append(barangay_info)
    
    # Sort by risk (highest first)
    affected_barangays.sort(key=lambda x: x['probability'], reverse=True)
    
    return affected_barangays
