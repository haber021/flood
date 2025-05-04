from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth import login
from django.contrib.auth.forms import PasswordResetForm
from django.contrib import messages
from django.db.models import Avg, Max, Min
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from .models import (
    Sensor, SensorData, Barangay, FloodRiskZone, 
    FloodAlert, ThresholdSetting, NotificationLog, EmergencyContact
)
from .forms import FloodAlertForm, ThresholdSettingForm, BarangaySearchForm, RegisterForm

class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

class CustomPasswordResetView(PasswordResetView):
    template_name = 'password_reset.html'
    form_class = PasswordResetForm
    success_url = '/login/'

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately after registration
            login(request, user)
            messages.success(request, f'Account created for {user.username}!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'register.html', {'form': form})

@login_required
def dashboard(request):
    """Main dashboard view showing all real-time data and visualizations"""
    # Get latest sensor readings
    latest_temperature = SensorData.objects.filter(
        sensor__sensor_type='temperature'
    ).order_by('-timestamp').first()
    
    latest_humidity = SensorData.objects.filter(
        sensor__sensor_type='humidity'
    ).order_by('-timestamp').first()
    
    latest_rainfall = SensorData.objects.filter(
        sensor__sensor_type='rainfall'
    ).order_by('-timestamp').first()
    
    latest_water_level = SensorData.objects.filter(
        sensor__sensor_type='water_level'
    ).order_by('-timestamp').first()
    
    latest_wind_speed = SensorData.objects.filter(
        sensor__sensor_type='wind_speed'
    ).order_by('-timestamp').first()
    
    # Get active alerts
    active_alerts = FloodAlert.objects.filter(active=True).order_by('-severity_level')
    
    # Get sensor locations for map
    sensors = Sensor.objects.filter(active=True)
    
    # Get flood risk zones for map
    flood_zones = FloodRiskZone.objects.all()
    
    context = {
        'latest_temperature': latest_temperature,
        'latest_humidity': latest_humidity,
        'latest_rainfall': latest_rainfall,
        'latest_water_level': latest_water_level,
        'latest_wind_speed': latest_wind_speed,
        'active_alerts': active_alerts,
        'sensors': sensors,
        'flood_zones': flood_zones,
        'page': 'dashboard'
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def prediction_page(request):
    """Flood prediction page view"""
    # Get historic data for predictions
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    # Get rainfall data for the past week
    rainfall_data = SensorData.objects.filter(
        sensor__sensor_type='rainfall',
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).order_by('timestamp')
    
    # Get water level data for the past week
    water_level_data = SensorData.objects.filter(
        sensor__sensor_type='water_level',
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).order_by('timestamp')
    
    # Current active alerts
    active_alerts = FloodAlert.objects.filter(active=True)
    
    # Get all barangays for the alert form
    barangays = Barangay.objects.all()
    
    # Create new alert form
    form = FloodAlertForm()
    
    context = {
        'rainfall_data': rainfall_data,
        'water_level_data': water_level_data,
        'active_alerts': active_alerts,
        'barangays': barangays,
        'form': form,
        'page': 'prediction'
    }
    
    return render(request, 'prediction.html', context)

@login_required
def create_alert(request):
    """Create a new flood alert"""
    if request.method == 'POST':
        form = FloodAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.issued_by = request.user
            alert.save()
            # Save many-to-many relationships
            form.save_m2m()
            messages.success(request, "Alert created successfully!")
            return redirect('prediction_page')
        else:
            messages.error(request, "Error creating alert. Please check the form.")
    
    return redirect('prediction_page')

@login_required
def barangays_page(request):
    """Barangays management page view"""
    form = BarangaySearchForm(request.GET or None)
    barangays = Barangay.objects.all()
    
    # Apply search and filtering if form is valid
    if form.is_valid():
        name_query = form.cleaned_data.get('name')
        severity_level = form.cleaned_data.get('severity_level')
        
        if name_query:
            barangays = barangays.filter(name__icontains=name_query)
        
        if severity_level:
            # Filter barangays affected by alerts with the given severity level
            barangays = barangays.filter(flood_alerts__severity_level=severity_level).distinct()
    
    context = {
        'barangays': barangays,
        'form': form,
        'page': 'barangays'
    }
    
    return render(request, 'barangays.html', context)

@login_required
def barangay_detail(request, barangay_id):
    """Detailed view for a specific barangay"""
    barangay = get_object_or_404(Barangay, id=barangay_id)
    
    # Get flood alerts affecting this barangay
    alerts = FloodAlert.objects.filter(affected_barangays=barangay).order_by('-issued_at')
    
    # Get emergency contacts for this barangay
    contacts = EmergencyContact.objects.filter(barangay=barangay)
    
    context = {
        'barangay': barangay,
        'alerts': alerts,
        'contacts': contacts,
        'page': 'barangays'
    }
    
    return render(request, 'barangay_detail.html', context)

@login_required
def notifications_page(request):
    """Notifications center page view"""
    # Get all alerts
    alerts = FloodAlert.objects.all().order_by('-issued_at')
    
    # Get notification logs
    notifications = NotificationLog.objects.all().order_by('-sent_at')
    
    # Get emergency contacts
    contacts = EmergencyContact.objects.all()
    
    context = {
        'alerts': alerts,
        'notifications': notifications,
        'contacts': contacts,
        'page': 'notifications'
    }
    
    return render(request, 'notifications.html', context)

@login_required
def config_page(request):
    """System configuration page view"""
    # Get all threshold settings
    thresholds = ThresholdSetting.objects.all()
    
    # Create form for updating thresholds
    form = ThresholdSettingForm()
    
    if request.method == 'POST':
        form = ThresholdSettingForm(request.POST)
        if form.is_valid():
            threshold = form.save(commit=False)
            threshold.last_updated_by = request.user
            
            # Check if a threshold for this parameter already exists
            existing = ThresholdSetting.objects.filter(parameter=threshold.parameter).first()
            if existing:
                # Update existing threshold
                existing.advisory_threshold = threshold.advisory_threshold
                existing.watch_threshold = threshold.watch_threshold
                existing.warning_threshold = threshold.warning_threshold
                existing.emergency_threshold = threshold.emergency_threshold
                existing.catastrophic_threshold = threshold.catastrophic_threshold
                existing.unit = threshold.unit
                existing.last_updated_by = request.user
                existing.save()
                messages.success(request, f"{threshold.parameter} thresholds updated successfully.")
            else:
                # Save new threshold
                threshold.save()
                messages.success(request, f"{threshold.parameter} thresholds created successfully.")
            
            return redirect('config_page')
    
    context = {
        'thresholds': thresholds,
        'form': form,
        'page': 'config'
    }
    
    return render(request, 'config.html', context)

@login_required
def get_chart_data(request):
    """API endpoint to get chart data for the dashboard"""
    chart_type = request.GET.get('type', 'temperature')
    days = int(request.GET.get('days', 1))
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    data = SensorData.objects.filter(
        sensor__sensor_type=chart_type,
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).order_by('timestamp')
    
    chart_data = {
        'labels': [reading.timestamp.strftime('%Y-%m-%d %H:%M') for reading in data],
        'values': [reading.value for reading in data],
    }
    
    return JsonResponse(chart_data)

@login_required
def get_map_data(request):
    """API endpoint to get map data"""
    # Get sensors for map
    sensors = Sensor.objects.filter(active=True)
    sensor_data = []
    
    for sensor in sensors:
        latest_reading = SensorData.objects.filter(sensor=sensor).order_by('-timestamp').first()
        value = latest_reading.value if latest_reading else None
        
        sensor_data.append({
            'id': sensor.id,
            'name': sensor.name,
            'type': sensor.sensor_type,
            'lat': sensor.latitude,
            'lng': sensor.longitude,
            'value': value,
            'unit': get_unit_for_sensor_type(sensor.sensor_type),
        })
    
    # Get flood risk zones
    zones = FloodRiskZone.objects.all()
    zone_data = []
    
    for zone in zones:
        zone_data.append({
            'id': zone.id,
            'name': zone.name,
            'severity': zone.severity_level,
            'geojson': zone.geojson,
        })
    
    # Get affected barangays
    active_alerts = FloodAlert.objects.filter(active=True)
    affected_barangays = Barangay.objects.filter(flood_alerts__in=active_alerts).distinct()
    barangay_data = []
    
    for barangay in affected_barangays:
        # Get the highest severity alert for this barangay
        highest_severity = barangay.flood_alerts.filter(active=True).aggregate(Max('severity_level'))
        
        barangay_data.append({
            'id': barangay.id,
            'name': barangay.name,
            'population': barangay.population,
            'lat': barangay.latitude,
            'lng': barangay.longitude,
            'severity': highest_severity['severity_level__max'],
        })
    
    map_data = {
        'sensors': sensor_data,
        'zones': zone_data,
        'barangays': barangay_data,
    }
    
    return JsonResponse(map_data)

def get_unit_for_sensor_type(sensor_type):
    """Helper function to get the unit for a sensor type"""
    units = {
        'temperature': '°C',
        'humidity': '%',
        'rainfall': 'mm',
        'water_level': 'm',
        'wind_speed': 'km/h',
    }
    return units.get(sensor_type, '')
