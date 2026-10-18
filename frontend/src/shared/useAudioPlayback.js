export function useAudioPlayback() {
  function stopPageAudio(activeAudio = null) {
    document.querySelectorAll("audio").forEach((audio) => {
      if (audio === activeAudio) return;
      audio.pause();
      audio.currentTime = 0;
    });
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }

  function speakFallback(text, lang = "en-US") {
    if (!text || !window.speechSynthesis) return;
    stopPageAudio();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    window.speechSynthesis.speak(utterance);
  }

  function waitForAudioReady(audio) {
    if (audio.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) return Promise.resolve(true);
    return new Promise((resolve) => {
      let settled = false;
      let timeoutId = null;
      const finish = (ready) => {
        if (settled) return;
        settled = true;
        if (timeoutId) window.clearTimeout(timeoutId);
        audio.removeEventListener("canplay", onReady);
        audio.removeEventListener("loadeddata", onReady);
        audio.removeEventListener("error", onError);
        resolve(ready);
      };
      const onReady = () => finish(true);
      const onError = () => finish(false);
      audio.addEventListener("canplay", onReady, { once: true });
      audio.addEventListener("loadeddata", onReady, { once: true });
      audio.addEventListener("error", onError, { once: true });
      timeoutId = window.setTimeout(() => finish(audio.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA), 6000);
    });
  }

  async function playAudio(id, fallbackText = "", lang = "en-US", options = {}) {
    const fallbackToSpeech = options.fallbackToSpeech !== false;
    const audio = document.getElementById(id);
    if (!audio) {
      if (fallbackToSpeech) speakFallback(fallbackText, lang);
      return false;
    }
    stopPageAudio(audio);
    audio.controls = false;
    audio.load();
    audio.currentTime = 0;
    try {
      await audio.play();
      if (audio.error || audio.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) throw new Error("audio-not-playable");
      return true;
    } catch {
      // Start playback before waiting for canplay so a user click keeps its
      // transient activation on mobile browsers. If the first attempt failed
      // because the resource was still loading, wait once and retry normally.
      const ready = audio.error ? false : await waitForAudioReady(audio);
      if (ready || audio.readyState >= HTMLMediaElement.HAVE_METADATA) {
        try {
          await audio.play();
          if (audio.error || audio.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) throw new Error("audio-not-playable");
          return true;
        } catch {
          // Fall through to speech synthesis below.
        }
      }
      if (fallbackToSpeech) {
        audio.controls = true;
        speakFallback(fallbackText, lang);
      }
      return false;
    }
  }

  return {
    playAudio,
  };
}
