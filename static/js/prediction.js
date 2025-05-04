/**
 * Prediction.js - Flood prediction functionality
 * Handles historical data analysis, prediction model visualization, and alert management
 */

// Global chart objects
let historicalChart;

// Current data mode (rainfall or water level)
let currentHistoricalMode = 'rainfall';

// Current time period for historical data
let currentHistoricalPeriod = 7;

// Initialize prediction page
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the prediction page
    if (!document.getElementById('historical-chart')) return;
    
    // Initialize historical chart
    initializeHistoricalChart();
    
    // Set up tab switching
    document.getElementById('btn-rainfall-history').addEventListener('click', function() {
        if (currentHistoricalMode !== 'rainfall') {
            currentHistoricalMode = 'rainfall';
            toggleHistoricalButtons();
            loadHistoricalData();
        }
    });
    
    document.getElementById('btn-water-level-history').addEventListener('click', function() {
        if (currentHistoricalMode !== 'water_level') {
            currentHistoricalMode = 'water_level';
            toggleHistoricalButtons();
            loadHistoricalData();
        }
    });
    
    // Set up period buttons
    document.querySelectorAll('[data-period]').forEach(btn => {
        btn.addEventListener('click', function() {
            // Update active button
            document.querySelectorAll('[data-period]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Update period and reload data
            currentHistoricalPeriod = parseInt(this.getAttribute('data-period'));
            loadHistoricalData();
        });
    });
    
    // Initialize prediction model
    updatePredictionModel();
    
    // Load affected barangays
    loadPotentiallyAffectedBarangays();
    
    // Set up form validation
    setupAlertForm();
    
    // View all barangays button
    document.getElementById('view-all-barangays').addEventListener('click', function() {
        window.location.href = '/barangays/';
    });
    
    // Refresh prediction button
    document.getElementById('refresh-prediction').addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-sync-alt fa-spin me-1"></i> Refreshing...';
        
        // Simulate a delay for the refresh
        setTimeout(() => {
            updatePredictionModel();
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Refresh';
        }, 1500);
    });
    
    // Export chart button
    document.querySelector('.export-chart').addEventListener('click', function() {
        exportHistoricalChart();
    });
});

/**
 * Initialize historical comparison chart
 */
function initializeHistoricalChart() {
    const ctx = document.getElementById('historical-chart').getContext('2d');
    
    historicalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Current Data',
                data: [],
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderWidth: 2,
                tension: 0.2,
                pointRadius: 3,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Rainfall (mm)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'top',
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'xy',
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    
    // Load initial data
    loadHistoricalData();
}

/**
 * Toggle active class on historical data buttons
 */
function toggleHistoricalButtons() {
    if (currentHistoricalMode === 'rainfall') {
        document.getElementById('btn-rainfall-history').classList.add('active');
        document.getElementById('btn-water-level-history').classList.remove('active');
    } else {
        document.getElementById('btn-rainfall-history').classList.remove('active');
        document.getElementById('btn-water-level-history').classList.add('active');
    }
}

/**
 * Load historical data for comparison
 */
function loadHistoricalData() {
    // Update chart title and axis label based on mode
    if (currentHistoricalMode === 'rainfall') {
        historicalChart.options.scales.y.title.text = 'Rainfall (mm)';
    } else {
        historicalChart.options.scales.y.title.text = 'Water Level (m)';
    }
    
    // Fetch data from API
    fetch(`/api/chart-data/?type=${currentHistoricalMode}&days=${currentHistoricalPeriod}`)
        .then(response => response.json())
        .then(data => {
            // Update current data
            historicalChart.data.labels = data.labels || [];
            historicalChart.data.datasets[0].data = data.values || [];
            
            // Ensure we have only one or two datasets
            if (historicalChart.data.datasets.length > 2) {
                historicalChart.data.datasets.length = 1;
            }
            
            // Add historical comparison data if not already there
            if (historicalChart.data.datasets.length === 1) {
                addHistoricalComparisonData();
            } else {
                // Just update the chart with current data
                historicalChart.update();
            }
        })
        .catch(error => {
            console.error(`Error loading ${currentHistoricalMode} historical data:`, error);
        });
}

/**
 * Add historical comparison data to chart
 */
function addHistoricalComparisonData() {
    // In a real app, this would fetch past years' data from the API
    // For this example, we'll generate synthetic historical data
    
    // Get current dataset values and create a modified version for comparison
    const currentData = historicalChart.data.datasets[0].data;
    const historicalValues = currentData.map(value => {
        // Create a variation of current data for demonstration
        const variance = Math.random() * 0.3 + 0.7; // 70-100% of current value
        return value * variance;
    });
    
    // Add the historical dataset
    historicalChart.data.datasets.push({
        label: 'Historical Average (Past 3 Years)',
        data: historicalValues,
        borderColor: 'rgba(128, 128, 128, 0.7)',
        backgroundColor: 'rgba(128, 128, 128, 0.1)',
        borderWidth: 1,
        borderDash: [5, 5],
        tension: 0.2,
        pointRadius: 2,
        pointHoverRadius: 4
    });
    
    // Update the chart
    historicalChart.update();
    
    // Add flood threshold line if we're showing water level
    if (currentHistoricalMode === 'water_level') {
        // Get the max value to ensure our threshold is visible
        const maxValue = Math.max(...currentData, ...historicalValues);
        
        // Add threshold line at 1.5m (typical flood level)
        const floodThreshold = 1.5;
        
        // Add annotation if it's within visible range
        if (floodThreshold <= maxValue * 1.2) {
            addThresholdLine(floodThreshold, 'Flood Stage', 'rgba(220, 53, 69, 0.7)');
        }
    }
}

/**
 * Add a threshold line to the chart
 */
function addThresholdLine(value, label, color) {
    // We'd use the annotation plugin in a full implementation
    // For this example, we'll just add another dataset as a horizontal line
    
    // Create array of same value for every label
    const thresholdData = historicalChart.data.labels.map(() => value);
    
    // Add the threshold dataset
    historicalChart.data.datasets.push({
        label: label,
        data: thresholdData,
        borderColor: color,
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 0,
        pointHoverRadius: 0,
        tension: 0
    });
    
    // Update the chart
    historicalChart.update();
}

/**
 * Update the prediction model visualization
 */
function updatePredictionModel() {
    // In a real app, this would call an AI/ML model API
    // For demo purposes, we'll generate a probability
    
    // Generate random probability between 30-90%
    const probability = Math.floor(Math.random() * 60) + 30;
    
    // Update the gauge
    document.getElementById('flood-probability').textContent = probability + '%';
    
    // Change color based on probability
    const gaugeCircle = document.querySelector('.gauge-circle');
    if (probability >= 75) {
        gaugeCircle.style.background = 'conic-gradient(#dc3545 0% 100%)';
    } else if (probability >= 50) {
        gaugeCircle.style.background = 'conic-gradient(#ffc107 0% 100%)';
    } else {
        gaugeCircle.style.background = 'conic-gradient(#0dcaf0 0% 100%)';
    }
    
    // Update predicted impact
    let impactText;
    if (probability >= 75) {
        impactText = 'Severe flooding likely with significant impact to infrastructure and possible evacuation requirements.';
    } else if (probability >= 50) {
        impactText = 'Moderate flooding expected in low-lying areas with potential minor property damage.';
    } else {
        impactText = 'Minor flooding possible in flood-prone areas, general population unlikely to be affected.';
    }
    document.getElementById('prediction-impact').textContent = impactText;
    
    // Update ETA
    // Generate a random time between 6-48 hours from now
    const hoursToFlood = Math.floor(Math.random() * 42) + 6;
    const floodDate = new Date();
    floodDate.setHours(floodDate.getHours() + hoursToFlood);
    
    let etaText;
    if (probability >= 60) {
        etaText = `Estimated flood arrival: ${floodDate.toLocaleString()} (approximately ${hoursToFlood} hours from now)`;
    } else {
        etaText = 'No immediate flood threat expected in the next 24 hours.';
    }
    document.getElementById('prediction-eta').textContent = etaText;
    
    // Update contributing factors
    const factorsElement = document.getElementById('contributing-factors');
    const factorsList = [];
    
    if (Math.random() > 0.5) factorsList.push('Sustained heavy rainfall over the past 24 hours');
    if (Math.random() > 0.5) factorsList.push('Soil saturation from previous precipitation');
    if (Math.random() > 0.4) factorsList.push('Elevated water levels in nearby water bodies');
    if (Math.random() > 0.7) factorsList.push('Forecast for continued precipitation');
    if (Math.random() > 0.6) factorsList.push('Upstream dam water releases');
    if (factorsList.length === 0) factorsList.push('No significant contributing factors identified');
    
    factorsElement.innerHTML = factorsList.map(factor => `<li>${factor}</li>`).join('');
    
    // Update the last prediction time
    document.getElementById('last-prediction-time').textContent = new Date().toLocaleString();
}

/**
 * Load potentially affected barangays
 */
function loadPotentiallyAffectedBarangays() {
    // In a real app, this would fetch from an API based on the prediction model
    // For demo purposes, we'll use sample data
    
    fetch('/api/barangays/')
        .then(response => response.json())
        .then(data => {
            if (!data.results || data.results.length === 0) {
                document.getElementById('affected-barangays').innerHTML = 
                    '<tr><td colspan="4" class="text-center">No barangay data available.</td></tr>';
                return;
            }
            
            // Take a subset of barangays and mark them as potentially affected
            const barangays = data.results.slice(0, 5); // Limit to 5 for demo
            
            // Generate sample risk levels
            const riskLevels = ['High', 'Moderate', 'Moderate', 'Low', 'Low'];
            const evacuationCenters = [3, 2, 2, 1, 1]; // Sample number of evacuation centers
            
            // Build the table rows
            let barangayRows = '';
            
            barangays.forEach((barangay, index) => {
                const riskClass = riskLevels[index] === 'High' ? 'text-danger' : 
                    (riskLevels[index] === 'Moderate' ? 'text-warning' : 'text-success');
                
                barangayRows += `
                    <tr>
                        <td><a href="/barangays/${barangay.id}/" class="text-decoration-none">${barangay.name}</a></td>
                        <td class="text-center">${barangay.population.toLocaleString()}</td>
                        <td class="text-center"><span class="${riskClass} fw-bold">${riskLevels[index]}</span></td>
                        <td class="text-center">${evacuationCenters[index]}</td>
                    </tr>
                `;
            });
            
            // Update the table
            document.getElementById('affected-barangays').innerHTML = barangayRows;
        })
        .catch(error => {
            console.error('Error loading barangay data:', error);
            document.getElementById('affected-barangays').innerHTML = 
                '<tr><td colspan="4" class="text-center text-danger">Error loading barangay data.</td></tr>';
        });
}

/**
 * Set up the alert form validation and enhancement
 */
function setupAlertForm() {
    const form = document.getElementById('alert-form');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        // Basic validation
        const title = document.getElementById('id_title').value.trim();
        const description = document.getElementById('id_description').value.trim();
        const severity = document.getElementById('id_severity_level').value;
        const barangays = document.getElementById('id_affected_barangays');
        
        if (!title) {
            e.preventDefault();
            alert('Please enter an alert title.');
            return;
        }
        
        if (!description) {
            e.preventDefault();
            alert('Please enter an alert description.');
            return;
        }
        
        if (severity === '') {
            e.preventDefault();
            alert('Please select a severity level.');
            return;
        }
        
        // Check if at least one barangay is selected
        let barangaySelected = false;
        for (let i = 0; i < barangays.options.length; i++) {
            if (barangays.options[i].selected) {
                barangaySelected = true;
                break;
            }
        }
        
        if (!barangaySelected) {
            e.preventDefault();
            alert('Please select at least one affected barangay.');
            return;
        }
        
        // Confirm before sending emergency alert (levels 4-5)
        if (severity === '4' || severity === '5') {
            if (!confirm('You are about to send an EMERGENCY LEVEL alert. This will trigger immediate notifications to all emergency contacts. Are you sure you want to proceed?')) {
                e.preventDefault();
                return;
            }
        }
    });
    
    // Dynamic form behavior - update predicted flood time requirement based on severity
    document.getElementById('id_severity_level').addEventListener('change', function() {
        const severityLevel = parseInt(this.value);
        const predictionTimeField = document.getElementById('id_predicted_flood_time');
        
        // Make prediction time required for high severity levels
        if (severityLevel >= 3) {
            predictionTimeField.setAttribute('required', 'required');
            predictionTimeField.parentElement.classList.add('required-field');
        } else {
            predictionTimeField.removeAttribute('required');
            predictionTimeField.parentElement.classList.remove('required-field');
        }
    });
}

/**
 * Export historical chart as image
 */
function exportHistoricalChart() {
    if (!historicalChart) return;
    
    // Create a temporary link for downloading
    const link = document.createElement('a');
    link.download = `flood-prediction-${currentHistoricalMode}-${new Date().toISOString().slice(0, 10)}.png`;
    
    // Convert chart to data URL
    link.href = historicalChart.toBase64Image();
    link.click();
}
