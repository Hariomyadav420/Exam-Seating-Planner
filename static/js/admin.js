let utilizationChart = null;

function showMessage(message, type = 'info') {
    const messageArea = document.getElementById('messageArea');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    messageArea.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// ---------------------- SEAT SWAP ----------------------
function swapSeats() {
    const roll1 = document.getElementById('swapRoll1').value.trim();
    const roll2 = document.getElementById('swapRoll2').value.trim();

    if (!roll1 || !roll2) {
        showMessage('Please enter both roll numbers.', 'warning');
        return;
    }
    if (roll1 === roll2) {
        showMessage('Please provide two different roll numbers.', 'warning');
        return;
    }

    if (!confirm(`Are you sure you want to swap seats between ${roll1} and ${roll2}?`)) {
        return;
    }

    showMessage('Swapping seats...', 'info');

    fetch('/api/swap_seats', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ roll1, roll2 })
    })
        .then(resp => resp.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                document.getElementById('swapRoll1').value = '';
                document.getElementById('swapRoll2').value = '';
                setTimeout(() => location.reload(), 1200);
            } else {
                showMessage(data.message || 'Swap failed', 'danger');
            }
        })
        .catch(err => {
            showMessage('Error during swap: ' + err.message, 'danger');
        });
}

// ---------------------- UPLOAD STUDENTS ----------------------
function uploadStudents() {
    const fileInput = document.getElementById('studentFile');
    const file = fileInput.files[0];

    if (!file) {
        showMessage('Please select a file', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showMessage('Uploading students...', 'info');

    fetch('/api/upload_students', {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                fileInput.value = '';
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage(data.message, 'danger');
            }
        })
        .catch(err => {
            showMessage('Error uploading file: ' + err.message, 'danger');
        });
}

// ---------------------- UPLOAD ROOMS ----------------------
function uploadRooms() {
    const fileInput = document.getElementById('roomFile');
    const file = fileInput.files[0];

    if (!file) {
        showMessage('Please select a file', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showMessage('Uploading rooms...', 'info');

    fetch('/api/upload_rooms', {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                fileInput.value = '';
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage(data.message, 'danger');
            }
        })
        .catch(err => {
            showMessage('Error uploading file: ' + err.message, 'danger');
        });
}

// ---------------------- GENERATE ALLOCATION ----------------------
function generateAllocation() {
    const method = document.getElementById('allocationMethod').value;

    let endpoint = '/api/allocate'; // default
    let confirmText = '';

    if (method === 'anti-cheating') {
        endpoint = '/api/allocate_anti_cheating';
        confirmText = 'Generate Anti-Cheating Zig-Zag Seating Plan (2 Courses)?';
    } else if (method === 'rollwise') {
        confirmText = 'Generate Roll-wise Sequential Seating Plan?';
    } else if (method === 'random') {
        confirmText = 'Generate Random Seating Plan?';
    }

    if (!confirm(`${confirmText} This will clear existing allocations.`)) {
        return;
    }

    showMessage('Generating seating plan...', 'info');

    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ method })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage(data.message, 'danger');
            }
        })
        .catch(err => {
            showMessage('Error generating allocation: ' + err.message, 'danger');
        });
}

// ---------------------- ADMIT CARDS ----------------------
function generateAdmitCards() {
    showMessage('Generating admit cards...', 'info');

    fetch('/api/generate_admit_cards', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
            } else {
                showMessage(data.message, 'danger');
            }
        })
        .catch(err => {
            showMessage('Error generating admit cards: ' + err.message, 'danger');
        });
}

// ---------------------- EXPORT EXCEL ----------------------
function exportExcel() {
    window.location.href = '/api/export_excel';
}

// ---------------------- DASHBOARD STATS ----------------------
function loadStats() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const stats = data.stats;
                if (stats.total_capacity > 0) {
                    const utilization = Math.round((stats.allocations / stats.total_capacity) * 100);
                    document.getElementById('utilization').textContent = utilization + '%';
                }
                if (stats.room_utilization && stats.room_utilization.length > 0) {
                    drawUtilizationChart(stats.room_utilization);
                }
            }
        })
        .catch(err => console.error('Error loading stats:', err));
}

function drawUtilizationChart(roomData) {
    const ctx = document.getElementById('utilizationChart');
    if (!ctx) return;

    if (utilizationChart) utilizationChart.destroy();

    const labels = roomData.map(r => r.room_no);
    const percentages = roomData.map(r => r.percentage);

    utilizationChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Utilization %',
                data: percentages,
                backgroundColor: 'rgba(13, 110, 253, 0.7)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: value => value + '%' }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

document.addEventListener('DOMContentLoaded', loadStats);