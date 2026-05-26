// --- PYWEBVIEW ZERO-SOCKET IPC FETCH INTERCEPTOR ---
        // Transparently routes all fetch('/api/...') calls through pywebview's
        // in-memory IPC bridge when available. Falls back to normal HTTP fetch
        // when running in browser mode. Works on Windows, macOS, Linux, Ubuntu.
        const originalFetch = window.fetch;
        let _pywebviewReady = false;

        // Create a readiness promise to block early fetch calls until IPC is initialized
        const pywebviewPromise = new Promise(resolve => {
            if (window.pywebview) {
                _pywebviewReady = true;
                resolve();
            } else {
                window.addEventListener('pywebviewready', () => { 
                    _pywebviewReady = true; 
                    resolve(); 
                });
                // Fallback timeout for normal web browser mode
                setTimeout(() => resolve(), 2000);
            }
        });

        window.fetch = async function(url, options) {
            // Block until we know whether we're using IPC or HTTP
            await pywebviewPromise;
            
            // Only intercept our own API calls, not external URLs
            if (_pywebviewReady && window.pywebview && window.pywebview.api && typeof url === 'string' && url.startsWith('/api/')) {
                try {
                    let body = (options && options.body) ? options.body : "{}";
                    let method = (options && options.method) ? options.method : "GET";
                    const result = await window.pywebview.api.fetch_proxy(method, url, body);
                    const parsed = result;
                    return {
                        json: async () => JSON.parse(parsed),
                        text: async () => parsed,
                        ok: true,
                        status: 200
                    };
                } catch (e) {
                    console.error("PyWebView IPC fetch error:", e);
                    return { json: async () => ({success: false, error: String(e)}), text: async () => "", ok: false, status: 500 };
                }
            }
            return originalFetch.call(window, url, options);
        };
        // -------------------------------------------------
        
        // Toast notification system (replaces alert())
        function showToast(message, type = 'info', duration = 4000) {
            const container = document.getElementById('toastContainer');
            if (!container) { alert(message); return; }
            const el = document.createElement('div');
            el.className = 'toast toast-' + type;
            el.textContent = message;
            container.appendChild(el);
            setTimeout(() => {
                el.style.animation = 'toastOut 0.2s ease-in forwards';
                setTimeout(() => el.remove(), 200);
            }, duration);
        }

        // Icons are inline SVGs — no external library needed

        // APP STATE
        const state = {
            activeTab: 'PROCESS',
            activeBank: 'IDFC First Bank',
            idfc: {
                auditType: 'POA',
                outputMode: 'BOTH'
            },
            equitas: {
                stage: 'STAGE 1',
                outputFormat: 'BOTH'
            },
            selectedFiles: {
                'IDFC First Bank': [],
                'Equitas Small Finance Bank': [],
                'Arvog Bank': []
            },
            previewIndex: {
                'IDFC First Bank': -1,
                'Equitas Small Finance Bank': -1,
                'Arvog Bank': -1
            },
            isGenerating: false,
            logsCount: 0,
            genStartTime: null,
            totalBranches: 0,
            totalRows: 0
        };

        // DOM REFERENCES
        const bankSelector = document.getElementById('bankSelector');
        const idfcInputFile = document.getElementById('idfcInputFile');
        const idfcOutputDir = document.getElementById('idfcOutputDir');
        const eqInputFile = document.getElementById('eqInputFile');
        const eqOutputDir = document.getElementById('eqOutputDir');
        const arvogInputFile = document.getElementById('arvogInputFile');
        const arvogOutputDir = document.getElementById('arvogOutputDir');

        // HEARTBEAT self-termination loop (keeps server alive while window is open)
        setInterval(() => {
            fetch('/api/heartbeat')
                .catch(() => console.warn('Heartbeat server unreachable.'));
        }, 15000);

        // INITIALIZATION
        function handleHashRouting() {
            let hash = window.location.hash.replace('#', '').toUpperCase();
            const validTabs = ['PROCESS', 'STATS', 'HISTORY', 'SETTINGS'];
            if (!validTabs.includes(hash)) hash = 'PROCESS';
            
            if (state.activeTab !== hash) {
                switchTab(hash);
            }
        }

        window.addEventListener('hashchange', handleHashRouting);

        window.addEventListener('DOMContentLoaded', () => {
            // Load configs and history list
            loadDashboardData();
            // Start silent updater background check after 2 seconds
            setTimeout(checkUpdatesBackground, 2000);
            
            // Sync initial tab from URL hash
            handleHashRouting();
        });

        // BANK SELECTION CHANGE EVENT
        bankSelector.addEventListener('change', (e) => {
            const val = e.target.value;
            state.activeBank = val;
            
            // Save active bank to config
            saveConfig('bank', val);
            
            // Dynamic branding updates
            updateThemeBranding();
            
            // Render selection checklist for this newly active bank!
            renderSelectedFilesList();
            
            // Trigger preview highlight for this bank if there are success files
            const bankFiles = state.selectedFiles[val] || [];
            const successIdx = bankFiles.findIndex(f => f.status === "success");
            if (successIdx !== -1) {
                selectPreviewFile(successIdx);
            } else {
                // Clear active preview input values
                const prefix = getActivePrefix();
                const targetInput = document.getElementById(`${prefix}InputFile`);
                if (targetInput) targetInput.value = '';
                const gridContainer = document.getElementById(`${prefix}GridContainer`);
                if (gridContainer) gridContainer.classList.add('hidden');
            }
        });

        // OUTPUT DIRECTORY SYNC & PERSIST LISTENERS
        ['idfcOutputDir', 'eqOutputDir', 'arvogOutputDir'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', () => {
                    const val = el.value;
                    idfcOutputDir.value = val;
                    eqOutputDir.value = val;
                    arvogOutputDir.value = val;
                    saveConfig('out_path', val);
                });
            }
        });

        // AUTO-OPEN CHECKBOX SYNC & PERSIST LISTENERS
        ['idfcAutoOpen', 'eqAutoOpen', 'arvogAutoOpen', 'prefAutoOpen'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', () => {
                    const val = el.checked;
                    document.getElementById('idfcAutoOpen').checked = val;
                    document.getElementById('eqAutoOpen').checked = val;
                    document.getElementById('arvogAutoOpen').checked = val;
                    document.getElementById('prefAutoOpen').checked = val;
                    saveConfig('auto_open', String(val));
                });
            }
        });

        // EQUITAS PACKAGING MODE PERSIST LISTENER
        const eqPkgSel = document.getElementById('eqPackagingSelector');
        if (eqPkgSel) {
            eqPkgSel.addEventListener('change', () => {
                state.equitas.packagingMode = eqPkgSel.value;
                saveConfig('equitas_pack', eqPkgSel.value);
            });
        }

        function updateThemeBranding() {
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const isArvog = (state.activeBank === 'Arvog Bank');
            
            // 1. Update logo area text and icons
            const logoText1 = document.querySelector('.logo-text-primary');
            const logoText2 = document.querySelector('.logo-text-secondary');
            const logoIcon = document.querySelector('.logo-icon');
            const logoCopyright = document.querySelector('.copyright-label');

            if (isIDFC) {
                logoText1.textContent = 'IDFC FIRST';
                logoText2.textContent = 'AUDIT ENGINE';
                logoText2.className = 'text-[10px] font-extrabold tracking-widest text-blue-500 mt-1 logo-text-secondary';
                logoIcon.className = 'w-8 h-8 text-blue-500 logo-icon';
                logoCopyright.textContent = '© 2026 IDFC FIRST Bank';
            } else if (isArvog) {
                logoText1.textContent = 'ARVOG';
                logoText2.textContent = 'AUDIT ENGINE';
                logoText2.className = 'text-[10px] font-extrabold tracking-widest text-emerald-500 mt-1 logo-text-secondary';
                logoIcon.className = 'w-8 h-8 text-emerald-500 logo-icon';
                logoCopyright.textContent = '© 2026 Arvog Bank';
            } else {
                logoText1.textContent = 'EQUITAS';
                logoText2.textContent = 'AUDIT ENGINE';
                logoText2.className = 'text-[10px] font-extrabold tracking-widest text-amber-500 mt-1 logo-text-secondary';
                logoIcon.className = 'w-8 h-8 text-amber-500 logo-icon';
                logoCopyright.textContent = '© 2026 Equitas Small Finance Bank';
            }

            // 2. Adjust active sidebar navigation indicator border-color and icons
            const activeBtn = document.getElementById(`tabBtn-${state.activeTab}`);
            if (activeBtn) {
                let borderCol = 'border-amber-500';
                if (isIDFC) borderCol = 'border-blue-500';
                else if (isArvog) borderCol = 'border-emerald-500';
                activeBtn.className = `w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 ${borderCol} nav-btn`;
            }

            // 3. Inject CSS dynamically for classes marked as "dynamic-accent-*"
            let primaryColor = '#D97706';
            if (isIDFC) primaryColor = '#2563EB';
            else if (isArvog) primaryColor = '#10B981';

            // Apply style dynamically
            document.querySelectorAll('.dynamic-accent-bg').forEach(el => {
                el.style.backgroundColor = primaryColor;
            });
            document.querySelectorAll('.dynamic-accent-fg').forEach(el => {
                el.style.color = primaryColor;
            });
            document.querySelectorAll('.dynamic-accent-border').forEach(el => {
                el.style.borderColor = primaryColor;
            });

            // Toggle show workflow sections
            const idfcSection = document.getElementById('tab-PROCESS-IDFC');
            const arvogSection = document.getElementById('tab-PROCESS-ARVOG');
            const eqSection = document.getElementById('tab-PROCESS-EQUITAS');
            
            idfcSection.classList.add('hidden');
            arvogSection.classList.add('hidden');
            eqSection.classList.add('hidden');
            
            if (state.activeTab === 'PROCESS') {
                if (isIDFC) {
                    idfcSection.classList.remove('hidden');
                } else if (isArvog) {
                    arvogSection.classList.remove('hidden');
                } else {
                    eqSection.classList.remove('hidden');
                }
            }
        }

        // TAB SWITCHER STATE
        function switchTab(tabId) {
            state.activeTab = tabId;
            
            // Sync URL hash without triggering hashchange event loop
            const expectedHash = '#' + tabId.toLowerCase();
            if (window.location.hash !== expectedHash) {
                window.history.pushState(null, null, expectedHash);
            }
            
            // Update navigation button active styles
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.className = 'w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn';
            });
            
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const isArvog = (state.activeBank === 'Arvog Bank');
            const activeBtn = document.getElementById(`tabBtn-${tabId}`);
            if (activeBtn) {
                let borderCol = 'border-amber-500';
                if (isIDFC) borderCol = 'border-blue-500';
                else if (isArvog) borderCol = 'border-emerald-500';
                activeBtn.className = `w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 ${borderCol} nav-btn`;
            }

            // Hide all tab sections
            document.getElementById('tab-PROCESS-IDFC').classList.add('hidden');
            document.getElementById('tab-PROCESS-ARVOG').classList.add('hidden');
            document.getElementById('tab-PROCESS-EQUITAS').classList.add('hidden');
            document.getElementById('tab-STATS').classList.add('hidden');
            document.getElementById('tab-HISTORY').classList.add('hidden');
            document.getElementById('tab-SETTINGS').classList.add('hidden');

            // Show active section
            if (tabId === 'PROCESS') {
                if (isIDFC) {
                    document.getElementById('tab-PROCESS-IDFC').classList.remove('hidden');
                } else if (isArvog) {
                    document.getElementById('tab-PROCESS-ARVOG').classList.remove('hidden');
                } else {
                    document.getElementById('tab-PROCESS-EQUITAS').classList.remove('hidden');
                }
            } else {
                document.getElementById(`tab-${tabId}`).classList.remove('hidden');
            }

            if (tabId === 'STATS') refreshStats();
            if (tabId === 'HISTORY') refreshHistory();
            if (tabId === 'SETTINGS') refreshSettings();
        }

        // DYNAMIC WIDGET OPTION UPDATERS
        function setIdfcAuditType(type) {
            state.idfc.auditType = type;
            saveConfig('audit_type', type);
            
            const btnPOA = document.getElementById('idfcOpt-POA');
            const btnTAF = document.getElementById('idfcOpt-TAF');
            
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const colorClass = isIDFC ? 'bg-blue-500' : 'bg-amber-500';
            
            if (type === 'POA') {
                btnPOA.className = `flex-1 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
                btnTAF.className = 'flex-1 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition';
            } else {
                btnPOA.className = 'flex-1 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition';
                btnTAF.className = `flex-1 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
            }
            updateThemeBranding();
        }

        function setIdfcOutputMode(mode) {
            state.idfc.outputMode = mode;
            saveConfig('output_mode', mode);
            
            const btnFolder = document.getElementById('idfcMode-FOLDER');
            const btnZip = document.getElementById('idfcMode-ZIPONLY');
            const btnBoth = document.getElementById('idfcMode-BOTH');
            
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const colorClass = isIDFC ? 'bg-blue-500' : 'bg-amber-500';
            
            [btnFolder, btnZip, btnBoth].forEach(btn => {
                btn.className = 'px-5 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition';
            });
            
            if (mode === 'FOLDER') {
                btnFolder.className = `px-5 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
            } else if (mode === 'ZIP ONLY') {
                btnZip.className = `px-5 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
            } else {
                btnBoth.className = `px-5 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
            }
            updateThemeBranding();
        }

        function setEquitasStage(stage) {
            state.equitas.stage = stage;
            
            const btnS1 = document.getElementById('eqStage-S1');
            const btnS2 = document.getElementById('eqStage-S2');
            
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const colorClass = isIDFC ? 'bg-blue-500' : 'bg-amber-500';
            
            const configRow = document.getElementById('eqStage1Config');
            const fileLabel = document.getElementById('eqFileLabel');
            const stageTitle = document.getElementById('eqStageTitle');
            const btnRun = document.getElementById('eqBtnRun');
            
            if (stage === 'STAGE 1') {
                btnS1.className = `px-6 py-2 text-xs font-bold rounded-lg ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
                btnS2.className = 'px-6 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition';
                
                configRow.classList.remove('hidden');
                fileLabel.textContent = 'Source Excel (Normal + JSR sheets)';
                stageTitle.textContent = 'Stage 1: Generate Branch Audits & Excels';
                btnRun.textContent = 'Generate (Stage 1)';
            } else {
                btnS1.className = 'px-6 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition';
                btnS2.className = `px-6 py-2 text-xs font-bold rounded-lg ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
                
                configRow.classList.add('hidden');
                fileLabel.textContent = 'Select Consolidation Folder (containing generated stage 1 excels)';
                stageTitle.textContent = 'Stage 2: Consolidate Audit Worksheets & ZIP outputs';
                btnRun.textContent = 'Consolidate (Stage 2)';
            }
            updateThemeBranding();
        }

        function setEqFormat(fmt) {
            state.equitas.outputFormat = fmt;
            saveConfig('equitas_format', fmt);
            
            const btnPdf = document.getElementById('eqFormat-PDFONLY');
            const btnExcel = document.getElementById('eqFormat-EXCELONLY');
            const btnBoth = document.getElementById('eqFormat-BOTH');
            
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const colorClass = isIDFC ? 'bg-blue-500' : 'bg-amber-500';
            
            [btnPdf, btnExcel, btnBoth].forEach(btn => {
                btn.className = 'flex-1 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition';
            });
            
            if (fmt === 'PDF ONLY') {
                btnPdf.className = `flex-1 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
            } else if (fmt === 'EXCEL ONLY') {
                btnExcel.className = `flex-1 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
            } else {
                btnBoth.className = `flex-1 py-1.5 text-xs font-bold rounded-md ${colorClass} text-white shadow-sm transition dynamic-accent-bg`;
            }
            updateThemeBranding();
        }

        // CONFIG SAVE HELPER
        async function saveConfig(key, value) {
            try {
                await fetch('/api/config/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key, value })
                });
            } catch (err) {
                console.error('Failed to save config:', err);
            }
        }

        // LOAD DASHBOARD DATA (Initial load)
        async function loadDashboardData() {
            try {
                const resp = await fetch('/api/dashboard');
                const data = await resp.json();
                
                // Active bank
                if (data.bank) {
                    state.activeBank = data.bank;
                    bankSelector.value = data.bank;
                }
                
                // IDFC Preferences
                if (data.audit_type) setIdfcAuditType(data.audit_type);
                if (data.output_mode) setIdfcOutputMode(data.output_mode);
                if (data.auto_open !== undefined) {
                    document.getElementById('idfcAutoOpen').checked = data.auto_open;
                    document.getElementById('prefAutoOpen').checked = data.auto_open;
                    document.getElementById('arvogAutoOpen').checked = data.auto_open;
                }
                
                // Equitas Preferences
                if (data.equitas_format) setEqFormat(data.equitas_format);
                if (data.equitas_pack) {
                    document.getElementById('eqPackagingSelector').value = data.equitas_pack;
                    state.equitas.packagingMode = data.equitas_pack;
                }
                if (data.eq_auto_open !== undefined) {
                    document.getElementById('eqAutoOpen').checked = data.eq_auto_open;
                }
                
                // Set output path across all tabs
                if (data.out_path) {
                    idfcOutputDir.value = data.out_path;
                    eqOutputDir.value = data.out_path;
                    arvogOutputDir.value = data.out_path;
                }
                
                // Restore saved file checklists for each bank
                const checklistKeys = [
                    { key: 'selected_files_idfc', bank: 'IDFC First Bank' },
                    { key: 'selected_files_eq', bank: 'Equitas Small Finance Bank' },
                    { key: 'selected_files_arvog', bank: 'Arvog Bank' }
                ];
                let restoredAny = false;
                checklistKeys.forEach(item => {
                    try {
                        const raw = data[item.key];
                        if (raw) {
                            const paths = JSON.parse(raw);
                            if (Array.isArray(paths) && paths.length > 0) {
                                addSelectedFiles(paths, item.bank);
                                restoredAny = true;
                            }
                        }
                    } catch (parseErr) {
                        console.warn(`Failed to restore checklist for ${item.bank}:`, parseErr);
                    }
                });
                
                // Fallback: if no checklists were restored, use last_file for the active bank
                if (!restoredAny && data.last_file) {
                    addSelectedFiles([data.last_file]);
                }
                
                // Stats numbers
                document.getElementById('idfcStat-sessions').textContent = data.total_sessions || 0;
                document.getElementById('idfcStat-lastRun').textContent = data.last_run || 'No activity yet';
                document.getElementById('idfcStat-pdfs').textContent = data.total_pdfs || 0;
                
                // Load recent files cache
                renderRecentFiles(data.recent_files || []);
                
                // DB and Log path labels
                if (data.db_path) document.getElementById('dbPathLabel').textContent = data.db_path;
                if (data.log_path) document.getElementById('logPathLabel').textContent = data.log_path;
                if (data.naming_pattern) {
                    document.getElementById('settingsNamingPattern').value = data.naming_pattern;
                    updateNamingPreview();
                }

                updateThemeBranding();
                switchTab(state.activeTab);
            } catch (err) {
                console.error('Error loading dashboard:', err);
            }
        }

        // RENDER RECENT FILES
        function renderRecentFiles(files) {
            const idfcList = document.getElementById('idfcRecentList');
            const eqList = document.getElementById('eqRecentList');
            const arvogList = document.getElementById('arvogRecentList');
            
            if (!files || files.length === 0) {
                const empty = '<span class="text-slate-600 italic">None saved</span>';
                idfcList.innerHTML = empty;
                eqList.innerHTML = empty;
                if (arvogList) arvogList.innerHTML = empty;
                return;
            }
            
            let html = '';
            files.forEach(f => {
                const filename = f.split('/').pop().split('\\\\').pop();
                html += `<button onclick="selectRecentFile('${f.replace(/\\\\/g, '\\\\\\\\')}')" class="bg-slate-900 border border-brand-borderLine text-slate-400 hover:text-white hover:border-slate-500 rounded px-2.5 py-1 transition truncate max-w-[200px]" title="${f}">${filename}</button>`;
            });
            
            idfcList.innerHTML = html;
            eqList.innerHTML = html;
            if (arvogList) arvogList.innerHTML = html;
        }

        function selectRecentFile(path) {
            idfcInputFile.value = path;
            eqInputFile.value = path;
            if (arvogInputFile) arvogInputFile.value = path;
            saveConfig('last_file', path);
            
            addSelectedFiles([path]);
        }

        function renderPreviewGrid(prefix, headers, preview) {
            const container = document.getElementById(`${prefix}GridContainer`);
            const headerRow = document.getElementById(`${prefix}GridHeader`);
            const body = document.getElementById(`${prefix}GridBody`);
            
            if (!container || !headerRow || !body) return;
            
            if (!headers || headers.length === 0 || !preview || preview.length === 0) {
                container.classList.add('hidden');
                return;
            }
            
            // Build headers
            let hHtml = '';
            headers.forEach(h => {
                hHtml += `<th class="py-2.5 px-4 border-b border-brand-borderLine">${h}</th>`;
            });
            headerRow.innerHTML = hHtml;
            
            // Build preview rows
            let rHtml = '';
            preview.forEach(row => {
                rHtml += `<tr class="hover:bg-slate-900/30 transition border-b border-brand-borderLine">`;
                row.forEach(val => {
                    rHtml += `<td class="py-2.5 px-4 font-mono">${val}</td>`;
                });
                rHtml += `</tr>`;
            });
            body.innerHTML = rHtml;
            
            container.classList.remove('hidden');
        }
        
        function togglePreviewGrid(prefix) {
            const wrapper = document.getElementById(`${prefix}GridWrapper`);
            const icon = document.getElementById(`${prefix}GridIcon`);
            
            if (wrapper.classList.contains('hidden')) {
                wrapper.classList.remove('hidden');
                icon.style.transform = 'rotate(90deg)';
            } else {
                wrapper.classList.add('hidden');
                icon.style.transform = 'rotate(0deg)';
            }
        }

        function populateMapperDropdowns(prefix, headers) {
            const container = document.getElementById(`${prefix}MapperContainer`);
            if (!container) return;
            if (!headers || headers.length === 0) {
                container.classList.add('hidden');
                return;
            }
            
            let fields = [];
            if (prefix === 'idfc') {
                fields = [
                    { id: 'idfcMap-prospect', defaultFingerprints: ['prospectno', 'prospect_no', 'prospect number', 'prospect_number'] },
                    { id: 'idfcMap-cuid', defaultFingerprints: ['cuid', 'customerid', 'customer_id', 'customer id'] },
                    { id: 'idfcMap-tare', defaultFingerprints: ['tare weight', 'tareweight', 'tare_weight', 'tare_wt'] },
                    { id: 'idfcMap-branch', defaultFingerprints: ['currentbranch', 'current_branch', 'branchname', 'branch_name', 'branch name'] }
                ];
            } else {
                fields = [
                    { id: 'eqMap-svs', defaultFingerprints: ['svs_loan_no', 'svs loanno', 'svs_loan', 'svs loan'] },
                    { id: 'eqMap-sole', defaultFingerprints: ['sole_id', 'soleid', 'branch_code', 'branch code', 'sole id'] },
                    { id: 'eqMap-branch', defaultFingerprints: ['branch_name', 'branchname', 'branch name', 'branch'] },
                    { id: 'eqMap-loan', defaultFingerprints: ['loan no', 'loanno', 'loan_no', 'loan number'] }
                ];
            }
            
            fields.forEach(field => {
                const select = document.getElementById(field.id);
                if (!select) return;
                
                select.innerHTML = '';
                
                let selectedIdx = 0;
                headers.forEach((h, idx) => {
                    const option = document.createElement('option');
                    option.value = h;
                    option.textContent = h;
                    select.appendChild(option);
                    
                    const lowerH = h.toLowerCase().trim();
                    field.defaultFingerprints.forEach(fingerprint => {
                        if (lowerH.includes(fingerprint) || fingerprint.includes(lowerH)) {
                            selectedIdx = idx;
                        }
                    });
                });
                
                select.selectedIndex = selectedIdx;
            });
            
            container.classList.remove('hidden');
        }

        // PREVIEW & VALIDATION OF EXCEL PEAK
        async function validateFile(filepath) {
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const isArvog = (state.activeBank === 'Arvog Bank');
            
            let validationBox, previewBox, previewText;
            if (isIDFC) {
                validationBox = document.getElementById('idfcValidationBox');
                previewBox = document.getElementById('idfcPreviewBox');
                previewText = document.getElementById('idfcPreviewText');
            } else if (isArvog) {
                validationBox = document.getElementById('arvogValidationBox');
                previewBox = document.getElementById('arvogPreviewBox');
                previewText = document.getElementById('arvogPreviewText');
            } else {
                validationBox = document.getElementById('eqValidationBox');
                previewBox = document.getElementById('eqPreviewBox');
                previewText = document.getElementById('eqPreviewText');
            }
            
            try {
                const resp = await fetch('/api/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        filepath,
                        expected_stage: isIDFC ? null : state.equitas.stage
                    })
                });
                const data = await resp.json();
                
                if (data.success) {
                    // Update active bank if file auto-detects another bank!
                    if (data.detected_bank && data.detected_bank !== state.activeBank) {
                        state.activeBank = data.detected_bank;
                        bankSelector.value = data.detected_bank;
                        saveConfig('bank', data.detected_bank);
                        updateThemeBranding();
                        
                        addSelectedFiles([filepath]);
                        return;
                    }

                    if (validationBox) validationBox.classList.add('hidden');
                    if (previewBox) {
                        previewBox.classList.remove('hidden');
                        previewBox.className = "bg-emerald-950/20 border border-emerald-900/30 rounded-lg px-4 py-3 flex items-center space-x-2 text-emerald-400 text-xs";
                    }
                    if (previewText) {
                        previewText.innerHTML = `<strong>✓ Excel Loaded:</strong> Found ${data.rows || 0} rows, representing ${data.branches || 0} branches to audit.`;
                    }
                    
                    state.totalBranches = parseInt(data.branches) || 0;
                    state.totalRows = parseInt(data.rows) || 0;
                    
                    const prefix = isIDFC ? 'idfc' : (isArvog ? 'arvog' : 'eq');
                    renderPreviewGrid(prefix, data.headers, data.preview);
                    populateMapperDropdowns(prefix, data.headers);
                } else {
                    if (previewBox) previewBox.classList.add('hidden');
                    if (validationBox) {
                        validationBox.classList.remove('hidden');
                        validationBox.className = "bg-rose-950/20 border border-rose-900/30 rounded-lg px-4 py-3 text-rose-400 text-xs";
                        validationBox.innerHTML = `<strong>✗ Load Error:</strong> ${data.error || 'Invalid spreadsheet file format.'}`;
                    }
                    
                    const prefix = isIDFC ? 'idfc' : (isArvog ? 'arvog' : 'eq');
                    if (data.headers && data.headers.length > 0 && data.preview && data.preview.length > 0) {
                        renderPreviewGrid(prefix, data.headers, data.preview);
                        populateMapperDropdowns(prefix, data.headers);
                    } else {
                        const gridContainer = document.getElementById(`${prefix}GridContainer`);
                        if (gridContainer) gridContainer.classList.add('hidden');
                        const mapperContainer = document.getElementById(`${prefix}MapperContainer`);
                        if (mapperContainer) mapperContainer.classList.add('hidden');
                    }
                }
            } catch (err) {
                console.error('File validation request failed:', err);
            }
        }

        // DRAG & DROP AND BULK UPLOAD HANDLERS (UNIFIED FOR ALL BANKS)
        function getActivePrefix() {
            if (state.activeBank === 'IDFC First Bank') return 'idfc';
            if (state.activeBank === 'Equitas Small Finance Bank') return 'eq';
            return 'arvog';
        }

        function handleDragOver(e) {
            e.preventDefault();
            e.stopPropagation();
            const prefix = getActivePrefix();
            const zone = document.getElementById(`${prefix}DropZone`);
            if (zone) zone.classList.add('dragover');
        }

        function handleDragLeave(e) {
            e.preventDefault();
            e.stopPropagation();
            const prefix = getActivePrefix();
            const zone = document.getElementById(`${prefix}DropZone`);
            if (zone) zone.classList.remove('dragover');
        }

        function handleDrop(e) {
            e.preventDefault();
            e.stopPropagation();
            const prefix = getActivePrefix();
            const zone = document.getElementById(`${prefix}DropZone`);
            if (zone) zone.classList.remove('dragover');

            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files && files.length > 0) {
                const paths = [];
                for (let i = 0; i < files.length; i++) {
                    const f = files[i];
                    if (f.path) {
                        paths.push(f.path);
                    } else {
                        console.warn("Browser environment hidden path for file:", f.name);
                    }
                }
                
                if (paths.length > 0) {
                    addSelectedFiles(paths);
                } else {
                    showToast("Due to sandbox restrictions, please click the drop zone directly to browse and select local files using the native file picker.", "warning");
                }
            }
        }

        function triggerBrowseMultipleFiles() {
            browseMultipleFiles();
        }

        async function browseMultipleFiles() {
            try {
                const resp = await fetch('/api/browse/files');
                const data = await resp.json();
                if (data.paths && data.paths.length > 0) {
                    addSelectedFiles(data.paths);
                }
            } catch (err) {
                console.error('Browse multiple files failed, falling back to hidden HTML file input:', err);
                const prefix = getActivePrefix();
                const hiddenInput = document.getElementById(`${prefix}FileInputHidden`);
                if (hiddenInput) hiddenInput.click();
            }
        }

        function handleNativeFileSelect(e) {
            const files = e.target.files;
            if (files && files.length > 0) {
                const paths = [];
                for (let i = 0; i < files.length; i++) {
                    if (files[i].path) {
                        paths.push(files[i].path);
                    } else {
                        console.warn("Selected virtual file path:", files[i].name);
                    }
                }
                if (paths.length > 0) {
                    addSelectedFiles(paths);
                }
            }
        }

        function addSelectedFiles(paths, targetBank = null) {
            const bank = targetBank || state.activeBank;
            if (!state.selectedFiles[bank]) {
                state.selectedFiles[bank] = [];
            }
            
            paths.forEach(p => {
                const pathStr = String(p).trim();
                if (!pathStr) return;
                
                if (state.selectedFiles[bank].some(f => f.path === pathStr)) return;
                
                const name = pathStr.split(String.fromCharCode(47)).pop().split(String.fromCharCode(92)).pop();
                const fileObj = {
                    path: pathStr,
                    name: name,
                    size: "Calculating...",
                    isValid: null,
                    error: "",
                    rows: 0,
                    branches: 0,
                    headers: [],
                    preview: [],
                    status: "loading"
                };
                
                state.selectedFiles[bank].push(fileObj);
            });
            
            if (bank === state.activeBank) {
                renderSelectedFilesList();
            }
            
            state.selectedFiles[bank].forEach((fileObj, idx) => {
                if (fileObj.status === "loading") {
                    validateIndividualFile(idx, bank);
                }
            });

            // Save checklists to SQLite configs persistently
            const cleanPaths = state.selectedFiles[bank].map(f => f.path);
            saveConfig(`selected_files_${bank}`, JSON.stringify(cleanPaths));
        }

        async function validateIndividualFile(index, targetBank = null) {
            const bank = targetBank || state.activeBank;
            const fileObj = state.selectedFiles[bank][index];
            if (!fileObj) return;
            
            try {
                const isIDFC = (bank === 'IDFC First Bank');
                const isEq = (bank === 'Equitas Small Finance Bank');
                
                const resp = await fetch('/api/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        filepath: fileObj.path,
                        expected_stage: isEq ? state.equitas.stage : null
                    })
                });
                const data = await resp.json();
                
                if (data.success) {
                    fileObj.status = "success";
                    fileObj.isValid = true;
                    fileObj.rows = parseInt(data.rows) || 0;
                    fileObj.branches = parseInt(data.branches) || 0;
                    fileObj.headers = data.headers || [];
                    fileObj.preview = data.preview || [];
                    fileObj.size = isIDFC ? `${(data.rows || 0)} rows, ${data.branches || 0} branches` : `${data.rows || 0} rows`;
                    
                    if (state.previewIndex[bank] === -1 && bank === state.activeBank) {
                        selectPreviewFile(index);
                    }
                } else {
                    fileObj.status = "error";
                    fileObj.isValid = false;
                    fileObj.error = data.error || "Validation failed";
                    fileObj.size = "Failed to load";
                }
            } catch (err) {
                fileObj.status = "error";
                fileObj.isValid = false;
                fileObj.error = String(err);
                fileObj.size = "Connection error";
            }
            
            if (bank === state.activeBank) {
                renderSelectedFilesList();
            }
        }

        function removeSelectedFile(index, event) {
            if (event) event.stopPropagation();
            const bank = state.activeBank;
            const prefix = getActivePrefix();
            
            state.selectedFiles[bank].splice(index, 1);
            
            if (state.previewIndex[bank] === index) {
                state.previewIndex[bank] = -1;
                const firstSuccessIdx = state.selectedFiles[bank].findIndex(f => f.status === "success");
                if (firstSuccessIdx !== -1) {
                    selectPreviewFile(firstSuccessIdx);
                } else {
                    const gridContainer = document.getElementById(`${prefix}GridContainer`);
                    if (gridContainer) gridContainer.classList.add('hidden');
                }
            } else if (state.previewIndex[bank] > index) {
                state.previewIndex[bank]--;
            }
            
            renderSelectedFilesList();

            // Save checklists to SQLite configs persistently
            const cleanPaths = state.selectedFiles[bank].map(f => f.path);
            saveConfig(`selected_files_${bank}`, JSON.stringify(cleanPaths));
        }

        function clearAllSelectedFiles() {
            const bank = state.activeBank;
            const prefix = getActivePrefix();
            
            state.selectedFiles[bank] = [];
            state.previewIndex[bank] = -1;
            
            const gridContainer = document.getElementById(`${prefix}GridContainer`);
            if (gridContainer) gridContainer.classList.add('hidden');
            
            renderSelectedFilesList();

            // Save checklists to SQLite configs persistently (empty list)
            saveConfig(`selected_files_${bank}`, JSON.stringify([]));
        }

        function selectPreviewFile(index) {
            const bank = state.activeBank;
            const prefix = getActivePrefix();
            const fileObj = state.selectedFiles[bank][index];
            if (!fileObj || fileObj.status !== "success") return;
            
            state.previewIndex[bank] = index;
            
            renderPreviewGrid(prefix, fileObj.headers, fileObj.preview);
            populateMapperDropdowns(prefix, fileObj.headers);
            
            const targetInput = document.getElementById(`${prefix}InputFile`);
            if (targetInput) targetInput.value = fileObj.path;
            
            renderSelectedFilesList();
        }

        function renderSelectedFilesList() {
            const bank = state.activeBank;
            const prefix = getActivePrefix();
            
            const container = document.getElementById(`${prefix}SelectedFilesContainer`);
            const list = document.getElementById(`${prefix}SelectedFilesList`);
            const countLabel = document.getElementById(`${prefix}SelectedCount`);
            
            if (!container || !list || !countLabel) return;
            
            const files = state.selectedFiles[bank] || [];
            const totalFiles = files.length;
            countLabel.textContent = totalFiles;
            
            if (totalFiles === 0) {
                container.classList.add('hidden');
                return;
            }
            
            container.classList.remove('hidden');
            
            let accentColorClass = "text-emerald-400";
            if (prefix === 'idfc') accentColorClass = "text-blue-400";
            else if (prefix === 'eq') accentColorClass = "text-amber-400";
            
            let html = "";
            files.forEach((file, idx) => {
                const isActive = (state.previewIndex[bank] === idx);
                const activeClass = isActive ? "active-preview" : "";
                
                let iconHtml = "";
                let statusHtml = "";
                let clickAction = "";
                let cursorStyle = "";
                
                if (file.status === "loading") {
                    iconHtml = `
                        <svg class="icon w-4 h-4 ${accentColorClass} emerald-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="12" y1="2" x2="12" y2="6"/>
                            <line x1="12" y1="18" x2="12" y2="22"/>
                            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/>
                            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>
                            <line x1="2" y1="12" x2="6" y2="12"/>
                            <line x1="18" y1="12" x2="22" y2="12"/>
                            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/>
                            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
                        </svg>`;
                    statusHtml = `<span class="text-[10px] text-slate-500 italic">Verifying spreadsheet schema...</span>`;
                } else if (file.status === "success") {
                    iconHtml = `
                        <svg class="icon w-4 h-4 ${accentColorClass}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                            <polyline points="10 9 9 9 8 9"/>
                        </svg>`;
                    statusHtml = `<span class="text-[10px] ${accentColorClass} font-semibold">✓ ${file.size}</span>`;
                    clickAction = `onclick="selectPreviewFile(${idx})"`;
                    cursorStyle = "cursor-pointer";
                } else {
                    iconHtml = `
                        <svg class="icon w-4 h-4 text-rose-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="12" y1="8" x2="12" y2="12"/>
                            <line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>`;
                    statusHtml = `<span class="text-[10px] text-rose-400 font-semibold" title="${file.error.replace(/"/g, '&quot;')}">✗ Load Error: ${file.error.substring(0, 50)}${file.error.length > 50 ? '...' : ''}</span>`;
                }
                
                html += `
                <div class="arvog-file-tile ${activeClass} ${cursorStyle} flex items-center justify-between space-x-3" ${clickAction}>
                    <div class="flex items-center space-x-3 min-w-0 flex-1">
                        ${iconHtml}
                        <div class="min-w-0 flex-1">
                            <span class="block text-xs font-bold text-slate-200 truncate" title="${file.path}">${file.name}</span>
                            ${statusHtml}
                        </div>
                    </div>
                    <button onclick="removeSelectedFile(${idx}, event)" class="bg-transparent border-0 text-slate-500 hover:text-rose-400 p-1 cursor-pointer transition" title="Remove file">
                        <svg class="icon w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>`;
            });
            
            list.innerHTML = html;
        }

        // HEADLESS BROWSE DIALOG TRIGGERS
        async function browseFile(fieldId) {
            try {
                const resp = await fetch('/api/browse/file');
                const data = await resp.json();
                if (data.path) {
                    document.getElementById(fieldId).value = data.path;
                    // Sync other view just in case
                    idfcInputFile.value = data.path;
                    eqInputFile.value = data.path;
                    if (arvogInputFile) arvogInputFile.value = data.path;
                    
                    saveConfig('last_file', data.path);
                    validateFile(data.path);
                }
            } catch (err) {
                console.error('Browse file trigger failed:', err);
            }
        }

        async function browseFolder(fieldId) {
            try {
                const resp = await fetch('/api/browse/folder');
                const data = await resp.json();
                if (data.path) {
                    document.getElementById(fieldId).value = data.path;
                    // Sync both inputs
                    idfcOutputDir.value = data.path;
                    eqOutputDir.value = data.path;
                    if (arvogOutputDir) arvogOutputDir.value = data.path;
                    
                    saveConfig('out_path', data.path);
                }
            } catch (err) {
                console.error('Browse directory trigger failed:', err);
            }
        }

        // GENERATION POLLING ENGINE
        let progressInterval = null;

        async function startGeneration() {
            if (state.isGenerating) return;
            
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const isArvog = (state.activeBank === 'Arvog Bank');
            
            const prefix = getActivePrefix();
            
            // Unified file extraction from selected files checklist for ALL banks
            const validFiles = (state.selectedFiles[state.activeBank] || []).filter(f => f.status === "success");
            if (validFiles.length === 0) {
                showToast('Please select and load at least one valid Excel master file first.', 'warning');
                return;
            }
            
            let file;
            if (validFiles.length === 1) {
                file = validFiles[0].path;
            } else {
                file = validFiles.map(f => f.path);
            }
            
            const output = document.getElementById(`${prefix}OutputDir`).value;
            
            if (!output) {
                showToast('Please select an output directory.', 'warning');
                return;
            }
            
            state.isGenerating = true;
            state.genStartTime = Date.now();
            
            // UI Toggle to busy
            setUiGeneratingState(true);
            
            // Console clearing and focus
            const consoleBox = document.getElementById(`${prefix}Console`);
            consoleBox.innerHTML = '<div class="text-slate-500">[00:00:00] Initializing generation background worker thread...</div>';
            state.logsCount = 0;
            
            // Gather custom column mappings
            let columnMappings = null;
            if (isIDFC) {
                columnMappings = {
                    prospect: document.getElementById('idfcMap-prospect').value,
                    cuid: document.getElementById('idfcMap-cuid').value,
                    tare: document.getElementById('idfcMap-tare').value,
                    branch: document.getElementById('idfcMap-branch').value
                };
            } else if (!isArvog) {
                columnMappings = {
                    svs: document.getElementById('eqMap-svs').value,
                    sole: document.getElementById('eqMap-sole').value,
                    branch: document.getElementById('eqMap-branch').value,
                    loan: document.getElementById('eqMap-loan').value
                };
            }
            
            const autoOpenChecked = document.getElementById(`${prefix}AutoOpen`).checked;
            
            // Gather run parameters
            const payload = {
                bank: state.activeBank,
                filepath: file,
                out_path: output,
                auto_open: autoOpenChecked,
                naming_pattern: document.getElementById('settingsNamingPattern').value || '{branch}_{type}',
                column_mappings: columnMappings,
                
                // IDFC specific
                audit_type: state.idfc.auditType,
                output_mode: state.idfc.outputMode,
                
                // Equitas specific
                equitas_stage: state.equitas.stage,
                equitas_format: state.equitas.outputFormat,
                equitas_pack: document.getElementById('eqPackagingSelector') ? document.getElementById('eqPackagingSelector').value : 'FOLDER'
            };
            
            try {
                const resp = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await resp.json();
                
                if (!data.success) {
                    showToast('Failed to start generation: ' + data.error, 'error');
                    state.isGenerating = false;
                    setUiGeneratingState(false);
                    return;
                }
                
                // Start polling logs and percentage bar
                progressInterval = setInterval(pollProgress, 1500);
            } catch (err) {
                console.error('Failed to spawn generation:', err);
                state.isGenerating = false;
                setUiGeneratingState(false);
            }
        }

        async function cancelGeneration() {
            try {
                const resp = await fetch('/api/cancel');
                const data = await resp.json();
                if (data.success) {
                    appendConsoleLog('WARN', 'Generation Cancel request submitted by user! Gracefully winding down...');
                }
            } catch (err) {
                console.error('Cancel request failed:', err);
            }
        }

        // POLL PROGRESS
        async function pollProgress() {
            try {
                const resp = await fetch('/api/progress');
                const data = await resp.json();
                
                const isIDFC = (state.activeBank === 'IDFC First Bank');
                const isArvog = (state.activeBank === 'Arvog Bank');
                const prefix = isIDFC ? 'idfc' : (isArvog ? 'arvog' : 'eq');
                
                const pct = Math.round(data.pct || 0);
                const branchText = data.active_branch || 'Processing spreadsheet records...';
                
                // Animate circular SVG progress rings
                const circ = 2 * Math.PI * 34; // ~213.6
                const offset = circ - (circ * pct / 100);
                
                document.getElementById(`${prefix}ProgressPct`).textContent = `${pct}%`;
                document.getElementById(`${prefix}ProgressBranch`).textContent = branchText;
                
                const ring = document.getElementById(`${prefix}ProgressRing`);
                if (ring) {
                    ring.style.strokeDashoffset = offset;
                }
                
                // Scan logs for speed/ETA calculation
                let total = state.totalBranches || 0;
                let completed = 0;
                
                if (data.logs) {
                    data.logs.forEach(log => {
                        const msg = log.message;
                        if (msg.includes('branches. Starting generation')) {
                            const match = msg.match(/Found (\\d+) branches/);
                            if (match) {
                                total = parseInt(match[1]);
                            }
                        }
                        if (msg.includes('Building:')) {
                            completed++;
                        }
                    });
                }
                
                if (total === 0 && isIDFC) {
                    total = state.totalBranches || 1;
                }
                
                const elapsedSeconds = (Date.now() - state.genStartTime) / 1000;
                let speedText = 'Speed: Calculating...';
                let etaText = 'ETA: Calculating...';
                
                if (completed > 0 && elapsedSeconds > 0) {
                    const speedVal = completed / elapsedSeconds;
                    speedText = `Speed: ${speedVal.toFixed(1)} PDFs/sec`;
                    
                    if (total > completed) {
                        const remaining = total - completed;
                        const etaSeconds = remaining / speedVal;
                        const m = Math.floor(etaSeconds / 60);
                        const s = Math.floor(etaSeconds % 60);
                        etaText = m > 0 ? `ETA: ${m}m ${s}s` : `ETA: ${s}s`;
                    } else {
                        etaText = 'ETA: Done';
                    }
                }
                
                const speedElem = document.getElementById(`${prefix}ProgressSpeed`);
                const etaElem = document.getElementById(`${prefix}ProgressEta`);
                if (speedElem) speedElem.textContent = speedText;
                if (etaElem) etaElem.textContent = etaText;
                
                // Swap checklist badge icons dynamically
                const iconRead = document.getElementById(`${prefix}StatusIcon-read`);
                const iconPdf = document.getElementById(`${prefix}StatusIcon-pdf`);
                const iconZip = document.getElementById(`${prefix}StatusIcon-zip`);
                
                if (pct === 0) {
                    if (iconRead) iconRead.innerHTML = ICON_SPIN;
                    if (iconPdf) iconPdf.innerHTML = ICON_CIRCLE;
                    if (iconZip) iconZip.innerHTML = ICON_CIRCLE;
                } else if (pct > 0 && pct < 90) {
                    if (iconRead) iconRead.innerHTML = ICON_CHECK;
                    if (iconPdf) iconPdf.innerHTML = ICON_SPIN;
                    if (iconZip) iconZip.innerHTML = ICON_CIRCLE;
                } else if (pct >= 90 && pct < 100) {
                    if (iconRead) iconRead.innerHTML = ICON_CHECK;
                    if (iconPdf) iconPdf.innerHTML = ICON_CHECK;
                    if (iconZip) iconZip.innerHTML = ICON_SPIN;
                } else if (pct === 100) {
                    if (iconRead) iconRead.innerHTML = ICON_CHECK;
                    if (iconPdf) iconPdf.innerHTML = ICON_CHECK;
                    if (iconZip) iconZip.innerHTML = ICON_CHECK;
                }
                
                // Render console logs
                if (data.logs && data.logs.length > state.logsCount) {
                    const newLogs = data.logs.slice(state.logsCount);
                    newLogs.forEach(log => {
                        appendConsoleLog(log.level, log.message, log.timestamp);
                    });
                    state.logsCount = data.logs.length;
                }
                
                // Handle completed state
                if (!data.is_running) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                    state.isGenerating = false;
                    setUiGeneratingState(false);
                    
                    if (data.summary) {
                        openSummaryModal(data.summary);
                    }
                    
                    loadDashboardData();
                }
            } catch (err) {
                console.error('Progress polling query failed:', err);
            }
        }

        function appendConsoleLog(level, message, timestamp) {
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const isArvog = (state.activeBank === 'Arvog Bank');
            let consoleBox;
            if (isIDFC) {
                consoleBox = document.getElementById('idfcConsole');
            } else if (isArvog) {
                consoleBox = document.getElementById('arvogConsole');
            } else {
                consoleBox = document.getElementById('eqConsole');
            }
            
            const time = timestamp || new Date().toTimeString().split(' ')[0];
            
            let color = 'text-sky-400';
            if (level === 'OK') color = 'text-emerald-400';
            if (level === 'WARN') color = 'text-amber-500 font-semibold';
            if (level === 'ERROR') color = 'text-rose-500 font-bold';
            if (level === 'DEBUG') color = 'text-slate-500';
            
            const row = `<div class="font-mono text-[11px]"><span class="text-slate-600">[${time}]</span> <span class="${color}">[${level}]</span> <span class="text-slate-200">${message}</span></div>`;
            consoleBox.insertAdjacentHTML('beforeend', row);
            consoleBox.scrollTop = consoleBox.scrollHeight;
        }

        function setUiGeneratingState(busy) {
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const isArvog = (state.activeBank === 'Arvog Bank');
            
            const idfcBtnRun = document.getElementById('idfcBtnRun');
            const idfcBtnCancel = document.getElementById('idfcBtnCancel');
            const idfcProgressContainer = document.getElementById('idfcProgressContainer');
            
            const arvogBtnRun = document.getElementById('arvogBtnRun');
            const arvogBtnCancel = document.getElementById('arvogBtnCancel');
            const arvogProgressContainer = document.getElementById('arvogProgressContainer');
            
            const eqBtnRun = document.getElementById('eqBtnRun');
            const eqBtnCancel = document.getElementById('eqBtnCancel');
            const eqProgressContainer = document.getElementById('eqProgressContainer');
            
            const footerStatus = document.getElementById('footerStatusText');
            
            if (busy) {
                idfcBtnRun.textContent = 'Generating... Please wait';
                idfcBtnRun.disabled = true;
                idfcBtnCancel.disabled = false;
                idfcProgressContainer.classList.remove('hidden');
                
                arvogBtnRun.textContent = 'Generating... Please wait';
                arvogBtnRun.disabled = true;
                arvogBtnCancel.disabled = false;
                arvogProgressContainer.classList.remove('hidden');
                
                eqBtnRun.textContent = 'Processing Stage...';
                eqBtnRun.disabled = true;
                eqBtnCancel.disabled = false;
                eqProgressContainer.classList.remove('hidden');
                
                footerStatus.textContent = 'STATUS: Active Report Generation Thread Running';
                footerStatus.className = 'text-[10px] font-bold text-amber-500 uppercase tracking-wider animate-pulse';
            } else {
                idfcBtnRun.textContent = 'Generate Reports';
                idfcBtnRun.disabled = false;
                idfcBtnCancel.disabled = true;
                
                arvogBtnRun.textContent = 'Generate Reports';
                arvogBtnRun.disabled = false;
                arvogBtnCancel.disabled = true;
                
                const stageText = (state.equitas.stage === 'STAGE 1') ? 'Generate (Stage 1)' : 'Consolidate (Stage 2)';
                eqBtnRun.textContent = stageText;
                eqBtnRun.disabled = false;
                eqBtnCancel.disabled = true;
                
                footerStatus.textContent = 'STATUS: Headless Worker Pool Idle';
                footerStatus.className = 'text-[10px] font-bold text-slate-500 uppercase tracking-wider';
            }
        }

        // MODAL SUMMARY DIALOG POPUPS
        function openSummaryModal(summaryData) {
            const modal = document.getElementById('summaryModal');
            const contentBox = document.getElementById('summaryTextContent');
            const title = document.getElementById('summaryTitle');
            
            title.textContent = summaryData.title || 'Generation Completed';
            
            let html = '';
            if (summaryData.items && summaryData.items.length > 0) {
                summaryData.items.forEach(item => {
                    html += `<div class="py-1 border-b border-brand-borderLine flex justify-between"><span class="text-slate-400">${item.label}</span><strong class="text-emerald-400 font-mono">${item.value}</strong></div>`;
                });
            } else {
                html = `<div class="text-slate-400 italic">${summaryData.message || 'Workflow finished successfully.'}</div>`;
            }
            
            contentBox.innerHTML = html;
            modal.classList.remove('hidden');
        }

        function closeSummaryModal() {
            document.getElementById('summaryModal').classList.add('hidden');
        }

        // DYNAMIC SVG ANCHORS AND CHARTS RENDERING ENGINES
        const ICON_CIRCLE = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3 h-3 text-slate-600"><circle cx="12" cy="12" r="10"></circle></svg>`;
        const ICON_CHECK = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="w-3 h-3 text-emerald-400"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
        const ICON_SPIN = `<svg class="animate-spin w-3 h-3 text-sky-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`;

        function drawDonutChart(dataDict) {
            const svg = document.getElementById('statsDonutSvg');
            const list = document.getElementById('statsDistribution');
            const centerPct = document.getElementById('statsDonutCenterPct');
            
            if (!svg || !list || !centerPct) return;
            
            if (!dataDict || Object.keys(dataDict).length === 0) {
                svg.innerHTML = `<circle cx="50" cy="50" r="30" fill="none" stroke="#1E293B" stroke-width="12" />`;
                list.innerHTML = `<div class="text-xs text-slate-500 italic">No runs recorded yet.</div>`;
                centerPct.textContent = '0%';
                return;
            }
            
            const colors = ['#3B82F6', '#F59E0B', '#10B981', '#6366F1', '#EC4899', '#8B5CF6'];
            const total = Object.values(dataDict).reduce((a, b) => a + b, 0);
            
            let htmlSvg = '';
            let htmlList = '';
            let accumPercent = 0;
            const circ = 2 * Math.PI * 30; // ~188.495
            
            let idx = 0;
            Object.entries(dataDict).forEach(([name, val]) => {
                const pct = (val / total) * 100;
                const strokeOffset = circ - (circ * pct / 100);
                const rotationOffset = (accumPercent / 100) * 360 - 90; // Start at top
                const color = colors[idx % colors.length];
                
                htmlSvg += `
                    <circle cx="50" cy="50" r="30" fill="none" stroke="${color}" stroke-width="12" 
                            stroke-dasharray="${circ}" stroke-dashoffset="${strokeOffset}" 
                            transform="rotate(${rotationOffset} 50 50)" class="transition-all duration-500" />`;
                
                htmlList += `
                    <div class="flex justify-between items-center text-xs font-semibold text-slate-300">
                        <div class="flex items-center space-x-2">
                            <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${color}"></span>
                            <span>${name}</span>
                        </div>
                        <span>${val} (${pct.toFixed(0)}%)</span>
                    </div>`;
                
                accumPercent += pct;
                idx++;
            });
            
            svg.innerHTML = htmlSvg;
            list.innerHTML = htmlList;
            centerPct.textContent = `100%`;
        }

        function drawLineChart(trendData) {
            const svg = document.getElementById('statsLineSvg');
            const labelRow = document.getElementById('statsActivity');
            
            if (!svg || !labelRow) return;
            
            if (!trendData || trendData.length === 0) {
                svg.innerHTML = `
                    <line x1="30" y1="100" x2="270" y2="100" stroke="#1E293B" stroke-width="1" />
                    <text x="150" y="60" fill="#64748B" font-size="10" text-anchor="middle" font-family="sans-serif">No activity recorded</text>`;
                labelRow.innerHTML = '<div class="col-span-7 italic text-slate-500 text-center py-4">No recent history</div>';
                return;
            }
            
            const reversed = [...trendData].reverse();
            const maxVal = Math.max(...reversed.map(r => r[1]), 1);
            
            const width = 300;
            const height = 120;
            const paddingX = 35;
            const paddingY = 20;
            const chartWidth = width - 2 * paddingX;
            const chartHeight = height - 2 * paddingY;
            
            const points = [];
            const stepX = chartWidth / Math.max(reversed.length - 1, 1);
            
            reversed.forEach((row, i) => {
                const x = paddingX + i * stepX;
                const val = row[1];
                const y = paddingY + chartHeight - (val / maxVal) * chartHeight;
                points.push({ x, y, date: row[0], val });
            });
            
            let htmlGrid = `
                <line x1="${paddingX}" y1="${paddingY}" x2="${width - paddingX}" y2="${paddingY}" stroke="#1E293B" stroke-width="0.5" stroke-dasharray="2,2" />
                <line x1="${paddingX}" y1="${paddingY + chartHeight/2}" x2="${width - paddingX}" y2="${paddingY + chartHeight/2}" stroke="#1E293B" stroke-width="0.5" stroke-dasharray="2,2" />
                <line x1="${paddingX}" y1="${paddingY + chartHeight}" x2="${width - paddingX}" y2="${paddingY + chartHeight}" stroke="#1E293B" stroke-dasharray="2,2" />
            `;
            
            let pathD = '';
            points.forEach((pt, idx) => {
                if (idx === 0) {
                    pathD += `M ${pt.x} ${pt.y}`;
                } else {
                    pathD += ` L ${pt.x} ${pt.y}`;
                }
            });
            
            let htmlChart = htmlGrid;
            if (points.length > 1) {
                htmlChart += `<path d="${pathD}" fill="none" stroke="#3B82F6" stroke-width="4" opacity="0.15" stroke-linecap="round" stroke-linejoin="round" />`;
                htmlChart += `<path d="${pathD}" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="dynamic-accent-stroke" />`;
            }
            
            points.forEach(pt => {
                htmlChart += `
                    <g>
                        <circle cx="${pt.x}" cy="${pt.y}" r="6" fill="#3B82F6" opacity="0.1" />
                        <circle cx="${pt.x}" cy="${pt.y}" r="3" fill="#ffffff" stroke="#3B82F6" stroke-width="1.5" class="dynamic-accent-stroke" />
                        <text x="${pt.x}" y="${pt.y - 8}" fill="#3B82F6" font-size="8" font-weight="extrabold" text-anchor="middle" font-family="sans-serif" class="dynamic-accent-fg">${pt.val}</text>
                    </g>`;
            });
            
            svg.innerHTML = htmlChart;
            
            let htmlLabels = '';
            reversed.forEach(pt => {
                const displayDate = pt.date.substring(5); // MM-DD
                htmlLabels += `<div>${displayDate}</div>`;
            });
            labelRow.innerHTML = htmlLabels;
        }

        // STATS AND INSIGHT ANALYTICS
        async function refreshStats() {
            try {
                const resp = await fetch('/api/stats');
                const data = await resp.json();
                
                // Update summary statistics badges
                document.getElementById('statBadge-totalBatches').textContent = data.total_sessions || 0;
                document.getElementById('statBadge-totalPDFs').textContent = data.total_pdfs || 0;
                document.getElementById('statBadge-totalExcels').textContent = data.total_excels || 0;
                
                // Draw Donut chart and legend list
                drawDonutChart(data.distribution);
                
                // Draw weekly line trend chart
                drawLineChart(data.trend);
                
                updateThemeBranding();
            } catch (err) {
                console.error('Stats loading failed:', err);
            }
        }

        // HISTORY LOGS SECTION
        let searchTimeout = null;
        function debouncedSearch() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(refreshHistory, 300);
        }

        async function refreshHistory() {
            const query = document.getElementById('historySearch').value;
            try {
                const resp = await fetch(`/api/history?search=${encodeURIComponent(query)}`);
                const data = await resp.json();
                
                const body = document.getElementById('historyTableBody');
                if (!data || data.length === 0) {
                    body.innerHTML = `<tr><td colspan="5" class="py-8 text-center text-slate-500 italic">No historical audit logs found</td></tr>`;
                    return;
                }
                
                let html = '';
                data.forEach(row => {
                    const escPath = (row.full_path || row.output_path || '').replace(/\\\\/g, '\\\\\\\\');
                    html += `
                        <tr class="hover:bg-slate-900/30 transition text-xs border-b border-brand-borderLine">
                            <td class="py-3.5 px-6 font-mono text-slate-400">${row.timestamp}</td>
                            <td class="py-3.5 px-6 font-semibold text-slate-200 truncate max-w-[250px]" title="${row.excel_name}">${row.excel_name}</td>
                            <td class="py-3.5 px-6 text-center font-bold text-sky-400">${row.pdf_count}</td>
                            <td class="py-3.5 px-6 text-center"><span class="px-2 py-0.5 rounded-full font-bold bg-slate-900 border border-brand-borderLine text-slate-400">${row.audit_type}</span></td>
                            <td class="py-3.5 px-6 text-center">
                                <button onclick="openSystemPath('${escPath}')" class="text-blue-500 hover:text-white bg-blue-500/10 hover:bg-blue-500 border border-blue-500/20 px-3 py-1.5 rounded transition font-semibold dynamic-accent-fg">Open Files</button>
                            </td>
                        </tr>`;
                });
                body.innerHTML = html;
                updateThemeBranding();
            } catch (err) {
                console.error('History retrieval request error:', err);
            }
        }

        async function openSystemPath(path) {
            if (!path) return;
            try {
                await fetch('/api/open', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path })
                });
            } catch (err) {
                console.error('Open directory path failed:', err);
            }
        }

        // SETTINGS AND AUTO-UPDATER
        function refreshSettings() {
            updateNamingPreview();
        }

        function updateNamingPreview() {
            const pattern = document.getElementById('settingsNamingPattern').value || '{branch}_{type}';
            const preview = document.getElementById('namingPreview');
            
            let replaced = pattern.replace('{branch}', 'MUMBAI_CENTRAL').replace('{type}', 'POA');
            preview.textContent = `e.g. ${replaced}.pdf`;
        }

        async function saveNamingPattern() {
            const pattern = document.getElementById('settingsNamingPattern').value || '{branch}_{type}';
            try {
                await saveConfig('naming_pattern', pattern);
                showToast('Output naming convention pattern saved successfully!', 'success');
            } catch (err) {
                console.error('Failed to save pattern:', err);
            }
        }

        async function clearRecentFiles() {
            if (!confirm('Are you sure you want to clear the cached recent master Excel paths?')) return;
            try {
                const resp = await fetch('/api/recent/clear', { method: 'POST' });
                const data = await resp.json();
                if (data.success) {
                    showToast('Recent file cache links cleared.', 'success');
                    loadDashboardData();
                }
            } catch (err) {
                console.error(err);
            }
        }

        async function clearDatabaseHistory() {
            if (!confirm('CAUTION: This will delete ALL historical audit logs and analytics statistics permanently! Are you absolutely sure?')) return;
            try {
                const resp = await fetch('/api/history/clear', { method: 'POST' });
                const data = await resp.json();
                if (data.success) {
                    showToast('Database audit logs history purged completely.', 'success');
                    loadDashboardData();
                }
            } catch (err) {
                console.error(err);
            }
        }

        // AUTO-UPDATER TRIGGERS
        let updateCheckInterval = null;

        async function checkUpdatesBackground() {
            try {
                const resp = await fetch('/api/update/check');
                const data = await resp.json();
                if (data.update_ready) {
                    // Show update ready banner at top of header
                    const banner = document.getElementById('updateBanner');
                    banner.classList.remove('hidden');
                }
            } catch (err) {
                console.warn('Background update query unreachable.');
            }
        }

        async function manualCheckUpdates() {
            const btn = document.getElementById('btnCheckUpdates');
            const statusText = document.getElementById('updateStatusText');
            const progressContainer = document.getElementById('updateProgressBarContainer');
            const progressBar = document.getElementById('updateProgressBar');
            
            btn.disabled = true;
            statusText.textContent = 'Checking GitHub repo for latest release...';
            statusText.className = 'text-xs text-sky-400 font-semibold';
            
            try {
                const resp = await fetch('/api/update/check');
                const data = await resp.json();
                
                if (!data.update_ready) {
                    statusText.textContent = `✓ Audit Engine Elite is fully up-to-date (${data.current || '{{VERSION}}'}).`;
                    statusText.className = 'text-xs text-emerald-400 font-semibold';
                    btn.disabled = false;
                    return;
                }
                
                // Update found! Start download
                statusText.textContent = `Update Found: Downloading Elite ${data.latest} binary ZIP...`;
                progressContainer.classList.remove('hidden');
                progressBar.style.width = '0%';
                
                const startResp = await fetch('/api/update/install', { method: 'POST' });
                const startData = await startResp.json();
                
                if (!startData.success) {
                    statusText.textContent = '✗ Update download failed: ' + startData.error;
                    statusText.className = 'text-xs text-rose-500 font-semibold';
                    btn.disabled = false;
                    return;
                }
                
                // Poll download percentage
                updateCheckInterval = setInterval(async () => {
                    const progResp = await fetch('/api/update/progress');
                    const progData = await progResp.json();
                    
                    const pct = Math.round(progData.pct || 0);
                    progressBar.style.width = `${pct}%`;
                    statusText.textContent = `Downloading Update: ${pct}% complete...`;
                    
                    if (!progData.is_downloading) {
                        clearInterval(updateCheckInterval);
                        btn.disabled = false;
                        
                        if (progData.success) {
                            statusText.textContent = '✓ Update staged successfully! Application needs a restart to apply changes.';
                            statusText.className = 'text-xs text-emerald-400 font-semibold';
                            
                            // Show top banner too
                            document.getElementById('updateBanner').classList.remove('hidden');
                        } else {
                            statusText.textContent = '✗ Extraction download failed: ' + (progData.error || 'Network error.');
                            statusText.className = 'text-xs text-rose-500 font-semibold';
                        }
                    }
                }, 500);
                
            } catch (err) {
                console.error(err);
                statusText.textContent = 'Error querying update servers.';
                btn.disabled = false;
            }
        }

        async function applyUpdate() {
            try {
                await fetch('/api/update/apply', { method: 'POST' });
                openSummaryModal({
                    title: 'Restarting Audit Engine...',
                    message: 'The backend server is applying the update and restarting. This page will automatically refresh when the new version is ready. Please wait...'
                });
                
                setTimeout(() => {
                    const pollInterval = setInterval(async () => {
                        try {
                            const res = await fetch('/api/config', { cache: 'no-store' });
                            if (res.ok) {
                                clearInterval(pollInterval);
                                window.location.reload(true);
                            }
                        } catch (e) {
                            // Still waiting for server
                        }
                    }, 1000);
                }, 2000);
            } catch (err) {
                console.error(err);
            }
        }

        function dismissUpdateBanner() {
            document.getElementById('updateBanner').classList.add('hidden');
        }