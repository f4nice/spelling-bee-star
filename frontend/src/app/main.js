import { createApp } from 'vue';
import App from './App.vue';

function installSingleAudioPlaybackGuard() {
  window.addEventListener(
    "play",
    (event) => {
      const activeMedia = event.target;
      if (!(activeMedia instanceof HTMLMediaElement)) return;
      document.querySelectorAll("audio, video").forEach((media) => {
        if (media === activeMedia) return;
        media.pause();
        media.currentTime = 0;
      });
      if (window.speechSynthesis) window.speechSynthesis.cancel();
    },
    true,
  );
}

function installAssetLoadRecovery() {
  const shouldRecover = (message) => /Failed to fetch dynamically imported module|Importing a module script failed|Unable to preload CSS/i.test(String(message || ""));
  const recover = () => {
    const key = `speakeasy:asset-reload:${window.location.pathname}`;
    const lastReload = Number(window.sessionStorage.getItem(key) || 0);
    if (Date.now() - lastReload < 30000) return;
    window.sessionStorage.setItem(key, String(Date.now()));
    window.location.reload();
  };

  window.addEventListener("vite:preloadError", (event) => {
    event.preventDefault();
    recover();
  });
  window.addEventListener(
    "error",
    (event) => {
      if (shouldRecover(event.message)) recover();
    },
    true,
  );
  window.addEventListener("unhandledrejection", (event) => {
    if (shouldRecover(event.reason?.message || event.reason)) recover();
  });
}

installSingleAudioPlaybackGuard();
installAssetLoadRecovery();

createApp(App).mount('#speakeasy-vue-app');
