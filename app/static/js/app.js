// Theme toggle
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-bs-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', next);
    localStorage.setItem('theme', next);
    const icon = document.getElementById('theme-icon');
    icon.className = next === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
}

// Restore theme
(function() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-bs-theme', saved);
        const icon = document.getElementById('theme-icon');
        if (icon) icon.className = saved === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
    }
})();

// Button group active state
function setActiveBtn(el) {
    el.closest('.btn-group').querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
}

// Sortable table
function initSortable(table) {
    const headers = table.querySelectorAll('th.sortable');
    headers.forEach(th => {
        th.addEventListener('click', () => {
            const col = parseInt(th.dataset.col);
            const type = th.dataset.sort;
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const icon = th.querySelector('.sort-icon');

            // Toggle direction
            const asc = th.dataset.dir !== 'asc';
            th.dataset.dir = asc ? 'asc' : 'desc';

            // Reset all icons
            headers.forEach(h => {
                h.querySelector('.sort-icon').className = 'bi bi-chevron-expand sort-icon';
                if (h !== th) delete h.dataset.dir;
            });
            icon.className = asc ? 'bi bi-chevron-up sort-icon' : 'bi bi-chevron-down sort-icon';

            rows.sort((a, b) => {
                const av = a.children[col].dataset.value || a.children[col].textContent.trim();
                const bv = b.children[col].dataset.value || b.children[col].textContent.trim();
                let cmp;
                if (type === 'num') {
                    cmp = parseFloat(av) - parseFloat(bv);
                } else {
                    cmp = av.localeCompare(bv, 'de');
                }
                return asc ? cmp : -cmp;
            });

            // Re-number and re-append
            rows.forEach((row, i) => {
                row.querySelector('.row-num').textContent = i + 1;
                tbody.appendChild(row);
            });
        });
    });
}

// Price chart rendering
let currentChart = null;

function renderPriceChart() {
    const canvas = document.getElementById('priceChart');
    if (!canvas || !canvas.dataset.events) return;

    if (currentChart) {
        currentChart.destroy();
        currentChart = null;
    }

    const events = JSON.parse(canvas.dataset.events);
    const ctx = canvas.getContext('2d');

    const labels = events.map(e => {
        const d = new Date(e.fetched_at);
        return d.toLocaleString('de-DE', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'});
    });

    const datasets = [];
    const colors = {diesel: '#198754', e5: '#0d6efd', e10: '#fd7e14'};
    const names = {diesel: 'Diesel', e5: 'Super E5', e10: 'Super E10'};

    for (const fuel of ['diesel', 'e5', 'e10']) {
        const data = events.map(e => e[fuel]);
        if (data.some(v => v !== null && v !== undefined)) {
            datasets.push({
                label: names[fuel],
                data: data,
                borderColor: colors[fuel],
                backgroundColor: colors[fuel] + '20',
                tension: 0.3,
                pointRadius: 3,
                fill: true,
            });
        }
    }

    currentChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                y: { ticks: { callback: v => v.toFixed(3) + ' €' } }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: item => item.dataset.label + ': ' + item.raw.toFixed(3) + ' €'
                    }
                }
            }
        }
    });
}

// Init on load and after HTMX swaps
function initAllSortables() {
    document.querySelectorAll('.sortable-table').forEach(initSortable);
}

function onSwap() {
    initAllSortables();
    renderPriceChart();
}

document.addEventListener('DOMContentLoaded', onSwap);
document.addEventListener('htmx:afterSwap', onSwap);
