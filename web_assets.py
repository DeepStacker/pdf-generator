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
    <!-- ZERO EXTERNAL DEPENDENCIES - 100% Offline / Air-gapped compatible -->
    <style>
        /* ===== RESET & BASE ===== */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif;
            line-height: 1.5; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
        }
        h1, h2, h3, .logo-font {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-weight: 700;
        }
        /* Custom scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #0B0F19; }
        ::-webkit-scrollbar-thumb { background: #1E293B; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }

        /* ===== LAYOUT ===== */
        .block { display: block; }
        .hidden { display: none !important; }
        .flex { display: flex; }
        .grid { display: grid; }
        .fixed { position: fixed; }
        .absolute { position: absolute; }
        .relative { position: relative; }
        .flex-1 { flex: 1 1 0%; }
        .flex-col { flex-direction: column; }
        .flex-shrink-0 { flex-shrink: 0; }
        .items-center { align-items: center; }
        .items-end { align-items: flex-end; }
        .justify-between { justify-content: space-between; }
        .justify-center { justify-content: center; }
        .justify-end { justify-content: flex-end; }
        .overflow-hidden { overflow: hidden; }
        .overflow-visible { overflow: visible; }
        .overflow-x-auto { overflow-x: auto; }
        .overflow-y-auto { overflow-y: auto; }
        .min-w-0 { min-width: 0; }
        .inset-0 { top: 0; right: 0; bottom: 0; left: 0; }
        .inset-y-0 { top: 0; bottom: 0; }
        .left-0 { left: 0; }
        .right-0 { right: 0; }
        .z-50 { z-index: 50; }

        /* ===== GRID ===== */
        .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .grid-cols-7 { grid-template-columns: repeat(7, minmax(0, 1fr)); }
        .col-span-7 { grid-column: span 7 / span 7; }
        .gap-2 { gap: 0.5rem; }
        .gap-4 { gap: 1rem; }
        .gap-6 { gap: 1.5rem; }
        .gap-8 { gap: 2rem; }

        /* ===== SIZING ===== */
        .h-full { height: 100%; }
        .h-2 { height: 0.5rem; }
        .h-2\\.5 { height: 0.625rem; }
        .h-3 { height: 0.75rem; }
        .h-4 { height: 1rem; }
        .h-5 { height: 1.25rem; }
        .h-8 { height: 2rem; }
        .h-10 { height: 2.5rem; }
        .h-20 { height: 5rem; }
        .h-44 { height: 11rem; }
        .h-52 { height: 13rem; }
        .h-56 { height: 14rem; }
        .w-3 { width: 0.75rem; }
        .w-4 { width: 1rem; }
        .w-5 { width: 1.25rem; }
        .w-8 { width: 2rem; }
        .w-20 { width: 5rem; }
        .w-44 { width: 11rem; }
        .w-64 { width: 16rem; }
        .w-2\\.5 { width: 0.625rem; }
        .w-full { width: 100%; }
        .w-max { width: max-content; }
        .max-w-lg { max-width: 32rem; }
        .max-w-\\[200px\\] { max-width: 200px; }
        .max-w-\\[250px\\] { max-width: 250px; }

        /* ===== SPACING ===== */
        .p-1 { padding: 0.25rem; }
        .p-1\\.5 { padding: 0.375rem; }
        .p-3 { padding: 0.75rem; }
        .p-4 { padding: 1rem; }
        .p-5 { padding: 1.25rem; }
        .p-6 { padding: 1.5rem; }
        .px-2 { padding-left: 0.5rem; padding-right: 0.5rem; }
        .px-2\\.5 { padding-left: 0.625rem; padding-right: 0.625rem; }
        .px-3 { padding-left: 0.75rem; padding-right: 0.75rem; }
        .px-4 { padding-left: 1rem; padding-right: 1rem; }
        .px-5 { padding-left: 1.25rem; padding-right: 1.25rem; }
        .px-6 { padding-left: 1.5rem; padding-right: 1.5rem; }
        .px-10 { padding-left: 2.5rem; padding-right: 2.5rem; }
        .py-0\\.5 { padding-top: 0.125rem; padding-bottom: 0.125rem; }
        .py-1 { padding-top: 0.25rem; padding-bottom: 0.25rem; }
        .py-1\\.5 { padding-top: 0.375rem; padding-bottom: 0.375rem; }
        .py-2 { padding-top: 0.5rem; padding-bottom: 0.5rem; }
        .py-2\\.5 { padding-top: 0.625rem; padding-bottom: 0.625rem; }
        .py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
        .py-3\\.5 { padding-top: 0.875rem; padding-bottom: 0.875rem; }
        .py-4 { padding-top: 1rem; padding-bottom: 1rem; }
        .py-5 { padding-top: 1.25rem; padding-bottom: 1.25rem; }
        .py-6 { padding-top: 1.5rem; padding-bottom: 1.5rem; }
        .py-8 { padding-top: 2rem; padding-bottom: 2rem; }
        .pt-2 { padding-top: 0.5rem; }
        .pt-4 { padding-top: 1rem; }
        .pb-2 { padding-bottom: 0.5rem; }
        .pb-4 { padding-bottom: 1rem; }
        .pl-3 { padding-left: 0.75rem; }
        .pl-10 { padding-left: 2.5rem; }
        .pr-4 { padding-right: 1rem; }
        .mt-1 { margin-top: 0.25rem; }
        .mt-2 { margin-top: 0.5rem; }
        .mb-1 { margin-bottom: 0.25rem; }
        .mb-2 { margin-bottom: 0.5rem; }
        .mb-6 { margin-bottom: 1.5rem; }

        /* ===== SPACE-X / SPACE-Y ===== */
        .space-x-1 > :not([hidden]) ~ :not([hidden]) { margin-left: 0.25rem; }
        .space-x-1\\.5 > :not([hidden]) ~ :not([hidden]) { margin-left: 0.375rem; }
        .space-x-2 > :not([hidden]) ~ :not([hidden]) { margin-left: 0.5rem; }
        .space-x-3 > :not([hidden]) ~ :not([hidden]) { margin-left: 0.75rem; }
        .space-x-4 > :not([hidden]) ~ :not([hidden]) { margin-left: 1rem; }
        .space-x-6 > :not([hidden]) ~ :not([hidden]) { margin-left: 1.5rem; }
        .space-x-8 > :not([hidden]) ~ :not([hidden]) { margin-left: 2rem; }
        .space-y-1 > :not([hidden]) ~ :not([hidden]) { margin-top: 0.25rem; }
        .space-y-1\\.5 > :not([hidden]) ~ :not([hidden]) { margin-top: 0.375rem; }
        .space-y-2 > :not([hidden]) ~ :not([hidden]) { margin-top: 0.5rem; }
        .space-y-3 > :not([hidden]) ~ :not([hidden]) { margin-top: 0.75rem; }
        .space-y-4 > :not([hidden]) ~ :not([hidden]) { margin-top: 1rem; }
        .space-y-5 > :not([hidden]) ~ :not([hidden]) { margin-top: 1.25rem; }
        .space-y-6 > :not([hidden]) ~ :not([hidden]) { margin-top: 1.5rem; }

        /* ===== DIVIDE ===== */
        .divide-y > :not([hidden]) ~ :not([hidden]) { border-top-width: 1px; border-top-style: solid; }
        .divide-brand-borderLine > :not([hidden]) ~ :not([hidden]) { border-color: #1E293B; }

        /* ===== TYPOGRAPHY ===== */
        .text-\\[9px\\] { font-size: 9px; }
        .text-\\[10px\\] { font-size: 10px; }
        .text-\\[11px\\] { font-size: 11px; }
        .text-xs { font-size: 0.75rem; line-height: 1rem; }
        .text-sm { font-size: 0.875rem; line-height: 1.25rem; }
        .text-base { font-size: 1rem; line-height: 1.5rem; }
        .text-lg { font-size: 1.125rem; line-height: 1.75rem; }
        .text-2xl { font-size: 1.5rem; line-height: 2rem; }
        .text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
        .font-sans { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .font-mono { font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace; }
        .font-semibold { font-weight: 600; }
        .font-bold { font-weight: 700; }
        .font-extrabold { font-weight: 800; }
        .italic { font-style: italic; }
        .uppercase { text-transform: uppercase; }
        .tracking-tight { letter-spacing: -0.025em; }
        .tracking-wider { letter-spacing: 0.05em; }
        .tracking-widest { letter-spacing: 0.1em; }
        .leading-none { line-height: 1; }
        .text-left { text-align: left; }
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .whitespace-nowrap { white-space: nowrap; }

        /* ===== TEXT COLORS ===== */
        .text-white { color: #ffffff; }
        .text-slate-100 { color: #f1f5f9; }
        .text-slate-200 { color: #e2e8f0; }
        .text-slate-300 { color: #cbd5e1; }
        .text-slate-400 { color: #94a3b8; }
        .text-slate-500 { color: #64748b; }
        .text-slate-600 { color: #475569; }
        .text-slate-700 { color: #334155; }
        .text-blue-400 { color: #60a5fa; }
        .text-blue-500 { color: #3b82f6; }
        .text-amber-400 { color: #fbbf24; }
        .text-amber-500 { color: #f59e0b; }
        .text-emerald-200 { color: #a7f3d0; }
        .text-emerald-400 { color: #34d399; }
        .text-emerald-700 { color: #047857; }
        .text-rose-400 { color: #fb7185; }
        .text-rose-500 { color: #f43f5e; }
        .text-sky-400 { color: #38bdf8; }
        .text-indigo-400 { color: #818cf8; }
        .text-brand-idfc { color: #2563EB; }

        /* ===== BACKGROUND COLORS ===== */
        .bg-white { background-color: #ffffff; }
        .bg-black\\/60 { background-color: rgba(0,0,0,0.6); }
        .bg-slate-800 { background-color: #1e293b; }
        .bg-slate-900 { background-color: #0f172a; }
        .bg-slate-900\\/30 { background-color: rgba(15,23,42,0.3); }
        .bg-slate-950 { background-color: #020617; }
        .bg-slate-950\\/30 { background-color: rgba(2,6,23,0.3); }
        .bg-slate-950\\/40 { background-color: rgba(2,6,23,0.4); }
        .bg-blue-500 { background-color: #3b82f6; }
        .bg-blue-500\\/10 { background-color: rgba(59,130,246,0.1); }
        .bg-blue-600 { background-color: #2563eb; }
        .bg-amber-500 { background-color: #f59e0b; }
        .bg-amber-500\\/10 { background-color: rgba(245,158,11,0.1); }
        .bg-amber-600 { background-color: #d97706; }
        .bg-emerald-500\\/10 { background-color: rgba(16,185,129,0.1); }
        .bg-emerald-600 { background-color: #059669; }
        .bg-emerald-950\\/20 { background-color: rgba(2,44,34,0.2); }
        .bg-rose-600 { background-color: #e11d48; }
        .bg-rose-950\\/20 { background-color: rgba(76,5,25,0.2); }
        .bg-indigo-500\\/10 { background-color: rgba(99,102,241,0.1); }
        .bg-brand-slateBlack { background-color: #0B0F19; }
        .bg-brand-panelBg { background-color: #162032; }
        .bg-brand-termBg { background-color: #050811; }

        /* ===== BORDERS ===== */
        .border { border-width: 1px; border-style: solid; border-color: #1E293B; }
        .border-b { border-bottom-width: 1px; border-bottom-style: solid; }
        .border-t { border-top-width: 1px; border-top-style: solid; }
        .border-r { border-right-width: 1px; border-right-style: solid; }
        .border-l-4 { border-left-width: 4px; border-left-style: solid; }
        .border-brand-borderLine { border-color: #1E293B; }
        .border-blue-500 { border-color: #3b82f6; }
        .border-blue-500\\/20 { border-color: rgba(59,130,246,0.2); }
        .border-amber-500\\/20 { border-color: rgba(245,158,11,0.2); }
        .border-emerald-500\\/20 { border-color: rgba(16,185,129,0.2); }
        .border-emerald-900\\/30 { border-color: rgba(6,78,59,0.3); }
        .border-rose-900\\/30 { border-color: rgba(136,19,55,0.3); }
        .border-indigo-500\\/20 { border-color: rgba(99,102,241,0.2); }
        .border-collapse { border-collapse: collapse; }

        /* ===== BORDER RADIUS ===== */
        .rounded { border-radius: 0.25rem; }
        .rounded-md { border-radius: 0.375rem; }
        .rounded-lg { border-radius: 0.5rem; }
        .rounded-xl { border-radius: 0.75rem; }
        .rounded-2xl { border-radius: 1rem; }
        .rounded-full { border-radius: 9999px; }

        /* ===== SHADOWS ===== */
        .shadow-sm { box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); }
        .shadow-md { box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1); }
        .shadow-xl { box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1); }
        .shadow-inner { box-shadow: inset 0 2px 4px 0 rgba(0,0,0,0.05); }

        /* ===== OPACITY ===== */
        .opacity-25 { opacity: 0.25; }
        .opacity-75 { opacity: 0.75; }

        /* ===== TRANSFORMS ===== */
        .transform { transform: translateX(0); }
        .scale-95 { transform: scale(0.95); }
        .-rotate-90 { transform: rotate(-90deg); }

        /* ===== TRANSITIONS ===== */
        .transition { transition-property: color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter; transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1); transition-duration: 150ms; }
        .transition-all { transition-property: all; transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1); transition-duration: 150ms; }
        .transition-transform { transition-property: transform; transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1); transition-duration: 150ms; }
        .duration-200 { transition-duration: 200ms; }
        .duration-300 { transition-duration: 300ms; }
        .duration-500 { transition-duration: 500ms; }

        /* ===== ANIMATIONS ===== */
        @keyframes pulse { 50% { opacity: .5; } }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        .animate-spin { animation: spin 1s linear infinite; }
        .animate-fade-in { animation: fadeIn 0.3s ease-out forwards; }

        /* ===== INTERACTIVITY ===== */
        .cursor-pointer { cursor: pointer; }
        .pointer-events-none { pointer-events: none; }
        .appearance-none { appearance: none; -webkit-appearance: none; }
        .backdrop-blur-sm { backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); }

        /* ===== HOVER STATES ===== */
        .hover\\:bg-slate-100:hover { background-color: #f1f5f9; }
        .hover\\:bg-slate-700:hover { background-color: #334155; }
        .hover\\:bg-slate-900:hover { background-color: #0f172a; }
        .hover\\:bg-slate-900\\/30:hover { background-color: rgba(15,23,42,0.3); }
        .hover\\:bg-blue-500:hover { background-color: #3b82f6; }
        .hover\\:bg-amber-500:hover { background-color: #f59e0b; }
        .hover\\:bg-rose-500:hover { background-color: #f43f5e; }
        .hover\\:bg-rose-900:hover { background-color: #881337; }
        .hover\\:text-white:hover { color: #ffffff; }
        .hover\\:border-slate-500:hover { border-color: #64748b; }

        /* ===== FOCUS STATES ===== */
        .focus\\:outline-none:focus { outline: 2px solid transparent; outline-offset: 2px; }
        .focus\\:border-blue-500:focus { border-color: #3b82f6; }
        .focus\\:ring-0:focus { box-shadow: 0 0 0 0px transparent; }

        /* ===== DISABLED STATES ===== */
        .disabled\\:opacity-40:disabled { opacity: 0.4; }
        .disabled\\:pointer-events-none:disabled { pointer-events: none; }

        /* ===== INLINE SVG ICON SIZING (replaces Lucide CSS) ===== */
        svg.icon { display: inline-block; vertical-align: middle; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
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
                        <svg class="icon w-8 h-8 text-blue-500 logo-icon" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
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
                            <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>
                        </div>
                    </div>
                </div>

                <!-- Navigation Links -->
                <nav class="px-2 space-y-1">
                    <button onclick="switchTab('PROCESS')" id="tabBtn-PROCESS" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 bg-brand-panelBg text-white border-l-4 border-blue-500 nav-btn">
                        <svg class="icon w-4 h-4" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        <span>New Batch</span>
                    </button>
                    <button onclick="switchTab('STATS')" id="tabBtn-STATS" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn">
                        <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>
                        <span>Analytics</span>
                    </button>
                    <button onclick="switchTab('HISTORY')" id="tabBtn-HISTORY" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn">
                        <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
                        <span>History</span>
                    </button>
                    <button onclick="switchTab('SETTINGS')" id="tabBtn-SETTINGS" class="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-slate-400 hover:bg-slate-900 hover:text-white nav-btn">
                        <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
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
                    <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="M12 17V3"/><path d="m6 11 6 6 6-6"/><path d="M19 21H5"/></svg>
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
                            <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>
                            <span id="idfcPreviewText">File loaded successfully</span>
                        </div>

                        <!-- Excel Preview Grid (Collapsible) -->
                        <div id="idfcGridContainer" class="hidden space-y-3">
                            <button onclick="togglePreviewGrid('idfc')" class="flex items-center space-x-2 text-xs font-bold text-slate-400 hover:text-white transition">
                                <svg id="idfcGridIcon" class="icon w-4 h-4 transition-transform duration-200" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>
                                <span>Preview Gold Loan Spreadsheet Records (First 5 Rows)</span>
                            </button>
                            <div id="idfcGridWrapper" class="hidden overflow-x-auto rounded-xl border border-brand-borderLine bg-slate-950/40 shadow-inner">
                                <table class="w-full text-left border-collapse text-[10px] font-mono whitespace-nowrap">
                                    <thead>
                                        <tr id="idfcGridHeader" class="bg-slate-900 border-b border-brand-borderLine text-slate-500 uppercase tracking-wider font-sans font-bold">
                                            <!-- Dynamic headers -->
                                        </tr>
                                    </thead>
                                    <tbody id="idfcGridBody" class="divide-y divide-brand-borderLine text-slate-300">
                                        <!-- Dynamic rows -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Column Mapper Assistant (Collapsible) -->
                        <div id="idfcMapperContainer" class="hidden space-y-3 p-4 bg-slate-900/30 border border-brand-borderLine rounded-xl">
                            <span class="block text-xs font-bold text-slate-400 uppercase tracking-wider">Column Mapping Assistant</span>
                            <p class="text-[10px] text-slate-500">Gold loan audit engine columns mapped automatically. Adjust below if necessary:</p>
                            <div class="grid grid-cols-2 gap-4 text-xs">
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">Prospect Number Key</label>
                                    <select id="idfcMap-prospect" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">CUID (Customer ID) Key</label>
                                    <select id="idfcMap-cuid" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">Tare Weight Key</label>
                                    <select id="idfcMap-tare" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">Branch Name Key</label>
                                    <select id="idfcMap-branch" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                            </div>
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

                        <!-- Progress indicator (Circular Gauge) -->
                        <div id="idfcProgressContainer" class="hidden bg-slate-950/30 border border-brand-borderLine rounded-xl p-5 flex items-center justify-between shadow-inner">
                            <div class="flex items-center space-x-6">
                                <!-- Circular Gauge Ring -->
                                <div class="relative w-20 h-20 flex-shrink-0">
                                    <svg class="w-full h-full transform -rotate-90">
                                        <!-- Track Ring -->
                                        <circle cx="40" cy="40" r="34" stroke-width="6" stroke="#1E293B" fill="transparent"/>
                                        <!-- Active Progress Ring -->
                                        <circle id="idfcProgressRing" cx="40" cy="40" r="34" stroke-width="6" stroke="#2563EB" fill="transparent"
                                                stroke-dasharray="213.6" stroke-dashoffset="213.6" stroke-linecap="round" class="transition-all duration-300 dynamic-accent-stroke"/>
                                    </svg>
                                    <span id="idfcProgressPct" class="absolute inset-0 flex items-center justify-center text-sm font-extrabold text-white font-mono">0%</span>
                                </div>
                                <div class="space-y-1">
                                    <span id="idfcProgressBranch" class="block text-xs font-bold text-slate-200">Initializing thread...</span>
                                    <span id="idfcProgressSpeed" class="block text-[10px] text-slate-500 font-mono">Speed: Calculating...</span>
                                    <span id="idfcProgressEta" class="block text-[10px] text-emerald-400 font-semibold">ETA: Calculating...</span>
                                </div>
                            </div>
                            <!-- Fluent checklisted status badges -->
                            <div class="flex flex-col space-y-1.5 text-right font-mono text-[9px] text-slate-500">
                                <div class="flex items-center justify-end space-x-1.5" id="idfcStatusBadge-read">
                                    <span>READ spreadsheet</span>
                                    <svg class="icon w-3 h-3 text-slate-600" id="idfcStatusIcon-read" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
                                </div>
                                <div class="flex items-center justify-end space-x-1.5" id="idfcStatusBadge-pdf">
                                    <span>GENERATE gold audits</span>
                                    <svg class="icon w-3 h-3 text-slate-600" id="idfcStatusIcon-pdf" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
                                </div>
                                <div class="flex items-center justify-end space-x-1.5" id="idfcStatusBadge-zip">
                                    <span>COMPRESS packaging</span>
                                    <svg class="icon w-3 h-3 text-slate-600" id="idfcStatusIcon-zip" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
                                </div>
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
                            <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>
                            <span id="eqPreviewText">File loaded successfully</span>
                        </div>

                        <!-- Excel Preview Grid (Collapsible) -->
                        <div id="eqGridContainer" class="hidden space-y-3">
                            <button onclick="togglePreviewGrid('eq')" class="flex items-center space-x-2 text-xs font-bold text-slate-400 hover:text-white transition">
                                <svg id="eqGridIcon" class="icon w-4 h-4 transition-transform duration-200" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>
                                <span>Preview Gold Loan Spreadsheet Records (First 5 Rows)</span>
                            </button>
                            <div id="eqGridWrapper" class="hidden overflow-x-auto rounded-xl border border-brand-borderLine bg-slate-950/40 shadow-inner">
                                <table class="w-full text-left border-collapse text-[10px] font-mono whitespace-nowrap">
                                    <thead>
                                        <tr id="eqGridHeader" class="bg-slate-900 border-b border-brand-borderLine text-slate-500 uppercase tracking-wider font-sans font-bold">
                                            <!-- Dynamic headers -->
                                        </tr>
                                    </thead>
                                    <tbody id="eqGridBody" class="divide-y divide-brand-borderLine text-slate-300">
                                        <!-- Dynamic rows -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Column Mapper Assistant (Collapsible) -->
                        <div id="eqMapperContainer" class="hidden space-y-3 p-4 bg-slate-900/30 border border-brand-borderLine rounded-xl">
                            <span class="block text-xs font-bold text-slate-400 uppercase tracking-wider">Column Mapping Assistant</span>
                            <p class="text-[10px] text-slate-500">Gold loan audit engine columns mapped automatically. Adjust below if necessary:</p>
                            <div class="grid grid-cols-2 gap-4 text-xs">
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">SVS Loan Number Key</label>
                                    <select id="eqMap-svs" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">Branch Code (Sole ID) Key</label>
                                    <select id="eqMap-sole" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">Branch Name Key</label>
                                    <select id="eqMap-branch" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-[10px] font-semibold text-slate-400 mb-1">Loan Number Key</label>
                                    <select id="eqMap-loan" class="w-full bg-slate-950 border border-brand-borderLine rounded px-2 py-1.5 focus:outline-none text-slate-200">
                                    </select>
                                </div>
                            </div>
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
                                        <svg class="icon w-4 h-4" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>
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

                        <!-- Progress indicator (Circular Gauge) -->
                        <div id="eqProgressContainer" class="hidden bg-slate-950/30 border border-brand-borderLine rounded-xl p-5 flex items-center justify-between shadow-inner">
                            <div class="flex items-center space-x-6">
                                <!-- Circular Gauge Ring -->
                                <div class="relative w-20 h-20 flex-shrink-0">
                                    <svg class="w-full h-full transform -rotate-90">
                                        <!-- Track Ring -->
                                        <circle cx="40" cy="40" r="34" stroke-width="6" stroke="#1E293B" fill="transparent"/>
                                        <!-- Active Progress Ring -->
                                        <circle id="eqProgressRing" cx="40" cy="40" r="34" stroke-width="6" stroke="#F59E0B" fill="transparent"
                                                stroke-dasharray="213.6" stroke-dashoffset="213.6" stroke-linecap="round" class="transition-all duration-300 dynamic-accent-stroke"/>
                                    </svg>
                                    <span id="eqProgressPct" class="absolute inset-0 flex items-center justify-center text-sm font-extrabold text-white font-mono">0%</span>
                                </div>
                                <div class="space-y-1">
                                    <span id="eqProgressBranch" class="block text-xs font-bold text-slate-200">Initializing thread...</span>
                                    <span id="eqProgressSpeed" class="block text-[10px] text-slate-500 font-mono">Speed: Calculating...</span>
                                    <span id="eqProgressEta" class="block text-[10px] text-amber-400 font-semibold">ETA: Calculating...</span>
                                </div>
                            </div>
                            <!-- Fluent checklisted status badges -->
                            <div class="flex flex-col space-y-1.5 text-right font-mono text-[9px] text-slate-500">
                                <div class="flex items-center justify-end space-x-1.5" id="eqStatusBadge-read">
                                    <span>READ spreadsheet</span>
                                    <svg class="icon w-3 h-3 text-slate-600" id="eqStatusIcon-read" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
                                </div>
                                <div class="flex items-center justify-end space-x-1.5" id="eqStatusBadge-pdf">
                                    <span>GENERATE gold audits</span>
                                    <svg class="icon w-3 h-3 text-slate-600" id="eqStatusIcon-pdf" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
                                </div>
                                <div class="flex items-center justify-end space-x-1.5" id="eqStatusBadge-zip">
                                    <span>COMPRESS packaging</span>
                                    <svg class="icon w-3 h-3 text-slate-600" id="eqStatusIcon-zip" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
                                </div>
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

                    <!-- Summary Stats Badges row -->
                    <div class="grid grid-cols-3 gap-6">
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-5 flex items-center justify-between shadow-sm">
                            <div>
                                <span class="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Batches Run</span>
                                <strong id="statBadge-totalBatches" class="block text-2xl font-extrabold text-white font-sans mt-1">0</strong>
                            </div>
                            <div class="bg-blue-500/10 text-blue-400 p-3 rounded-lg border border-blue-500/20">
                                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2" /></svg>
                            </div>
                        </div>
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-5 flex items-center justify-between shadow-sm">
                            <div>
                                <span class="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Reports Created</span>
                                <strong id="statBadge-totalPDFs" class="block text-2xl font-extrabold text-white font-sans mt-1">0</strong>
                            </div>
                            <div class="bg-emerald-500/10 text-emerald-400 p-3 rounded-lg border border-emerald-500/20">
                                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                            </div>
                        </div>
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-5 flex items-center justify-between shadow-sm">
                            <div>
                                <span class="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Unique Excel Files</span>
                                <strong id="statBadge-totalExcels" class="block text-2xl font-extrabold text-white font-sans mt-1">0</strong>
                            </div>
                            <div class="bg-indigo-500/10 text-indigo-400 p-3 rounded-lg border border-indigo-500/20">
                                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                            </div>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-8">
                        <!-- Left card: Donut Share Distribution -->
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-6">
                            <div>
                                <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Audit Type Share Distribution</h3>
                                <p class="text-[10px] text-slate-500 mt-1">Relative proportion of audit runs grouped by Bank product type</p>
                            </div>
                            <div class="flex items-center justify-center space-x-8 py-4">
                                <div class="relative w-44 h-44 flex-shrink-0">
                                    <svg viewBox="0 0 100 100" class="w-full h-full transform -rotate-90" id="statsDonutSvg">
                                    </svg>
                                    <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                        <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider leading-none">Share</span>
                                        <span id="statsDonutCenterPct" class="text-lg font-extrabold text-white font-mono mt-1">-</span>
                                    </div>
                                </div>
                                <div id="statsDistribution" class="flex-1 space-y-3">
                                    <div class="text-sm text-slate-500 italic">No activity logs recorded yet.</div>
                                </div>
                            </div>
                        </div>

                        <!-- Right card: Weekly Neon Volume Line Chart -->
                        <div class="bg-brand-panelBg border border-brand-borderLine rounded-xl p-6 space-y-6 flex flex-col justify-between">
                            <div>
                                <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Weekly Batch Volume Trend</h3>
                                <p class="text-[10px] text-slate-500 mt-1">Number of generated worksheet runs over the last 7 active days</p>
                            </div>
                            <div class="w-full h-44 py-2">
                                <svg viewBox="0 0 300 120" class="w-full h-full overflow-visible" id="statsLineSvg">
                                </svg>
                            </div>
                            <div id="statsActivity" class="border-t border-brand-borderLine pt-4 grid grid-cols-7 gap-2 text-center text-[9px] font-semibold text-slate-400 font-mono">
                                <div class="col-span-7 italic text-slate-500 text-center py-4">No recent history</div>
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
                            <svg class="icon w-4 h-4" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
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

        // HEARTBEAT self-termination loop
        setInterval(() => {
            fetch('/api/heartbeat')
                .catch(() => console.warn('Heartbeat server unreachable.'));
        }, 3000);

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

        // SPREADSHEET PREVIEW GRID & DYNAMIC COLUMN MAPPER
        function renderPreviewGrid(prefix, headers, preview) {
            const container = document.getElementById(`${prefix}GridContainer`);
            const headerRow = document.getElementById(`${prefix}GridHeader`);
            const body = document.getElementById(`${prefix}GridBody`);
            
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
                    
                    state.totalBranches = parseInt(data.branches) || 0;
                    state.totalRows = parseInt(data.rows) || 0;
                    
                    const prefix = isIDFC ? 'idfc' : 'eq';
                    renderPreviewGrid(prefix, data.headers, data.preview);
                    populateMapperDropdowns(prefix, data.headers);
                } else {
                    previewBox.classList.add('hidden');
                    validationBox.classList.remove('hidden');
                    validationBox.className = "bg-rose-950/20 border border-rose-900/30 rounded-lg px-4 py-3 text-rose-400 text-xs";
                    validationBox.innerHTML = `<strong>✗ Load Error:</strong> ${data.error || 'Invalid spreadsheet file format.'}`;
                    
                    const prefix = isIDFC ? 'idfc' : 'eq';
                    if (data.headers && data.headers.length > 0 && data.preview && data.preview.length > 0) {
                        renderPreviewGrid(prefix, data.headers, data.preview);
                        populateMapperDropdowns(prefix, data.headers);
                    } else {
                        document.getElementById(`${prefix}GridContainer`).classList.add('hidden');
                        document.getElementById(`${prefix}MapperContainer`).classList.add('hidden');
                    }
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
            state.genStartTime = Date.now();
            
            // UI Toggle to busy
            setUiGeneratingState(true);
            
            // Console clearing and focus
            const consoleBox = isIDFC ? document.getElementById('idfcConsole') : document.getElementById('eqConsole');
            consoleBox.innerHTML = '<div class="text-slate-500">[00:00:00] Initializing generation background worker thread...</div>';
            state.logsCount = 0;
            
            // Gather custom column mappings
            const columnMappings = isIDFC ? {
                prospect: document.getElementById('idfcMap-prospect').value,
                cuid: document.getElementById('idfcMap-cuid').value,
                tare: document.getElementById('idfcMap-tare').value,
                branch: document.getElementById('idfcMap-branch').value
            } : {
                svs: document.getElementById('eqMap-svs').value,
                sole: document.getElementById('eqMap-sole').value,
                branch: document.getElementById('eqMap-branch').value,
                loan: document.getElementById('eqMap-loan').value
            };
            
            // Gather run parameters
            const payload = {
                bank: state.activeBank,
                filepath: file,
                out_path: output,
                auto_open: isIDFC ? document.getElementById('idfcAutoOpen').checked : document.getElementById('eqAutoOpen').checked,
                naming_pattern: document.getElementById('settingsNamingPattern').value || '{branch}_{type}',
                column_mappings: columnMappings,
                
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
                const prefix = isIDFC ? 'idfc' : 'eq';
                
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
                openSummaryModal({
                    title: 'Restarting Audit Engine...',
                    message: 'The backend server is applying the update and restarting. The new version will be active momentarily! You may close this tab.'
                });
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
