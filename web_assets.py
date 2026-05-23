# -*- coding: utf-8 -*-
"""Web assets for Audit Engine modern browser interface.
Defines the premium, high-fidelity responsive HTML5/CSS3 Single-Page App dashboard.
"""

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audit Engine Elite v5</title>
    <!-- Tailwind CSS Play CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        brand: {
                            idfc: '#2563EB',
                            idfcHover: '#1D4ED8',
                            eq: '#D97706',
                            eqHover: '#B45309',
                            slateBlack: '#0B0F19',
                            panelBg: '#162032',
                            borderLine: '#1E293B',
                            termBg: '#050811'
                        }
                    }
                }
            }
        }
    </script>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        h1, h2, h3, .logo-font {
            font-family: 'Outfit', sans-serif;
        }
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #0B0F19;
        }
        ::-webkit-scrollbar-thumb {
            background: #1E293B;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #475569;
        }
    </style>
</head>
<body class="h-full flex overflow-hidden">
    <!-- Root Container -->
    <div class="flex-1 flex overflow-hidden">
        
        <!-- Sidebar Navigation -->
        <aside class="w-64 bg-brand-slateBlack border-r border-brand-borderLine flex flex-col justify-between flex-shrink-0">
            <div>
                <!-- Brand logo area -->
                <div class="px-6 py-8 flex flex-col items-center">
                    <div class="flex items-center space-x-2">
                        <i data-lucide="shield-check" class="w-8 h-8 text-blue-500 logo-icon"></i>
                        <span class="text-2xl font-bold logo-font tracking-tight text-white logo-text-primary">IDFC FIRST</span>
                    </div>
                    <span class="text-[10px] font-extrabold tracking-widest text-blue-500 mt-1 logo-text-secondary">AUDIT ENGINE</span>
                </div>

                <!-- Bank Profile Selector -->
                <div class="px-4 mb-6">
                    <label class="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Bank Profile</label>
                    <div class="relative">
                        <select id="bankSelector" class="w-full bg-slate-900 border border-brand-borderLine rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 appearance-none cursor-pointer">
                            <option value="IDFC First Bank">IDFC First Bank</option>
                            <option value="Equitas Small Finance Bank">Equitas Small Finance Bank</option>
                        </select>
                        <div class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none text-slate-500">
                            <i data-lucide="chevron-down" class="w-4 h-4"></i>
                        </div>
                    </div>
                </div>

                <!-- Navigation Links -->
                <nav class="px-2 space-y-1">
                    <button onclick="switchTab('PROCESS')" id="tabBtn-PROCESS" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 border-blue-500 nav-btn">
                        <i data-lucide="play" class="w-4 h-4"></i>
                        <span>New Batch</span>
                    </button>
                    <button onclick="switchTab('STATS')" id="tabBtn-STATS" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn">
                        <i data-lucide="bar-chart-3" class="w-4 h-4"></i>
                        <span>Analytics</span>
                    </button>
                    <button onclick="switchTab('HISTORY')" id="tabBtn-HISTORY" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn">
                        <i data-lucide="history" class="w-4 h-4"></i>
                        <span>History</span>
                    </button>
                    <button onclick="switchTab('SETTINGS')" id="tabBtn-SETTINGS" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn">
                        <i data-lucide="settings" class="w-4 h-4"></i>
                        <span>Settings</span>
                    </button>
                </nav>
            </div>

            <!-- Footer area -->
            <div class="px-6 py-6 border-t border-brand-borderLine flex flex-col items-center">
                <span class="text-xs text-slate-600 font-mono version-label">v5.2.145</span>
                <span class="text-[9px] text-slate-700 mt-1 copyright-label">© 2026 IDFC FIRST Bank</span>
            </div>
        </aside>

        <!-- Main Content Panel Area -->
        <main class="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-950">
            <!-- Header bar / Info Banner -->
            <header id="updateBanner" class="hidden bg-emerald-600 px-6 py-3 flex justify-between items-center flex-shrink-0 animate-pulse">
                <div class="flex items-center space-x-2 text-white">
                    <i data-lucide="arrow-down-to-line" class="w-4 h-4"></i>
                    <span class="text-sm font-semibold">✓ Dynamic update ready to install!</span>
                </div>
                <div class="flex space-x-3">
                    <button onclick="applyUpdate()" class="bg-white text-emerald-700 text-xs font-bold px-4 py-1.5 rounded-md shadow-sm hover:bg-slate-100 transition">Restart Now</button>
                    <button onclick="dismissUpdateBanner()" class="text-emerald-200 text-xs font-semibold hover:text-white transition">Later</button>
                </div>
            </header>

            <!-- Scrollable Content Frame -->
            <div class="flex-1 overflow-y-auto px-10 py-8 relative">
                
                <!-- SECTION: PROCESS (IDFC WORKFLOW) -->
                <section id="tab-PROCESS-IDFC" class="space-y-6">
                    <!-- Title Header -->
                    <div class="flex justify-between items-center">
                        <h2 class="text-3xl font-bold tracking-tight text-white">Generate Reports</h2>
                        <span class="px-3 py-1.5 text-xs font-bold rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">IDFC FIRST Bank</span>
                    </div>

                    <!-- Statistics Card Widgets -->
                    <div class="grid grid-cols-3 gap-6">
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-5 shadow-sm">
                            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Total Sessions</span>
                            <span id="idfcStat-sessions" class="text-2xl font-bold mt-2 block text-sky-400">0</span>
                        </div>
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-5 shadow-sm">
                            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Last Run</span>
                            <span id="idfcStat-lastRun" class="text-base font-bold mt-2 block text-emerald-400 truncate">No activity yet</span>
                        </div>
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-5 shadow-sm">
                            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">PDF Reports Generated</span>
                            <span id="idfcStat-pdfs" class="text-2xl font-bold mt-2 block text-blue-500 dynamic-accent-fg">0</span>
                        </div>
                    </div>

                    <!-- Primary Setup Controls Panel -->
                    <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-5 shadow-md">
                        <!-- Source File -->
                        <div>
                            <label class="block text-sm font-semibold text-slate-300 mb-2">Source Master Excel</label>
                            <div class="flex space-x-3">
                                <input type="text" id="idfcInputFile" readonly class="flex-1 bg-slate-900 border border-brand-borderLine rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none" placeholder="No file selected">
                                <button onclick="browseFile('idfcInputFile')" class="bg-slate-800 text-slate-300 text-sm font-semibold px-5 py-2.5 rounded-lg border border-brand-borderLine hover:bg-slate-700 transition">Browse...</button>
                            </div>
                        </div>

                        <!-- Validation Banner -->
                        <div id="idfcValidationBox" class="hidden text-xs rounded-lg px-4 py-2.5"></div>

                        <!-- Recent Files -->
                        <div id="idfcRecentContainer" class="flex items-center space-x-3 text-xs">
                            <span class="font-semibold text-slate-500">Recent:</span>
                            <div id="idfcRecentList" class="flex space-x-2 overflow-x-auto">
                                <span class="text-slate-600 italic">None saved</span>
                            </div>
                        </div>

                        <!-- File Preview -->
                        <div id="idfcPreviewBox" class="hidden bg-emerald-950/20 border border-emerald-900/30 rounded-lg px-4 py-3 flex items-center space-x-2 text-emerald-400 text-xs">
                            <i data-lucide="check-circle" class="w-4 h-4"></i>
                            <span id="idfcPreviewText">File loaded successfully</span>
                        </div>

                        <!-- Options config -->
                        <div class="grid grid-cols-2 gap-6 pt-2">
                            <!-- Left: Audit Type Segment -->
                            <div>
                                <label class="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Audit Type</label>
                                <div class="bg-slate-900 p-1 rounded-lg border border-brand-borderLine flex space-x-1">
                                    <button onclick="setIdfcAuditType('POA')" id="idfcOpt-POA" class="flex-1 py-1.5 text-xs font-bold rounded-md bg-blue-500 text-white shadow-sm transition dynamic-accent-bg">POA</button>
                                    <button onclick="setIdfcAuditType('TAF')" id="idfcOpt-TAF" class="flex-1 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition">TAF</button>
                                </div>
                            </div>
                            <!-- Right: Folder Auto-open -->
                            <div class="flex items-end pb-2">
                                <label class="flex items-center space-x-3 cursor-pointer">
                                    <input type="checkbox" id="idfcAutoOpen" class="w-4 h-4 text-blue-500 rounded bg-slate-900 border-brand-borderLine focus:ring-0 cursor-pointer dynamic-accent-accent">
                                    <span class="text-xs text-slate-300">Auto-open destination folder after generation</span>
                                </label>
                            </div>
                        </div>

                        <!-- Output Mode Row -->
                        <div class="pt-2">
                            <label class="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Output Mode</label>
                            <div class="bg-slate-900 p-1 rounded-lg border border-brand-borderLine flex space-x-1 w-max">
                                <button onclick="setIdfcOutputMode('FOLDER')" id="idfcMode-FOLDER" class="px-5 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition">FOLDER</button>
                                <button onclick="setIdfcOutputMode('ZIP ONLY')" id="idfcMode-ZIPONLY" class="px-5 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition">ZIP ONLY</button>
                                <button onclick="setIdfcOutputMode('BOTH')" id="idfcMode-BOTH" class="px-5 py-1.5 text-xs font-bold rounded-md bg-blue-500 text-white shadow-sm transition dynamic-accent-bg">BOTH</button>
                            </div>
                        </div>

                        <!-- Output Folder -->
                        <div class="pt-2">
                            <label class="block text-sm font-semibold text-slate-300 mb-2">Output Directory</label>
                            <div class="flex space-x-3">
                                <input type="text" id="idfcOutputDir" readonly class="flex-1 bg-slate-900 border border-brand-borderLine rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none" placeholder="No directory selected">
                                <button onclick="browseFolder('idfcOutputDir')" class="bg-slate-800 text-slate-300 text-sm font-semibold px-5 py-2.5 rounded-lg border border-brand-borderLine hover:bg-slate-700 transition">Browse...</button>
                            </div>
                        </div>

                        <!-- Divider line -->
                        <div class="border-t border-brand-borderLine pt-2"></div>

                        <!-- Action Buttons and Progress bar -->
                        <div class="flex items-center space-x-4">
                            <button id="idfcBtnRun" onclick="startGeneration()" class="flex-1 bg-blue-600 text-white text-sm font-bold py-3.5 px-6 rounded-lg hover:bg-blue-500 transition shadow-md dynamic-accent-bg dynamic-accent-hover-bg">Generate Reports</button>
                            <button id="idfcBtnCancel" onclick="cancelGeneration()" disabled class="bg-rose-600 text-white text-sm font-bold py-3.5 px-6 rounded-lg hover:bg-rose-500 transition disabled:opacity-40 disabled:pointer-events-none">Stop</button>
                        </div>

                        <!-- Progress indicator -->
                        <div id="idfcProgressContainer" class="space-y-2 pt-2 hidden">
                            <div class="flex justify-between text-xs text-slate-400">
                                <span id="idfcProgressBranch" class="italic">Initializing build...</span>
                                <span id="idfcProgressPct" class="font-bold text-white">0%</span>
                            </div>
                            <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-brand-borderLine">
                                <div id="idfcProgressBar" class="bg-blue-500 h-full rounded-full transition-all duration-300 dynamic-accent-bg" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Console Logs terminal -->
                    <div class="space-y-2">
                        <span class="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Console Logs</span>
                        <div id="idfcConsole" class="bg-brand-termBg border border-brand-borderLine rounded-xl h-56 font-mono text-[11px] p-5 overflow-y-auto space-y-1.5 shadow-inner">
                            <div class="text-slate-500">[00:00:00] Terminal logger online. Ready.</div>
                        </div>
                    </div>
                </section>

                <!-- SECTION: PROCESS (EQUITAS WORKFLOW) -->
                <section id="tab-PROCESS-EQUITAS" class="space-y-6 hidden">
                    <!-- Title Header -->
                    <div class="flex justify-between items-center">
                        <h2 class="text-3xl font-bold tracking-tight text-white">Generate Reports</h2>
                        <span class="px-3 py-1.5 text-xs font-bold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Equitas Small Finance Bank</span>
                    </div>

                    <!-- Stage Tab Selector segmented pill bar -->
                    <div class="bg-brand-panelBg p-1.5 rounded-xl border border-brand-borderLine flex space-x-2 w-max">
                        <button onclick="setEquitasStage('STAGE 1')" id="eqStage-S1" class="px-6 py-2 text-xs font-bold rounded-lg bg-amber-500 text-white shadow-sm transition dynamic-accent-bg">STAGE 1: GENERATE BRANCH TEMPLATES</button>
                        <button onclick="setEquitasStage('STAGE 2')" id="eqStage-S2" class="px-6 py-2 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition">STAGE 2: CONSOLIDATE REPORTS</button>
                    </div>

                    <!-- Control Panel -->
                    <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-5 shadow-md">
                        <!-- Stage Title label -->
                        <h3 id="eqStageTitle" class="text-sm font-bold text-slate-300">Stage 1: Generate Branch Audits & Excels</h3>

                        <!-- Source File -->
                        <div>
                            <label id="eqFileLabel" class="block text-sm font-semibold text-slate-300 mb-2">Source Excel (Normal + JSR sheets)</label>
                            <div class="flex space-x-3">
                                <input type="text" id="eqInputFile" readonly class="flex-1 bg-slate-900 border border-brand-borderLine rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none" placeholder="No file selected">
                                <button onclick="browseFile('eqInputFile')" class="bg-slate-800 text-slate-300 text-sm font-semibold px-5 py-2.5 rounded-lg border border-brand-borderLine hover:bg-slate-700 transition">Browse...</button>
                            </div>
                        </div>

                        <!-- Validation Banner -->
                        <div id="eqValidationBox" class="hidden text-xs rounded-lg px-4 py-2.5"></div>

                        <!-- Recent Files -->
                        <div id="eqRecentContainer" class="flex items-center space-x-3 text-xs">
                            <span class="font-semibold text-slate-500">Recent:</span>
                            <div id="eqRecentList" class="flex space-x-2 overflow-x-auto">
                                <span class="text-slate-600 italic">None saved</span>
                            </div>
                        </div>

                        <!-- File Preview -->
                        <div id="eqPreviewBox" class="hidden bg-emerald-950/20 border border-emerald-900/30 rounded-lg px-4 py-3 flex items-center space-x-2 text-emerald-400 text-xs">
                            <i data-lucide="check-circle" class="w-4 h-4"></i>
                            <span id="eqPreviewText">File loaded successfully</span>
                        </div>

                        <!-- Format & Packaging row (Stage 1 Only) -->
                        <div id="eqStage1Config" class="grid grid-cols-2 gap-6 pt-2">
                            <!-- Left: Output Format pills -->
                            <div>
                                <label class="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Output Format</label>
                                <div class="bg-slate-900 p-1 rounded-lg border border-brand-borderLine flex space-x-1">
                                    <button onclick="setEqFormat('PDF ONLY')" id="eqFormat-PDFONLY" class="flex-1 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition">PDF ONLY</button>
                                    <button onclick="setEqFormat('EXCEL ONLY')" id="eqFormat-EXCELONLY" class="flex-1 py-1.5 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition">EXCEL ONLY</button>
                                    <button onclick="setEqFormat('BOTH')" id="eqFormat-BOTH" class="flex-1 py-1.5 text-xs font-bold rounded-md bg-amber-500 text-white shadow-sm transition dynamic-accent-bg">BOTH</button>
                                </div>
                            </div>
                            <!-- Right: Packaging ComboBox -->
                            <div>
                                <label class="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Packaging Mode</label>
                                <div class="relative">
                                    <select id="eqPackagingSelector" class="w-full bg-slate-900 border border-brand-borderLine rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none appearance-none cursor-pointer">
                                        <option value="FOLDER">FOLDER</option>
                                        <option value="ZIP OF PDF">ZIP OF PDF</option>
                                        <option value="ZIP OF EXCEL">ZIP OF EXCEL</option>
                                        <option value="ZIP OF BOTH">ZIP OF BOTH</option>
                                        <option value="BOTH (FOLDER + ZIP OF PDF)">BOTH (FOLDER + ZIP OF PDF)</option>
                                        <option value="BOTH (FOLDER + ZIP OF EXCEL)">BOTH (FOLDER + ZIP OF EXCEL)</option>
                                        <option value="BOTH (FOLDER + ZIP OF BOTH)">BOTH (FOLDER + ZIP OF BOTH)</option>
                                    </select>
                                    <div class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none text-slate-500">
                                        <i data-lucide="chevron-down" class="w-4 h-4"></i>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Output Folder -->
                        <div class="pt-2">
                            <label class="block text-sm font-semibold text-slate-300 mb-2">Output Directory</label>
                            <div class="flex space-x-3">
                                <input type="text" id="eqOutputDir" readonly class="flex-1 bg-slate-900 border border-brand-borderLine rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none" placeholder="No directory selected">
                                <button onclick="browseFolder('eqOutputDir')" class="bg-slate-800 text-slate-300 text-sm font-semibold px-5 py-2.5 rounded-lg border border-brand-borderLine hover:bg-slate-700 transition">Browse...</button>
                            </div>
                        </div>

                        <!-- Folder Auto-open -->
                        <div class="flex items-center space-x-3 cursor-pointer pt-2">
                            <input type="checkbox" id="eqAutoOpen" class="w-4 h-4 text-amber-500 rounded bg-slate-900 border-brand-borderLine focus:ring-0 cursor-pointer dynamic-accent-accent">
                            <span class="text-xs text-slate-300">Auto-open destination folder after generation</span>
                        </div>

                        <!-- Divider line -->
                        <div class="border-t border-brand-borderLine pt-2"></div>

                        <!-- Action Buttons and Progress bar -->
                        <div class="flex items-center space-x-4">
                            <button id="eqBtnRun" onclick="startGeneration()" class="flex-1 bg-amber-600 text-white text-sm font-bold py-3.5 px-6 rounded-lg hover:bg-amber-500 transition shadow-md dynamic-accent-bg dynamic-accent-hover-bg">Generate (Stage 1)</button>
                            <button id="eqBtnCancel" onclick="cancelGeneration()" disabled class="bg-rose-600 text-white text-sm font-bold py-3.5 px-6 rounded-lg hover:bg-rose-500 transition disabled:opacity-40 disabled:pointer-events-none">Stop</button>
                        </div>

                        <!-- Progress indicator -->
                        <div id="eqProgressContainer" class="space-y-2 pt-2 hidden">
                            <div class="flex justify-between text-xs text-slate-400">
                                <span id="eqProgressBranch" class="italic">Initializing build...</span>
                                <span id="eqProgressPct" class="font-bold text-white">0%</span>
                            </div>
                            <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-brand-borderLine">
                                <div id="eqProgressBar" class="bg-amber-500 h-full rounded-full transition-all duration-300 dynamic-accent-bg" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Console Logs terminal -->
                    <div class="space-y-2">
                        <span class="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Console Logs</span>
                        <div id="eqConsole" class="bg-brand-termBg border border-brand-borderLine rounded-xl h-56 font-mono text-[11px] p-5 overflow-y-auto space-y-1.5 shadow-inner">
                            <div class="text-slate-500">[00:00:00] Terminal logger online. Ready.</div>
                        </div>
                    </div>
                </section>

                <!-- SECTION: STATS (ANALYTICS) -->
                <section id="tab-STATS" class="space-y-6 hidden">
                    <div class="flex justify-between items-center border-b border-brand-borderLine pb-4">
                        <h2 class="text-3xl font-bold tracking-tight text-white font-sans">Insight Analytics</h2>
                        <button onclick="refreshStats()" class="bg-slate-800 text-slate-300 text-xs font-semibold px-4 py-2 rounded-lg border border-brand-borderLine hover:bg-slate-700 transition">Refresh</button>
                    </div>

                    <div class="grid grid-cols-2 gap-8">
                        <!-- Left card: Audit Type Distribution -->
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-6">
                            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Audit Type Distribution</h3>
                            <div id="statsDistribution" class="space-y-4">
                                <!-- Dynamic progress rows -->
                                <div class="text-sm text-slate-400 italic">No activity logs recorded yet.</div>
                            </div>
                        </div>

                        <!-- Right card: Daily activity logs -->
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-6">
                            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Daily Activity (Last 7 Days)</h3>
                            <div id="statsActivity" class="space-y-3">
                                <!-- Dynamic daily list -->
                                <div class="text-sm text-slate-400 italic">No activity logs recorded yet.</div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- SECTION: HISTORY -->
                <section id="tab-HISTORY" class="space-y-6 hidden">
                    <div class="border-b border-brand-borderLine pb-4">
                        <h2 class="text-3xl font-bold tracking-tight text-white font-sans">History Logs</h2>
                    </div>

                    <!-- Search panel -->
                    <div class="relative">
                        <input type="text" id="historySearch" oninput="debouncedSearch()" class="w-full bg-slate-900 border border-brand-borderLine rounded-lg pl-10 pr-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-blue-500" placeholder="Type branch or Excel filename to search past audit logs...">
                        <div class="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                            <i data-lucide="search" class="w-4 h-4"></i>
                        </div>
                    </div>

                    <!-- History Table container -->
                    <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl overflow-hidden shadow-md">
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse text-sm">
                                <thead>
                                    <tr class="bg-slate-900 border-b border-brand-borderLine text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                                        <th class="py-3.5 px-6">Timestamp</th>
                                        <th class="py-3.5 px-6">Master Excel Name</th>
                                        <th class="py-3.5 px-6 text-center">Items Generated</th>
                                        <th class="py-3.5 px-6 text-center">Audit Type</th>
                                        <th class="py-3.5 px-6 text-center">Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="historyTableBody" class="divide-y divide-brand-borderLine text-slate-300">
                                    <tr>
                                        <td colspan="5" class="py-8 text-center text-slate-500 italic">No logs found</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

                <!-- SECTION: SETTINGS -->
                <section id="tab-SETTINGS" class="space-y-6 hidden">
                    <div class="border-b border-brand-borderLine pb-4">
                        <h2 class="text-3xl font-bold tracking-tight text-white font-sans">Settings</h2>
                    </div>

                    <!-- Card 1: Output naming customizer -->
                    <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-4 shadow-sm">
                        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Output File Naming Pattern</h3>
                        <p class="text-xs text-slate-500">Placeholders: <code>{branch}</code> = branch name, <code>{type}</code> = audit type (POA or TAF)</p>
                        <div class="flex space-x-3">
                            <input type="text" id="settingsNamingPattern" class="flex-1 bg-slate-900 border border-brand-borderLine rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none" placeholder="{branch}_{type}">
                            <button onclick="saveNamingPattern()" class="bg-blue-600 text-white text-sm font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-500 transition dynamic-accent-bg dynamic-accent-hover-bg">Save</button>
                        </div>
                        <div class="text-xs text-slate-500 italic">Preview: <span id="namingPreview" class="font-mono text-slate-400">e.g. BRANCH_A_POA.pdf</span></div>
                    </div>

                    <!-- Card 2: Automatic Updates -->
                    <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-4 shadow-sm">
                        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Auto-Updates</h3>
                        <div class="flex justify-between items-center text-sm text-slate-200">
                            <span>Current running version: <strong class="font-mono text-white text-brand-idfc dynamic-accent-fg">v5.2.145</strong></span>
                            <div id="updateStatusText" class="text-xs font-semibold"></div>
                        </div>
                        <div class="flex items-center space-x-4">
                            <button id="btnCheckUpdates" onclick="manualCheckUpdates()" class="bg-slate-800 text-slate-300 text-xs font-semibold px-5 py-2.5 rounded-lg border border-brand-borderLine hover:bg-slate-700 transition">Check for Updates</button>
                            <div id="updateProgressBarContainer" class="flex-1 bg-slate-900 h-2 rounded-full overflow-hidden border border-brand-borderLine hidden">
                                <div id="updateProgressBar" class="bg-blue-500 h-full rounded-full transition-all duration-300 dynamic-accent-bg" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Card 3: Default Preferences -->
                    <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-4 shadow-sm">
                        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Default Preferences</h3>
                        <div class="space-y-3">
                            <label class="flex items-center space-x-3 cursor-pointer">
                                <input type="checkbox" id="prefAutoOpen" class="w-4 h-4 text-blue-500 rounded bg-slate-900 border-brand-borderLine focus:ring-0 cursor-pointer dynamic-accent-accent">
                                <span class="text-sm text-slate-300">Auto-open destination folder after generating reports</span>
                            </label>
                            <div class="pt-2 flex items-center space-x-4">
                                <span class="text-xs text-slate-400">Clear cached history links:</span>
                                <button onclick="clearRecentFiles()" class="bg-slate-900 text-rose-500 hover:text-white hover:bg-rose-900 border border-brand-borderLine text-xs font-bold px-4 py-2 rounded-lg transition">Clear Recent Cache</button>
                            </div>
                        </div>
                    </div>

                    <!-- Card 4: Database cleanup -->
                    <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-4 shadow-sm">
                        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Database & System Logs Management</h3>
                        <p class="text-xs text-slate-500">Database location: <code class="font-mono text-slate-400" id="dbPathLabel">~/.idfc_pdf_generator_v3.db</code></p>
                        <p class="text-xs text-slate-500">Log file location: <code class="font-mono text-slate-400" id="logPathLabel">~/.idfc_audit_engine.log</code></p>
                        <button onclick="clearDatabaseHistory()" class="bg-slate-900 text-rose-500 hover:text-white hover:bg-rose-900 border border-brand-borderLine text-xs font-bold px-5 py-2.5 rounded-lg transition">Clear All Audit Logs History</button>
                    </div>
                </section>
            </div>

            <!-- Bottom status status bar -->
            <footer class="h-10 bg-brand-slateBlack border-t border-brand-borderLine flex items-center justify-between px-6 flex-shrink-0">
                <span id="footerStatusText" class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">STATUS: Idle. Ready.</span>
                <span class="text-[9px] text-slate-700 italic">Audit Engine Premium WSGI Portal</span>
            </footer>
        </main>
    </div>

    <!-- MODAL POPUP: SUMMARY DIALOG -->
    <div id="summaryModal" class="hidden fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
        <div class="bg-brand-slateBlack border border-brand-borderLine w-full max-w-lg rounded-2xl shadow-xl overflow-hidden transform scale-95 transition-all duration-300">
            <div class="px-6 py-5 border-b border-brand-borderLine">
                <h3 id="summaryTitle" class="text-base font-bold text-white tracking-tight">Generation Complete</h3>
            </div>
            <div class="p-6">
                <div id="summaryTextContent" class="bg-slate-950 border border-brand-borderLine font-mono text-xs p-5 rounded-xl h-52 overflow-y-auto space-y-1">
                    <!-- Dynamic summary items -->
                </div>
            </div>
            <div class="px-6 py-4 bg-slate-900 border-t border-brand-borderLine flex justify-end">
                <button onclick="closeSummaryModal()" class="bg-slate-800 text-slate-300 hover:bg-slate-700 border border-brand-borderLine text-xs font-bold px-6 py-2.5 rounded-lg transition">Close</button>
            </div>
        </div>
    </div>

    <!-- Javascript Core App State Management -->
    <script>
        // Init Lucide Icons
        lucide.createIcons();

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
            isGenerating: false,
            logsCount: 0
        };

        // DOM REFERENCES
        const bankSelector = document.getElementById('bankSelector');
        const idfcInputFile = document.getElementById('idfcInputFile');
        const idfcOutputDir = document.getElementById('idfcOutputDir');
        const eqInputFile = document.getElementById('eqInputFile');
        const eqOutputDir = document.getElementById('eqOutputDir');

        // HEARTBEAT self-termination loop
        setInterval(() => {
            fetch('/api/heartbeat')
                .catch(() => console.warn('Heartbeat server unreachable.'));
        }, 3000);

        // INITIALIZATION
        window.addEventListener('DOMContentLoaded', () => {
            // Load configs and history list
            loadDashboardData();
            // Start silent updater background check after 2 seconds
            setTimeout(checkUpdatesBackground, 2000);
        });

        // BANK SELECTION CHANGE EVENT
        bankSelector.addEventListener('change', (e) => {
            const val = e.target.value;
            state.activeBank = val;
            
            // Save active bank to config
            saveConfig('bank', val);
            
            // Dynamic branding updates
            updateThemeBranding();
        });

        function updateThemeBranding() {
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            
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
                activeBtn.className = isIDFC 
                    ? 'w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 border-blue-500 nav-btn'
                    : 'w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 border-amber-500 nav-btn';
            }

            // 3. Inject CSS dynamically for classes marked as "dynamic-accent-*"
            const primaryColor = isIDFC ? '#2563EB' : '#D97706';
            const hoverColor = isIDFC ? '#1D4ED8' : '#B45309';

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
            const eqSection = document.getElementById('tab-PROCESS-EQUITAS');
            
            if (state.activeTab === 'PROCESS') {
                if (isIDFC) {
                    idfcSection.classList.remove('hidden');
                    eqSection.classList.add('hidden');
                } else {
                    idfcSection.classList.add('hidden');
                    eqSection.classList.remove('hidden');
                }
            }
        }

        // TAB SWITCHER STATE
        function switchTab(tabId) {
            state.activeTab = tabId;
            
            // Update navigation button active styles
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.className = 'w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn';
            });
            
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const activeBtn = document.getElementById(`tabBtn-${tabId}`);
            if (activeBtn) {
                activeBtn.className = isIDFC 
                    ? 'w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 border-blue-500 nav-btn'
                    : 'w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 border-amber-500 nav-btn';
            }

            // Hide all tab sections
            document.getElementById('tab-PROCESS-IDFC').classList.add('hidden');
            document.getElementById('tab-PROCESS-EQUITAS').classList.add('hidden');
            document.getElementById('tab-STATS').classList.add('hidden');
            document.getElementById('tab-HISTORY').classList.add('hidden');
            document.getElementById('tab-SETTINGS').classList.add('hidden');

            // Show active section
            if (tabId === 'PROCESS') {
                if (isIDFC) {
                    document.getElementById('tab-PROCESS-IDFC').classList.remove('hidden');
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
                
                // Set initial paths
                if (data.last_file) {
                    idfcInputFile.value = data.last_file;
                    eqInputFile.value = data.last_file;
                    // Trigger validation peek
                    validateFile(data.last_file);
                }
                if (data.out_path) {
                    idfcOutputDir.value = data.out_path;
                    eqOutputDir.value = data.out_path;
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
            
            if (!files || files.length === 0) {
                const empty = '<span class="text-slate-600 italic">None saved</span>';
                idfcList.innerHTML = empty;
                eqList.innerHTML = empty;
                return;
            }
            
            let html = '';
            files.forEach(f => {
                const filename = f.split('/').pop().split('\\\\').pop();
                html += `<button onclick="selectRecentFile('${f.replace(/\\\\/g, '\\\\\\\\')}')" class="bg-slate-900 border border-brand-borderLine text-slate-400 hover:text-white hover:border-slate-500 rounded px-2.5 py-1 transition truncate max-w-[200px]" title="${f}">${filename}</button>`;
            });
            
            idfcList.innerHTML = html;
            eqList.innerHTML = html;
        }

        function selectRecentFile(path) {
            idfcInputFile.value = path;
            eqInputFile.value = path;
            saveConfig('last_file', path);
            validateFile(path);
        }

        // PREVIEW & VALIDATION OF EXCEL PEAK
        async function validateFile(filepath) {
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const validationBox = isIDFC ? document.getElementById('idfcValidationBox') : document.getElementById('eqValidationBox');
            const previewBox = isIDFC ? document.getElementById('idfcPreviewBox') : document.getElementById('eqPreviewBox');
            const previewText = isIDFC ? document.getElementById('idfcPreviewText') : document.getElementById('eqPreviewText');
            
            try {
                const resp = await fetch('/api/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filepath })
                });
                const data = await resp.json();
                
                if (data.success) {
                    // Update active bank if file auto-detects another bank!
                    if (data.detected_bank && data.detected_bank !== state.activeBank) {
                        state.activeBank = data.detected_bank;
                        bankSelector.value = data.detected_bank;
                        saveConfig('bank', data.detected_bank);
                        updateThemeBranding();
                        // Re-trigger validation on the correct bank view
                        validateFile(filepath);
                        return;
                    }

                    validationBox.classList.add('hidden');
                    previewBox.classList.remove('hidden');
                    previewBox.className = "bg-emerald-950/20 border border-emerald-900/30 rounded-lg px-4 py-3 flex items-center space-x-2 text-emerald-400 text-xs";
                    previewText.innerHTML = `<strong>✓ Excel Loaded:</strong> Found ${data.rows || 0} rows, representing ${data.branches || 0} branches to audit.`;
                } else {
                    previewBox.classList.add('hidden');
                    validationBox.classList.remove('hidden');
                    validationBox.className = "bg-rose-950/20 border border-rose-900/30 rounded-lg px-4 py-3 text-rose-400 text-xs";
                    validationBox.innerHTML = `<strong>✗ Load Error:</strong> ${data.error || 'Invalid spreadsheet file format.'}`;
                }
            } catch (err) {
                console.error('File validation request failed:', err);
            }
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
            const file = isIDFC ? idfcInputFile.value : eqInputFile.value;
            const output = isIDFC ? idfcOutputDir.value : eqOutputDir.value;
            
            if (!file) {
                alert('Please select a source Excel master file first.');
                return;
            }
            if (!output) {
                alert('Please select an output directory.');
                return;
            }
            
            state.isGenerating = true;
            
            // UI Toggle to busy
            setUiGeneratingState(true);
            
            // Console clearing and focus
            const consoleBox = isIDFC ? document.getElementById('idfcConsole') : document.getElementById('eqConsole');
            consoleBox.innerHTML = '<div class="text-slate-500">[00:00:00] Initializing generation background worker thread...</div>';
            state.logsCount = 0;
            
            // Gather run parameters
            const payload = {
                bank: state.activeBank,
                filepath: file,
                out_path: output,
                auto_open: isIDFC ? document.getElementById('idfcAutoOpen').checked : document.getElementById('eqAutoOpen').checked,
                naming_pattern: document.getElementById('settingsNamingPattern').value || '{branch}_{type}',
                
                // IDFC specific
                audit_type: state.idfc.auditType,
                output_mode: state.idfc.outputMode,
                
                // Equitas specific
                equitas_stage: state.equitas.stage,
                equitas_format: state.equitas.outputFormat,
                equitas_pack: document.getElementById('eqPackagingSelector').value
            };
            
            try {
                const resp = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await resp.json();
                
                if (!data.success) {
                    alert('Failed to start report generation thread: ' + data.error);
                    state.isGenerating = false;
                    setUiGeneratingState(false);
                    return;
                }
                
                // Start polling logs and percentage bar
                progressInterval = setInterval(pollProgress, 400);
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
                
                // Render progress bars
                const pct = Math.round(data.pct || 0);
                const branchText = data.active_branch || 'Processing spreadsheet records...';
                
                if (isIDFC) {
                    document.getElementById('idfcProgressPct').textContent = `${pct}%`;
                    document.getElementById('idfcProgressBranch').textContent = branchText;
                    document.getElementById('idfcProgressBar').style.width = `${pct}%`;
                } else {
                    document.getElementById('eqProgressPct').textContent = `${pct}%`;
                    document.getElementById('eqProgressBranch').textContent = branchText;
                    document.getElementById('eqProgressBar').style.width = `${pct}%`;
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
                    
                    // Show final report popup modal summary
                    if (data.summary) {
                        openSummaryModal(data.summary);
                    }
                    
                    // Reload Stats and dashboard history numbers
                    loadDashboardData();
                }
            } catch (err) {
                console.error('Progress polling query failed:', err);
            }
        }

        function appendConsoleLog(level, message, timestamp) {
            const isIDFC = (state.activeBank === 'IDFC First Bank');
            const consoleBox = isIDFC ? document.getElementById('idfcConsole') : document.getElementById('eqConsole');
            
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
            
            const idfcBtnRun = document.getElementById('idfcBtnRun');
            const idfcBtnCancel = document.getElementById('idfcBtnCancel');
            const idfcProgressContainer = document.getElementById('idfcProgressContainer');
            
            const eqBtnRun = document.getElementById('eqBtnRun');
            const eqBtnCancel = document.getElementById('eqBtnCancel');
            const eqProgressContainer = document.getElementById('eqProgressContainer');
            
            const footerStatus = document.getElementById('footerStatusText');
            
            if (busy) {
                idfcBtnRun.textContent = 'Generating... Please wait';
                idfcBtnRun.disabled = true;
                idfcBtnCancel.disabled = false;
                idfcProgressContainer.classList.remove('hidden');
                
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
                
                const stageText = (state.equitas.stage === 'STAGE 1') ? 'Generate (Stage 1)' : 'Consolidate (Stage 2)';
                eqBtnRun.textContent = stageText;
                eqBtnRun.disabled = false;
                eqBtnCancel.disabled = true;
                
                footerStatus.textContent = 'STATUS: Idle. Ready.';
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

        // STATS AND INSIGHT ANALYTICS
        async function refreshStats() {
            try {
                const resp = await fetch('/api/stats');
                const data = await resp.json();
                
                // Build distribution lists
                const distBox = document.getElementById('statsDistribution');
                const actBox = document.getElementById('statsActivity');
                
                if (data.distribution && Object.keys(data.distribution).length > 0) {
                    let html = '';
                    const total = Object.values(data.distribution).reduce((a, b) => a + b, 0);
                    Object.entries(data.distribution).forEach(([type, count]) => {
                        const pct = Math.round((count / total) * 100);
                        html += `
                            <div class="space-y-1">
                                <div class="flex justify-between text-xs font-semibold text-slate-300">
                                    <span>${type} Audit Batches</span>
                                    <span>${count} (${pct}%)</span>
                                </div>
                                <div class="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-brand-borderLine">
                                    <div class="bg-blue-500 h-full rounded-full dynamic-accent-bg" style="width: ${pct}%"></div>
                                </div>
                            </div>`;
                    });
                    distBox.innerHTML = html;
                } else {
                    distBox.innerHTML = '<div class="text-sm text-slate-500 italic">No activity recorded yet. Run a report batch to build analytics.</div>';
                }
                
                if (data.trend && data.trend.length > 0) {
                    let html = '';
                    data.trend.forEach(([date, count]) => {
                        html += `
                            <div class="flex justify-between items-center py-2 border-b border-brand-borderLine text-xs">
                                <span class="text-slate-400 font-mono">${date}</span>
                                <span class="bg-blue-500/10 text-blue-400 font-bold px-2.5 py-1 rounded border border-blue-500/20 dynamic-accent-fg">${count} runs</span>
                            </div>`;
                    });
                    actBox.innerHTML = html;
                } else {
                    actBox.innerHTML = '<div class="text-sm text-slate-500 italic">No activity logs recorded.</div>';
                }
                
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
                alert('Output naming convention pattern saved successfully!');
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
                    alert('Recent file cache links cleared.');
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
                    alert('Database audit logs history purged completely.');
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
                    statusText.textContent = `✓ Audit Engine Elite is fully up-to-date (${data.current || 'v5.2.145'}).`;
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
                alert('Applying update... The application will restart automatically.');
            } catch (err) {
                console.error(err);
            }
        }

        function dismissUpdateBanner() {
            document.getElementById('updateBanner').classList.add('hidden');
        }
    </script>
</body>
</html>
"""
