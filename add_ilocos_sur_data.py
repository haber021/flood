import os
import django
import random

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flood_monitoring.settings')
django.setup()

# Import models
from core.models import Municipality, Barangay

# Ilocos Sur municipalities with coordinates and population data
ilocos_sur_municipalities = [
    {
        'name': 'Vigan City', 
        'province': 'Ilocos Sur',
        'population': 53879, 
        'area_sqkm': 25.12, 
        'latitude': 17.5747, 
        'longitude': 120.3874,
        'contact_person': 'Mayor Juan Carlo Medina',
        'contact_number': '+639171234567',
        'barangays': [
            {'name': 'Pagpandayan', 'population': 3826, 'area_sqkm': 1.2, 'latitude': 17.5742, 'longitude': 120.3884},
            {'name': 'Pagburnayan', 'population': 4235, 'area_sqkm': 1.5, 'latitude': 17.5736, 'longitude': 120.3864},
            {'name': 'Caoayan', 'population': 3612, 'area_sqkm': 1.3, 'latitude': 17.5756, 'longitude': 120.3894},
            {'name': 'Bantay', 'population': 5128, 'area_sqkm': 1.8, 'latitude': 17.5767, 'longitude': 120.3904},
            {'name': 'San Vicente', 'population': 4526, 'area_sqkm': 1.6, 'latitude': 17.5727, 'longitude': 120.3854},
        ]
    },
    {
        'name': 'Candon City', 
        'province': 'Ilocos Sur',
        'population': 60493, 
        'area_sqkm': 103.28, 
        'latitude': 17.1964, 
        'longitude': 120.4467,
        'contact_person': 'Mayor Ericson Singson',
        'contact_number': '+639181234567',
        'barangays': [
            {'name': 'Patpata', 'population': 3300, 'area_sqkm': 2.5, 'latitude': 17.1954, 'longitude': 120.4457},
            {'name': 'Darapidap', 'population': 3890, 'area_sqkm': 3.2, 'latitude': 17.1974, 'longitude': 120.4477},
            {'name': 'San Jose', 'population': 4250, 'area_sqkm': 3.8, 'latitude': 17.1944, 'longitude': 120.4447},
            {'name': 'San Isidro', 'population': 3750, 'area_sqkm': 2.8, 'latitude': 17.1984, 'longitude': 120.4487},
            {'name': 'San Antonio', 'population': 4120, 'area_sqkm': 3.5, 'latitude': 17.1934, 'longitude': 120.4437},
        ]
    },
    {
        'name': 'Santa Lucia', 
        'province': 'Ilocos Sur',
        'population': 15800, 
        'area_sqkm': 28.3, 
        'latitude': 17.13852, 
        'longitude': 120.435678,
        'contact_person': 'Mayor Fernandez',
        'contact_number': '+639187654321',
        'barangays': [
            {'name': 'Poblacion Norte', 'population': 2350, 'area_sqkm': 1.8, 'latitude': 17.13952, 'longitude': 120.436678},
            {'name': 'Poblacion Sur', 'population': 2150, 'area_sqkm': 1.6, 'latitude': 17.13752, 'longitude': 120.434678},
            {'name': 'Vical', 'population': 1980, 'area_sqkm': 1.4, 'latitude': 17.13652, 'longitude': 120.433678},
            {'name': 'San Pedro', 'population': 2560, 'area_sqkm': 2.0, 'latitude': 17.14052, 'longitude': 120.437678},
            {'name': 'Santa Catalina', 'population': 2210, 'area_sqkm': 1.7, 'latitude': 17.13552, 'longitude': 120.432678},
        ]
    },
    {
        'name': 'Narvacan', 
        'province': 'Ilocos Sur',
        'population': 43891, 
        'area_sqkm': 107.89, 
        'latitude': 17.4217, 
        'longitude': 120.4733,
        'contact_person': 'Mayor Chavit Singson',
        'contact_number': '+639191234567',
        'barangays': [
            {'name': 'Sulvec', 'population': 3120, 'area_sqkm': 2.3, 'latitude': 17.4227, 'longitude': 120.4743},
            {'name': 'Santa Lucia', 'population': 3540, 'area_sqkm': 2.6, 'latitude': 17.4207, 'longitude': 120.4723},
            {'name': 'San Jose', 'population': 4020, 'area_sqkm': 3.1, 'latitude': 17.4237, 'longitude': 120.4753},
            {'name': 'Santa Maria', 'population': 3680, 'area_sqkm': 2.7, 'latitude': 17.4197, 'longitude': 120.4713},
            {'name': 'San Antonio', 'population': 3350, 'area_sqkm': 2.5, 'latitude': 17.4247, 'longitude': 120.4763},
        ]
    },
    {
        'name': 'Santa Cruz', 
        'province': 'Ilocos Sur',
        'population': 39868, 
        'area_sqkm': 115.5, 
        'latitude': 17.0864, 
        'longitude': 120.4575,
        'contact_person': 'Mayor Erwin Salmon',
        'contact_number': '+639201234567',
        'barangays': [
            {'name': 'Caoayan', 'population': 2980, 'area_sqkm': 2.1, 'latitude': 17.0874, 'longitude': 120.4585},
            {'name': 'Poblacion', 'population': 3260, 'area_sqkm': 2.3, 'latitude': 17.0854, 'longitude': 120.4565},
            {'name': 'San Jose', 'population': 3120, 'area_sqkm': 2.2, 'latitude': 17.0884, 'longitude': 120.4595},
            {'name': 'Santa Maria', 'population': 3050, 'area_sqkm': 2.2, 'latitude': 17.0844, 'longitude': 120.4555},
            {'name': 'Santa Lucia', 'population': 3180, 'area_sqkm': 2.3, 'latitude': 17.0894, 'longitude': 120.4605},
        ]
    },
    {
        'name': 'San Juan', 
        'province': 'Ilocos Sur',
        'population': 21936, 
        'area_sqkm': 63.9, 
        'latitude': 16.9703, 
        'longitude': 120.4597,
        'contact_person': 'Mayor Arnold Sablaya',
        'contact_number': '+639211234567',
        'barangays': [
            {'name': 'Immaculate Conception', 'population': 1850, 'area_sqkm': 1.2, 'latitude': 16.9713, 'longitude': 120.4607},
            {'name': 'San Julian', 'population': 1920, 'area_sqkm': 1.3, 'latitude': 16.9693, 'longitude': 120.4587},
            {'name': 'San Isidro', 'population': 1780, 'area_sqkm': 1.2, 'latitude': 16.9723, 'longitude': 120.4617},
            {'name': 'Santo Rosario', 'population': 1650, 'area_sqkm': 1.1, 'latitude': 16.9683, 'longitude': 120.4577},
            {'name': 'San Pedro', 'population': 1890, 'area_sqkm': 1.2, 'latitude': 16.9733, 'longitude': 120.4627},
        ]
    },
    {
        'name': 'Magsingal', 
        'province': 'Ilocos Sur',
        'population': 28035, 
        'area_sqkm': 75.48, 
        'latitude': 17.6833, 
        'longitude': 120.4167,
        'contact_person': 'Mayor Victoria Ines',
        'contact_number': '+639221234567',
        'barangays': [
            {'name': 'Paratong', 'population': 2120, 'area_sqkm': 1.5, 'latitude': 17.6843, 'longitude': 120.4177},
            {'name': 'San Basilio', 'population': 2350, 'area_sqkm': 1.7, 'latitude': 17.6823, 'longitude': 120.4157},
            {'name': 'San Vicente', 'population': 2250, 'area_sqkm': 1.6, 'latitude': 17.6853, 'longitude': 120.4187},
            {'name': 'Santa Monica', 'population': 2180, 'area_sqkm': 1.6, 'latitude': 17.6813, 'longitude': 120.4147},
            {'name': 'San Julian', 'population': 2280, 'area_sqkm': 1.6, 'latitude': 17.6863, 'longitude': 120.4197},
        ]
    },
    {
        'name': 'San Ildefonso', 
        'province': 'Ilocos Sur',
        'population': 7103, 
        'area_sqkm': 40.7, 
        'latitude': 17.3453, 
        'longitude': 120.3947,
        'contact_person': 'Mayor Christian Purisima',
        'contact_number': '+639231234567',
        'barangays': [
            {'name': 'Poblacion Sur', 'population': 780, 'area_sqkm': 0.8, 'latitude': 17.3463, 'longitude': 120.3957},
            {'name': 'Poblacion Norte', 'population': 750, 'area_sqkm': 0.7, 'latitude': 17.3443, 'longitude': 120.3937},
            {'name': 'Otol', 'population': 680, 'area_sqkm': 0.7, 'latitude': 17.3473, 'longitude': 120.3967},
            {'name': 'Bungro', 'population': 620, 'area_sqkm': 0.6, 'latitude': 17.3433, 'longitude': 120.3927},
            {'name': 'Poldapol', 'population': 710, 'area_sqkm': 0.7, 'latitude': 17.3483, 'longitude': 120.3977},
        ]
    }
]

# Function to add a barangay to a municipality
def add_barangay(municipality, barangay_data):
    barangay = Barangay.objects.create(
        name=barangay_data['name'],
        municipality=municipality,
        population=barangay_data['population'],
        area_sqkm=barangay_data['area_sqkm'],
        latitude=barangay_data['latitude'],
        longitude=barangay_data['longitude'],
        contact_person=f"Barangay Captain of {barangay_data['name']}",
        contact_number=f"+63919{random.randint(1000000, 9999999)}"
    )
    return barangay

# Main function to add all data
def add_ilocos_sur_data():
    print("Adding Ilocos Sur municipalities and barangays...")
    
    # Clear existing data if any
    Municipality.objects.all().delete()
    Barangay.objects.all().delete()
    
    # Add municipalities and their barangays
    for muni_data in ilocos_sur_municipalities:
        # Create municipality
        municipality = Municipality.objects.create(
            name=muni_data['name'],
            province=muni_data['province'],
            population=muni_data['population'],
            area_sqkm=muni_data['area_sqkm'],
            latitude=muni_data['latitude'],
            longitude=muni_data['longitude'],
            contact_person=muni_data['contact_person'],
            contact_number=muni_data['contact_number']
        )
        
        print(f"Added municipality: {municipality.name}")
        
        # Add barangays for this municipality
        for barangay_data in muni_data['barangays']:
            barangay = add_barangay(municipality, barangay_data)
            print(f"  Added barangay: {barangay.name}")
    
    print("\nSummary:")
    print(f"Added {Municipality.objects.count()} municipalities")
    print(f"Added {Barangay.objects.count()} barangays")

if __name__ == "__main__":
    add_ilocos_sur_data()
