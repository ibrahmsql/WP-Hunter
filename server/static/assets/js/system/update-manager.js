(function() {
    const runtime = window.temodarAgentRuntime;

function normalizeVersionTag(tag) {
    const value = String(tag || "").trim();
    if (!value) return "";
    return value.replace(/^v+/i, "");
}

function formatVersionLabel(tag) {
    const normalized = normalizeVersionTag(tag);
    return normalized ? `v${normalized}` : "";
}

function renderServerUpdateAlert(data) {
    const sidebar = document.getElementById('sidebar');
    if (!data) return;

    const hasLatestVersion = !!(data.latest_version && String(data.latest_version).trim());

    if (data.in_progress) {
        if (sidebar) sidebar.classList.add('has-update');
        return;
    }

    if (data.update_available && hasLatestVersion) {
        if (sidebar) sidebar.classList.add('has-update');
        const latestVersion = formatVersionLabel(data.latest_version) || "NEW";

        if (data.latest_version && runtime.getAnnouncedUpdateVersion() !== data.latest_version) {
            runtime.setAnnouncedUpdateVersion(data.latest_version);
            showToast(
                `New release detected (${latestVersion}). Open the update card to install it.`,
                "warn"
            );
        }
        return;
    }

    if (sidebar) sidebar.classList.remove('has-update');
    runtime.setAnnouncedUpdateVersion("");
}

async function loadSystemStatus(force = false) {
    try {
        const url = `/api/system/update${force ? "?force=true" : ""}`;
        const resp = await fetch(url);
        if (!resp.ok) {
            throw new Error("Release check failed");
        }
        const data = await resp.json();
        runtime.setSystemStatus(data);
        renderSystemStatus(data);
    } catch (err) {
        console.error("System status refresh failed:", err);
        runtime.setSystemStatus(runtime.getSystemStatus() || null);
    }
}

function renderSystemStatus(data) {
    if (!data) return;

    const versionEl = document.getElementById("app-version");
    if (versionEl && data.current_version) {
        versionEl.textContent = `v${data.current_version}`;
    }
    renderServerUpdateAlert(data);

    const updateCallout = document.getElementById("update-callout");
    const updateButton = document.getElementById("update-action-btn");
    const updateDescription = document.getElementById("update-description");
    const updateVersion = document.getElementById("update-latest-version");
    const releaseLink = document.getElementById("update-release-link");
    const updateProgress = document.getElementById("update-progress");
    const updateProgressText = document.getElementById("update-progress-text");

    const hasLatestVersion = !!(data.latest_version && String(data.latest_version).trim());
    if (data.update_available && hasLatestVersion) {
        if (updateCallout) updateCallout.hidden = false;
        if (updateVersion) {
            updateVersion.textContent = formatVersionLabel(data.latest_version) || "New release";
        }
        if (updateDescription) {
            updateDescription.textContent =
                truncateText(data.release_notes) ||
                "Release notes are not available yet.";
        }
        if (releaseLink) {
            releaseLink.href = data.release_url || "#";
        }
        if (updateButton) {
            updateButton.disabled = !!data.in_progress;
            updateButton.textContent = data.in_progress
                ? "UPDATING…"
                : "REBUILD & UPDATE";
        }
    } else if (updateCallout) {
        updateCallout.hidden = true;
    }

    if (data.in_progress) {
        if (updateProgress) updateProgress.hidden = false;
        if (updateProgressText) {
            updateProgressText.textContent =
                data.progress_message || "Downloading update…";
        }
    } else if (updateProgress) {
        updateProgress.hidden = true;
    }

    if (data.last_error && data.last_error !== runtime.getLastSystemErrorMessage()) {
        runtime.setLastSystemErrorMessage(data.last_error);
        showToast(`Update check failed: ${data.last_error}`, "warn");
    }

    if (
        data.last_update_message &&
        data.last_update_message !== runtime.getLastSystemUpdateMessage()
    ) {
        runtime.setLastSystemUpdateMessage(data.last_update_message);
        showToast(data.last_update_message, "success");
    }
}

function startSystemStatusPolling() {
    const activeTimer = runtime.getSystemStatusTimer();
    if (activeTimer) {
        clearInterval(activeTimer);
    }

    loadSystemStatus();
    runtime.setSystemStatusTimer(
        setInterval(() => loadSystemStatus(), runtime.getSystemPollInterval())
    );
}

async function initiateSystemUpdate() {
    const systemStatus = runtime.getSystemStatus();
    if (!systemStatus || !systemStatus.update_available) {
        showToast("No newer update is available right now.", "info");
        return;
    }

    if (systemStatus.in_progress) {
        showToast("An update is already running.", "info");
        return;
    }

    const latestVersion =
        formatVersionLabel(systemStatus.latest_version) || "the latest release";
    const confirmMessage = `${latestVersion} will be pulled from source, a fresh Docker image will be built, and the container will be restarted automatically. Do you want to continue?`;
    const userConfirmed = await window.showConfirm(confirmMessage);
    if (!userConfirmed) return;

    try {
        const resp = await fetch("/api/system/update", {
            method: "POST",
        });
        if (!resp.ok) {
            const errorText = await resp.text();
            throw new Error(errorText || "Update request failed.");
        }

        const payload = await resp.json();
        showToast(
            payload.message || "Update started. Rebuild and restart are running in the background.",
            "success"
        );
        loadSystemStatus(true);
    } catch (err) {
        console.error("Failed to trigger update:", err);
        showToast(
            `Failed to start update: ${err.message || "unknown error"}`,
            "error"
        );
    }
}

window.startSystemStatusPolling = startSystemStatusPolling;
window.initiateSystemUpdate = initiateSystemUpdate;
})();
