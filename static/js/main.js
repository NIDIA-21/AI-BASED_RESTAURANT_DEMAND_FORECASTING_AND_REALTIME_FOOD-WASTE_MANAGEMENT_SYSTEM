// General Application Utilities

document.addEventListener('DOMContentLoaded', () => {
    // Automatically dismiss flash alerts after 6 seconds
    const alerts = document.querySelectorAll('.flash-alert');
    if (alerts.length > 0) {
        setTimeout(() => {
            alerts.forEach(el => {
                el.style.opacity = '0';
                el.style.transform = 'translateY(-10px)';
                setTimeout(() => el.remove(), 300);
            });
        }, 6000);
    }
});
