from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Max, Avg, Sum, Q, Count, Min
import math
import logging
from datetime import timedelta

# Import ML model functions
from flood_monitoring.ml.flood_prediction_model import predict_flood_probability, get_affected_barangays as ml_get_affected_barangays
from flood_monitoring.ml.flood_prediction_model import ADVANCED_ALGORITHMS_AVAILABLE, TENSORFLOW_AVAILABLE
from flood_monitoring.ml.flood_prediction_model import DEFAULT_CLASSIFICATION_ALGORITHM

# Set up logging
logger = logging.getLogger(__name__)

from core.models import (
    Sensor, SensorData, Municipality, Barangay, FloodRiskZone, 
    FloodAlert, ThresholdSetting, NotificationLog, EmergencyContact,
    ResilienceScore
)
from .serializers import (
    SensorSerializer, SensorDataSerializer, MunicipalitySerializer, BarangaySerializer,
    FloodRiskZoneSerializer, FloodAlertSerializer, ThresholdSettingSerializer, 
    NotificationLogSerializer, EmergencyContactSerializer, ResilienceScoreSerializer
)

class SensorViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for sensors"""
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Sensor.objects.all()
        sensor_type = self.request.query_params.get('type', None)
        active = self.request.query_params.get('active', None)
        
        if sensor_type:
            queryset = queryset.filter(sensor_type=sensor_type)
        
        if active:
            active_bool = active.lower() == 'true'
            queryset = queryset.filter(active=active_bool)
            
        return queryset

class SensorDataViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for sensor data"""
    queryset = SensorData.objects.all()
    serializer_class = SensorDataSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = SensorData.objects.all().order_by('-timestamp')
        sensor_id = self.request.query_params.get('sensor_id', None)
        sensor_type = self.request.query_params.get('sensor_type', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        limit = self.request.query_params.get('limit', None)
        municipality_id = self.request.query_params.get('municipality_id', None)
        barangay_id = self.request.query_params.get('barangay_id', None)
        
        if sensor_id:
            queryset = queryset.filter(sensor_id=sensor_id)
        
        if sensor_type:
            queryset = queryset.filter(sensor__sensor_type=sensor_type)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
            
        # Filter by location if specified
        if municipality_id:
            queryset = queryset.filter(sensor__municipality_id=municipality_id)
            
        if barangay_id:
            queryset = queryset.filter(sensor__barangay_id=barangay_id)
        
        if limit:
            queryset = queryset[:int(limit)]
            
        return queryset

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def add_sensor_data(request):
    """API endpoint for adding new sensor data"""
    sensor_id = request.data.get('sensor_id')
    value = request.data.get('value')
    timestamp = request.data.get('timestamp', timezone.now())
    
    try:
        sensor = Sensor.objects.get(id=sensor_id)
    except Sensor.DoesNotExist:
        return Response(
            {'error': f'Sensor with ID {sensor_id} does not exist'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Create the new sensor data
    data = SensorData.objects.create(
        sensor=sensor,
        value=value,
        timestamp=timestamp
    )
    
    # Check if the new reading exceeds any thresholds
    check_thresholds(sensor, value)
    
    serializer = SensorDataSerializer(data)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

def check_thresholds(sensor, value):
    """Check if a sensor reading exceeds any thresholds and create alerts if needed"""
    try:
        threshold = ThresholdSetting.objects.get(parameter=sensor.sensor_type)
    except ThresholdSetting.DoesNotExist:
        # No threshold set for this sensor type
        return
    
    # Determine the severity level based on the thresholds
    severity_level = None
    
    if value >= threshold.catastrophic_threshold:
        severity_level = 5  # Catastrophic
    elif value >= threshold.emergency_threshold:
        severity_level = 4  # Emergency
    elif value >= threshold.warning_threshold:
        severity_level = 3  # Warning
    elif value >= threshold.watch_threshold:
        severity_level = 2  # Watch
    elif value >= threshold.advisory_threshold:
        severity_level = 1  # Advisory
    
    if severity_level:
        # Check if there's already an active alert for this sensor type
        existing_alert = FloodAlert.objects.filter(
            title__startswith=f"{sensor.sensor_type.title()} Alert",
            active=True
        ).first()
        
        if existing_alert:
            # Update the existing alert if the new severity is higher
            if severity_level > existing_alert.severity_level:
                existing_alert.severity_level = severity_level
                existing_alert.description = f"{sensor.sensor_type.title()} has reached {value} {threshold.unit}, which exceeds the {get_severity_name(severity_level)} threshold."
                existing_alert.updated_at = timezone.now()
                existing_alert.save()
        else:
            # Create a new alert
            alert = FloodAlert.objects.create(
                title=f"{sensor.sensor_type.title()} Alert: {get_severity_name(severity_level)}",
                description=f"{sensor.sensor_type.title()} has reached {value} {threshold.unit}, which exceeds the {get_severity_name(severity_level)} threshold.",
                severity_level=severity_level,
                active=True
            )
            
            # For simplicity, we'll add all barangays to the alert
            # In a real system, you'd determine which barangays are affected
            barangays = Barangay.objects.all()
            alert.affected_barangays.set(barangays)

def get_severity_name(severity_level):
    """Get the human-readable name for a severity level"""
    severity_names = {
        1: 'Advisory',
        2: 'Watch',
        3: 'Warning',
        4: 'Emergency',
        5: 'Catastrophic'
    }
    return severity_names.get(severity_level, 'Unknown')

class MunicipalityViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for municipalities"""
    queryset = Municipality.objects.all()
    serializer_class = MunicipalitySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Municipality.objects.all()
        name = self.request.query_params.get('name', None)
        province = self.request.query_params.get('province', None)
        is_active = self.request.query_params.get('is_active', None)
        
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        if province:
            queryset = queryset.filter(province__icontains=province)
        
        if is_active:
            is_active_bool = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active_bool)
            
        return queryset

class BarangayViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for barangays"""
    queryset = Barangay.objects.all()
    serializer_class = BarangaySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Barangay.objects.all()
        name = self.request.query_params.get('name', None)
        affected = self.request.query_params.get('affected', None)
        municipality_id = self.request.query_params.get('municipality_id', None)
        
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        if municipality_id:
            queryset = queryset.filter(municipality_id=municipality_id)
            
        if affected and affected.lower() == 'true':
            # Get barangays affected by active alerts
            active_alerts = FloodAlert.objects.filter(active=True)
            queryset = queryset.filter(flood_alerts__in=active_alerts).distinct()
            
        return queryset

class FloodAlertViewSet(viewsets.ModelViewSet):
    """API endpoint for flood alerts"""
    queryset = FloodAlert.objects.all().order_by('-issued_at')
    serializer_class = FloodAlertSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = FloodAlert.objects.all().order_by('-issued_at')
        active = self.request.query_params.get('active', None)
        severity = self.request.query_params.get('severity', None)
        municipality_id = self.request.query_params.get('municipality_id', None)
        barangay_id = self.request.query_params.get('barangay_id', None)
        
        if active:
            active_bool = active.lower() == 'true'
            queryset = queryset.filter(active=active_bool)
        
        if severity:
            queryset = queryset.filter(severity_level=severity)
            
        if municipality_id:
            # Filter alerts by affected barangays within the municipality
            queryset = queryset.filter(affected_barangays__municipality_id=municipality_id).distinct()
        
        if barangay_id:
            queryset = queryset.filter(affected_barangays__id=barangay_id)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)

class FloodRiskZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for flood risk zones"""
    queryset = FloodRiskZone.objects.all()
    serializer_class = FloodRiskZoneSerializer
    permission_classes = [permissions.AllowAny]

class ThresholdSettingViewSet(viewsets.ModelViewSet):
    """API endpoint for threshold settings"""
    queryset = ThresholdSetting.objects.all()
    serializer_class = ThresholdSettingSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        serializer.save(last_updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(last_updated_by=self.request.user)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def compare_prediction_algorithms(request):
    """API endpoint for comparing predictions from different ML algorithms"""
    
    # Get location filters from request parameters
    municipality_id = request.GET.get('municipality_id', None)
    barangay_id = request.GET.get('barangay_id', None)
    
    # Get the algorithms to compare
    algorithms = request.GET.getlist('algorithms', [])
    
    # Default to comparing all available algorithms if none specified
    if not algorithms:
        algorithms = ['random_forest']
        if ADVANCED_ALGORITHMS_AVAILABLE:
            algorithms.extend(['gradient_boosting', 'svm'])
            if TENSORFLOW_AVAILABLE:
                algorithms.append('lstm')
    
    # Query filters to apply to sensor data - same as flood_prediction
    sensor_filters = {}
    
    # Apply location filters if provided
    municipality = None
    if municipality_id:
        try:
            # Get the municipality
            municipality = Municipality.objects.get(id=municipality_id)
            # Filter sensors by municipality
            sensor_filters['sensor__municipality'] = municipality
        except Municipality.DoesNotExist:
            pass
    
    barangay = None
    if barangay_id:
        try:
            # Get the barangay
            barangay = Barangay.objects.get(id=barangay_id)
            # Filter sensors by barangay
            sensor_filters['sensor__barangay'] = barangay
        except Barangay.DoesNotExist:
            pass
    
    # Get recent rainfall data
    end_date = timezone.now()
    start_date_24h = end_date - timedelta(hours=24)
    start_date_48h = end_date - timedelta(hours=48)
    start_date_7d = end_date - timedelta(days=7)
    
    # Get rainfall data for different time periods
    rainfall_filters_24h = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_24h,
        'timestamp__lte': end_date
    }
    rainfall_filters_24h.update(sensor_filters)  # Add location filters
    
    rainfall_24h = SensorData.objects.filter(
        **rainfall_filters_24h
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    rainfall_filters_48h = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_48h,
        'timestamp__lte': end_date
    }
    rainfall_filters_48h.update(sensor_filters)  # Add location filters
    
    rainfall_48h = SensorData.objects.filter(
        **rainfall_filters_48h
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    rainfall_filters_7d = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_7d,
        'timestamp__lte': end_date
    }
    rainfall_filters_7d.update(sensor_filters)  # Add location filters
    
    rainfall_7d = SensorData.objects.filter(
        **rainfall_filters_7d
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    # Get water level, soil saturation, and temperature data (same as in flood_prediction)
    water_level_filters = {
        'sensor__sensor_type': 'water_level',
        'timestamp__gte': start_date_24h
    }
    water_level_filters.update(sensor_filters)  # Add location filters
    
    water_level_data = SensorData.objects.filter(
        **water_level_filters
    ).order_by('-timestamp')
    
    water_level_current = 0
    water_level_24h_ago = 0
    
    # Get current water level and water level 24 hours ago
    if water_level_data.exists():
        water_level_current = water_level_data.first().value
        
        # Get water level 24 hours ago (approximately)
        old_water_level_data = water_level_data.filter(timestamp__lte=start_date_24h + timedelta(hours=1)).order_by('-timestamp').first()
        if old_water_level_data:
            water_level_24h_ago = old_water_level_data.value
    
    # Calculate water level change in 24 hours
    water_level_change_24h = water_level_current - water_level_24h_ago
    
    # Get soil saturation (using humidity as a proxy in our system)
    humidity_filters = {
        'sensor__sensor_type': 'humidity',
        'timestamp__gte': start_date_24h
    }
    humidity_filters.update(sensor_filters)  # Add location filters
    
    humidity_data = SensorData.objects.filter(
        **humidity_filters
    ).order_by('-timestamp')
    
    soil_saturation = 0
    
    if humidity_data.exists():
        # Using humidity as a proxy for soil saturation
        soil_saturation = humidity_data.first().value
    
    # Get temperature data
    temp_filters = {
        'sensor__sensor_type': 'temperature',
        'timestamp__gte': start_date_24h
    }
    temp_filters.update(sensor_filters)  # Add location filters
    
    temp_data = SensorData.objects.filter(
        **temp_filters
    ).order_by('-timestamp')
    
    temperature_value = 25  # Default temperature
    
    if temp_data.exists():
        temperature_value = temp_data.first().value
    
    # Create input data for ML prediction model
    input_data = {
        'rainfall_24h': rainfall_24h['total'] if rainfall_24h['total'] else 0,
        'rainfall_48h': rainfall_48h['total'] if rainfall_48h['total'] else 0,
        'rainfall_7d': rainfall_7d['total'] if rainfall_7d['total'] else 0,
        'water_level': water_level_current,
        'water_level_change_24h': water_level_change_24h,
        'temperature': temperature_value,
        'humidity': soil_saturation,
        'soil_saturation': soil_saturation,
        # Use a default elevation for the selected area
        'elevation': 25 if municipality else 20,
        # Add the month and day for seasonal patterns
        'month': end_date.month,
        'day_of_year': end_date.timetuple().tm_yday,
        # Historical floods (this would come from a database in a real system)
        'historical_floods_count': 2 if barangay_id else 1
    }
    
    logger.info(f"Input data for ML prediction comparison: {input_data}")
    
    # Compare predictions from different algorithms
    comparison_results = []
    
    for algorithm in algorithms:
        try:
            # Use the ML model to predict flood probability with this algorithm
            ml_prediction = predict_flood_probability(input_data, classification_algorithm=algorithm)
            logger.info(f"ML Prediction results using {algorithm} algorithm: {ml_prediction}")
            
            # Format the prediction result with algorithm info
            algorithm_result = {
                'algorithm': algorithm,
                'probability': ml_prediction['probability'],
                'severity_level': ml_prediction['severity_level'],
                'severity_name': get_severity_name(ml_prediction['severity_level']),
                'hours_to_flood': ml_prediction['hours_to_flood'],
                'impact': ml_prediction['impact'],
                'contributing_factors': ml_prediction['contributing_factors']
            }
            
            comparison_results.append(algorithm_result)
        except Exception as e:
            logger.error(f"Error using {algorithm} for prediction: {e}")
            # Skip this algorithm and continue with others
            comparison_results.append({
                'algorithm': algorithm,
                'error': str(e),
                'status': 'failed'
            })
    
    # Return the comparison results
    return Response({
        'input_data': input_data,
        'available_algorithms': algorithms,
        'results': comparison_results,
        'location': {
            'municipality': municipality.name if municipality else None,
            'municipality_id': municipality.id if municipality else None,
            'barangay': barangay.name if barangay else None,
            'barangay_id': barangay.id if barangay else None
        },
        'timestamp': end_date,
        'default_algorithm': DEFAULT_CLASSIFICATION_ALGORITHM
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def flood_prediction(request):
    """API endpoint for flood prediction based on real-time sensor data using ML models"""
    
    # Get location filters from request parameters
    municipality_id = request.GET.get('municipality_id', None)
    barangay_id = request.GET.get('barangay_id', None)
    algorithm = request.GET.get('algorithm', None)  # Get algorithm selection if provided
    
    # Query filters to apply to sensor data
    sensor_filters = {}
    
    # Apply location filters if provided
    municipality = None
    if municipality_id:
        try:
            # Get the municipality
            municipality = Municipality.objects.get(id=municipality_id)
            # Filter sensors by municipality
            sensor_filters['sensor__municipality'] = municipality
        except Municipality.DoesNotExist:
            pass
    
    barangay = None
    if barangay_id:
        try:
            # Get the barangay
            barangay = Barangay.objects.get(id=barangay_id)
            # Filter sensors by barangay
            sensor_filters['sensor__barangay'] = barangay
        except Barangay.DoesNotExist:
            pass
    
    # Get recent rainfall data
    end_date = timezone.now()
    start_date_24h = end_date - timedelta(hours=24)
    start_date_48h = end_date - timedelta(hours=48)
    start_date_7d = end_date - timedelta(days=7)
    start_date_72h = end_date - timedelta(hours=72) # For backward compatibility
    
    # Get rainfall data for different time periods
    rainfall_filters_24h = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_24h,
        'timestamp__lte': end_date
    }
    rainfall_filters_24h.update(sensor_filters)  # Add location filters
    
    rainfall_24h = SensorData.objects.filter(
        **rainfall_filters_24h
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    rainfall_filters_48h = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_48h,
        'timestamp__lte': end_date
    }
    rainfall_filters_48h.update(sensor_filters)  # Add location filters
    
    rainfall_48h = SensorData.objects.filter(
        **rainfall_filters_48h
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    rainfall_filters_7d = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_7d,
        'timestamp__lte': end_date
    }
    rainfall_filters_7d.update(sensor_filters)  # Add location filters
    
    rainfall_7d = SensorData.objects.filter(
        **rainfall_filters_7d
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    # For backward compatibility
    rainfall_filters_72h = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_72h,
        'timestamp__lte': end_date
    }
    rainfall_filters_72h.update(sensor_filters)
    
    rainfall_72h = SensorData.objects.filter(
        **rainfall_filters_72h
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    # Get water level data
    water_level_filters = {
        'sensor__sensor_type': 'water_level',
        'timestamp__gte': start_date_24h
    }
    water_level_filters.update(sensor_filters)  # Add location filters
    
    water_level_data = SensorData.objects.filter(
        **water_level_filters
    ).order_by('-timestamp')
    
    water_level_current = 0
    water_level_24h_ago = 0
    
    # Get current water level and water level 24 hours ago
    if water_level_data.exists():
        water_level_current = water_level_data.first().value
        
        # Get water level 24 hours ago (approximately)
        old_water_level_data = water_level_data.filter(timestamp__lte=start_date_24h + timedelta(hours=1)).order_by('-timestamp').first()
        if old_water_level_data:
            water_level_24h_ago = old_water_level_data.value
    
    # Calculate water level change in 24 hours
    water_level_change_24h = water_level_current - water_level_24h_ago
    
    # Get soil saturation (using humidity as a proxy in our system)
    humidity_filters = {
        'sensor__sensor_type': 'humidity',
        'timestamp__gte': start_date_24h
    }
    humidity_filters.update(sensor_filters)  # Add location filters
    
    humidity_data = SensorData.objects.filter(
        **humidity_filters
    ).order_by('-timestamp')
    
    soil_saturation = 0
    
    if humidity_data.exists():
        # Using humidity as a proxy for soil saturation
        soil_saturation = humidity_data.first().value
    
    # Get temperature data
    temp_filters = {
        'sensor__sensor_type': 'temperature',
        'timestamp__gte': start_date_24h
    }
    temp_filters.update(sensor_filters)  # Add location filters
    
    temp_data = SensorData.objects.filter(
        **temp_filters
    ).order_by('-timestamp')
    
    temperature_value = 25  # Default temperature
    
    if temp_data.exists():
        temperature_value = temp_data.first().value
        
    # For backward compatibility
    humidity = {'current': soil_saturation, 'avg': soil_saturation}
    temperature = {'current': temperature_value, 'avg': temperature_value}
    water_level = {'current': water_level_current, 'avg': water_level_current}
    
    # Create input data for ML prediction model
    input_data = {
        'rainfall_24h': rainfall_24h['total'] if rainfall_24h['total'] else 0,
        'rainfall_48h': rainfall_48h['total'] if rainfall_48h['total'] else 0,
        'rainfall_7d': rainfall_7d['total'] if rainfall_7d['total'] else 0,
        'water_level': water_level_current,
        'water_level_change_24h': water_level_change_24h,
        'temperature': temperature_value,
        'humidity': soil_saturation,
        'soil_saturation': soil_saturation,
        # Use a default elevation for the selected area
        'elevation': 25 if municipality else 20,
        # Add the month and day for seasonal patterns
        'month': end_date.month,
        'day_of_year': end_date.timetuple().tm_yday,
        # Historical floods (this would come from a database in a real system)
        'historical_floods_count': 2 if barangay_id else 1
    }
    
    logger.info(f"Input data for ML prediction: {input_data}")
    
    try:
        # Use the ML model to predict flood probability
        # If algorithm is specified and supported, use it
        ml_prediction = predict_flood_probability(input_data, classification_algorithm=algorithm) if algorithm else predict_flood_probability(input_data)
        logger.info(f"ML Prediction results using {algorithm if algorithm else 'default'} algorithm: {ml_prediction}")
        
        # Extract prediction data
        probability = ml_prediction['probability']
        impact = ml_prediction['impact']
        hours_to_flood = ml_prediction['hours_to_flood']
        factors = ml_prediction['contributing_factors']
        severity_level = ml_prediction['severity_level']
        
    except Exception as e:
        logger.error(f"Error using ML model for prediction: {e}")
        
        # Fall back to the heuristic model if ML fails
        logger.info("Falling back to heuristic model for prediction")
        
        # Initialize probability
        probability = 0
        
        # Factor 1: Recent heavy rainfall (24-hour)
        if rainfall_24h['total']:
            if rainfall_24h['total'] > 50:  # More than 50mm in 24 hours is significant
                probability += 30
            elif rainfall_24h['total'] > 25:
                probability += 20
            elif rainfall_24h['total'] > 10:
                probability += 10
        
        # Factor 2: Sustained rainfall (72-hour)
        if rainfall_72h['total']:
            if rainfall_72h['total'] > 100:  # More than 100mm in 72 hours
                probability += 25
            elif rainfall_72h['total'] > 50:
                probability += 15
            elif rainfall_72h['total'] > 25:
                probability += 5
        
        # Factor 3: Current water level
        if water_level['current']:
            if water_level['current'] > 1.5:  # Above 1.5m is high
                probability += 30
            elif water_level['current'] > 1.0:
                probability += 20
            elif water_level['current'] > 0.5:
                probability += 10
        
        # Factor 4: Soil saturation (using humidity as a proxy)
        if humidity['current']:
            if humidity['current'] > 90:  # Very humid/saturated soil
                probability += 15
            elif humidity['current'] > 80:
                probability += 10
            elif humidity['current'] > 70:
                probability += 5
        
        # Cap the probability
        probability = min(probability, 100)
        
        # Based on probability, calculate ETA
        hours_to_flood = None
        if probability >= 60:
            # Estimate hours to flood based on current water level and rainfall rate
            if water_level['current'] and rainfall_24h['avg']:
                # Simple formula: time to flood decreases with higher water level and rainfall rate
                current_level = water_level['current']
                target_level = 1.8  # assumed flood level
                level_difference = max(0, target_level - current_level)
                
                rainfall_rate = rainfall_24h['avg'] / 24  # mm per hour
                if rainfall_rate > 0:
                    # Simplified conversion from rainfall to water level rise
                    # This would be more complex in a real model
                    estimated_rise_rate = rainfall_rate * 0.02  # 1mm rain -> 0.02m water rise
                    
                    if estimated_rise_rate > 0:
                        hours_to_flood = level_difference / estimated_rise_rate
                        hours_to_flood = max(1, min(48, hours_to_flood))  # Cap between 1-48 hours
        
        # Determine contributing factors based on real data
        factors = []
        
        if rainfall_24h['total'] and rainfall_24h['total'] > 10:
            factors.append(f"Rainfall in the past 24 hours: {rainfall_24h['total']:.1f}mm")
            
        if rainfall_72h['total'] and rainfall_72h['total'] > 30:
            factors.append(f"Sustained rainfall over 72 hours: {rainfall_72h['total']:.1f}mm")
            
        if water_level['current'] and water_level['current'] > 0.8:
            factors.append(f"Elevated water level: {water_level['current']:.2f}m")
            
        if humidity['current'] and humidity['current'] > 70:
            factors.append(f"High soil moisture/humidity: {humidity['current']:.0f}%")
        
        if rainfall_24h['max'] and rainfall_24h['max'] > 5:
            factors.append(f"Heavy rainfall intensity: {rainfall_24h['max']:.1f}mm")
            
        # If we don't have enough factors, add a default
        if len(factors) < 2:
            if probability < 30:
                factors.append("No significant contributing factors identified")
            else:
                factors.append("Limited sensor data available for analysis")
        
        # Calculate flood impact based on probability
        impact = ""
        if probability >= 75:
            impact = "Severe flooding likely with significant impact to infrastructure and possible evacuation requirements."
            severity_level = 4  # Emergency
        elif probability >= 60:
            impact = "Moderate to severe flooding expected with potential property damage and road closures."
            severity_level = 3  # Warning
        elif probability >= 50:
            impact = "Moderate flooding expected in low-lying areas with potential minor property damage."
            severity_level = 2  # Watch
        elif probability >= 30:
            impact = "Minor flooding possible in flood-prone areas, general population unlikely to be affected."
            severity_level = 1  # Advisory
        else:
            impact = "No significant flooding expected under current conditions."
            severity_level = 0  # Normal
    
    # Find potentially affected barangays using the ML model if available
    affected_barangays = []
    
    try:
        # Try to use the ML model to get affected barangays first
        if probability >= 30 and municipality_id:
            ml_affected_barangays = ml_get_affected_barangays(municipality_id=municipality_id, probability_threshold=30)
            if ml_affected_barangays:
                logger.info(f"Using ML model to get affected barangays: {len(ml_affected_barangays)} found")
                affected_barangays = ml_affected_barangays
    except Exception as e:
        logger.error(f"Error using ML model for affected barangays: {e}")
    
    # If ML model didn't find any barangays or failed, fall back to the traditional method
    if not affected_barangays and probability >= 30:
        logger.info("Using traditional method to get affected barangays")
        # In a real system, we would use more sophisticated logic to determine affected areas
        # For now, we'll query barangays based on predicted severity level
        # Get barangays with recent alerts of this severity or higher
        recent_alert_filters = {
            'severity_level__gte': severity_level,
            'issued_at__gte': start_date_72h
        }
        
        # If a municipality filter was provided, get alerts for that municipality's barangays
        if municipality_id:
            try:
                municipality = Municipality.objects.get(id=municipality_id)
                # Get all barangays in this municipality
                municipality_barangays = Barangay.objects.filter(municipality=municipality).values_list('id', flat=True)
                # Only include alerts that affect at least one barangay in this municipality
                recent_alert_filters['affected_barangays__in'] = municipality_barangays
            except Municipality.DoesNotExist:
                pass
        
        # If a specific barangay was requested, only get alerts for that barangay
        if barangay_id:
            try:
                barangay = Barangay.objects.get(id=barangay_id)
                recent_alert_filters['affected_barangays'] = barangay
            except Barangay.DoesNotExist:
                pass
        
        recent_alerts = FloodAlert.objects.filter(**recent_alert_filters)
        
        if recent_alerts.exists():
            # Use barangays from similar past alerts
            barangay_ids = set()
            for alert in recent_alerts:
                barangay_ids.update(alert.affected_barangays.values_list('id', flat=True))
                
            barangays = Barangay.objects.filter(id__in=barangay_ids)
        else:
            # Fallback to barangays near water sensors with high readings
            if water_level['current'] and water_level['current'] > 0.5:
                # Get sensors with high water level readings
                high_water_sensor_filters = {
                    'sensor__sensor_type': 'water_level',
                    'value__gte': 0.5,
                    'timestamp__gte': start_date_24h
                }
                high_water_sensor_filters.update(sensor_filters)  # Add location filters
                
                high_water_sensors = SensorData.objects.filter(
                    **high_water_sensor_filters
                ).values_list('sensor_id', flat=True).distinct()
                
                # Get barangays from the requested municipality or a subset of all barangays
                barangay_filters = {}
                
                # If a municipality filter was provided, use it for barangays too
                if municipality_id:
                    try:
                        municipality = Municipality.objects.get(id=municipality_id)
                        barangay_filters['municipality'] = municipality
                    except Municipality.DoesNotExist:
                        pass
                        
                # If a specific barangay was requested, prioritize it
                if barangay_id:
                    try:
                        specific_barangay = Barangay.objects.get(id=barangay_id)
                        barangays = [specific_barangay]
                    except Barangay.DoesNotExist:
                        # Fall back to filtered barangays
                        barangays = Barangay.objects.filter(**barangay_filters).order_by('name')[:5]
                else:
                    # Get barangays based on municipality filter
                    barangays = Barangay.objects.filter(**barangay_filters).order_by('name')[:5]
            else:
                # Get a smaller set of barangays if water level is not high
                barangay_filters = {}
                
                # If a municipality filter was provided, use it for barangays too
                if municipality_id:
                    try:
                        municipality = Municipality.objects.get(id=municipality_id)
                        barangay_filters['municipality'] = municipality
                    except Municipality.DoesNotExist:
                        pass
                
                if barangay_id:
                    try:
                        specific_barangay = Barangay.objects.get(id=barangay_id)
                        barangays = [specific_barangay]
                    except Barangay.DoesNotExist:
                        barangays = Barangay.objects.filter(**barangay_filters).order_by('name')[:3]
                else:
                    barangays = Barangay.objects.filter(**barangay_filters).order_by('name')[:3]
        
            # Format barangay data for response if we didn't get from ML model
            if not affected_barangays:
                for barangay in barangays:
                    risk_level = "High" if probability >= 70 else ("Moderate" if probability >= 40 else "Low")
                    evacuation_centers = 3 if risk_level == "High" else (2 if risk_level == "Moderate" else 1)
                    
                    affected_barangays.append({
                        "id": barangay.id,
                        "name": barangay.name,
                        "municipality": barangay.municipality.name,
                        "population": barangay.population,
                        "risk_level": risk_level,
                        "evacuation_centers": evacuation_centers
                    })
    
    # Calculate flood time if hours_to_flood is available
    flood_time = None
    if hours_to_flood:
        flood_time = timezone.now() + timedelta(hours=hours_to_flood)
    
    # Prepare and return the prediction response
    prediction_data = {
        "probability": probability,
        "severity_level": severity_level,
        "impact": impact,
        "hours_to_flood": hours_to_flood,
        "flood_time": flood_time.isoformat() if flood_time else None,
        "contributing_factors": factors,
        "affected_barangays": affected_barangays,
        "last_updated": timezone.now().isoformat(),
        "rainfall_24h": rainfall_24h['total'] if rainfall_24h['total'] else 0,
        "water_level": water_level['current'] if water_level['current'] else 0,
        "prediction_source": "machine_learning" if 'ml_prediction' in locals() else "heuristic"
    }
    
    return Response(prediction_data)


class ResilienceScoreViewSet(viewsets.ModelViewSet):
    """API endpoint for community resilience scores"""
    queryset = ResilienceScore.objects.all().order_by('-assessment_date')
    serializer_class = ResilienceScoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Set the assessed_by field to the current user
        serializer.save(assessed_by=self.request.user)
        
    def perform_update(self, serializer):
        # Don't change the assessed_by field on updates
        serializer.save()
    
    def get_queryset(self):
        queryset = ResilienceScore.objects.all().order_by('-assessment_date')
        
        # Filter parameters
        municipality_id = self.request.query_params.get('municipality_id', None)
        barangay_id = self.request.query_params.get('barangay_id', None)
        is_current = self.request.query_params.get('is_current', None)
        min_score = self.request.query_params.get('min_score', None)
        max_score = self.request.query_params.get('max_score', None)
        category = self.request.query_params.get('category', None)
        assessed_after = self.request.query_params.get('assessed_after', None)
        assessed_before = self.request.query_params.get('assessed_before', None)
        
        # Apply filters
        if municipality_id:
            queryset = queryset.filter(municipality_id=municipality_id)
        
        if barangay_id:
            queryset = queryset.filter(barangay_id=barangay_id)
        
        if is_current:
            is_current_bool = is_current.lower() == 'true'
            queryset = queryset.filter(is_current=is_current_bool)
        
        if min_score:
            queryset = queryset.filter(overall_score__gte=float(min_score))
        
        if max_score:
            queryset = queryset.filter(overall_score__lte=float(max_score))
        
        if category:
            queryset = queryset.filter(resilience_category=category)
        
        if assessed_after:
            queryset = queryset.filter(assessment_date__gte=assessed_after)
        
        if assessed_before:
            queryset = queryset.filter(assessment_date__lte=assessed_before)
            
        return queryset
    
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_map_data(request):
    """API endpoint for consolidated map data including sensors, risk zones, and barangays"""
    # Get filter parameters
    municipality_id = request.GET.get('municipality_id', None)
    barangay_id = request.GET.get('barangay_id', None)
    
    # Base querysets
    sensors_queryset = Sensor.objects.filter(active=True)
    zones_queryset = FloodRiskZone.objects.all()
    barangays_queryset = Barangay.objects.all()
    
    # Apply filters if provided
    if municipality_id:
        barangays_queryset = barangays_queryset.filter(municipality_id=municipality_id)
        # For sensors and zones, we need to filter based on geographical coordinates
        # In a real system with proper GIS, this would use spatial queries
        # For this system, we'll just filter sensors by municipality association
        sensors_queryset = sensors_queryset.filter(
            Q(municipality_id=municipality_id) | Q(municipality_id__isnull=True))
        
        # For risk zones, we'll rely on the front-end to display only relevant zones
        # But we could add logic here to filter zones by municipality bounds
        
    if barangay_id:
        barangays_queryset = barangays_queryset.filter(id=barangay_id)
        # Similarly, filter sensors by barangay association
        sensors_queryset = sensors_queryset.filter(
            Q(barangay_id=barangay_id) | Q(barangay_id__isnull=True))
    
    # Prepare sensor data with latest readings
    sensor_data = []
    for sensor in sensors_queryset:
        # Get the latest reading for this sensor
        latest_reading = SensorData.objects.filter(sensor=sensor).order_by('-timestamp').first()
        
        # Prepare the sensor info with coordinates and value
        sensor_info = {
            'id': sensor.id,
            'name': sensor.name,
            'type': sensor.sensor_type,
            'lat': sensor.latitude,
            'lng': sensor.longitude,
            'unit': sensor.unit,
            'value': latest_reading.value if latest_reading else None,
            'timestamp': latest_reading.timestamp if latest_reading else None,
            'municipality_id': sensor.municipality_id,
            'barangay_id': sensor.barangay_id
        }
        
        sensor_data.append(sensor_info)
    
    # Prepare risk zone data
    zone_data = []
    for zone in zones_queryset:
        zone_info = {
            'id': zone.id,
            'name': zone.name,
            'severity': zone.severity_level,
            'geojson': zone.geojson,
            'municipality_id': zone.municipality_id if hasattr(zone, 'municipality_id') else None,
            'barangay_id': zone.barangay_id if hasattr(zone, 'barangay_id') else None
        }
        
        zone_data.append(zone_info)
    
    # Prepare barangay data with flood risk levels
    barangay_data = []
    for barangay in barangays_queryset:
        # In a real system, this would be calculated based on sensor readings,
        # active alerts, and historical data for this specific barangay
        # For now, we'll use a simplified approach
        
        # Check if there are any active alerts for this barangay
        active_alerts = FloodAlert.objects.filter(
            active=True,
            affected_barangays=barangay
        ).order_by('-severity_level')
        
        # Determine severity based on the highest alert level
        severity = 0
        if active_alerts.exists():
            severity = active_alerts.first().severity_level
        
        # Add some basic severity for demonstration if no alerts
        # This would normally be based on real-time risk analysis
        if severity == 0:
            # Create a deterministic but varied severity based on barangay id
            # This ensures consistent display while testing different views
            severity = (barangay.id % 5) if barangay.id % 7 == 0 else 0
        
        barangay_info = {
            'id': barangay.id,
            'name': barangay.name,
            'municipality_id': barangay.municipality_id,
            'municipality_name': barangay.municipality.name,
            'population': barangay.population,
            'contact_person': barangay.contact_person,
            'contact_number': barangay.contact_number,
            'lat': barangay.latitude,
            'lng': barangay.longitude,
            'severity': severity  # 0-5 scale of flood risk
        }
        
        barangay_data.append(barangay_info)
    
    return Response({
        'sensors': sensor_data,
        'zones': zone_data,
        'barangays': barangay_data
    })
