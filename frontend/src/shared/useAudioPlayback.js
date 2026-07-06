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

  function playAudio(id, fallbackText = "", lang = "en-US") {
    const audio = document.getElementById(id);
    if (!audio) {
      speakFallback(fallbackText, lang);
      return;
    }
    stopPageAudio(audio);
    if (!audio.readyState) audio.load();
    audio.currentTime = 0;
    audio.play().catch(() => {
      audio.controls = true;
      speakFallback(fallbackText, lang);
    });
  }

  return {
    playAudio,
  };
}
