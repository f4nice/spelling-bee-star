import { ref } from "vue";
import { useAudioPlayback } from "../../shared/useAudioPlayback.js";
import {
  chooseWordAudioOption,
  generateDefinitionAudioOption,
  generateExampleAudioOption,
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
    const result = await chooseWordAudioOption({ wordId: data.value.word.id, accent, url, loadRoute });
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.committed && result?.audio_url) {
      if (accent === "gb") data.value.word.british_audio_url = result.audio_url;
      else data.value.word.american_audio_url = result.audio_url;
    }
    return result;
  }

  async function uploadAudio(accent, file) {
    const result = await uploadWordAudioOption({ wordId: data.value.word.id, accent, file, loadRoute });
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.committed && result?.audio_url) {
      if (accent === "gb") data.value.word.british_audio_url = result.audio_url;
      else data.value.word.american_audio_url = result.audio_url;
    }
    return result;
  }

  async function generateAiAudio(accent, voiceGender = "female", textMode = "word") {
    const result = await generateWordAiAudioOption({ wordId: data.value.word.id, accent, voiceGender, textMode, loadRoute });
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.committed && result?.audio_url) {
      if (accent === "gb") data.value.word.british_audio_url = result.audio_url;
      else data.value.word.american_audio_url = result.audio_url;
    }
    return result;
  }

  async function generateDefinitionAudio(options = {}) {
    return generateDefinitionAudioOption({ data, source: options.source || "auto" });
  }

  async function generateExampleAudio(options = {}) {
    return generateExampleAudioOption({ data, source: options.source || "auto" });
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
    generateExampleAudio,
    startRecording,
    stopRecording,
    saveRecording,
  };
}
