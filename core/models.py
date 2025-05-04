from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Sensor(models.Model):
    """Model for environmental sensors in the system"""
    name = models.CharField(max_length=100)
    sensor_type = models.CharField(max_length=50, choices=[
        ('temperature', 'Temperature'),
        ('humidity', 'Humidity'),
        ('rainfall', 'Rainfall'),
        ('water_level', 'Water Level'),
        ('wind_speed', 'Wind Speed'),
    ])
    latitude = models.FloatField()
    longitude = models.FloatField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.sensor_type})"

class SensorData(models.Model):
    """Model for storing sensor readings"""
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    value = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.sensor.name}: {self.value} ({self.timestamp})"

class Municipality(models.Model):
    """Model for municipality data"""
    name = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    population = models.IntegerField()
    area_sqkm = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}, {self.province}"
    
    class Meta:
        verbose_name_plural = "Municipalities"

class Barangay(models.Model):
    """Model for barangay (neighborhood/village) data"""
    name = models.CharField(max_length=100)
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, related_name='barangays', null=True)
    population = models.IntegerField()
    area_sqkm = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Barangays"

class FloodRiskZone(models.Model):
    """Model for flood risk zones"""
    name = models.CharField(max_length=100)
    severity_level = models.IntegerField(choices=[
        (1, 'Low Risk'),
        (2, 'Medium Risk'),
        (3, 'High Risk'),
        (4, 'Severe Risk'),
        (5, 'Extreme Risk'),
    ])
    description = models.TextField(blank=True, null=True)
    # GeoJSON data for map visualization
    geojson = models.TextField()
    
    def __str__(self):
        return f"{self.name} (Level {self.severity_level})"

class FloodAlert(models.Model):
    """Model for flood alerts/warnings"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity_level = models.IntegerField(choices=[
        (1, 'Advisory'),
        (2, 'Watch'),
        (3, 'Warning'),
        (4, 'Emergency'),
        (5, 'Catastrophic'),
    ])
    active = models.BooleanField(default=True)
    predicted_flood_time = models.DateTimeField(blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    affected_barangays = models.ManyToManyField(Barangay, related_name='flood_alerts')
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.get_severity_level_display()}: {self.title}"
    
    class Meta:
        ordering = ['-issued_at']

class ThresholdSetting(models.Model):
    """Model for threshold settings for alerts"""
    parameter = models.CharField(max_length=50, choices=[
        ('temperature', 'Temperature'),
        ('humidity', 'Humidity'),
        ('rainfall', 'Rainfall'),
        ('water_level', 'Water Level'),
        ('wind_speed', 'Wind Speed'),
    ])
    advisory_threshold = models.FloatField()
    watch_threshold = models.FloatField()
    warning_threshold = models.FloatField()
    emergency_threshold = models.FloatField()
    catastrophic_threshold = models.FloatField()
    unit = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.parameter} Thresholds"
    
    class Meta:
        unique_together = ['parameter']

class NotificationLog(models.Model):
    """Model for logging notifications sent"""
    alert = models.ForeignKey(FloodAlert, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=[
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('app', 'App Notification'),
    ])
    recipient = models.CharField(max_length=100)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    ], default='pending')
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient} at {self.sent_at}"
    
    class Meta:
        ordering = ['-sent_at']

class EmergencyContact(models.Model):
    """Model for emergency contacts"""
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='emergency_contacts', null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.role})"
