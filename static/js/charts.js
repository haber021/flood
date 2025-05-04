/**
 * Charts.js - Data visualization charts functionality
 * Handles chart creation, updates, and exports for the dashboard
 */

// Global chart objects
let temperatureChart;
let rainfallChart;
let waterLevelChart;

// Chart colors
const chartColors = {
    temperature: {
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)'
    },
    rainfall: {
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)'
    },
    waterLevel: {
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)'
    }
};

// Default time period in days
let chartTimePeriod = 1;

// Chart initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts if we're on the dashboard page
    if (document.getElementById('temperature-chart')) {
        initializeCharts();
        
        // Setup time period selector
        document.querySelectorAll('.chart-period').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                // Update active period
                chartTimePeriod = parseInt(this.getAttribute('data-days'));
                // Update dropdown button text
                document.getElementById('chartDropdown').textContent = this.textContent;
                // Reload chart data
                loadChartData('temperature');
                loadChartData('rainfall');
                loadChartData('water_level');
            });
        });
        
        // Setup reset zoom buttons
        document.querySelectorAll('.reset-zoom').forEach(btn => {
            btn.addEventListener('click', function() {
                const chartId = this.getAttribute('data-chart');
                resetZoom(chartId);
            });
        });
        
        // Setup export buttons
        document.querySelectorAll('.export-chart').forEach(btn => {
            btn.addEventListener('click', function() {
                const chartId = this.getAttribute('data-chart');
                exportChart(chartId);
            });
        });
        
        // Set up window resize handler to adjust charts
        window.addEventListener('resize', function() {
            if (temperatureChart) {
                setTimeout(function() { temperatureChart.resize(); }, 100);
            }
            if (rainfallChart) {
                setTimeout(function() { rainfallChart.resize(); }, 100);
            }
            if (waterLevelChart) {
                setTimeout(function() { waterLevelChart.resize(); }, 100);
            }
        });
    }
});

/**
 * Initialize all charts with empty data
 */
function initializeCharts() {
    // Create temperature chart
    temperatureChart = createChart('temperature-chart', 'Temperature (°C)', chartColors.temperature);
    
    // Create rainfall chart
    rainfallChart = createChart('rainfall-chart', 'Rainfall (mm)', chartColors.rainfall);
    
    // Create water level chart
    waterLevelChart = createChart('water-level-chart', 'Water Level (m)', chartColors.waterLevel);
    
    // Load initial data
    loadChartData('temperature');
    loadChartData('rainfall');
    loadChartData('water_level');
}

/**
 * Update all charts at once
 * Used when location or filters change
 */
function updateAllCharts() {
    console.log('Updating all charts with location filters...');
    console.log('Current Municipality:', window.selectedMunicipality ? window.selectedMunicipality.name : 'All Municipalities');
    console.log('Current Barangay:', window.selectedBarangay ? window.selectedBarangay.name : 'All Barangays');
    
    // Reset zoom on all charts
    resetZoom('temperature-chart');
    resetZoom('rainfall-chart');
    resetZoom('water-level-chart');
    
    // Reload data for all charts with the current location filters
    loadChartData('temperature');
    loadChartData('rainfall');
    loadChartData('water_level');
    
    // Update the location display in the UI if applicable
    const locationDisplay = document.getElementById('current-location-display');
    if (locationDisplay) {
        let locationText = 'All Areas';
        
        if (window.selectedMunicipality) {
            locationText = window.selectedMunicipality.name;
            
            if (window.selectedBarangay) {
                locationText += ' > ' + window.selectedBarangay.name;
            }
        }
        
        locationDisplay.textContent = locationText;
    }
}

/**
 * Create a new chart with the specified configuration
 */
function createChart(canvasId, label, colors) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Register the zoom plugin if not already registered
    if (!Chart.registry.getPlugin('zoom')) {
        console.warn('Chart.js zoom plugin not detected. Some features may be limited.');
    }
    
    // Determine if we're on a mobile device
    const isMobile = window.innerWidth < 768;
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderColor: colors.borderColor,
                backgroundColor: colors.backgroundColor,
                borderWidth: isMobile ? 1.5 : 2,
                tension: 0.2,
                pointRadius: isMobile ? 2 : 3,
                pointHoverRadius: isMobile ? 4 : 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 750, // General animation duration
                easing: 'easeOutQuart'
            },
            onResize: function(chart, size) {
                // Adjust point sizes based on screen width
                const newIsMobile = size.width < 768;
                chart.data.datasets.forEach(dataset => {
                    dataset.pointRadius = newIsMobile ? 2 : 3;
                    dataset.pointHoverRadius = newIsMobile ? 4 : 5;
                    dataset.borderWidth = newIsMobile ? 1.5 : 2;
                });
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: label,
                        font: {
                            size: isMobile ? 10 : 12
                        }
                    },
                    ticks: {
                        // Add padding so that points near the top or bottom are visible
                        padding: isMobile ? 5 : 10,
                        font: {
                            size: isMobile ? 9 : 11
                        },
                        maxTicksLimit: isMobile ? 5 : 8 // Limit number of ticks on mobile
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time',
                        padding: {top: 10, bottom: 0}
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)' // Light grid lines
                    },
                    ticks: {
                        // For better readability on mobile
                        maxRotation: 0, // Prevent label rotation
                        minRotation: 0,
                        padding: 12, // More padding between labels
                        font: {
                            size: isMobile ? 10 : 12
                        },
                        maxTicksLimit: isMobile ? 4 : 6, // Further reduce number of ticks to prevent overlap
                        autoSkip: true,
                        callback: function(value, index, values) {
                            // Simplified time formatting
                            if (typeof value === 'string' && value.includes('-')) {
                                // Extract just the time part from ISO format
                                const timePart = value.split('T')[1] || '';
                                if (timePart) {
                                    // Just show hour:minute
                                    return timePart.substring(0, 5); // Take HH:MM part
                                }
                                
                                // If we can't extract a time part, try to use Date object
                                try {
                                    const date = new Date(value);
                                    if (!isNaN(date.getTime())) {
                                        const hours = date.getHours();
                                        const minutes = date.getMinutes();
                                        return hours + ':' + (minutes < 10 ? '0' : '') + minutes;
                                    }
                                } catch (e) {}
                            }
                            return value;
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleFont: {
                        size: isMobile ? 12 : 14
                    },
                    bodyFont: {
                        size: isMobile ? 11 : 13
                    },
                    padding: isMobile ? 8 : 10,
                    displayColors: true,
                    caretSize: isMobile ? 4 : 5
                },
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: isMobile ? 10 : 15,
                        boxWidth: isMobile ? 8 : 10,
                        font: {
                            size: isMobile ? 10 : 12
                        }
                    }
                },
                zoom: {
                    limits: {
                        y: {min: 'original', max: 'original', minRange: 1}
                    },
                    pan: {
                        enabled: true,
                        mode: 'xy',
                        threshold: 10
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        drag: {
                            enabled: true,
                            backgroundColor: 'rgba(0, 100, 200, 0.1)'
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
}

/**
 * Load chart data from API based on sensor type
 */
function loadChartData(sensorType) {
    // Determine which chart to update
    let chart;
    switch (sensorType) {
        case 'temperature':
            chart = temperatureChart;
            break;
        case 'rainfall':
            chart = rainfallChart;
            break;
        case 'water_level':
            chart = waterLevelChart;
            break;
        default:
            console.error('Unknown sensor type:', sensorType);
            return;
    }
    
    // Show loading state
    if (chart) {
        chart.data.labels = ['Loading...'];
        chart.data.datasets[0].data = [0];
        chart.update();
    }
    
    // Construct the URL with parameters
    let url = `/api/chart-data/?type=${sensorType}&days=${chartTimePeriod}`;
    
    // Add location parameters if available
    if (window.selectedMunicipality) {
        url += `&municipality_id=${window.selectedMunicipality.id}`;
        console.log(`[Chart] Adding municipality filter: ${window.selectedMunicipality.name}`);
    }
    
    if (window.selectedBarangay) {
        url += `&barangay_id=${window.selectedBarangay.id}`;
        console.log(`[Chart] Adding barangay filter: ${window.selectedBarangay.name}`);
    }
    
    console.log(`[Chart] Fetching ${sensorType} data with URL: ${url}`);
    
    // Fetch data from API with location filters
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Ensure we have valid data
            if (!data.labels || !data.values || data.labels.length === 0) {
                console.warn(`No chart data available for ${sensorType}`);
                chart.data.labels = ['No Data Available'];
                chart.data.datasets[0].data = [0];
                chart.update();
                return;
            }
            
            // Update chart with new data
            chart.data.labels = data.labels;
            chart.data.datasets[0].data = data.values;
            chart.update();
            
            console.log(`Updated ${sensorType} chart with ${data.labels.length} data points`);
        })
        .catch(error => {
            console.error(`Error loading ${sensorType} chart data:`, error);
            if (chart) {
                chart.data.labels = ['Error Loading Data'];
                chart.data.datasets[0].data = [0];
                chart.update();
            }
        });
}

/**
 * Export chart as image
 */
function exportChart(chartId) {
    let chart;
    
    // Get the appropriate chart object
    switch (chartId) {
        case 'temperature-chart':
            chart = temperatureChart;
            break;
        case 'rainfall-chart':
            chart = rainfallChart;
            break;
        case 'water-level-chart':
            chart = waterLevelChart;
            break;
        default:
            console.error('Unknown chart ID:', chartId);
            return;
    }
    
    if (!chart) return;
    
    // Create a temporary link for downloading
    const link = document.createElement('a');
    link.download = `${chartId}-${new Date().toISOString().slice(0, 10)}.png`;
    
    // Convert chart to data URL
    link.href = chart.toBase64Image();
    link.click();
}

/**
 * Update chart annotations with threshold markers
 */
function addThresholdAnnotation(chart, thresholdValue, label, color) {
    // If we're using Chart.js v3+, we need the annotation plugin
    if (!chart.options.plugins.annotation) {
        chart.options.plugins.annotation = {
            annotations: {}
        };
    }
    
    // Create a unique ID for this annotation
    const id = `threshold-${label.replace(/\s+/g, '-').toLowerCase()}`;
    
    // Add the horizontal line annotation
    chart.options.plugins.annotation.annotations[id] = {
        type: 'line',
        mode: 'horizontal',
        scaleID: 'y',
        value: thresholdValue,
        borderColor: color,
        borderWidth: 2,
        label: {
            backgroundColor: color,
            content: label,
            enabled: true,
            position: 'right'
        }
    };
    
    // Update the chart
    chart.update();
}

/**
 * Add historical comparison data to chart
 */
function addHistoricalComparison(chart, historicalData, label) {
    // Add a new dataset to the chart
    chart.data.datasets.push({
        label: label,
        data: historicalData.values,
        borderColor: 'rgba(128, 128, 128, 0.7)',
        backgroundColor: 'rgba(128, 128, 128, 0.1)',
        borderWidth: 1,
        borderDash: [5, 5],
        tension: 0.2,
        pointRadius: 2,
        pointHoverRadius: 4
    });
    
    // Update the chart
    chart.update();
}

/**
 * Reset chart zoom level
 */
function resetZoom(chartId) {
    let chart;
    
    switch (chartId) {
        case 'temperature-chart':
            chart = temperatureChart;
            break;
        case 'rainfall-chart':
            chart = rainfallChart;
            break;
        case 'water-level-chart':
            chart = waterLevelChart;
            break;
        default:
            return;
    }
    
    if (chart && chart.resetZoom) {
        chart.resetZoom();
    } else if (chart) {
        // For Chart.js v3+ with zoom plugin
        const zoomPlugin = Chart.getPlugin('zoom');
        if (zoomPlugin) {
            zoomPlugin.resetZoom(chart);
        }
    }
}
