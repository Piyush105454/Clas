/**
 * Main PWA initialization script
 * Handles service worker registration and PWA install prompt
 */

// Register Service Worker from root
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js', {
      scope: '/'
    })
    .then((registration) => {
      console.log('[PWA] Service Worker registered successfully:', registration);
      
      // Check for updates periodically
      setInterval(() => {
        registration.update();
      }, 60000); // Check every minute
    })
    .catch((error) => {
      console.error('[PWA] Service Worker registration failed:', error);
    });
  });
}

// Handle PWA Install Prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  console.log('[PWA] Install prompt available');
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  // Stash the event for later use
  deferredPrompt = e;
  
  // Show install button/prompt to user
  showInstallPrompt();
});

window.addEventListener('appinstalled', () => {
  console.log('[PWA] App installed successfully');
  deferredPrompt = null;
  hideInstallPrompt();
});

function showInstallPrompt() {
  // Check if there's a custom install button
  const installButton = document.getElementById('pwa-install-btn');
  if (installButton) {
    installButton.style.display = 'block';
    installButton.addEventListener('click', async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`[PWA] User response to install prompt: ${outcome}`);
        deferredPrompt = null;
      }
    });
  }
}

function hideInstallPrompt() {
  const installButton = document.getElementById('pwa-install-btn');
  if (installButton) {
    installButton.style.display = 'none';
  }
}

// Handle online/offline status
window.addEventListener('online', () => {
  console.log('[PWA] Application is online');
  document.body.classList.remove('offline');
});

window.addEventListener('offline', () => {
  console.log('[PWA] Application is offline');
  document.body.classList.add('offline');
});

// Initial offline status check
if (!navigator.onLine) {
  document.body.classList.add('offline');
}
