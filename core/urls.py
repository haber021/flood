from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    
    # Main application URLs
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('prediction/', views.prediction_page, name='prediction_page'),
    path('prediction/create-alert/', views.create_alert, name='create_alert'),
    path('barangays/', views.barangays_page, name='barangays_page'),
    path('barangays/<int:barangay_id>/', views.barangay_detail, name='barangay_detail'),
    path('notifications/', views.notifications_page, name='notifications_page'),
    path('config/', views.config_page, name='config_page'),
    
    # API endpoints for frontend
    path('api/chart-data/', views.get_chart_data, name='get_chart_data'),
    path('api/map-data/', views.get_map_data, name='get_map_data'),
]
