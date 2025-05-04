/**
 * Map.js - Interactive flood map functionality
 * Handles map visualization, risk zones, sensors, and affected barangays
 */

// Global map variables
let floodMap;

// Layer groups
let riskZonesLayer;
let sensorsLayer;
let barangaysLayer;

// Active view mode
let activeMapMode = 'risk-zones';

// Selected municipality and barangay - global variables to be used in all modules
window.selectedMunicipality = null;
window.selectedBarangay = null;

// Store all data
let allMunicipalities = [];
let allBarangays = [];

// Map markers for barangays
let barangayMarkers = {};

// Map initialization
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if the map container exists
    const mapContainer = document.getElementById('flood-map');
    if (!mapContainer) return;
    
    // Initialize the map (centered on Vical, Santa Lucia, Ilocos Sur)
    floodMap = L.map('flood-map').setView([17.135678, 120.437203], 14);
    
    // Add tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(floodMap);
    
    // Initialize layer groups
    riskZonesLayer = L.layerGroup().addTo(floodMap);
    sensorsLayer = L.layerGroup();
    barangaysLayer = L.layerGroup();
    
    // Setup controls
    setupMapControls();
    
    // Load initial data
    loadMapData();
    loadMunicipalityData();
    
    // Setup event listeners for municipality selection
    const municipalitySelector = document.getElementById('municipality-selector');
    if (municipalitySelector) {
        municipalitySelector.addEventListener('change', function() {
            const selectedId = this.value;
            if (selectedId) {
                // Find the selected municipality object
                const municipality = allMunicipalities.find(m => m.id.toString() === selectedId);
                if (municipality) {
                    window.selectedMunicipality = municipality;
                    // Clear barangay selection when municipality changes
                    document.getElementById('barangay-selector').value = '';
                    window.selectedBarangay = null;
                    resetBarangayHighlights();
                    document.getElementById('focus-selected-barangay').disabled = true;
                    // Filter barangays by municipality
                    setupBarangaySelector();
                    
                    // Auto-adjust map to focus on the selected municipality
                    if (municipality.latitude && municipality.longitude) {
                        // Set the map view to the municipality location with appropriate zoom level
                        floodMap.setView([municipality.latitude, municipality.longitude], 13);
                        // Show a temporary marker to highlight the municipality center
                        const marker = L.marker([municipality.latitude, municipality.longitude], {
                            icon: L.divIcon({
                                className: 'municipality-highlight',
                                html: `<div style="background-color: #0d6efd; width: 20px; height: 20px; border-radius: 50%; 
                                        border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>`,
                                iconSize: [20, 20],
                                iconAnchor: [10, 10]
                            })
                        }).addTo(floodMap);
                        // Add a popup with municipality info
                        marker.bindPopup(`
                            <strong>${municipality.name}</strong><br>
                            Province: ${municipality.province}<br>
                            Population: ${municipality.population.toLocaleString()}<br>
                            Contact: ${municipality.contact_person || 'N/A'}
                        `).openPopup();
                        // Remove the marker after 3 seconds
                        setTimeout(() => {
                            floodMap.removeLayer(marker);
                        }, 3000);
                    }
                    
                    // Trigger all data refresh for the new location
                    refreshAllDataForNewLocation();
                }
            } else {
                // Clear selection
                window.selectedMunicipality = null;
                // Show all barangays
                setupBarangaySelector();
                // Reset map to default view
                floodMap.setView([17.135678, 120.437203], 11);
                
                // Refresh all data for the default view
                refreshAllDataForNewLocation();
            }
        });
    }
    
    // Setup event listeners for barangay selection
    const barangaySelector = document.getElementById('barangay-selector');
    if (barangaySelector) {
        barangaySelector.addEventListener('change', function() {
            const selectedId = this.value;
            if (selectedId) {
                // Find the selected barangay object
                const barangay = allBarangays.find(b => b.id.toString() === selectedId);
                if (barangay) {
                    window.selectedBarangay = barangay;
                    highlightSelectedBarangay(barangay);
                    document.getElementById('focus-selected-barangay').disabled = false;
                    
                    // Auto-focus on the selected barangay
                    focusOnBarangay(barangay);
                    
                    // Refresh all data for the selected barangay
                    refreshAllDataForNewLocation();
                }
            } else {
                // Clear selection
                window.selectedBarangay = null;
                resetBarangayHighlights();
                document.getElementById('focus-selected-barangay').disabled = true;
                
                // Refresh all data for the default view
                refreshAllDataForNewLocation();
            }
        });
    }
    
    // Reset map view button
    const resetButton = document.getElementById('reset-map-view');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            loadMapData(); // This will reset the view
        });
    }
    
    // Focus selected barangay button
    const focusButton = document.getElementById('focus-selected-barangay');
    if (focusButton) {
        focusButton.addEventListener('click', function() {
            if (selectedBarangay) {
                focusOnBarangay(selectedBarangay);
            }
        });
    }
    
    // Refresh map data every 3 minutes
    setInterval(loadMapData, 3 * 60 * 1000);
});

/**
 * Set up map control buttons
 */
function setupMapControls() {
    // Setup toggle buttons
    document.getElementById('btn-risk-zones').addEventListener('click', function() {
        setMapMode('risk-zones');
    });
    
    document.getElementById('btn-sensors').addEventListener('click', function() {
        setMapMode('sensors');
    });
    
    document.getElementById('btn-barangays').addEventListener('click', function() {
        setMapMode('barangays');
    });
}

/**
 * Set map display mode
 */
function setMapMode(mode) {
    // Update active button
    document.querySelectorAll('#btn-risk-zones, #btn-sensors, #btn-barangays').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`btn-${mode}`).classList.add('active');
    
    // Update active map mode
    activeMapMode = mode;
    
    // Show/hide appropriate layers
    floodMap.removeLayer(riskZonesLayer);
    floodMap.removeLayer(sensorsLayer);
    floodMap.removeLayer(barangaysLayer);
    
    switch(mode) {
        case 'risk-zones':
            floodMap.addLayer(riskZonesLayer);
            break;
        case 'sensors':
            floodMap.addLayer(sensorsLayer);
            break;
        case 'barangays':
            floodMap.addLayer(barangaysLayer);
            break;
    }
}

/**
 * Load map data from API
 */
function loadMapData() {
    // Show loading status on the map
    if (document.getElementById('map-last-updated')) {
        document.getElementById('map-last-updated').textContent = 'Loading data...';
    }
    
    // Construct URL with location filters
    let url = '/api/map-data/';
    const params = [];
    
    // Add municipality filter if selected
    if (window.selectedMunicipality) {
        params.push(`municipality_id=${window.selectedMunicipality.id}`);
        console.log(`[Map] Adding municipality filter: ${window.selectedMunicipality.name}`);
    }
    
    // Add barangay filter if selected
    if (window.selectedBarangay) {
        params.push(`barangay_id=${window.selectedBarangay.id}`);
        console.log(`[Map] Adding barangay filter: ${window.selectedBarangay.name}`);
    }
    
    // Add parameters to URL if any
    if (params.length > 0) {
        url += '?' + params.join('&');
    }
    
    console.log(`[Map] Fetching map data with URL: ${url}`);
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(`[Map] Received map data with ${data.barangays ? data.barangays.length : 0} barangays, ${data.sensors ? data.sensors.length : 0} sensors, and ${data.zones ? data.zones.length : 0} risk zones`);
            
            // Clear existing layers
            riskZonesLayer.clearLayers();
            sensorsLayer.clearLayers();
            barangaysLayer.clearLayers();
            
            // Process flood risk zones
            processFloodRiskZones(data.zones || []);
            
            // Process sensors
            processSensors(data.sensors || []);
            
            // Process affected barangays
            processBarangays(data.barangays || []);
            
            // Update map view if we have data
            updateMapView(data);
            
            // Update last updated timestamp
            if (document.getElementById('map-last-updated')) {
                document.getElementById('map-last-updated').textContent = new Date().toLocaleString();
            }
        })
        .catch(error => {
            console.error('Error loading map data:', error);
            
            // Show error on map
            if (document.getElementById('map-last-updated')) {
                document.getElementById('map-last-updated').textContent = 'Error loading map data';
            }
            
            // Clear layers on error
            riskZonesLayer.clearLayers();
            sensorsLayer.clearLayers();
            barangaysLayer.clearLayers();
        });
}

/**
 * Process and display flood risk zones
 */
function processFloodRiskZones(zones) {
    // Clear previous layers
    riskZonesLayer.clearLayers();
    
    // Add each zone to the map
    zones.forEach(zone => {
        try {
            // Parse GeoJSON
            const geoJson = typeof zone.geojson === 'string' ? JSON.parse(zone.geojson) : zone.geojson;
            
            // Determine color based on severity
            const color = getSeverityColor(zone.severity);
            
            // Create the GeoJSON layer with style
            const zoneLayer = L.geoJSON(geoJson, {
                style: {
                    fillColor: color,
                    weight: 2,
                    opacity: 0.8,
                    color: darkenColor(color, 20),
                    fillOpacity: 0.35
                }
            }).bindPopup(`
                <strong>${zone.name}</strong><br>
                Severity: ${getSeverityText(zone.severity)}
            `);
            
            // Add to layer group
            riskZonesLayer.addLayer(zoneLayer);
        } catch (e) {
            console.error('Error processing zone GeoJSON:', e);
        }
    });
    
    // Handle barangay selection - show relevant risk zones
    if (selectedBarangay) {
        // In a production system, we would filter risk zones by barangay location here
        // For now, we'll just focus the map on the selected barangay
    }
}

/**
 * Process and display sensors
 */
function processSensors(sensors) {
    // Clear previous layers
    sensorsLayer.clearLayers();
    
    // Add each sensor to the map
    sensors.forEach(sensor => {
        // Create custom icon based on sensor type
        const icon = createSensorIcon(sensor);
        
        // Add marker with popup
        const marker = L.marker([sensor.lat, sensor.lng], { icon: icon })
            .bindPopup(`
                <strong>${sensor.name}</strong><br>
                Type: ${formatSensorType(sensor.type)}<br>
                ${sensor.value !== null ? `Value: ${sensor.value} ${sensor.unit}` : 'No data available'}
            `)
            .addTo(sensorsLayer);
        
        // Add animation for active sensors
        if (sensor.value !== null) {
            marker._icon.classList.add('pulse-icon');
        }
    });
}

/**
 * Process and display affected barangays
 */
function processBarangays(barangays) {
    // Clear previous layers
    barangaysLayer.clearLayers();
    barangayMarkers = {};
    
    // Store all barangays for the selector
    allBarangays = barangays;
    
    // Add each barangay to the map
    barangays.forEach(barangay => {
        // Determine color based on severity
        const color = getSeverityColor(barangay.severity);
        
        // Create custom icon
        const icon = L.divIcon({
            className: 'custom-div-icon',
            html: `<div style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 8px rgba(0,0,0,0.3);"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        // Add marker with popup
        const marker = L.marker([barangay.lat, barangay.lng], { icon: icon })
            .bindPopup(`
                <strong>${barangay.name}</strong><br>
                Population: ${barangay.population.toLocaleString()}<br>
                Alert Level: ${getSeverityText(barangay.severity)}
            `)
            .addTo(barangaysLayer);
            
        // Store marker reference by barangay ID
        barangayMarkers[barangay.id] = marker;
    });
    
    // Update the barangay selector
    setupBarangaySelector();
    
    // If a barangay was previously selected, highlight it again
    if (selectedBarangay) {
        highlightSelectedBarangay(selectedBarangay);
    }
}

/**
 * Update map view based on data
 */
function updateMapView(data) {
    // Determine bounds based on available data
    let points = [];
    
    // Add sensor points
    if (data.sensors && data.sensors.length > 0) {
        data.sensors.forEach(sensor => {
            points.push([sensor.lat, sensor.lng]);
        });
    }
    
    // Add barangay points
    if (data.barangays && data.barangays.length > 0) {
        data.barangays.forEach(barangay => {
            points.push([barangay.lat, barangay.lng]);
        });
    }
    
    // Adjust map view if we have points
    if (points.length > 0) {
        floodMap.fitBounds(L.latLngBounds(points), {
            padding: [50, 50],
            maxZoom: 12
        });
    }
}

/**
 * Refresh all data for a new location
 * This centralizes data refreshing when location changes
 */
function refreshAllDataForNewLocation() {
    console.log('========== LOCATION CHANGE DETECTED ==========');
    console.log('Refreshing all data for new location filter:');
    console.log('Selected Municipality:', window.selectedMunicipality ? 
        `${window.selectedMunicipality.name} (ID: ${window.selectedMunicipality.id})` : 'All Municipalities');
    console.log('Selected Barangay:', window.selectedBarangay ? 
        `${window.selectedBarangay.name} (ID: ${window.selectedBarangay.id})` : 'All Barangays');
    console.log('============================================');
    
    // Update any UI location displays
    const locationDisplays = document.querySelectorAll('#current-location-display');
    locationDisplays.forEach(display => {
        let locationText = 'All Areas';
        
        if (window.selectedMunicipality) {
            locationText = window.selectedMunicipality.name;
            
            if (window.selectedBarangay) {
                locationText += ' > ' + window.selectedBarangay.name;
            }
        }
        
        display.textContent = locationText;
    });
    
    // Refresh map data with location filters
    console.log('Refreshing map with location filters...');
    loadMapData();
    
    // Trigger dashboard chart updates if we're on the dashboard
    if (typeof updateAllCharts === 'function') {
        console.log('Updating all charts with new location data...');
        updateAllCharts();
    }
    
    // Update prediction data if we're on the prediction page
    if (typeof updatePredictionModel === 'function') {
        console.log('Updating prediction model with new location data...');
        updatePredictionModel();
    }
    
    // Update any other location-specific data
    // For example, refresh alerts
    const alertsContainer = document.getElementById('alerts-container');
    if (alertsContainer) {
        if (typeof loadActiveAlerts === 'function') {
            console.log('Updating alerts with new location data');
            loadActiveAlerts();
        }
    }
    
    // Update sensor data if we're on the dashboard
    if (typeof updateSensorData === 'function') {
        console.log('Updating sensor data with new location data...');
        updateSensorData();
    }
    
    // Update active alerts (for all pages that have them)
    if (typeof checkActiveAlerts === 'function') {
        console.log('Updating active alerts with new location data...');
        checkActiveAlerts();
    }
    
    // Set a global indication that the location has changed (for other components to check)
    window.locationChanged = true;
    
    // Reset the flag after a brief delay (giving components time to check)
    setTimeout(() => {
        window.locationChanged = false;
    }, 500);
}

/**
 * Create a sensor icon based on type and value
 */
function createSensorIcon(sensor) {
    let iconHtml;
    let iconColor;
    
    // Determine color based on value if available
    if (sensor.value !== null) {
        // Use different colors based on sensor type and value
        switch (sensor.type) {
            case 'temperature':
                iconColor = sensor.value > 30 ? '#dc3545' : (sensor.value > 25 ? '#ffc107' : '#198754');
                break;
            case 'humidity':
                iconColor = sensor.value > 80 ? '#0dcaf0' : (sensor.value > 60 ? '#0d6efd' : '#6c757d');
                break;
            case 'rainfall':
                iconColor = sensor.value > 50 ? '#0d6efd' : (sensor.value > 20 ? '#0dcaf0' : '#6c757d');
                break;
            case 'water_level':
                iconColor = sensor.value > 1.5 ? '#dc3545' : (sensor.value > 1 ? '#ffc107' : '#198754');
                break;
            case 'wind_speed':
                iconColor = sensor.value > 40 ? '#dc3545' : (sensor.value > 20 ? '#ffc107' : '#198754');
                break;
            default:
                iconColor = '#6c757d';
        }
    } else {
        // Default color for sensors without values
        iconColor = '#6c757d';
    }
    
    // Create icon HTML based on sensor type
    switch (sensor.type) {
        case 'temperature':
            iconHtml = `<i class="fas fa-thermometer-half" style="color: ${iconColor};"></i>`;
            break;
        case 'humidity':
            iconHtml = `<i class="fas fa-tint" style="color: ${iconColor};"></i>`;
            break;
        case 'rainfall':
            iconHtml = `<i class="fas fa-cloud-rain" style="color: ${iconColor};"></i>`;
            break;
        case 'water_level':
            iconHtml = `<i class="fas fa-water" style="color: ${iconColor};"></i>`;
            break;
        case 'wind_speed':
            iconHtml = `<i class="fas fa-wind" style="color: ${iconColor};"></i>`;
            break;
        default:
            iconHtml = `<i class="fas fa-broadcast-tower" style="color: ${iconColor};"></i>`;
    }
    
    return L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background-color: white; width: 30px; height: 30px; border-radius: 50%; border: 2px solid ${iconColor}; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 8px rgba(0,0,0,0.3);">${iconHtml}</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
}

/**
 * Helper function to get color based on severity level
 */
function getSeverityColor(severity) {
    switch (parseInt(severity)) {
        case 5: return '#7F0000'; // Catastrophic
        case 4: return '#DC3545'; // Emergency
        case 3: return '#FD7E14'; // Warning
        case 2: return '#FFC107'; // Watch
        case 1: return '#0DCAF0'; // Advisory
        default: return '#198754'; // Normal
    }
}

/**
 * Helper function to get severity text
 */
function getSeverityText(severity) {
    switch (parseInt(severity)) {
        case 5: return 'Catastrophic';
        case 4: return 'Emergency';
        case 3: return 'Warning';
        case 2: return 'Watch';
        case 1: return 'Advisory';
        default: return 'Normal';
    }
}

/**
 * Format sensor type for display
 */
function formatSensorType(type) {
    if (!type) return 'Unknown';
    
    // Replace underscores with spaces and capitalize
    return type.replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Darken a hex color by percentage
 */
function darkenColor(hex, percent) {
    // Remove the # if present
    hex = hex.replace('#', '');
    
    // Convert to RGB
    let r = parseInt(hex.substring(0, 2), 16);
    let g = parseInt(hex.substring(2, 4), 16);
    let b = parseInt(hex.substring(4, 6), 16);
    
    // Darken
    r = Math.floor(r * (100 - percent) / 100);
    g = Math.floor(g * (100 - percent) / 100);
    b = Math.floor(b * (100 - percent) / 100);
    
    // Convert back to hex
    r = r.toString(16).padStart(2, '0');
    g = g.toString(16).padStart(2, '0');
    b = b.toString(16).padStart(2, '0');
    
    return `#${r}${g}${b}`;
}

/**
 * Load municipality data from API
 */
function loadMunicipalityData() {
    fetch('/api/municipalities/')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Municipality data received:', data);
            
            // Store all municipalities for the selector
            allMunicipalities = data.results || [];
            
            // Update the municipality selector
            setupMunicipalitySelector();
        })
        .catch(error => {
            console.error('Error loading municipality data:', error);
        });
}

/**
 * Setup the municipality selector dropdown
 */
function setupMunicipalitySelector() {
    const selector = document.getElementById('municipality-selector');
    if (!selector) return;
    
    // Store current value if there is one
    const currentValue = selector.value;
    
    // Clear existing options except the first one
    while (selector.options.length > 1) {
        selector.remove(1);
    }
    
    // Sort municipalities alphabetically by name
    const sortedMunicipalities = [...allMunicipalities].sort((a, b) => {
        return a.name.localeCompare(b.name);
    });
    
    // Add options for each municipality
    sortedMunicipalities.forEach(municipality => {
        const option = document.createElement('option');
        option.value = municipality.id;
        option.textContent = municipality.name;
        selector.appendChild(option);
    });
    
    // Restore previous selection if it exists
    if (currentValue) {
        selector.value = currentValue;
    }
}

/**
 * Setup the barangay selector dropdown
 */
function setupBarangaySelector() {
    const selector = document.getElementById('barangay-selector');
    if (!selector) return;
    
    // Store current value if there is one
    const currentValue = selector.value;
    
    // Clear existing options except the first one
    while (selector.options.length > 1) {
        selector.remove(1);
    }
    
    // Filter barangays by selected municipality if applicable
    let filteredBarangays = allBarangays;
    if (selectedMunicipality) {
        filteredBarangays = allBarangays.filter(
            barangay => barangay.municipality_id === selectedMunicipality.id
        );
    }
    
    // Sort barangays alphabetically by name
    const sortedBarangays = [...filteredBarangays].sort((a, b) => {
        return a.name.localeCompare(b.name);
    });
    
    // Add options for each barangay
    sortedBarangays.forEach(barangay => {
        const option = document.createElement('option');
        option.value = barangay.id;
        option.textContent = barangay.name;
        
        // Add severity level indicator
        if (barangay.severity > 1) {
            const severityText = getSeverityText(barangay.severity);
            option.textContent += ` (${severityText})`;
            
            // Add color coding to options based on severity
            option.style.color = getSeverityColor(barangay.severity);
            option.style.fontWeight = 'bold';
        }
        
        selector.appendChild(option);
    });
    
    // Restore previous selection if it exists and is in the filtered list
    if (currentValue && filteredBarangays.some(b => b.id.toString() === currentValue)) {
        selector.value = currentValue;
    }
}

/**
 * Highlight the selected barangay on the map
 */
function highlightSelectedBarangay(barangay) {
    // Reset all markers first
    resetBarangayHighlights();
    
    // Get the marker for the selected barangay
    const marker = barangayMarkers[barangay.id];
    if (marker) {
        // Create a pulsing circle around the marker
        const pulsingCircle = L.circle([barangay.lat, barangay.lng], {
            color: '#FFC107',
            fillColor: '#FFC107',
            fillOpacity: 0.3,
            radius: 300,
            weight: 2,
            className: 'pulsing-circle'
        }).addTo(barangaysLayer);
        
        // Store the pulsing circle reference for later removal
        marker._pulsingCircle = pulsingCircle;
        
        // Open the popup
        marker.openPopup();
        
        // Focus the map on this barangay
        focusOnBarangay(barangay);
    }
}

/**
 * Reset all barangay highlights
 */
function resetBarangayHighlights() {
    // Remove all pulsing circles
    for (const id in barangayMarkers) {
        const marker = barangayMarkers[id];
        if (marker && marker._pulsingCircle) {
            barangaysLayer.removeLayer(marker._pulsingCircle);
            marker._pulsingCircle = null;
        }
    }
}

/**
 * Focus the map view on a specific barangay
 */
function focusOnBarangay(barangay) {
    if (barangay && barangay.lat && barangay.lng) {
        floodMap.setView([barangay.lat, barangay.lng], 14);
        
        // Switch to barangays view mode
        setMapMode('barangays');
        
        // Show a temporary highlight effect
        const highlightMarker = L.circleMarker([barangay.lat, barangay.lng], {
            radius: 30,
            color: '#ffc107',
            weight: 3,
            opacity: 0.8,
            fillOpacity: 0.2,
            interactive: false
        }).addTo(floodMap);
        
        // Animate the highlight
        function animateHighlight() {
            let opacity = 0.8;
            let radius = 30;
            const interval = setInterval(() => {
                opacity -= 0.05;
                radius += 2;
                highlightMarker.setStyle({
                    opacity: opacity,
                    radius: radius
                });
                if (opacity <= 0.1) {
                    clearInterval(interval);
                    floodMap.removeLayer(highlightMarker);
                }
            }, 50);
        }
        
        animateHighlight();
    }
}
