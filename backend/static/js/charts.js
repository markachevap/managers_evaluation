// Инициализация всех графиков на странице
document.addEventListener('DOMContentLoaded', function() {
    // График эффективности
    const perfChart = document.getElementById('performanceChart');
    if (perfChart) {
        new Chart(perfChart, {
            type: 'line',
            data: {
                labels: JSON.parse(perfChart.dataset.labels),
                datasets: [{
                    label: 'Эффективность',
                    data: JSON.parse(perfChart.dataset.values),
                    borderColor: '#3e95cd',
                    fill: false
                }]
            }
        });
    }
});