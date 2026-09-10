import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Installability and an app shell that survives a dropped connection. The
// worker itself is deliberately narrow: it never touches /api/, so nothing a
// customer uploads or downloads is ever put in a browser cache. Registered
// after load so it never competes with the first render for bandwidth.
// isSecureContext rather than a protocol check: it is what the API itself
// requires, and it is true on localhost, so a dev build behaves like the
// deployed one instead of silently skipping registration.
if ('serviceWorker' in navigator && window.isSecureContext) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('Service worker registration failed:', err);
    });
  });
}
