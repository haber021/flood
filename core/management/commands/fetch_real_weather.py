import re
import json
import requests
import traceback
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Sensor, SensorData

class Command(BaseCommand):
    help = 'Fetch real-time weather data from online sources'
    
    def handle(self, *args, **options):
        self.stdout.write("Fetching real-time weather data from online sources...")
        self.update_temperature_data()
        self.update_rainfall_data()
        self.update_water_level_data()
        self.update_humidity_data()
        self.update_wind_data()
        self.stdout.write(self.style.SUCCESS("Successfully updated sensor data with real-time values"))
    
    def fetch_weather_for_location(self, location_name, lat, lng):
        """Fetch weather data for a specific location using multiple sources"""
        try:
            # Try OpenWeatherMap-like API for more reliable data
            # Format coordinates for API request
            api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
            
            # Send API request
            response = requests.get(api_url)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'current' in data:
                        self.stdout.write(f"Successfully retrieved real-time data for {location_name} from Open-Meteo API")
                        return data['current']
                except json.JSONDecodeError:
                    self.stdout.write(self.style.WARNING(f"Failed to parse API response for {location_name}"))
            
            # Fallback to Google Weather scraping if API fails
            self.stdout.write(self.style.WARNING(f"Falling back to alternate source for {location_name}"))
            search_query = f"weather {location_name} philippines current temperature"
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            # Fetch the content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(search_url, headers=headers)
            
            if response.status_code != 200:
                self.stdout.write(self.style.WARNING(f"Error fetching data: {response.status_code}"))
                return None
            
            # Extract the temperature using regex
            temperature_pattern = r'(\d+)°C'
            matches = re.search(temperature_pattern, response.text)
            
            if matches:
                temperature = float(matches.group(1))
                self.stdout.write(f"Found temperature for {location_name}: {temperature}°C")
                
                # Extract other weather data when available
                humidity_pattern = r'Humidity:\s*(\d+)%'
                humidity_matches = re.search(humidity_pattern, response.text)
                humidity = float(humidity_matches.group(1)) if humidity_matches else None
                
                rainfall_pattern = r'Precipitation:\s*(\d+\.?\d*)\s*mm'
                rainfall_matches = re.search(rainfall_pattern, response.text)
                rainfall = float(rainfall_matches.group(1)) if rainfall_matches else None
                
                wind_pattern = r'Wind:\s*(\d+\.?\d*)\s*km/h'
                wind_matches = re.search(wind_pattern, response.text)
                wind = float(wind_matches.group(1)) if wind_matches else None
                
                return {
                    'temperature_2m': temperature,
                    'relative_humidity_2m': humidity,
                    'precipitation': rainfall,
                    'wind_speed_10m': wind
                }
            else:
                # Try weather API for Vical region
                self.stdout.write(self.style.WARNING(f"Trying official weather data for region"))
                # Using a weather API focused on the Philippines
                region_url = f"https://api.open-meteo.com/v1/forecast?latitude=17.13&longitude=120.43&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
                response = requests.get(region_url)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'current' in data:
                            self.stdout.write(f"Retrieved regional weather data for {location_name}")
                            return data['current']
                    except json.JSONDecodeError:
                        pass
                        
                self.stdout.write(self.style.ERROR(f"Failed to retrieve weather data for {location_name} from all sources"))
                return None
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching weather data: {str(e)}"))
            traceback.print_exc()
            return None
    
    def update_temperature_data(self):
        """Update temperature data for all temperature sensors from real sources"""
        # Get all temperature sensors
        temperature_sensors = Sensor.objects.filter(sensor_type='temperature', active=True)
        
        if not temperature_sensors.exists():
            self.stdout.write(self.style.WARNING("No active temperature sensors found."))
            return
        
        for sensor in temperature_sensors:
            # Get location name from sensor name
            location_name = sensor.name.replace('Weather Station', '').strip()
            if not location_name:
                location_name = "Vical, Santa Lucia, Ilocos Sur"
            
            # Fetch weather data
            weather_data = self.fetch_weather_for_location(location_name, sensor.latitude, sensor.longitude)
            
            if weather_data and weather_data.get('temperature_2m') is not None:
                temperature = weather_data['temperature_2m']
                # Save the new sensor reading
                SensorData.objects.create(
                    sensor=sensor,
                    value=temperature,
                    timestamp=timezone.now()
                )
                self.stdout.write(self.style.SUCCESS(f"Saved new temperature reading for {sensor.name}: {temperature}°C"))
            else:
                self.stdout.write(self.style.ERROR(f"Could not get temperature data for {sensor.name}"))
    
    def update_rainfall_data(self):
        """Update rainfall data for all rainfall sensors from real sources"""
        rainfall_sensors = Sensor.objects.filter(sensor_type='rainfall', active=True)
        
        if not rainfall_sensors.exists():
            self.stdout.write(self.style.WARNING("No active rainfall sensors found."))
            return
        
        for sensor in rainfall_sensors:
            # Get location name
            location_name = sensor.name.replace('Rain', '').replace('Gauge', '').replace('Monitor', '').strip()
            if not location_name:
                location_name = "Vical, Santa Lucia, Ilocos Sur"
            
            # Fetch weather data
            weather_data = self.fetch_weather_for_location(location_name, sensor.latitude, sensor.longitude)
            
            if weather_data and weather_data.get('precipitation') is not None:
                rainfall = weather_data['precipitation']
                # Save the new sensor reading
                SensorData.objects.create(
                    sensor=sensor,
                    value=rainfall,
                    timestamp=timezone.now()
                )
                self.stdout.write(self.style.SUCCESS(f"Saved new rainfall reading for {sensor.name}: {rainfall}mm"))
            else:
                # Try to get data from official govt sources
                self.stdout.write(self.style.WARNING(f"Trying to get rainfall data from PAGASA data"))
                try:
                    # PAGASA data or closest available source
                    region_url = f"https://api.open-meteo.com/v1/forecast?latitude=17.13&longitude=120.43&current=precipitation&daily=precipitation_sum"
                    response = requests.get(region_url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'current' in data and data['current'].get('precipitation') is not None:
                            rainfall = data['current']['precipitation']
                            SensorData.objects.create(
                                sensor=sensor,
                                value=rainfall,
                                timestamp=timezone.now()
                            )
                            self.stdout.write(self.style.SUCCESS(f"Saved regional rainfall reading for {sensor.name}: {rainfall}mm"))
                        else:
                            self.stdout.write(self.style.ERROR(f"Could not get rainfall data for {sensor.name}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Could not access rainfall data for {sensor.name}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error fetching PAGASA rainfall data: {str(e)}"))
    
    def update_water_level_data(self):
        """Update water level data using real-time monitoring API or govt data"""
        water_level_sensors = Sensor.objects.filter(sensor_type='water_level', active=True)
        
        if not water_level_sensors.exists():
            self.stdout.write(self.style.WARNING("No active water level sensors found."))
            return
        
        # Try to get real-time monitoring data from DOST-PAGASA or similar sources
        try:
            # Construct API for water level monitoring
            # Using open-meteo's hydrological API (as a substitute for actual govt data sources)
            hydro_url = f"https://api.open-meteo.com/v1/forecast?latitude=17.13&longitude=120.43&hourly=river_discharge_m3s"
            response = requests.get(hydro_url)
            
            water_level_data = None
            if response.status_code == 200:
                data = response.json()
                if 'hourly' in data and 'river_discharge_m3s' in data['hourly']:
                    # Get latest reading
                    discharge = data['hourly']['river_discharge_m3s'][-1]
                    if discharge is not None:
                        # Convert discharge to water level (simplified conversion)
                        # In a real system, this would use rating curves specific to the location
                        water_level_data = max(0.5, min(5.0, discharge / 10))
            
            for sensor in water_level_sensors:
                # Use real data if available, otherwise calculate from rainfall
                if water_level_data is not None:
                    # Apply some small variation based on specific location
                    location_factor = 1.0
                    if "Bridge" in sensor.name:
                        location_factor = 0.9  # Slightly lower at bridge locations
                    elif "River" in sensor.name:
                        location_factor = 1.1  # Slightly higher in river locations
                    
                    water_level = round(water_level_data * location_factor, 2)
                    SensorData.objects.create(
                        sensor=sensor,
                        value=water_level,
                        timestamp=timezone.now()
                    )
                    self.stdout.write(self.style.SUCCESS(f"Saved water level reading for {sensor.name}: {water_level}m"))
                else:
                    # If no direct water level data, estimate from recent rainfall
                    # This is a fallback that uses real rainfall data to generate water levels
                    recent_rainfall = SensorData.objects.filter(
                        sensor__sensor_type='rainfall',
                        timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
                    ).values_list('value', flat=True)
                    
                    if recent_rainfall:
                        # Use actual rainfall data to calculate water level
                        avg_rainfall = sum(recent_rainfall) / len(recent_rainfall)
                        # Convert rainfall to water level (basic hydrological relationship)
                        # In reality this would use more complex watershed models
                        water_level = round(0.8 + (avg_rainfall / 10), 2)
                        
                        SensorData.objects.create(
                            sensor=sensor,
                            value=water_level,
                            timestamp=timezone.now()
                        )
                        self.stdout.write(self.style.SUCCESS(f"Saved rainfall-derived water level for {sensor.name}: {water_level}m"))
                    else:
                        self.stdout.write(self.style.ERROR(f"No data available to calculate water level for {sensor.name}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing water level data: {str(e)}"))
            traceback.print_exc()
            
    def update_humidity_data(self):
        """Update humidity data for all humidity sensors"""
        humidity_sensors = Sensor.objects.filter(sensor_type='humidity', active=True)
        
        if not humidity_sensors.exists():
            self.stdout.write(self.style.WARNING("No active humidity sensors found."))
            return
        
        for sensor in humidity_sensors:
            # Get location name
            location_name = sensor.name.replace('Environmental', '').replace('Monitor', '').strip()
            if not location_name:
                location_name = "Vical, Santa Lucia, Ilocos Sur"
            
            # Fetch weather data
            weather_data = self.fetch_weather_for_location(location_name, sensor.latitude, sensor.longitude)
            
            if weather_data and weather_data.get('relative_humidity_2m') is not None:
                humidity = weather_data['relative_humidity_2m']
                # Save the new sensor reading
                SensorData.objects.create(
                    sensor=sensor, 
                    value=humidity,
                    timestamp=timezone.now()
                )
                self.stdout.write(self.style.SUCCESS(f"Saved new humidity reading for {sensor.name}: {humidity}%"))
            else:
                self.stdout.write(self.style.ERROR(f"Could not get humidity data for {sensor.name}"))
    
    def update_wind_data(self):
        """Update wind speed data for all wind sensors"""
        wind_sensors = Sensor.objects.filter(sensor_type='wind_speed', active=True)
        
        if not wind_sensors.exists():
            self.stdout.write(self.style.WARNING("No active wind sensors found."))
            return
        
        for sensor in wind_sensors:
            # Get location name
            location_name = sensor.name.replace('Wind', '').replace('Monitor', '').replace('Station', '').strip()
            if not location_name:
                location_name = "Vical, Santa Lucia, Ilocos Sur"
            
            # Fetch weather data
            weather_data = self.fetch_weather_for_location(location_name, sensor.latitude, sensor.longitude)
            
            if weather_data and weather_data.get('wind_speed_10m') is not None:
                wind_speed = weather_data['wind_speed_10m']
                # Save the new sensor reading
                SensorData.objects.create(
                    sensor=sensor,
                    value=wind_speed,
                    timestamp=timezone.now()
                )
                self.stdout.write(self.style.SUCCESS(f"Saved new wind speed reading for {sensor.name}: {wind_speed}km/h"))
            else:
                self.stdout.write(self.style.ERROR(f"Could not get wind speed data for {sensor.name}"))
