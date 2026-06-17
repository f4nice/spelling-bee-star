import { ref } from "vue";
import { useAudioPlayback } from "../../shared/useAudioPlayback.js";
import { loadWordAudioOptions, saveWordAudioChoice } from "../wordAudioActions.js";
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
    audioOptions.value[accent] = await loadWordAudioOptions({ wordId: data.value.word.id, accent });
  }

  async function chooseAudio(accent, url) {
    await saveWordAudioChoice({ wordId: data.value.word.id, accent, url });
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
