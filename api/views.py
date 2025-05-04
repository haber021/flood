from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Max, Avg, Sum, Q, Count, Min
import math
from datetime import timedelta

from core.models import (
    Sensor, SensorData, Municipality, Barangay, FloodRiskZone, 
    FloodAlert, ThresholdSetting, NotificationLog, EmergencyContact
)
from .serializers import (
    SensorSerializer, SensorDataSerializer, MunicipalitySerializer, BarangaySerializer,
    FloodRiskZoneSerializer, FloodAlertSerializer, ThresholdSettingSerializer, 
    NotificationLogSerializer, EmergencyContactSerializer
)

class SensorViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for sensors"""
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = SensorData.objects.all().order_by('-timestamp')
        sensor_id = self.request.query_params.get('sensor_id', None)
        sensor_type = self.request.query_params.get('sensor_type', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        limit = self.request.query_params.get('limit', None)
        
        if sensor_id:
            queryset = queryset.filter(sensor_id=sensor_id)
        
        if sensor_type:
            queryset = queryset.filter(sensor__sensor_type=sensor_type)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        if limit:
            queryset = queryset[:int(limit)]
            
        return queryset

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = FloodAlert.objects.all().order_by('-issued_at')
        active = self.request.query_params.get('active', None)
        severity = self.request.query_params.get('severity', None)
        barangay_id = self.request.query_params.get('barangay_id', None)
        
        if active:
            active_bool = active.lower() == 'true'
            queryset = queryset.filter(active=active_bool)
        
        if severity:
            queryset = queryset.filter(severity_level=severity)
        
        if barangay_id:
            queryset = queryset.filter(affected_barangays__id=barangay_id)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)

class FloodRiskZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for flood risk zones"""
    queryset = FloodRiskZone.objects.all()
    serializer_class = FloodRiskZoneSerializer
    permission_classes = [permissions.IsAuthenticated]

class ThresholdSettingViewSet(viewsets.ModelViewSet):
    """API endpoint for threshold settings"""
    queryset = ThresholdSetting.objects.all()
    serializer_class = ThresholdSettingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(last_updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(last_updated_by=self.request.user)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def flood_prediction(request):
    """API endpoint for flood prediction based on real-time sensor data"""
    
    # Get location filters from request parameters
    municipality_id = request.GET.get('municipality_id', None)
    barangay_id = request.GET.get('barangay_id', None)
    
    # Query filters to apply to sensor data
    sensor_filters = {}
    
    # Apply location filters if provided
    if municipality_id:
        try:
            # Get the municipality
            municipality = Municipality.objects.get(id=municipality_id)
            # Filter sensors by municipality
            sensor_filters['sensor__municipality'] = municipality
        except Municipality.DoesNotExist:
            pass
    
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
    start_date_72h = end_date - timedelta(hours=72)
    
    # Get rainfall data for the past 24 and 72 hours
    rainfall_filters_24h = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_24h,
        'timestamp__lte': end_date
    }
    rainfall_filters_24h.update(sensor_filters)  # Add location filters
    
    rainfall_24h = SensorData.objects.filter(
        **rainfall_filters_24h
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    rainfall_filters_72h = {
        'sensor__sensor_type': 'rainfall',
        'timestamp__gte': start_date_72h,
        'timestamp__lte': end_date
    }
    rainfall_filters_72h.update(sensor_filters)  # Add location filters
    
    rainfall_72h = SensorData.objects.filter(
        **rainfall_filters_72h
    ).aggregate(total=Sum('value'), avg=Avg('value'), max=Max('value'))
    
    # Get water level data
    water_level_filters = {
        'sensor__sensor_type': 'water_level',
        'timestamp__gte': start_date_24h
    }
    water_level_filters.update(sensor_filters)  # Add location filters
    
    water_level = SensorData.objects.filter(
        **water_level_filters
    ).aggregate(current=Max('value'), avg=Avg('value'))
    
    # Get soil saturation (using humidity as a proxy in our system)
    humidity_filters = {
        'sensor__sensor_type': 'humidity',
        'timestamp__gte': start_date_24h
    }
    humidity_filters.update(sensor_filters)  # Add location filters
    
    humidity = SensorData.objects.filter(
        **humidity_filters
    ).aggregate(current=Max('value'), avg=Avg('value'))
    
    # Calculate flood probability based on real data
    # This is a simplified model - a real system would use more complex ML/AI
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
    elif probability >= 50:
        impact = "Moderate flooding expected in low-lying areas with potential minor property damage."
    else:
        impact = "Minor flooding possible in flood-prone areas, general population unlikely to be affected."
    
    # Find potentially affected barangays (in a real system, this would use geospatial analysis)
    affected_barangays = []
    if probability >= 30:
        # In a real system, we would use more sophisticated logic to determine affected areas
        # For now, we'll query barangays based on predicted severity level
        severity_level = 1  # Default to Advisory
        if probability >= 75:
            severity_level = 4  # Emergency
        elif probability >= 60:
            severity_level = 3  # Warning
        elif probability >= 40:
            severity_level = 2  # Watch
            
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
        
        # Format barangay data for response
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
    
    # Prepare and return the prediction response
    prediction_data = {
        "probability": probability,
        "impact": impact,
        "hours_to_flood": hours_to_flood,
        "flood_time": timezone.now() + timedelta(hours=hours_to_flood) if hours_to_flood else None,
        "contributing_factors": factors,
        "affected_barangays": affected_barangays,
        "last_updated": timezone.now().isoformat(),
        "rainfall_24h": rainfall_24h,
        "water_level": water_level['current'] if water_level['current'] else 0
    }
    
    return Response(prediction_data)
