// Basic JS for policy card click (opens URL in new tab)
document.addEventListener('DOMContentLoaded', function() {
    const policyCards = document.querySelectorAll('.policy-card');
    policyCards.forEach(card => {
        card.addEventListener('click', function() {
            const url = this.dataset.url;
            if (url) {
                window.open(url, '_blank');
            }
        });
    });

    // TODO: Implement notification dropdown toggle and functionality in home.js
    // You will need to fetch notifications and handle the red dot and close buttons.
});
