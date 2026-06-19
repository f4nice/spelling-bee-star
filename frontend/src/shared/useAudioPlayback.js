export function useAudioPlayback() {
  function speakFallback(text, lang = "en-US") {
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
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
