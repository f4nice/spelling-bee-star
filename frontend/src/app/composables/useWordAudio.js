import { ref } from "vue";
import { useAudioPlayback } from "../../shared/useAudioPlayback.js";
import { chooseWordAudioOption, updateWordAudioOptions } from "../wordAudioChoiceBindings.js";
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
    await updateWordAudioOptions({ wordId: data.value.word.id, audioOptions, accent });
  }

  async function chooseAudio(accent, url) {
    await chooseWordAudioOption({ wordId: data.value.word.id, accent, url, loadRoute });
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
