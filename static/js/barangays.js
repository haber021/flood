/**
 * Barangays.js - Barangay management functionality
 * Handles barangay listings, filtering, searching, and map visualization
 */

// Global map variable
let barangayMap;

// Initialize barangays page
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the barangays map if present
    const mapElement = document.getElementById('barangays-map');
    if (mapElement) {
        initializeBarangaysMap();
    }
    
    // Set up search form functionality
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        setupSearchForm(searchForm);
    }
});

/**
 * Initialize the barangays overview map
 */
function initializeBarangaysMap() {
    // Create the map centered on the Philippines
    barangayMap = L.map('barangays-map').setView([12.8797, 121.7740], 6);
    
    // Add the base tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(barangayMap);
    
    // Load barangay data
    loadBarangayMapData();
}

/**
 * Load barangay data for map visualization
 */
function loadBarangayMapData() {
    fetch('/api/barangays/')
        .then(response => response.json())
        .then(data => {
            if (!data.results || data.results.length === 0) {
                console.warn('No barangay data available');
                return;
            }
            
            // Load active alerts to check affected barangays
            fetch('/api/flood-alerts/?active=true')
                .then(alertResponse => alertResponse.json())
                .then(alertData => {
                    const activeAlerts = alertData.results || [];
                    // Create a map of barangay IDs to their highest alert severity
                    const affectedBarangays = {};
                    
                    activeAlerts.forEach(alert => {
                        (alert.affected_barangays || []).forEach(barangayId => {
                            // If this barangay doesn't have a severity yet or this alert has higher severity, update it
                            if (!affectedBarangays[barangayId] || alert.severity_level > affectedBarangays[barangayId]) {
                                affectedBarangays[barangayId] = alert.severity_level;
                            }
                        });
                    });
                    
                    // Add barangay markers to the map
                    addBarangayMarkers(data.results, affectedBarangays);
                })
                .catch(error => {
                    console.error('Error loading alert data:', error);
                    // Still add markers without alert status
                    addBarangayMarkers(data.results, {});
                });
        })
        .catch(error => {
            console.error('Error loading barangay data:', error);
        });
}

/**
 * Add barangay markers to the map
 */
function addBarangayMarkers(barangays, affectedBarangays) {
    // Collect all coordinates for bounding the map
    let coordinates = [];
    
    // Create markers for each barangay
    barangays.forEach(barangay => {
        // Add to coordinates list
        coordinates.push([barangay.latitude, barangay.longitude]);
        
        // Determine marker color based on alert severity
        let markerColor = '#198754'; // Default green (Normal)
        let severityText = 'Normal';
        const severity = affectedBarangays[barangay.id];
        
        if (severity) {
            switch (severity) {
                case 5:
                    markerColor = '#7F0000'; // Catastrophic
                    severityText = 'Catastrophic';
                    break;
                case 4:
                    markerColor = '#DC3545'; // Emergency
                    severityText = 'Emergency';
                    break;
                case 3:
                    markerColor = '#FD7E14'; // Warning
                    severityText = 'Warning';
                    break;
                case 2:
                    markerColor = '#FFC107'; // Watch
                    severityText = 'Watch';
                    break;
                case 1:
                    markerColor = '#0DCAF0'; // Advisory
                    severityText = 'Advisory';
                    break;
            }
        }
        
        // Create custom icon
        const icon = L.divIcon({
            className: 'custom-div-icon',
            html: `<div style="background-color: ${markerColor}; width: 15px; height: 15px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 8px rgba(0,0,0,0.3);"></div>`,
            iconSize: [15, 15],
            iconAnchor: [7.5, 7.5]
        });
        
        // Add marker with popup
        L.marker([barangay.latitude, barangay.longitude], { icon: icon })
            .bindPopup(`
                <strong>${barangay.name}</strong><br>
                Population: ${barangay.population.toLocaleString()}<br>
                Status: <span style="color: ${markerColor};">${severityText}</span><br>
                <a href="/barangays/${barangay.id}/" class="btn btn-sm btn-primary mt-2">View Details</a>
            `)
            .addTo(barangayMap);
    });
    
    // If we have coordinates, adjust the map view
    if (coordinates.length > 0) {
        barangayMap.fitBounds(L.latLngBounds(coordinates), {
            padding: [50, 50],
            maxZoom: 10
        });
    }
}

/**
 * Set up search and filter functionality
 */
function setupSearchForm(form) {
    // Add event listener for real-time filtering
    const nameInput = form.querySelector('input[name="name"]');
    const severitySelect = form.querySelector('select[name="severity_level"]');
    
    // Real-time filtering with debounce
    let debounceTimer;
    
    nameInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            form.submit();
        }, 500);
    });
    
    severitySelect.addEventListener('change', function() {
        form.submit();
    });
}

/**
 * Format number with commas for thousands
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Handle individual barangay map if on detail page
 */
if (document.getElementById('barangay-map')) {
    // Get barangay coordinates from data attributes or default to Philippines
    const mapElement = document.getElementById('barangay-map');
    const latitude = parseFloat(mapElement.getAttribute('data-latitude') || 12.8797);
    const longitude = parseFloat(mapElement.getAttribute('data-longitude') || 121.7740);
    
    // Initialize map
    const map = L.map('barangay-map').setView([latitude, longitude], 14);
    
    // Add base tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Add barangay marker
    const barangayIcon = L.divIcon({
        html: '<i class="fas fa-home fa-2x text-primary"></i>',
        className: 'custom-div-icon',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
    
    L.marker([latitude, longitude], {icon: barangayIcon})
        .addTo(map)
        .bindPopup(`<strong>${mapElement.getAttribute('data-name') || 'Barangay'}</strong><br>Barangay Office`);
}
