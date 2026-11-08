// Dashboard Chart.js Visualizations
// Fetches live JSON data from /api/charts/demand-vs-actual and /api/charts/category-breakdown

document.addEventListener('DOMContentLoaded', () => {
    initDemandVsActualChart();
    initCategoryDonutChart();
});

async function initDemandVsActualChart() {
    const canvas = document.getElementById('demandVsActualChart');
    if (!canvas) return;

    try {
        const response = await fetch('/api/charts/demand-vs-actual');
        const data = await response.json();

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: data.datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            font: { size: 11, family: 'Inter, system-ui, sans-serif' }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.dataset.label}: ${context.parsed.y} portions`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 10 },
                            maxRotation: 30,
                            minRotation: 15
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(226, 232, 240, 0.6)' },
                        ticks: {
                            stepSize: 10,
                            font: { size: 10 }
                        },
                        title: {
                            display: true,
                            text: 'Units (Portions)',
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    } catch (err) {
        console.error('Failed to load demand vs actual chart data:', err);
    }
}

async function initCategoryDonutChart() {
    const canvas = document.getElementById('categoryDonutChart');
    if (!canvas) return;

    try {
        const response = await fetch('/api/charts/category-breakdown');
        const res = await response.json();

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: res.labels,
                datasets: [{
                    data: res.data,
                    backgroundColor: [
                        '#10b981', // Emerald
                        '#3b82f6', // Blue
                        '#8b5cf6', // Purple
                        '#f59e0b', // Amber
                        '#ec4899', // Pink
                        '#14b8a6'  // Teal
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 10,
                            font: { size: 10 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const val = context.parsed;
                                return ` ${context.label}: ${val} portions forecasted`;
                            }
                        }
                    }
                },
                cutout: '65%'
            }
        });
    } catch (err) {
        console.error('Failed to load category donut chart:', err);
    }
}
