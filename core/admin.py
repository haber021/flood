from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin
from .models import (
    Sensor, SensorData, Municipality, Barangay, FloodRiskZone, 
    FloodAlert, ThresholdSetting, NotificationLog, EmergencyContact, UserProfile
)

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('name', 'sensor_type', 'active', 'last_updated')
    list_filter = ('sensor_type', 'active')
    search_fields = ('name',)

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'value', 'timestamp')
    list_filter = ('sensor__sensor_type', 'timestamp')
    date_hierarchy = 'timestamp'

@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'population', 'contact_person', 'contact_number')
    list_filter = ('province', 'is_active')
    search_fields = ('name', 'province', 'contact_person')

@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality', 'population', 'contact_person', 'contact_number')
    list_filter = ('municipality',)
    search_fields = ('name', 'contact_person')

@admin.register(FloodRiskZone)
class FloodRiskZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'severity_level')
    list_filter = ('severity_level',)
    search_fields = ('name',)

@admin.register(FloodAlert)
class FloodAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity_level', 'active', 'issued_at', 'predicted_flood_time')
    list_filter = ('severity_level', 'active', 'issued_at')
    search_fields = ('title', 'description')
    filter_horizontal = ('affected_barangays',)
    date_hierarchy = 'issued_at'

@admin.register(ThresholdSetting)
class ThresholdSettingAdmin(admin.ModelAdmin):
    list_display = ('parameter', 'advisory_threshold', 'warning_threshold', 'emergency_threshold', 'updated_at')
    list_filter = ('parameter',)

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('alert', 'notification_type', 'recipient', 'status', 'sent_at')
    list_filter = ('notification_type', 'status', 'sent_at')
    search_fields = ('recipient',)
    date_hierarchy = 'sent_at'

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'phone', 'email', 'barangay')
    list_filter = ('role', 'barangay')
    search_fields = ('name', 'role', 'phone', 'email')
    
# Define an inline admin descriptor for UserProfile model
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'

# Define a new User admin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile', )
    
    def get_role(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.get_role_display()
        return '-'
    get_role.short_description = 'Role'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'municipality', 'barangay', 'phone_number', 'receive_alerts')
    list_filter = ('role', 'municipality', 'barangay', 'receive_alerts', 'receive_sms', 'receive_email')
    search_fields = ('user__username', 'user__email', 'phone_number')
    raw_id_fields = ('user',)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
