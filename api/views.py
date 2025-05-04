from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Max
from core.models import (
    Sensor, SensorData, Barangay, FloodRiskZone, 
    FloodAlert, ThresholdSetting, NotificationLog
)
from .serializers import (
    SensorSerializer, SensorDataSerializer, BarangaySerializer,
    FloodRiskZoneSerializer, FloodAlertSerializer, ThresholdSettingSerializer
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

class BarangayViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for barangays"""
    queryset = Barangay.objects.all()
    serializer_class = BarangaySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Barangay.objects.all()
        name = self.request.query_params.get('name', None)
        affected = self.request.query_params.get('affected', None)
        
        if name:
            queryset = queryset.filter(name__icontains=name)
        
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
