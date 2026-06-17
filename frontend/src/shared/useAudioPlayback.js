export function useAudioPlayback() {
  function playAudio(id) {
    const audio = document.getElementById(id);
    if (!audio) return;
    audio.load();
    audio.currentTime = 0;
    audio.play().catch(() => {
      audio.controls = true;
    });
  }

  return {
    playAudio,
  };
}
