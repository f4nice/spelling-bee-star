import { ref } from "vue";
import { useAudioPlayback } from "../../shared/useAudioPlayback.js";
import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { createAudioChoiceForm, createAudioOptionsForm } from "../wordAudioForms.js";
import { useWordRecorder } from "./useWordRecorder.js";

export function useWordAudio({ data, loadRoute }) {
  const audioOptions = ref({ us: [], gb: [] });
  const {
    recorderState,
    startRecording,
    stopRecording,
    saveRecording,
  } = useWordRecorder({ data, loadRoute });
  const { playAudio } = useAudioPlayback();

  function resetAudioTools() {
    audioOptions.value = { us: [], gb: [] };
  }

  async function fetchAudioOptions(accent) {
    const form = createAudioOptionsForm(accent);
    const result = await fetchJson(wordApiPaths.audioOptions(data.value.word.id), { method: "POST", body: form });
    audioOptions.value[accent] = result.options || [];
  }

  async function chooseAudio(accent, url) {
    const form = createAudioChoiceForm(accent, url);
    await fetchJson(wordApiPaths.audioChoice(data.value.word.id), { method: "POST", body: form });
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
