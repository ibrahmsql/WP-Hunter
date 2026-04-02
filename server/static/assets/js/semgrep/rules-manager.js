(function() {
// SEMGREP RULES MANAGEMENT
// ==========================================

window.loadSemgrepRules = async function() {
    const rulesetsListEl = document.getElementById('semgrep-rulesets-list');
    const customRulesListEl = document.getElementById('semgrep-custom-rules-list');

    if (!rulesetsListEl || !customRulesListEl) return;

    try {
        const response = await fetch('/api/semgrep/rules');
        const data = await response.json();

        const formatRulesetLabel = (rs) => {
            const id = String(rs?.id || '').trim();
            if (!id) return 'p/custom';
            if (id.startsWith('p/') || id.startsWith('r/')) return id;
            const known = {
                'owasp-top-ten': 'p/owasp-top-ten',
                'php-security': 'p/php',
                'security-audit': 'p/security-audit'
            };
            return known[id] || `p/${id}`;
        };
        const jsArg = (value) => JSON.stringify(String(value || ''));

        let rulesetsHtml = `
            <div class="semgrep-section-head">
                <h3>SECURITY RULESETS</h3>
            </div>
            <div class="semgrep-ruleset-input-row">
                <input type="text" id="new-ruleset-id" placeholder="p/cwe-top-25 or p/owasp-top-ten">
                <button onclick="addSemgrepRuleset()" class="action-btn semgrep-outline-btn">ADD RULESET</button>
            </div>
        `;

        const renderRulesetCard = (rs) => {
            const idText = escapeHtml(formatRulesetLabel(rs));
            const rawId = escapeHtml(String(rs.id || ''));
            const link = escapeHtml(String(rs.url || '#'));
            const enabled = !!rs.enabled;
            const toggleTitle = enabled ? 'Set Disabled' : 'Set Active';
            return `
                <div class="semgrep-ruleset-card${enabled ? '' : ' is-disabled'}">
                    <div class="semgrep-ruleset-row">
                        <div class="semgrep-ruleset-meta">
                            <span class="semgrep-ruleset-id" title="${rawId}">${idText}</span>
                            <a class="semgrep-ruleset-view" href="${link}" target="_blank" rel="noreferrer noopener">View ↗</a>
                        </div>
                        <div class="semgrep-card-actions">
                            <button onclick='toggleRuleset(${jsArg(rs.id)})' class="semgrep-mini-toggle${enabled ? ' is-on' : ''}" title="${toggleTitle}" aria-label="${toggleTitle}"></button>
                            ${rs.deletable ? `
                            <button onclick='deleteRuleset(${jsArg(rs.id)}, true)' class="action-btn semgrep-icon-btn semgrep-delete-btn" title="Delete Ruleset" aria-label="Delete Ruleset">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                            </button>` : ''}
                        </div>
                    </div>
                </div>
            `;
        };

        if (data.rulesets && data.rulesets.length > 0) {
            const coreRulesetIds = new Set(['owasp-top-ten', 'php-security', 'security-audit']);
            const coreRulesets = data.rulesets.filter(rs => coreRulesetIds.has(String(rs.id || '').trim()));
            const extraRulesets = data.rulesets.filter(rs => !coreRulesetIds.has(String(rs.id || '').trim()));

            rulesetsHtml += coreRulesets.map(renderRulesetCard).join('');

            if (extraRulesets.length > 0) {
                rulesetsHtml += `<div style="margin-top: 12px; margin-bottom: 10px;">
                    <div class="semgrep-subgroup-label">Advanced / Extra Rulesets (${extraRulesets.length})</div>
                    ${extraRulesets.map(renderRulesetCard).join('')}
                </div>`;
            }
        } else {
            rulesetsHtml += '<div class="semgrep-empty">No rulesets found. Add one above (example: p/cwe-top-25).</div>';
        }

        const customRules = data.custom_rules || [];
        const enabledCustomRules = customRules.filter(rule => rule.enabled).length;
        const allCustomRulesEnabled = customRules.length > 0 && enabledCustomRules === customRules.length;
        const bulkToggleTargetEnabled = !allCustomRulesEnabled;
        const bulkToggleLabel = allCustomRulesEnabled ? 'ALL OFF' : 'ALL ON';
        const bulkToggleStyles = allCustomRulesEnabled
            ? 'background: rgba(255,0,85,0.1); color: #ff0055; border: 1px solid rgba(255,0,85,0.35);'
            : 'background: rgba(0,255,157,0.1); color: var(--accent-primary); border: 1px solid rgba(0,255,157,0.35);';
        const bulkToggleDisabled = customRules.length === 0;
        const bulkToggleDisabledAttr = bulkToggleDisabled
            ? 'disabled title="No custom rules to toggle"'
            : '';
        const bulkToggleResolvedStyles = bulkToggleDisabled
            ? 'opacity:0.6; cursor:not-allowed; border:1px solid #444; color:#777; background:rgba(90,90,90,0.1);'
            : bulkToggleStyles;

        let customHtml = `<div class="semgrep-section-head">
                    <h3>CUSTOM RULES</h3>
                    <button
                        onclick="toggleAllCustomRules(${bulkToggleTargetEnabled})"
                        class="action-btn semgrep-outline-btn ${allCustomRulesEnabled ? 'is-danger' : ''}"
                        style="${bulkToggleResolvedStyles}"
                        ${bulkToggleDisabledAttr}
                    >${bulkToggleLabel}</button>
                </div>`;

        if (customRules.length > 0) {
            customHtml += customRules.map(rule => `
                <div class="semgrep-custom-card${!rule.enabled ? ' is-disabled' : ''}">
                    <div class="semgrep-custom-row">
                        <div class="semgrep-custom-meta">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                                <span class="semgrep-custom-id">${escapeHtml(rule.id)}</span>
                                <span class="tag ${rule.severity === 'ERROR' ? 'risk' : (rule.severity === 'WARNING' ? 'warn' : '')}" style="font-size: 9px;">${escapeHtml(rule.severity)}</span>
                            </div>
                            <div class="semgrep-custom-message">${escapeHtml(rule.message)}</div>
                            <div class="semgrep-custom-pattern">
                                ${escapeHtml(rule.pattern || 'Multiple patterns')}
                            </div>
                        </div>
                        <div class="semgrep-card-actions">
                            <button onclick='toggleSemgrepRule(${jsArg(rule.id)})' class="semgrep-mini-toggle${rule.enabled ? ' is-on' : ''}" title="${rule.enabled ? 'Set Disabled' : 'Set Active'}" aria-label="Toggle rule status"></button>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            customHtml += '<div class="semgrep-empty">No custom rules defined. Add one above.</div>';
        }

        rulesetsListEl.innerHTML = rulesetsHtml;
        customRulesListEl.innerHTML = customHtml;

    } catch (error) {
        console.error('Error loading Semgrep rules:', error);
        const errHtml = `<div class="semgrep-empty" style="color: var(--accent-secondary);">Error loading rules: ${escapeHtml(error.message)}</div>`;
        rulesetsListEl.innerHTML = errHtml;
        customRulesListEl.innerHTML = errHtml;
    }
}

window.toggleRuleset = async function(rulesetId) {
    try {
        const response = await fetch(`/api/semgrep/rulesets/${encodeURIComponent(rulesetId)}/toggle`, {
            method: 'POST'
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            showToast('Failed to toggle ruleset: ' + (data.detail || data.error || `HTTP ${response.status}`), 'error');
            return;
        }

        if (data.success) {
            loadSemgrepRules(); // Reload UI
        } else {
            showToast('Failed to toggle ruleset: ' + (data.detail || data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error toggling ruleset:', error);
        showToast('Error toggling ruleset: ' + (error.message || 'unknown error'), 'error');
    }
}

window.deleteRuleset = async function(rulesetId, deletable = true) {
    if (!deletable) {
        showToast('Built-in rulesets cannot be deleted. You can disable them with the toggle.', 'warn');
        return;
    }
    const confirmed = await showConfirm(`Delete ruleset "${rulesetId}"?`);
    if (!confirmed) return;
    try {
        const response = await fetch(`/api/semgrep/rulesets/${encodeURIComponent(rulesetId)}`, {
            method: 'DELETE'
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            showToast('Failed to delete ruleset: ' + (data.detail || data.error || `HTTP ${response.status}`), 'error');
            return;
        }
        if (data.success) {
            showToast(`Ruleset deleted: ${rulesetId}`, 'success');
            loadSemgrepRules();
        } else {
            showToast('Failed to delete ruleset: ' + (data.detail || data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error deleting ruleset:', error);
        showToast('Error deleting ruleset: ' + error.message, 'error');
    }
}

window.addSemgrepRuleset = async function() {
    const input = document.getElementById('new-ruleset-id');
    const ruleset = (input?.value || '').trim();

    if (!ruleset) {
        showToast('Please enter a ruleset (example: p/cwe-top-25).', 'warn');
        return;
    }

    if (!/^[a-zA-Z0-9_./:-]+$/.test(ruleset)) {
        showToast('Invalid ruleset format. Use values like p/cwe-top-25.', 'warn');
        return;
    }

    try {
        const response = await fetch('/api/semgrep/rulesets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ruleset })
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            showToast('Failed to add ruleset: ' + (data.detail || data.error || `HTTP ${response.status}`), 'error');
            return;
        }

        if (data.success) {
            if (input) input.value = '';
            showToast(`Ruleset added: ${ruleset}`, 'success');
            loadSemgrepRules();
        } else {
            showToast('Failed to add ruleset: ' + (data.detail || data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error adding ruleset: ' + error.message, 'error');
    }
}

window.toggleSemgrepRule = async function(ruleId) {
    try {
        const response = await fetch(`/api/semgrep/rules/${encodeURIComponent(ruleId)}/toggle`, {
            method: 'POST'
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            showToast('Failed to toggle rule: ' + (data.detail || data.error || `HTTP ${response.status}`), 'error');
            return;
        }

        if (data.success) {
            loadSemgrepRules(); // Reload UI
        } else {
            showToast('Failed to toggle rule: ' + (data.detail || data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error toggling rule:', error);
        showToast('Error toggling rule: ' + (error.message || 'unknown error'), 'error');
    }
}

window.toggleAllCustomRules = async function(enabled) {
    try {
        const response = await fetch('/api/semgrep/rules/actions/toggle-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            showToast('Failed to update custom rules: ' + (data.detail || data.error || `HTTP ${response.status}`), 'error');
            return;
        }

        if (data.success) {
            showToast(
                `${enabled ? 'Enabled' : 'Disabled'} ${data.changed}/${data.total} custom rule(s)`,
                'success'
            );
            loadSemgrepRules();
        } else {
            showToast('Failed to update custom rules', 'error');
        }
    } catch (error) {
        showToast('Error updating custom rules: ' + (error.message || 'unknown error'), 'error');
    }
}

window.addSemgrepRule = async function() {
    const ruleId = document.getElementById('new-rule-id').value.trim();
    const pattern = document.getElementById('new-rule-pattern').value.trim();
    const message = document.getElementById('new-rule-message').value.trim();
    const severity = document.getElementById('new-rule-severity').value;

    if (!ruleId || !pattern || !message) {
        showToast('Please fill in all fields: Rule ID, Pattern, and Message.', 'warn');
        return;
    }

    // Validate rule ID format
    if (!/^[a-zA-Z0-9_-]+$/.test(ruleId)) {
        showToast('Rule ID can only contain letters, numbers, hyphens, and underscores.', 'warn');
        return;
    }

    try {
        const response = await fetch('/api/semgrep/rules', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: ruleId,
                pattern: pattern,
                message: message,
                severity: severity,
                languages: ['php']
            })
        });

        const data = await response.json();

        if (data.success) {
            // Clear form
            document.getElementById('new-rule-id').value = '';
            document.getElementById('new-rule-pattern').value = '';
            document.getElementById('new-rule-message').value = '';

            // Reload rules
            loadSemgrepRules();
        } else {
            showToast('Failed to add rule: ' + (data.detail || data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error adding rule: ' + error.message, 'error');
    }
}

})();
