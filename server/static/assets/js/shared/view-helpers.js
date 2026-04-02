(function() {
    window.formatInstallCount = function(value) {
        const installs = parseInt(value || 0, 10) || 0;
        if (installs >= 1000000) return `${(installs / 1000000).toFixed(1)}M`;
        if (installs >= 1000) return `${Math.round(installs / 1000)}K`;
        return String(installs);
    };

    window.parseDaysSinceUpdate = function(value) {
        const parsed = parseInt(value, 10);
        return Number.isFinite(parsed) ? Math.max(0, parsed) : null;
    };

    window.getRiskClassForResult = function(score) {
        if (score >= 40) return 'high';
        if (score >= 20) return 'medium';
        return 'low';
    };

    window.getRiskColorForClass = function(riskClass) {
        if (riskClass === 'high') return '#ff5f56';
        if (riskClass === 'medium') return '#ffbd2e';
        return '#00f3ff';
    };

    window.getRiskColorForScore = function(score) {
        return window.getRiskColorForClass(window.getRiskClassForResult(score));
    };

    window.getUpdatedChipClass = function(daysSinceUpdate) {
        if (daysSinceUpdate == null) return '';
        if (daysSinceUpdate >= 365) return 'old';
        if (daysSinceUpdate >= 180) return 'stale';
        return '';
    };

    window.getUpdatedLabel = function(daysSinceUpdate) {
        if (daysSinceUpdate == null) return 'N/A';
        if (daysSinceUpdate < 1) return 'today';
        if (daysSinceUpdate < 30) return `${daysSinceUpdate}d ago`;
        if (daysSinceUpdate < 365) return `${Math.round(daysSinceUpdate / 30)}mo ago`;
        return `${Math.round(daysSinceUpdate / 365)}y ago`;
    };
})();
