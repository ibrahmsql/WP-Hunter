(function() {
    async function initializeApp() {
        initializeSidebarToggle();
        initializeStarStripDismiss();
        initializeDashboardChartInteractions();
        initializePagesAutoRandom();
        bindPluginAiUiEvents();
        setPluginAiComposerEnabled(false);

        await refreshFavoriteSlugs();
        loadHistory();
        restoreViewFromUrl();
        window.addEventListener('popstate', restoreViewFromUrl);

        const updateButton = document.getElementById('update-action-btn');
        if (updateButton) {
            updateButton.addEventListener('click', initiateSystemUpdate);
        }

        startSystemStatusPolling();
    }

    document.addEventListener('DOMContentLoaded', () => {
        initializeApp().catch((error) => {
            console.error('App bootstrap failed:', error);
        });
    });
})();
