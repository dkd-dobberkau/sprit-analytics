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
