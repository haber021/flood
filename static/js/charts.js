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
            if (temperatureChart) temperatureChart.resize();
            if (rainfallChart) rainfallChart.resize();
            if (waterLevelChart) waterLevelChart.resize();
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
    console.log('Updating all charts...');
    // Reset zoom on all charts
    resetZoom('temperature-chart');
    resetZoom('rainfall-chart');
    resetZoom('water-level-chart');
    
    // Reload data for all charts
    loadChartData('temperature');
    loadChartData('rainfall');
    loadChartData('water_level');
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
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderColor: colors.borderColor,
                backgroundColor: colors.backgroundColor,
                borderWidth: 2,
                tension: 0.2,
                pointRadius: 3,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 750, // General animation duration
                easing: 'easeOutQuart'
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: label
                    },
                    ticks: {
                        // Add padding so that points near the top or bottom are visible
                        padding: 10
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    },
                    ticks: {
                        // For better readability on mobile
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 13
                    },
                    padding: 10
                },
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
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
    
    // Fetch data from API
    fetch(`/api/chart-data/?type=${sensorType}&days=${chartTimePeriod}`)
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
