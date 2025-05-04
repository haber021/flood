/**
 * Dashboard.js - Main dashboard functionality
 * Handles real-time data updates for sensor widgets, alerts, and dashboard refresh
 */

// Dashboard refresh interval in milliseconds (5 minutes)
const DASHBOARD_REFRESH_INTERVAL = 5 * 60 * 1000;

// Dashboard initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize sensor gauges
    initializeGauges();
    
    // Load initial sensor data
    updateSensorData();
    
    // Check for active alerts
    checkActiveAlerts();
    
    // Update data periodically
    setInterval(updateSensorData, 60000); // Update every minute
    setInterval(checkActiveAlerts, 30000); // Check alerts every 30 seconds
    
    // Auto-refresh dashboard
    setInterval(function() {
        // Don't refresh if user is interacting with form elements
        if (!document.activeElement || 
            !['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(document.activeElement.tagName)) {
            location.reload();
        }
    }, DASHBOARD_REFRESH_INTERVAL);
});

/**
 * Initialize gauge visualizations
 */
function initializeGauges() {
    // Set up empty gauges
    updateGauge('temperature-gauge', 0, '°C', '#temp-updated');
    updateGauge('humidity-gauge', 0, '%', '#humidity-updated');
    updateGauge('rainfall-gauge', 0, 'mm', '#rainfall-updated');
    updateGauge('water-level-gauge', 0, 'm', '#water-level-updated');
    updateGauge('wind-speed-gauge', 0, 'km/h', '#wind-speed-updated');
}

/**
 * Update sensor data for all gauges and stats
 */
function updateSensorData() {
    // Fetch the latest sensor data
    fetch('/api/sensor-data/?limit=5')
        .then(response => response.json())
        .then(data => {
            if (!data.results || data.results.length === 0) {
                console.warn('No sensor data available');
                return;
            }
            
            // Process each sensor type
            data.results.forEach(reading => {
                const sensorType = reading.sensor_type;
                const value = reading.value;
                const timestamp = new Date(reading.timestamp);
                
                // Update appropriate gauge based on sensor type
                switch(sensorType) {
                    case 'temperature':
                        updateGauge('temperature-gauge', value, '°C', '#temp-updated', timestamp);
                        break;
                    case 'humidity':
                        updateGauge('humidity-gauge', value, '%', '#humidity-updated', timestamp);
                        break;
                    case 'rainfall':
                        updateGauge('rainfall-gauge', value, 'mm', '#rainfall-updated', timestamp);
                        break;
                    case 'water_level':
                        updateGauge('water-level-gauge', value, 'm', '#water-level-updated', timestamp);
                        break;
                    case 'wind_speed':
                        updateGauge('wind-speed-gauge', value, 'km/h', '#wind-speed-updated', timestamp);
                        break;
                }
            });
            
            // Update map last updated timestamp
            document.getElementById('map-last-updated').textContent = new Date().toLocaleString();
        })
        .catch(error => {
            console.error('Error fetching sensor data:', error);
        });
}

/**
 * Update a gauge with new value
 */
function updateGauge(gaugeId, value, unit, timestampElementId, timestamp = null) {
    const gaugeElement = document.getElementById(gaugeId);
    if (!gaugeElement) return;
    
    // Update the gauge value
    const valueElement = gaugeElement.querySelector('.gauge-value');
    if (valueElement) {
        valueElement.textContent = value.toFixed(1);
    }
    
    // Change gauge color based on value if appropriate
    updateGaugeColor(gaugeId, value);
    
    // Update the timestamp if provided
    if (timestampElementId && timestamp) {
        const timestampElement = document.querySelector(timestampElementId);
        if (timestampElement) {
            timestampElement.textContent = 'Last updated: ' + timestamp.toLocaleString();
        }
    }
}

/**
 * Update gauge color based on value and thresholds
 */
function updateGaugeColor(gaugeId, value) {
    // Define thresholds for different parameters
    const thresholds = {
        'temperature-gauge': [28, 30, 32, 35], // Normal, Advisory, Watch, Warning, Emergency
        'humidity-gauge': [70, 80, 85, 90],
        'rainfall-gauge': [20, 40, 80, 120],
        'water-level-gauge': [0.5, 1, 1.5, 2],
        'wind-speed-gauge': [20, 30, 40, 60]
    };
    
    // Get the appropriate thresholds or use default
    const gaugeThresholds = thresholds[gaugeId] || [20, 40, 60, 80];
    
    // Define colors for different levels
    const colors = ['#198754', '#0dcaf0', '#ffc107', '#fd7e14', '#dc3545'];
    
    // Determine color index based on value and thresholds
    let colorIndex = 0;
    for (let i = 0; i < gaugeThresholds.length; i++) {
        if (value >= gaugeThresholds[i]) {
            colorIndex = i + 1;
        }
    }
    
    // Apply color to gauge
    const gauge = document.getElementById(gaugeId);
    if (gauge) {
        // Remove existing color classes
        gauge.classList.remove('gauge-normal', 'gauge-advisory', 'gauge-watch', 'gauge-warning', 'gauge-emergency');
        
        // Add appropriate color class
        const colorClasses = ['gauge-normal', 'gauge-advisory', 'gauge-watch', 'gauge-warning', 'gauge-emergency'];
        gauge.classList.add(colorClasses[colorIndex]);
        
        // Set gauge color using CSS variable
        gauge.style.setProperty('--gauge-color', colors[colorIndex]);
    }
}

/**
 * Check for active alerts and update the dashboard
 */
function checkActiveAlerts() {
    fetch('/api/flood-alerts/?active=true')
        .then(response => response.json())
        .then(data => {
            const alertsContainer = document.getElementById('alerts-list');
            const noAlertsElement = document.getElementById('no-alerts');
            
            if (data.results && data.results.length > 0) {
                // We have active alerts
                alertsContainer.classList.remove('d-none');
                if (noAlertsElement) {
                    noAlertsElement.classList.add('d-none');
                }
                
                // Sort alerts by severity (highest first)
                const alerts = data.results.sort((a, b) => b.severity_level - a.severity_level);
                
                // Update alerts list
                let alertsHtml = '';
                alerts.forEach(alert => {
                    // Determine alert color based on severity
                    let alertClass = 'alert-info';
                    let severityText = 'Advisory';
                    
                    switch (alert.severity_level) {
                        case 5:
                            alertClass = 'alert-danger';
                            severityText = 'CATASTROPHIC';
                            break;
                        case 4:
                            alertClass = 'alert-danger';
                            severityText = 'EMERGENCY';
                            break;
                        case 3:
                            alertClass = 'alert-warning';
                            severityText = 'WARNING';
                            break;
                        case 2:
                            alertClass = 'alert-warning';
                            severityText = 'WATCH';
                            break;
                        case 1:
                            alertClass = 'alert-info';
                            severityText = 'ADVISORY';
                            break;
                    }
                    
                    // Format the date
                    const issuedDate = new Date(alert.issued_at).toLocaleString();
                    
                    // Build the HTML for this alert
                    alertsHtml += `
                        <div class="alert ${alertClass} mb-3">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h5 class="alert-heading">${severityText}: ${alert.title}</h5>
                                    <p>${alert.description}</p>
                                    <div class="small text-muted mt-2">
                                        Issued: ${issuedDate} by ${alert.issued_by_username || 'System'}
                                    </div>
                                </div>
                                <div>
                                    ${alert.predicted_flood_time ? `
                                        <div class="text-center">
                                            <div class="fw-bold">Predicted Impact</div>
                                            <div class="countdown-timer" data-target="${new Date(alert.predicted_flood_time).getTime()}">
                                                Loading...
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                // Update the alerts container
                alertsContainer.innerHTML = alertsHtml;
                
                // Initialize countdown timers
                document.querySelectorAll('.countdown-timer').forEach(timer => {
                    const targetTime = parseInt(timer.getAttribute('data-target'));
                    updateCountdown(timer, targetTime);
                    setInterval(() => updateCountdown(timer, targetTime), 1000);
                });
                
                // Update alert status display
                updateAlertStatus(alerts[0]);
            } else {
                // No active alerts
                if (alertsContainer) {
                    alertsContainer.classList.add('d-none');
                }
                if (noAlertsElement) {
                    noAlertsElement.classList.remove('d-none');
                }
                
                // Update alert status to normal
                updateAlertStatus(null);
            }
        })
        .catch(error => {
            console.error('Error checking alerts:', error);
        });
}

/**
 * Update the alert status display
 */
function updateAlertStatus(highestAlert) {
    const statusIcon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');
    const alertsCount = document.getElementById('alerts-count');
    
    if (!highestAlert) {
        // No alerts - normal status
        statusIcon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success"></i>';
        statusText.textContent = 'Normal';
        statusText.className = 'status-text text-success';
        if (alertsCount) alertsCount.textContent = 'No active alerts';
        return;
    }
    
    // Update based on the highest severity alert
    switch (highestAlert.severity_level) {
        case 5:
            statusIcon.innerHTML = '<i class="fas fa-exclamation-triangle fa-3x text-danger"></i>';
            statusText.textContent = 'CATASTROPHIC';
            statusText.className = 'status-text text-danger';
            break;
        case 4:
            statusIcon.innerHTML = '<i class="fas fa-exclamation-triangle fa-3x text-danger"></i>';
            statusText.textContent = 'EMERGENCY';
            statusText.className = 'status-text text-danger';
            break;
        case 3:
            statusIcon.innerHTML = '<i class="fas fa-exclamation-circle fa-3x text-warning"></i>';
            statusText.textContent = 'WARNING';
            statusText.className = 'status-text text-warning';
            break;
        case 2:
            statusIcon.innerHTML = '<i class="fas fa-exclamation-circle fa-3x text-warning"></i>';
            statusText.textContent = 'WATCH';
            statusText.className = 'status-text text-warning';
            break;
        case 1:
            statusIcon.innerHTML = '<i class="fas fa-info-circle fa-3x text-info"></i>';
            statusText.textContent = 'ADVISORY';
            statusText.className = 'status-text text-info';
            break;
    }
    
    // Update alerts count text
    if (alertsCount) {
        fetch('/api/flood-alerts/?active=true')
            .then(response => response.json())
            .then(data => {
                const count = data.count || 0;
                alertsCount.textContent = `${count} active alert${count !== 1 ? 's' : ''}`;
            });
    }
}

/**
 * Update countdown timer display
 */
function updateCountdown(element, targetTime) {
    const now = new Date().getTime();
    const distance = targetTime - now;
    
    if (distance < 0) {
        element.innerHTML = '<span class="badge bg-danger">IMMINENT</span>';
        return;
    }
    
    // Calculate hours, minutes, seconds
    const hours = Math.floor(distance / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
    
    // Display countdown
    element.innerHTML = `
        <div class="badge bg-danger">
            ${hours}h ${minutes}m ${seconds}s
        </div>
    `;
}
