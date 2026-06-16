import { ref } from 'vue';
import { fetchJson } from '../utils.js';
import { useWordRecorder } from './useWordRecorder.js';

export function useWordAudio({ data, loadRoute }) {
  const audioOptions = ref({ us: [], gb: [] });
  const {
    recorderState,
    startRecording,
    stopRecording,
    saveRecording,
  } = useWordRecorder({ data, loadRoute });

  function resetAudioTools() {
    audioOptions.value = { us: [], gb: [] };
  }

  function playAudio(id) {
    const audio = document.getElementById(id);
    if (!audio) return;
    audio.load();
    audio.currentTime = 0;
    audio.play().catch(() => {
      audio.controls = true;
    });
  }

  async function fetchAudioOptions(accent) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('accent', accent);
    const result = await fetchJson(`/words/${data.value.word.id}/audio-options`, { method: 'POST', body: form });
    audioOptions.value[accent] = result.options || [];
  }

  async function chooseAudio(accent, url) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('accent', accent);
    form.append('audio_url', url);
    await fetchJson(`/words/${data.value.word.id}/audio-choice`, { method: 'POST', body: form });
    await loadRoute();
  }

  return {
    audioOptions,
    recorderState,
    resetAudioTools,
    playAudio,
    fetchAudioOptions,
    chooseAudio,
    startRecording,
    stopRecording,
    saveRecording,
  };
}
