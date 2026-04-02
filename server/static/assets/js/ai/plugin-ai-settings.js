(function() {
    function mergeAiSettingsConfig(previousConfig = {}, nextConfig = {}) {
        return {
            ...previousConfig,
            ...nextConfig,
            api_key: null,
        };
    }

    function syncPluginAiSettingsState(config = {}) {
        window.currentAiConfig = mergeAiSettingsConfig(window.currentAiConfig || {}, config || {});
        return window.currentAiConfig;
    }

    async function fetchCurrentAiSettings() {
        const response = await fetch('/api/ai/settings');
        const data = await response.json().catch(() => null);
        if (!response.ok) {
            throw new Error((data && data.detail) || `HTTP ${response.status}`);
        }
        window.currentAiConfig = data?.active_profile || null;
        if (typeof window.updatePluginAiComposerSelections === 'function') {
            window.updatePluginAiComposerSelections({
                profiles: Array.isArray(data?.profiles) ? data.profiles : [],
                selectedProfileKey: data?.active_profile?.profile_key || null,
                selectedModel: data?.active_profile?.model || null,
            });
        }
        return data;
    }

    window.mergeAiSettingsConfig = mergeAiSettingsConfig;
    window.syncPluginAiSettingsState = syncPluginAiSettingsState;
    window.fetchCurrentAiSettings = fetchCurrentAiSettings;
})();
