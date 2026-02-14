// Register Service Worker ONLY when running as installed PWA (standalone mode).
// In regular browser tabs, unregister any existing SW so updates are instant.
if ('serviceWorker' in navigator) {
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true;

  if (isStandalone) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js', { scope: '/' });
    });
  } else {
    // Clean up: unregister SW in regular browser so cached content doesn't get stale
    navigator.serviceWorker.getRegistrations().then(registrations => {
      registrations.forEach(r => r.unregister());
    });
  }
}
