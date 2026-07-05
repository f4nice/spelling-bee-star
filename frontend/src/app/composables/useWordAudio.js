import { ref } from "vue";
import { useAudioPlayback } from "../../shared/useAudioPlayback.js";
import {
  chooseWordAudioOption,
  generateDefinitionAudioOption,
  generateWordAiAudioOption,
  updateWordAudioOptions,
  uploadWordAudioOption,
} from "../wordAudioChoiceBindings.js";
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

  async function fetchAudioOptions(accent, source = "dictionary") {
    await updateWordAudioOptions({
      wordId: data.value.word.id,
      audioOptions,
      accent,
      source,
      listId: data.value.navigation?.list_id || "",
    });
  }

  async function chooseAudio(accent, url) {
    await chooseWordAudioOption({ wordId: data.value.word.id, accent, url, loadRoute });
  }

  async function uploadAudio(accent, file) {
    await uploadWordAudioOption({ wordId: data.value.word.id, accent, file, loadRoute });
  }

  async function generateAiAudio(accent, voiceGender = "female", textMode = "word") {
    return generateWordAiAudioOption({ wordId: data.value.word.id, accent, voiceGender, textMode, loadRoute });
  }

  async function generateDefinitionAudio() {
    return generateDefinitionAudioOption({ data });
  }

  return {
    audioOptions,
    recorderState,
    resetAudioTools,
    playAudio,
    fetchAudioOptions,
    chooseAudio,
    uploadAudio,
    generateAiAudio,
    generateDefinitionAudio,
    startRecording,
    stopRecording,
    saveRecording,
  };
}
