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

installSingleAudioPlaybackGuard();

createApp(App).mount('#speakeasy-vue-app');
