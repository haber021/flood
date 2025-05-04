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
let heatmapLayer;

// Active view mode
let activeMapMode = 'risk-zones';

// Selected municipality and barangay - global variables to be used in all modules
window.selectedMunicipality = null;
window.selectedBarangay = null;

// Store all data
let allMunicipalities = [];
let allBarangays = [];

// Track which municipalities have had their barangays loaded
let loadedMunicipalityBarangays = [];

// Map markers for barangays
let barangayMarkers = {};

// Map initialization
document.addEventListener('DOMContentLoaded', function() {
    // Check if there's a saved municipality preference in sessionStorage
    const savedMunicipalityId = sessionStorage.getItem('selectedMunicipalityId');
    const savedBarangayId = sessionStorage.getItem('selectedBarangayId');
    
    console.log('[Map] Checking for saved location preferences:', {
        savedMunicipalityId,
        savedBarangayId
    });
    
    // Initialize the barangays section
    displayMunicipalityBarangays();
    
    // Only initialize map if the map container exists
    const mapContainer = document.getElementById('flood-map');
    if (!mapContainer) return;
    
    // Initialize the map (centered on Vical, Santa Lucia, Ilocos Sur as default)
    floodMap = L.map('flood-map').setView([17.135678, 120.437203], 14);
    
    // Add tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(floodMap);
    
    // Initialize layer groups
    riskZonesLayer = L.layerGroup().addTo(floodMap);
    sensorsLayer = L.layerGroup();
    barangaysLayer = L.layerGroup();
    heatmapLayer = L.layerGroup();
    
    // Setup controls
    setupMapControls();
    
    // Load municipality data first to ensure we have it for filtering
    loadMunicipalityData().then(() => {
        // After municipalities are loaded, set the saved selection if available
        if (savedMunicipalityId) {
            // Find the municipality from loaded data
            const municipality = allMunicipalities.find(m => m.id.toString() === savedMunicipalityId);
            if (municipality) {
                console.log(`[Map] Restoring saved municipality selection: ${municipality.name}`);
                window.selectedMunicipality = municipality;
                
                // Update the selector UI if it exists
                const municipalitySelector = document.getElementById('municipality-selector');
                if (municipalitySelector) {
                    municipalitySelector.value = savedMunicipalityId;
                }
                
                // If we have a barangay preference, try to load that too
                if (savedBarangayId) {
                    // We'll wait for barangays to load and then select it
                    loadBarangaysForMunicipality(municipality.id);
                }
            }
        }
        
        // Now load map data with any filters applied
        loadMapData();
    });
    
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
                    // Save user's preference to sessionStorage
                    sessionStorage.setItem('selectedMunicipalityId', municipality.id);
                    
                    // Clear barangay selection when municipality changes
                    document.getElementById('barangay-selector').value = '';
                    window.selectedBarangay = null;
                    sessionStorage.removeItem('selectedBarangayId'); // Clear saved barangay preference
                    resetBarangayHighlights();
                    document.getElementById('focus-selected-barangay').disabled = true;
                    
                    // Load all barangays for this municipality
                    loadBarangaysForMunicipality(municipality.id);
                    
                    // Filter barangays by municipality for the dropdown
                    setupBarangaySelector();
                    
                    // Auto-adjust map to focus on the selected municipality
                    if (municipality.latitude && municipality.longitude) {
                        console.log(`[Map] Auto-focusing on municipality: ${municipality.name} at [${municipality.latitude}, ${municipality.longitude}]`);
                        
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
                    } else {
                        console.warn(`[Map] Municipality ${municipality.name} is missing coordinates - cannot auto-focus`);
                    }
                    
                    // Trigger all data refresh for the new location
                    refreshAllDataForNewLocation();
                }
            } else {
                // Clear selection
                window.selectedMunicipality = null;
                // Remove saved preference
                sessionStorage.removeItem('selectedMunicipalityId');
                sessionStorage.removeItem('selectedBarangayId');
                
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
                    // Save user's preference to sessionStorage
                    sessionStorage.setItem('selectedBarangayId', barangay.id);
                    
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
                // Remove saved preference
                sessionStorage.removeItem('selectedBarangayId');
                
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
    
    document.getElementById('btn-heatmap').addEventListener('click', function() {
        setMapMode('heatmap');
    });
}

/**
 * Set map display mode
 */
function setMapMode(mode) {
    // Update active button
    document.querySelectorAll('#btn-risk-zones, #btn-sensors, #btn-barangays, #btn-heatmap').forEach(btn => {
        if (btn) btn.classList.remove('active');
    });
    const activeBtn = document.getElementById(`btn-${mode}`);
    if (activeBtn) activeBtn.classList.add('active');
    
    // Update active map mode
    activeMapMode = mode;
    
    // Show/hide appropriate layers
    floodMap.removeLayer(riskZonesLayer);
    floodMap.removeLayer(sensorsLayer);
    floodMap.removeLayer(barangaysLayer);
    
    // Remove heatmap layer if it exists
    if (heatmapLayer) {
        floodMap.removeLayer(heatmapLayer);
    }
    
    // Toggle appropriate legend
    document.getElementById('risk-zones-legend').classList.add('d-none');
    document.getElementById('heatmap-legend').classList.add('d-none');
    
    switch(mode) {
        case 'risk-zones':
            floodMap.addLayer(riskZonesLayer);
            document.getElementById('risk-zones-legend').classList.remove('d-none');
            break;
        case 'sensors':
            floodMap.addLayer(sensorsLayer);
            document.getElementById('risk-zones-legend').classList.remove('d-none');
            break;
        case 'barangays':
            floodMap.addLayer(barangaysLayer);
            document.getElementById('risk-zones-legend').classList.remove('d-none');
            break;
        case 'heatmap':
            generateHeatmap();
            document.getElementById('heatmap-legend').classList.remove('d-none');
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
            
            // Update heatmap if it's active
            if (activeMapMode === 'heatmap') {
                generateHeatmap();
            }
        })
        .catch(error => {
            // Log the error but don't display the empty object in the console
            console.error('Error loading map data:', error.message || 'Network or server error');
            
            // Show error on map
            if (document.getElementById('map-last-updated')) {
                document.getElementById('map-last-updated').textContent = 'Unable to load map data. Please try again.';
            }
            
            // Show an error notification on the map
            if (floodMap) {
                // Create or update the error control if it doesn't exist
                if (!window.mapErrorControl) {
                    window.mapErrorControl = L.control({position: 'topright'});
                    window.mapErrorControl.onAdd = function() {
                        const div = L.DomUtil.create('div', 'map-error-control alert alert-warning');
                        div.innerHTML = '<strong><i class="fas fa-exclamation-triangle"></i> Map Data Error</strong><br>Unable to load location data';
                        div.style.padding = '10px';
                        div.style.margin = '10px';
                        div.style.maxWidth = '300px';
                        return div;
                    };
                    window.mapErrorControl.addTo(floodMap);
                }
            }
            
            // Clear layers on error
            riskZonesLayer.clearLayers();
            sensorsLayer.clearLayers();
            barangaysLayer.clearLayers();
            
            // Set map to default Philippines view as fallback
            if (floodMap && !window.hasActiveMapData) {
                floodMap.setView([12.8797, 121.7740], 6); // Philippines default view
            }
        });
}

/**
 * Generate heatmap based on flood risk data
 */
function generateHeatmap() {
    // Clear any existing heatmap layer
    if (heatmapLayer) {
        floodMap.removeLayer(heatmapLayer);
    }
    
    console.log('[Heatmap] Generating flood risk heatmap');
    
    // Get data from barangays and sensors
    const heatPoints = [];
    
    // Filter barangays based on selected municipality if applicable
    let filteredBarangays = [...allBarangays];
    if (window.selectedMunicipality) {
        filteredBarangays = allBarangays.filter(barangay => 
            barangay.municipality_id === parseInt(window.selectedMunicipality.id));
    }
    
    // Add points from barangays with severity as intensity
    filteredBarangays.forEach(barangay => {
        // Intensity based on severity (0-5 scale) and population (for radius)
        const intensity = barangay.severity > 0 ? barangay.severity * 5 : 1;
        // Population factor for radius - larger populations = larger affected area
        const populationFactor = Math.sqrt(barangay.population) / 20;
        // Create multiple points around the barangay center for radial effect
        const radius = Math.max(populationFactor, 1) * 500; // Radius in meters
        
        // Add the center point with highest intensity
        heatPoints.push([
            barangay.lat, 
            barangay.lng, 
            intensity * 3 // Center point has higher intensity
        ]);
        
        // Add surrounding points with decreasing intensity (radial pattern)
        const numPoints = Math.min(Math.max(barangay.severity, 1) * 5, 20);
        for (let i = 0; i < numPoints; i++) {
            // Calculate points in a circle around the barangay
            const angle = (i / numPoints) * 2 * Math.PI;
            const distance = (radius / 1000) * (0.5 + Math.random() * 0.5); // Random distance within radius
            
            // Convert polar coordinates to latitude/longitude offset
            // Approximate conversion: 111,111 meters = 1 degree latitude
            // Longitude conversion varies with latitude
            const latOffset = distance * Math.cos(angle) / 111.111;
            const lngOffset = distance * Math.sin(angle) / (111.111 * Math.cos(barangay.lat * (Math.PI / 180)));
            
            // Add point with intensity based on distance from center
            const pointIntensity = intensity * (1 - (0.7 * Math.random()));
            heatPoints.push([barangay.lat + latOffset, barangay.lng + lngOffset, pointIntensity]);
        }
    });
    
    // Add points from water level sensors
    const waterSensors = sensorsLayer.getLayers()
        .filter(layer => {
            const popup = layer.getPopup();
            return popup && popup._content.includes('Type: Water Level');
        });
    
    waterSensors.forEach(sensor => {
        const latLng = sensor.getLatLng();
        const popupContent = sensor.getPopup()._content;
        
        // Extract value from popup content
        const valueMatch = popupContent.match(/Value: ([\d.]+)\s/); 
        if (valueMatch && valueMatch[1]) {
            const value = parseFloat(valueMatch[1]);
            // Water level above 0.5m starts to get concerning
            const intensity = value > 0.5 ? (value * 10) : 0;
            
            if (intensity > 0) {
                // Add the center point
                heatPoints.push([latLng.lat, latLng.lng, intensity * 2]);
                
                // Add points around the sensor for a radial effect
                const radius = value * 200; // Radius proportional to water level
                const numPoints = Math.min(Math.max(value * 10, 3), 15);
                
                for (let i = 0; i < numPoints; i++) {
                    const angle = (i / numPoints) * 2 * Math.PI;
                    const distance = (radius / 1000) * (0.5 + Math.random() * 0.5);
                    
                    const latOffset = distance * Math.cos(angle) / 111.111;
                    const lngOffset = distance * Math.sin(angle) / (111.111 * Math.cos(latLng.lat * (Math.PI / 180)));
                    
                    // Decrease intensity with distance
                    const pointIntensity = intensity * (1 - (0.8 * Math.random()));
                    heatPoints.push([latLng.lat + latOffset, latLng.lng + lngOffset, pointIntensity]);
                }
            }
        }
    });
    
    // Add points from rainfall sensors
    const rainfallSensors = sensorsLayer.getLayers()
        .filter(layer => {
            const popup = layer.getPopup();
            return popup && popup._content.includes('Type: Rainfall');
        });
    
    rainfallSensors.forEach(sensor => {
        const latLng = sensor.getLatLng();
        const popupContent = sensor.getPopup()._content;
        
        // Extract value from popup content
        const valueMatch = popupContent.match(/Value: ([\d.]+)\s/);
        if (valueMatch && valueMatch[1]) {
            const value = parseFloat(valueMatch[1]);
            // Rainfall above 10mm starts to get concerning
            const intensity = value > 10 ? (value / 5) : 0;
            
            if (intensity > 0) {
                // Add center point
                heatPoints.push([latLng.lat, latLng.lng, intensity * 2]);
                
                // Add surrounding points
                const radius = value * 100; // Radius proportional to rainfall
                const numPoints = Math.min(Math.max(value / 5, 3), 15);
                
                for (let i = 0; i < numPoints; i++) {
                    const angle = (i / numPoints) * 2 * Math.PI;
                    const distance = (radius / 1000) * (0.5 + Math.random() * 0.5);
                    
                    const latOffset = distance * Math.cos(angle) / 111.111;
                    const lngOffset = distance * Math.sin(angle) / (111.111 * Math.cos(latLng.lat * (Math.PI / 180)));
                    
                    // Decrease intensity with distance
                    const pointIntensity = intensity * (1 - (0.8 * Math.random()));
                    heatPoints.push([latLng.lat + latOffset, latLng.lng + lngOffset, pointIntensity]);
                }
            }
        }
    });
    
    console.log(`[Heatmap] Generated ${heatPoints.length} heatmap points`);
    
    // Create the heat layer
    if (heatPoints.length > 0) {
        // Configure the heat layer
        const heatLayerConfig = {
            radius: 25,
            blur: 15,
            maxZoom: 17,
            max: 30, // Maximum intensity value
            gradient: {
                0.0: 'rgba(0,255,255,0)',  // Transparent at lowest values
                0.2: '#00ffff', // Cyan
                0.4: '#0088ff', // Light blue
                0.6: '#0000ff', // Blue
                0.7: '#8800ff', // Purple
                0.8: '#ff00ff', // Magenta
                0.9: '#ff0088', // Pink
                1.0: '#ff0000'  // Red at highest values
            }
        };
        
        // Create the heat layer and add it to the map
        heatmapLayer = L.heatLayer(heatPoints, heatLayerConfig).addTo(floodMap);
        console.log('[Heatmap] Heatmap layer added to map');
    } else {
        console.log('[Heatmap] No heatmap points available');
        // Show a message on the map
        const noDataControl = L.control({position: 'topright'});
        noDataControl.onAdd = function() {
            const div = L.DomUtil.create('div', 'map-error-control alert alert-info');
            div.innerHTML = '<strong><i class="fas fa-info-circle"></i> No Heatmap Data</strong><br>No flood risk data available for heatmap visualization';
            div.style.padding = '10px';
            div.style.margin = '10px';
            div.style.maxWidth = '300px';
            return div;
        };
        noDataControl.addTo(floodMap);
        
        // Remove after 3 seconds
        setTimeout(() => {
            floodMap.removeControl(noDataControl);
        }, 3000);
    }
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
        if (sensor.value !== null && marker._icon) {
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
        
        // Create custom icon with size based on population (scaled for visibility)
        const popScale = Math.min(Math.max(barangay.population / 1000, 1), 5); // Scale between 1-5 based on population
        const size = Math.floor(18 + (popScale * 4)); // Size between 20-38px
        
        // Create custom icon with population-scaled size
        const icon = L.divIcon({
            className: 'custom-div-icon',
            html: `<div style="background-color: ${color}; width: ${size}px; height: ${size}px; border-radius: 50%; border: 2px solid white; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 8px rgba(0,0,0,0.3);"></div>`,
            iconSize: [size, size],
            iconAnchor: [size/2, size/2]
        });
        
        // Create detailed popup content
        const popupContent = `
            <div class="barangay-popup">
                <h5>${barangay.name}</h5>
                <div class="popup-details">
                    <table class="table table-sm popup-table">
                        <tr>
                            <th>Municipality:</th>
                            <td>${barangay.municipality_name}</td>
                        </tr>
                        <tr>
                            <th>Population:</th>
                            <td>${barangay.population.toLocaleString()}</td>
                        </tr>
                        <tr>
                            <th>Alert Level:</th>
                            <td>
                                <span class="badge" style="background-color: ${color}">
                                    ${getSeverityText(barangay.severity)}
                                </span>
                            </td>
                        </tr>
                        ${barangay.contact_person ? `
                        <tr>
                            <th>Contact:</th>
                            <td>${barangay.contact_person}</td>
                        </tr>` : ''}
                        ${barangay.contact_number ? `
                        <tr>
                            <th>Phone:</th>
                            <td>${barangay.contact_number}</td>
                        </tr>` : ''}
                    </table>
                </div>
            </div>
        `;
        
        // Add marker with popup
        const marker = L.marker([barangay.lat, barangay.lng], { icon: icon })
            .bindPopup(popupContent, {maxWidth: 300})
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
    
    // Update the barangay count in the UI
    const barangayCountElement = document.getElementById('barangay-count');
    if (barangayCountElement) {
        barangayCountElement.textContent = barangays.length;
    }
}

/**
 * Update map view based on data
 */
function updateMapView(data) {
    // Determine bounds based on available data
    let points = [];
    
    // If a specific municipality is selected, prioritize that location
    if (window.selectedMunicipality && window.selectedMunicipality.latitude && window.selectedMunicipality.longitude) {
        console.log(`[Map] Centering map on selected municipality: ${window.selectedMunicipality.name}`);
        // If we have a specific barangay selected and it exists in our data
        if (window.selectedBarangay && window.selectedBarangay.lat && window.selectedBarangay.lng) {
            console.log(`[Map] Focusing on selected barangay: ${window.selectedBarangay.name}`);
            floodMap.setView([window.selectedBarangay.lat, window.selectedBarangay.lng], 14);
            return; // Exit early since we have a specific point to focus on
        }
        
        // Otherwise focus on the municipality
        floodMap.setView([window.selectedMunicipality.latitude, window.selectedMunicipality.longitude], 13);
        return; // Exit early since we have a specific point to focus on
    }
    
    // If we get here, we need to calculate a bounding box for all visible elements
    
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
    
    // Add risk zone points if available
    if (data.zones && data.zones.length > 0) {
        data.zones.forEach(zone => {
            try {
                // If we have geojson coordinates, extract them
                const geoJson = typeof zone.geojson === 'string' ? JSON.parse(zone.geojson) : zone.geojson;
                if (geoJson && geoJson.geometry && geoJson.geometry.coordinates) {
                    // For polygons, add each coordinate point
                    if (geoJson.geometry.type === 'Polygon') {
                        geoJson.geometry.coordinates[0].forEach(coord => {
                            points.push([coord[1], coord[0]]); // GeoJSON uses [lng, lat] but Leaflet uses [lat, lng]
                        });
                    }
                }
            } catch (e) {
                console.error('Error parsing zone GeoJSON:', e);
            }
        });
    }
    
    // Adjust map view if we have points
    if (points.length > 0) {
        console.log(`[Map] Adjusting map to fit ${points.length} points`);
        floodMap.fitBounds(L.latLngBounds(points), {
            padding: [50, 50],
            maxZoom: 13
        });
    } else {
        // Default view if no points (center of Philippines)
        console.log('[Map] No points to fit, using default view');
        floodMap.setView([17.135678, 120.437203], 12);
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
    
    // Set a global flag that can be detected by other components
    window.locationChanged = true;
    
    // Refresh map data with location filters
    console.log('Refreshing map with location filters...');
    loadMapData();
    
    // Load barangays for the selected municipality if not already loaded
    if (window.selectedMunicipality && !loadedMunicipalityBarangays.includes(parseInt(window.selectedMunicipality.id))) {
        loadBarangaysForMunicipality(window.selectedMunicipality.id);
    }
    
    // Display barangays for the selected municipality
    displayMunicipalityBarangays();
    
    // Update the active layers based on current map mode
    if (activeMapMode === 'heatmap') {
        generateHeatmap();
    } else if (activeMapMode === 'risk-zones') {
        // Risk zones are already refreshed by loadMapData
        // Just ensure they're visible
        if (!floodMap.hasLayer(riskZonesLayer)) {
            floodMap.addLayer(riskZonesLayer);
        }
    }
    
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
 * Load all barangays for a specific municipality ID 
 */
function loadBarangaysForMunicipality(municipalityId) {
    if (!municipalityId) return;
    
    // Convert to integer for consistent comparison
    const municipalityIdInt = parseInt(municipalityId);
    
    // Check if we've already loaded barangays for this municipality to avoid duplicate requests
    if (loadedMunicipalityBarangays.includes(municipalityIdInt)) {
        console.log(`[Barangays] Already loaded barangays for municipality ID ${municipalityId}, using cached data`);
        // Do NOT call displayMunicipalityBarangays() here to avoid potential circular calls
        return;
    }

    // Use our new API endpoint that returns all barangays without pagination
    const url = `/api/all-barangays/?municipality_id=${municipalityId}`;
    const municipalityName = window.selectedMunicipality ? window.selectedMunicipality.name : 'selected municipality';
    
    console.log(`[Barangays] Automatically loading all barangays for ${municipalityName} (ID: ${municipalityId})`);
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Store all the barangays for this municipality in our global array
            if (data.barangays && data.barangays.length > 0) {
                console.log(`[Barangays] Found ${data.barangays.length} barangays for ${municipalityName}`);
                
                // We need to update allBarangays with these results
                // Filter out any existing barangays with the same municipality_id
                allBarangays = allBarangays.filter(b => b.municipality_id !== parseInt(municipalityId));
                
                // Add the new barangays
                allBarangays = [...allBarangays, ...data.barangays];
                
                // Mark this municipality as loaded
                loadedMunicipalityBarangays.push(parseInt(municipalityId));
                
                // Make sure the barangays section updates
                displayMunicipalityBarangays();
            } else {
                console.log(`[Barangays] No barangays found for ${municipalityName}`);
                // Even though we didn't find any, mark as loaded to prevent repeated requests
                loadedMunicipalityBarangays.push(parseInt(municipalityId));
            }
        })
        .catch(error => {
            console.error(`Error loading barangays for municipality ${municipalityId}:`, error);
        });
}

/**
 * Display all barangays for the selected municipality
 */
function displayMunicipalityBarangays() {
    const municipalBarangaysSection = document.getElementById('municipal-barangays-section');
    const noMunicipalitySelectedDiv = document.getElementById('no-municipality-selected');
    const municipalityBarangaysList = document.getElementById('municipality-barangays-list');
    const municipalityBarangayCards = document.getElementById('municipality-barangay-cards');
    const selectedMunicipalityName = document.getElementById('selected-municipality-name');
    
    // If the section doesn't exist, we're not on the dashboard page
    if (!municipalBarangaysSection) return;
    
    // If no municipality is selected, show the message
    if (!window.selectedMunicipality) {
        if (noMunicipalitySelectedDiv) noMunicipalitySelectedDiv.classList.remove('d-none');
        if (municipalityBarangaysList) municipalityBarangaysList.classList.add('d-none');
        return;
    }
    
    // Update the municipality name display
    if (selectedMunicipalityName) {
        selectedMunicipalityName.textContent = window.selectedMunicipality.name;
    }
    
    // Hide the no municipality selected message and show the barangay list
    if (noMunicipalitySelectedDiv) noMunicipalitySelectedDiv.classList.add('d-none');
    if (municipalityBarangaysList) municipalityBarangaysList.classList.remove('d-none');
    
    // Convert to integer for consistent comparison
    const municipalityIdInt = parseInt(window.selectedMunicipality.id);
    
    // Filter the already loaded barangays for this municipality
    const municipalityBarangays = allBarangays.filter(
        b => b.municipality_id === municipalityIdInt
    );
    
    if (municipalityBarangays.length === 0) {
        // Check if we've already tried to load this municipality's barangays
        if (!loadedMunicipalityBarangays.includes(municipalityIdInt)) {
            // If we don't have any barangays for this municipality yet, load them
            loadBarangaysForMunicipality(municipalityIdInt);
            return;
        }
    }
            
    console.log(`[Municipal Barangays] Displaying ${municipalityBarangays.length} barangays for ${window.selectedMunicipality.name}`);
    
    // Sort barangays alphabetically
    const sortedBarangays = [...municipalityBarangays].sort((a, b) => a.name.localeCompare(b.name));
    
    if (sortedBarangays.length === 0) {
        municipalityBarangayCards.innerHTML = `
            <div class="col-12 text-center py-4">
                <div class="text-muted">
                    <i class="fas fa-info-circle fa-2x mb-3"></i>
                    <h5>No barangays found for ${window.selectedMunicipality.name}</h5>
                </div>
            </div>
        `;
        return;
    }
    
    // Create cards for each barangay
    let cardsHtml = '';
    
    // Calculate total population for this municipality
    const totalPopulation = sortedBarangays.reduce((sum, b) => sum + b.population, 0);
    
    // Add municipality summary card
    if (window.selectedMunicipality && sortedBarangays.length > 0) {
        cardsHtml += `
            <div class="col-12 mb-3">
                <div class="card bg-light">
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="mb-0">${window.selectedMunicipality.name}</h5>
                                <p class="mb-0">Total: ${sortedBarangays.length} Barangays</p>
                            </div>
                            <div class="text-end">
                                <h5 class="mb-0">${totalPopulation.toLocaleString()}</h5>
                                <p class="mb-0">Population</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    sortedBarangays.forEach(barangay => {
        // Calculate percentage of municipality population
        const populationPercentage = (barangay.population / totalPopulation * 100).toFixed(1);
        
        // Determine severity class for card border/header
        let severityClass = 'primary';
        if (barangay.severity >= 4) severityClass = 'danger';
        else if (barangay.severity == 3) severityClass = 'warning';
        else if (barangay.severity == 2) severityClass = 'info';
        else if (barangay.severity == 1) severityClass = 'success';
        
        cardsHtml += `
            <div class="col-md-4 col-lg-3 mb-3">
                <div class="card h-100 ${barangay.severity > 0 ? 'border-' + severityClass : ''}">
                    <div class="card-header ${barangay.severity > 0 ? 'bg-' + severityClass + ' text-white' : 'bg-light'}">
                        <h6 class="mb-0">${barangay.name}</h6>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong>Population:</strong>
                            <span class="badge bg-secondary">${barangay.population.toLocaleString()} (${populationPercentage}%)</span>
                        </div>
                        
                        ${barangay.severity > 0 ? `
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong>Alert Level:</strong>
                            <span class="badge bg-${severityClass}">${getSeverityText(barangay.severity)}</span>
                        </div>` : ''}
                        
                        ${barangay.contact_person ? `
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong>Contact:</strong>
                            <span>${barangay.contact_person}</span>
                        </div>` : ''}
                        
                        ${barangay.contact_number ? `
                        <div class="d-flex justify-content-between align-items-center">
                            <strong>Phone:</strong>
                            <span>${barangay.contact_number}</span>
                        </div>` : ''}
                    </div>
                    <div class="card-footer">
                        <button class="btn btn-sm btn-primary w-100" onclick="highlightBarangay(${parseInt(barangay.id)})">
                            <i class="fas fa-map-marker-alt me-1"></i> Show on Map
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    // Update the cards container
    municipalityBarangayCards.innerHTML = cardsHtml;
}

// NOTE: A duplicate definition of refreshAllDataForNewLocation was removed from here
// to fix the "Maximum call stack size exceeded" error. Only the implementation at line ~618 is used.

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
    // Simplified color scheme: only green (normal) and red (danger)
    return parseInt(severity) > 0 ? '#DC3545' : '#198754'; // Red for danger, Green for normal
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
 * @returns {Promise} A promise that resolves when municipalities are loaded
 */
function loadMunicipalityData() {
    return new Promise((resolve, reject) => {
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
                
                // Preload barangays for all municipalities
                preloadAllBarangays();
                
                // Resolve the promise to indicate municipalities are loaded
                resolve(allMunicipalities);
            })
            .catch(error => {
                console.error('Error loading municipality data:', error);
                reject(error);
            });
    });
}

/**
 * Preload barangays for all municipalities in the background
 */
function preloadAllBarangays() {
    if (allMunicipalities.length === 0) return;
    
    console.log(`[Barangays] Preloading barangays for all ${allMunicipalities.length} municipalities in the background...`);
    
    // Define a function to load barangays for a single municipality
    const loadMunicipalityBarangays = (index) => {
        if (index >= allMunicipalities.length) {
            console.log(`[Barangays] Completed preloading barangays for all municipalities`);
            return;
        }
        
        const municipality = allMunicipalities[index];
        // Use our existing function to load the barangays
        loadBarangaysForMunicipality(municipality.id);
        
        // Load the next municipality after a short delay to avoid overwhelming the server
        setTimeout(() => {
            loadMunicipalityBarangays(index + 1);
        }, 500); // 500ms delay between requests
    };
    
    // Start loading from the first municipality
    loadMunicipalityBarangays(0);
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
 * Highlight a barangay on the map when clicking the Show on Map button in the card
 */
function highlightBarangay(barangayId) {
    // Find the barangay by ID
    const barangay = allBarangays.find(b => b.id === barangayId);
    if (!barangay) return;
    
    // Set it as the selected barangay in the dropdown
    const barangaySelector = document.getElementById('barangay-selector');
    if (barangaySelector) {
        barangaySelector.value = barangayId;
        
        // Trigger the change event to update global selection
        const event = new Event('change');
        barangaySelector.dispatchEvent(event);
    } else {
        // If dropdown doesn't exist, set the global directly and focus
        window.selectedBarangay = barangay;
        focusOnBarangay(barangay);
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
