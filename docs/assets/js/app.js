document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const form = document.getElementById('configForm');
    const output = document.getElementById('commandOutput');
    
    // Select info values robustly by index within the container
    const contextInfo = document.getElementById('contextInfo');
    const infoValues = contextInfo.querySelectorAll('.info-value');
    const estTime = infoValues[0];
    const targetCount = infoValues[1];
    
    const modeDisplay = document.querySelector('.mode-display');
    const copyBtn = document.getElementById('copyBtn');
    const randomBtn = document.getElementById('randomBtn');

    // Run once on load
    updateCommand();

    // Event Delegation for Performance and Reliability
    form.addEventListener('change', updateCommand);
    form.addEventListener('input', updateCommand);

    // Copy Button Logic
    if(copyBtn) {
        copyBtn.addEventListener('click', () => {
            const cmdText = output.textContent;
            navigator.clipboard.writeText(cmdText).then(() => {
                const span = copyBtn.querySelector('span');
                const original = span.textContent;
                span.textContent = 'COPIED';
                copyBtn.style.background = '#fff';
                
                setTimeout(() => {
                    span.textContent = original;
                    copyBtn.style.background = '';
                }, 2000);
            }).catch(err => {
                console.error('Copy failed:', err);
                prompt("Copy manually:", cmdText);
            });
        });
    }

    // Random Button Logic
    if (randomBtn) {
        randomBtn.addEventListener('click', () => {
            randomizeConfig();
            updateCommand();
            
            // Visual feedback
            const span = randomBtn.querySelector('span');
            const original = span.textContent;
            span.textContent = '!';
            
            setTimeout(() => {
                span.textContent = original;
            }, 300);
        });
    }

    function randomizeConfig() {
        const randInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
        const randBool = (chance = 0.5) => Math.random() < chance;

        // Reset all first
        form.reset();

        // Scope
        const minVal = randBool(0.7) ? randInt(100, 5000) : 0;
        form.querySelector('[name="min"]').value = minVal || '';
        
        const maxVal = randBool(0.3) ? randInt(minVal + 1000, 50000) : 0;
        form.querySelector('[name="max"]').value = maxVal || '';
        
        form.querySelector('[name="min-days"]').value = randBool(0.2) ? randInt(1, 30) : '';
        form.querySelector('[name="max-days"]').value = randBool(0.2) ? randInt(30, 365) : '';
        
        // Strategy
        const sorts = ['updated', 'new', 'popular'];
        form.querySelector('[name="sort"]').value = sorts[randInt(0, 2)];
        
        const pages = randInt(1, 20);
        const pagesInput = form.querySelector('[name="pages"]');
        pagesInput.value = pages;
        // Update output sibling for slider
        if(pagesInput.nextElementSibling) pagesInput.nextElementSibling.value = pages;
        
        form.querySelector('[name="limit"]').value = randBool(0.4) ? randInt(10, 100) : '';
        
        // Filters (Smart/Risk)
        form.querySelector('[name="smart"]').checked = randBool(0.4);
        form.querySelector('[name="abandoned"]').checked = randBool(0.3);
        form.querySelector('[name="user-facing"]').checked = randBool(0.3);
        
        // Mode (Themes vs Plugins)
        form.querySelector('[name="themes"]').checked = randBool(0.1); 
        
        // Deep Analysis (Lower probability as it's slower)
        const deep = randBool(0.2);
        form.querySelector('[name="deep-analysis"]').checked = deep;
        if(deep) {
            form.querySelector('[name="dangerous-functions"]').checked = randBool(0.5);
            form.querySelector('[name="ajax-scan"]').checked = randBool(0.5);
            form.querySelector('[name="auto-download-risky"]').value = randBool(0.3) ? randInt(1, 5) : '';
        }

        // Output
        if(randBool(0.3)) {
            const formats = ['json', 'csv', 'html'];
            const fmt = formats[randInt(0, 2)];
            form.querySelector('[name="format"]').value = fmt;
            form.querySelector('[name="output"]').value = `scan_results.${fmt}`;
        }
        
        // Random Download Strategy
        if(randBool(0.2)) {
             form.querySelector('[name="download_qty"]').value = randInt(1, 10);
             const modes = ['all', 'risky'];
             form.querySelector('[name="download_mode"]').value = modes[randInt(0, 1)];
        } else {
             form.querySelector('[name="download_mode"]').value = 'none';
             form.querySelector('[name="download_qty"]').value = '';
        }
    }

    function updateCommand() {
        // Use FormData for robust value retrieval
        const data = new FormData(form);
        const parts = ['python3', 'wp-hunter.py'];

        // --- Mode Check ---
        // Checkboxes return 'on' if checked, null if not
        const isThemes = data.get('themes') === 'on';
        
        if (isThemes) {
            parts.push('--themes');
            if(modeDisplay) {
                modeDisplay.textContent = 'THEME SCAN';
                modeDisplay.style.color = '#ff0055';
            }
        } else {
            if(modeDisplay) {
                modeDisplay.textContent = 'PLUGIN RECON';
                modeDisplay.style.color = '#00ff9d';
            }
        }

        // --- Scope ---
        const min = data.get('min');
        if (min && min !== '0') parts.push(`--min ${min}`);

        const max = data.get('max');
        if (max && max !== '0') parts.push(`--max ${max}`);

        const minDays = data.get('min-days');
        if (minDays && minDays !== '0') parts.push(`--min-days ${minDays}`);

        const maxDays = data.get('max-days');
        if (maxDays && maxDays !== '0') parts.push(`--max-days ${maxDays}`);

        // --- Strategy ---
        const sort = data.get('sort');
        if (sort && sort !== 'updated') parts.push(`--sort ${sort}`);

        const pages = data.get('pages');
        if (pages && pages !== '5') parts.push(`--pages ${pages}`);

        const limit = data.get('limit');
        if (limit && limit !== '0') parts.push(`--limit ${limit}`);

        // --- Intelligence (Checkboxes) ---
        if (data.get('smart') === 'on') parts.push('--smart');
        if (data.get('abandoned') === 'on') parts.push('--abandoned');
        if (data.get('user-facing') === 'on') parts.push('--user-facing');

        // --- Deep Analysis ---
        const isDeep = data.get('deep-analysis') === 'on';
        if (isDeep) parts.push('--deep-analysis');
        if (data.get('dangerous-functions') === 'on') parts.push('--dangerous-functions');
        if (data.get('ajax-scan') === 'on') parts.push('--ajax-scan');

        // const riskyLimit = data.get('auto-download-risky'); REMOVED - Unified below
        // if (riskyLimit && riskyLimit !== '0') parts.push(`--auto-download-risky ${riskyLimit}`);

        // --- Output & Artifacts ---
        const outFile = data.get('output');
        if (outFile && outFile.trim() !== '') parts.push(`--output "${outFile.trim()}"`);

        const outFormat = data.get('format');
        if (outFormat && outFormat !== 'json') parts.push(`--format ${outFormat}`); // json is default

        // --- Download Strategy (Unified) ---
        const dlMode = data.get('download_mode');
        const dlQty = data.get('download_qty');
        
        if (dlQty && dlQty !== '0') {
            if (dlMode === 'all') {
                parts.push(`--download ${dlQty}`);
            } else if (dlMode === 'risky') {
                parts.push(`--auto-download-risky ${dlQty}`);
            }
        }

        // Update Output
        if(output) output.textContent = parts.join(' ');

        // Update Context Stats
        updateStats(pages, limit, isDeep);
    }

    function updateStats(pagesStr, limitStr, isDeep) {
        if (!targetCount || !estTime) return;

        const pages = parseInt(pagesStr) || 5;
        const limit = parseInt(limitStr) || 0;
        
        // Calculate total potential targets
        let totalTargets = pages * 100;
        
        // If limit is set and smaller than page capacity, use limit
        if (limit > 0 && limit < totalTargets) {
            totalTargets = limit;
            targetCount.textContent = `${totalTargets}`; // Exact number
        } else {
            targetCount.textContent = `${totalTargets}+`; // Potential range
        }

        // --- Time Calculation Logic ---
        // Base API latency + Page processing
        // Assume ~0.8s per page request (API latency + parsing)
        let seconds = pages * 0.8;
        
        if (isDeep) {
            // Deep Analysis Cost:
            // We assume about 10% of plugins might trigger a download in a broad scan,
            // or 100% if filters are very specific. Let's average to 20% for estimation.
            // Download (1.5s) + Unzip (0.2s) + Analysis (0.5s) = ~2.2s per plugin
            const estimatedDownloads = Math.ceil(totalTargets * 0.15); 
            seconds += (estimatedDownloads * 2.2);
            
            targetCount.style.color = '#ff5f56'; // Red warning color
        } else {
            // Basic metadata analysis is instant
            targetCount.style.color = '#00f3ff';
        }

        // Format Time
        if (seconds < 60) {
            estTime.textContent = `~${Math.ceil(seconds)}s`;
        } else {
            const mins = Math.ceil(seconds / 60);
            estTime.textContent = `~${mins}m`;
        }
    }
});
