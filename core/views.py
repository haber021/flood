from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth import login
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Avg, Max, Min, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from datetime import timedelta
from .models import (
    Sensor, SensorData, Barangay, FloodRiskZone, Municipality,
    FloodAlert, ThresholdSetting, NotificationLog, EmergencyContact, UserProfile,
    ResilienceScore
)
from .forms import FloodAlertForm, ThresholdSettingForm, BarangaySearchForm, RegisterForm, UserProfileForm

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

def get_chart_data(request):
    """API endpoint to get chart data for the dashboard (no login required)"""
    # This API endpoint is accessible without login for charts visualization
    chart_type = request.GET.get('type', 'temperature')
    days = int(request.GET.get('days', 1))
    historical = request.GET.get('historical', 'false').lower() == 'true'
    
    # Get location filters if provided
    municipality_id = request.GET.get('municipality_id')
    barangay_id = request.GET.get('barangay_id')
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Build the query filter
    filters = {
        'sensor__sensor_type': chart_type,
        'timestamp__gte': start_date,
        'timestamp__lte': end_date
    }
    
    # Add location filters if provided
    if municipality_id:
        filters['sensor__municipality_id'] = municipality_id
    
    if barangay_id:
        filters['sensor__barangay_id'] = barangay_id
    
    data = SensorData.objects.filter(**filters).order_by('timestamp')
    
    # If no data found with municipality filter, try getting global data
    if not data.exists() and municipality_id:
        # Log the fallback for debugging
        print(f"No {chart_type} data found for municipality {municipality_id}, using global data")
        
        # Build a new filter without the municipality filter
        global_filters = {
            'sensor__sensor_type': chart_type,
            'timestamp__gte': start_date,
            'timestamp__lte': end_date
        }
        
        # Get the most recent global data
        global_data = SensorData.objects.filter(**global_filters).order_by('timestamp')
        
        # If global data is found, use it
        if global_data.exists():
            data = global_data
    
    # Format timestamps based on the time range
    if days >= 30:  # Monthly view
        date_format = '%b %d'
    elif days >= 7:  # Weekly view
        date_format = '%b %d'
    elif days > 1:  # Multi-day view
        date_format = '%m/%d %H:%M'
    else:  # Single day view
        date_format = '%H:%M'
    
    chart_data = {
        'labels': [reading.timestamp.strftime('%Y-%m-%d %H:%M') for reading in data],
        'values': [reading.value for reading in data],
    }
    
    # Add historical comparison data if requested
    if historical:
        # In a real app, we would query historical data from previous years
        # For this example, we'll use a simplified approach
        chart_data['historical_values'] = [float(f"{value * 0.85:.2f}") for value in chart_data['values']]
        
        # Add threshold values based on sensor type
        if chart_type == 'water_level':
            chart_data['threshold_value'] = 1.5  # Default flood threshold in meters
        elif chart_type == 'rainfall':
            chart_data['threshold_value'] = 25.0  # Heavy rainfall threshold in mm
    
    return JsonResponse(chart_data)

def get_map_data(request):
    """API endpoint to get map data (no login required)"""
    # This API endpoint is accessible without login for map visualization
    # Optional filters
    barangay_id = request.GET.get('barangay_id', None)
    municipality_id = request.GET.get('municipality_id', None)
    
    # Initialize empty lists to use in JSON response
    sensor_data = []
    zone_data = []
    barangay_data = []
    
    try:
        # Get sensors for map
        sensors = Sensor.objects.filter(active=True)
        if municipality_id:
            # Filter sensors by municipality if requested
            sensors = sensors.filter(Q(municipality_id=municipality_id) | Q(municipality=None))
            
        # Process each sensor
        for sensor in sensors:
            try:
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
            except Exception as e:
                print(f"Error processing sensor {sensor.id}: {str(e)}")
                # Continue to next sensor
        
        # Get flood risk zones
        zones = FloodRiskZone.objects.all()
        
        for zone in zones:
            zone_data.append({
                'id': zone.id,
                'name': zone.name,
                'severity': zone.severity_level,
                'geojson': zone.geojson,
            })
            
        # Get all barangays, filter by municipality if provided
        barangay_queryset = Barangay.objects.all()
        if municipality_id:
            barangay_queryset = barangay_queryset.filter(municipality_id=municipality_id)
        
        # First, get all active alerts
        active_alerts = FloodAlert.objects.filter(active=True)
        if municipality_id:
            active_alerts = active_alerts.filter(affected_barangays__municipality_id=municipality_id).distinct()
        
        # Get affected barangays with their severities
        alert_severity_by_barangay = {}
        for alert in active_alerts:
            for barangay in alert.affected_barangays.all():
                # Track the highest severity level for each barangay
                current_severity = alert_severity_by_barangay.get(barangay.id, 0)
                alert_severity_by_barangay[barangay.id] = max(current_severity, alert.severity_level)
        
        # Build barangay data including all barangays
        for barangay in barangay_queryset:
            # Use the highest severity from alerts, or 0 if not affected
            severity = alert_severity_by_barangay.get(barangay.id, 0)
            
            # Include municipality information
            municipality_name = barangay.municipality.name if barangay.municipality else "-"
            
            barangay_data.append({
                'id': barangay.id,
                'name': barangay.name,
                'population': barangay.population,
                'municipality_id': barangay.municipality_id,
                'municipality_name': municipality_name,
                'lat': barangay.latitude,
                'lng': barangay.longitude,
                'severity': severity,
                # Add extra data
                'contact_person': barangay.contact_person,
                'contact_number': barangay.contact_number
            })
        
        # If barangay_id is provided, focus on that barangay
        if barangay_id:
            try:
                # Convert to integer
                barangay_id = int(barangay_id)
                
                # Find the selected barangay
                selected_barangay = None
                for b in barangay_data:
                    if b['id'] == barangay_id:
                        selected_barangay = b
                        break
                
                if selected_barangay:
                    # Filter sensors and zones to those near the selected barangay
                    # This is a simple approximation - in production, you'd use geospatial queries
                    # For demonstration, we'll just focus on the barangay without filtering
                    pass
            except (ValueError, TypeError):
                # Invalid barangay_id, ignore filtering
                pass
                
    except Exception as e:
        # Log the error but still return what we have
        print(f"Error in get_map_data: {str(e)}")
    
    # Return map data with whatever we've collected
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

def get_latest_sensor_data(request):
    """API endpoint to get the latest sensor data (no login required)"""
    # This API endpoint is accessible without login for dashboard visualization
    # Get limit parameter (default to 5)
    limit = int(request.GET.get('limit', 5))
    
    # Get municipality filter if provided
    municipality_id = request.GET.get('municipality_id')
    
    # Get the latest reading for each sensor type
    latest_readings = []
    
    for sensor_type in ['temperature', 'humidity', 'rainfall', 'water_level', 'wind_speed']:
        # Build the filter
        filters = {'sensor__sensor_type': sensor_type}
        
        # Add municipality filter if provided
        if municipality_id:
            filters['sensor__municipality_id'] = municipality_id
        
        # Get the reading with filters
        reading = SensorData.objects.filter(**filters).order_by('-timestamp').first()
        
        # If no municipality-specific reading, try fallback to global sensors
        if not reading and municipality_id:
            print(f"No {sensor_type} data found for municipality {municipality_id}, using global data")
            reading = SensorData.objects.filter(sensor__sensor_type=sensor_type).order_by('-timestamp').first()
        
        if reading:
            latest_readings.append({
                'id': reading.id,
                'sensor_id': reading.sensor.id,
                'sensor_name': reading.sensor.name,
                'sensor_type': reading.sensor.sensor_type,
                'value': reading.value,
                'timestamp': reading.timestamp,
                'municipality_id': reading.sensor.municipality_id if reading.sensor.municipality else None,
                'municipality_name': reading.sensor.municipality.name if reading.sensor.municipality else 'Global',
                'unit': get_unit_for_sensor_type(reading.sensor.sensor_type)
            })
    
    # Return as JSON
    return JsonResponse({
        'count': len(latest_readings),
        'results': latest_readings[:limit]
    })

def get_flood_alerts(request):
    """API endpoint to get flood alerts (no login required)"""
    # This API endpoint is accessible without login for alerts visualization
    # Check if we only want active alerts
    active_only = request.GET.get('active', 'false').lower() == 'true'
    
    # Get alerts, filtered if needed
    if active_only:
        alerts = FloodAlert.objects.filter(active=True).order_by('-severity_level', '-issued_at')
    else:
        alerts = FloodAlert.objects.all().order_by('-issued_at')
    
    # Format alerts for JSON response
    alert_data = []
    for alert in alerts:
        alert_data.append({
            'id': alert.id,
            'title': alert.title,
            'description': alert.description,
            'severity_level': alert.severity_level,
            'active': alert.active,
            'predicted_flood_time': alert.predicted_flood_time,
            'issued_at': alert.issued_at,
            'updated_at': alert.updated_at,
            'issued_by_username': alert.issued_by.username if alert.issued_by else 'System',
            'affected_barangay_count': alert.affected_barangays.count()
        })
    
    # Return as JSON
    return JsonResponse({
        'count': len(alert_data),
        'results': alert_data
    })


# This function has been moved up to avoid duplication


# User Management and Profile Views

@login_required
def profile(request):
    """User profile page view"""
    user = request.user
    profile = user.profile
    
    context = {
        'user': user,
        'profile': profile,
        'page': 'profile'
    }
    
    return render(request, 'profile.html', context)

@login_required
def edit_profile(request):
    """Edit user profile view"""
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user.profile, user=user)
        if form.is_valid():
            form.save(user=user)
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user.profile, user=user)
    
    context = {
        'form': form,
        'page': 'profile'
    }
    
    return render(request, 'edit_profile.html', context)

# Helper function to check if user is admin or manager
def is_admin_or_manager(user):
    """Check if the user is an admin or flood manager"""
    if user.is_superuser:
        return True
    if hasattr(user, 'profile'):
        return user.profile.role in ['admin', 'manager']
    return False

@login_required
@user_passes_test(is_admin_or_manager)
def user_management(request):
    """User management page for admins and managers"""
    # Get all users
    users = User.objects.all().select_related('profile').order_by('username')
    
    # Handle search and filtering
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    municipality_filter = request.GET.get('municipality', '')
    
    if search_query:
        users = users.filter(Q(username__icontains=search_query) | 
                            Q(first_name__icontains=search_query) | 
                            Q(last_name__icontains=search_query) | 
                            Q(email__icontains=search_query))
    
    if role_filter:
        users = users.filter(profile__role=role_filter)
    
    if municipality_filter:
        users = users.filter(profile__municipality_id=municipality_filter)
    
    # Pagination
    paginator = Paginator(users, 10)  # 10 users per page
    page_number = request.GET.get('page', 1)
    users_page = paginator.get_page(page_number)
    
    # Get all municipalities for the filter
    municipalities = Municipality.objects.filter(is_active=True).order_by('name')
    
    context = {
        'users': users_page,
        'search_query': search_query,
        'role_filter': role_filter,
        'municipality_filter': municipality_filter,
        'municipalities': municipalities,
        'user_roles': UserProfile.USER_ROLES,
        'page': 'user_management'
    }
    
    return render(request, 'user_management.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def view_user(request, user_id):
    """View details of a specific user"""
    viewed_user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    context = {
        'viewed_user': viewed_user,
        'page': 'user_management'
    }
    
    return render(request, 'view_user.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def edit_user(request, user_id):
    """Edit a specific user (admin only)"""
    viewed_user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    # Only superuser can edit other superusers
    if viewed_user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit this user.')
        return redirect('user_management')
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=viewed_user.profile, user=viewed_user)
        if form.is_valid():
            form.save(user=viewed_user)
            messages.success(request, f'User {viewed_user.username} has been updated!')
            return redirect('view_user', user_id=user_id)
    else:
        form = UserProfileForm(instance=viewed_user.profile, user=viewed_user)
    
    context = {
        'form': form,
        'viewed_user': viewed_user,
        'page': 'user_management'
    }
    
    return render(request, 'edit_user.html', context)

@login_required
def resilience_scores_page(request):
    """Community resilience scores view"""
    # Get all resilience scores, prioritizing current scores
    resilience_scores = ResilienceScore.objects.all().order_by('-is_current', '-assessment_date')
    
    # Get location filters from request
    municipality_id = request.GET.get('municipality_id', None)
    barangay_id = request.GET.get('barangay_id', None)
    show_only_current = request.GET.get('current', 'true').lower() == 'true'
    
    # Filter by municipality if specified
    if municipality_id:
        resilience_scores = resilience_scores.filter(municipality_id=municipality_id)
    
    # Filter by barangay if specified
    if barangay_id:
        resilience_scores = resilience_scores.filter(barangay_id=barangay_id)
    
    # Filter to show only current assessments if specified
    if show_only_current:
        resilience_scores = resilience_scores.filter(is_current=True)
    
    # Get all municipalities for filtering
    municipalities = Municipality.objects.all().order_by('name')
    
    # Get barangays belonging to the selected municipality or all if no municipality is selected
    barangay_filter = {}
    if municipality_id:
        barangay_filter['municipality_id'] = municipality_id
    
    barangays = Barangay.objects.filter(**barangay_filter).order_by('name')
    
    # Calculate summary statistics
    avg_scores = {}
    if resilience_scores.exists():
        # Overall average
        avg_scores['overall'] = resilience_scores.aggregate(Avg('overall_score'))['overall_score__avg']
        
        # By component
        avg_scores['infrastructure'] = resilience_scores.aggregate(Avg('infrastructure_score'))['infrastructure_score__avg']
        avg_scores['social'] = resilience_scores.aggregate(Avg('social_capital_score'))['social_capital_score__avg']
        avg_scores['institutional'] = resilience_scores.aggregate(Avg('institutional_score'))['institutional_score__avg']
        avg_scores['economic'] = resilience_scores.aggregate(Avg('economic_score'))['economic_score__avg']
        avg_scores['environmental'] = resilience_scores.aggregate(Avg('environmental_score'))['environmental_score__avg']
    
    context = {
        'resilience_scores': resilience_scores,
        'municipalities': municipalities,
        'barangays': barangays,
        'avg_scores': avg_scores,
        'selected_municipality_id': municipality_id,
        'selected_barangay_id': barangay_id,
        'show_only_current': show_only_current,
        'page': 'resilience'
    }
    
    return render(request, 'resilience_scores.html', context)
