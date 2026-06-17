import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { canRecordAudio, createWordRecorderCapture } from "../wordRecorderCapture.js";
import {
  createRecordedAudioForm,
  createReadyRecorderState,
  createRecorderState,
  createRecordingRecorderState,
  createSavedRecorderState,
  createUnsupportedRecorderState,
} from "../wordRecorderState.js";

export function useWordRecorder({ data, loadRoute }) {
  const recorderState = ref(createRecorderState());
  let mediaRecorder = null;

  async function startRecording(accent) {
    if (!canRecordAudio()) {
      recorderState.value = createUnsupportedRecorderState(accent);
      return;
    }

    mediaRecorder = await createWordRecorderCapture({
      onReady: (recording) => {
        recorderState.value = createReadyRecorderState(accent, recording);
      },
    });
    recorderState.value = createRecordingRecorderState(accent);
    mediaRecorder.start();
  }

  function stopRecording() {
    if (mediaRecorder?.state === "recording") mediaRecorder.stop();
  }

  async function saveRecording() {
    if (!recorderState.value.blob) return;
    const form = createRecordedAudioForm(recorderState.value);
    await fetchJson(wordApiPaths.recordedAudio(data.value.word.id), { method: "POST", body: form });
    recorderState.value = createSavedRecorderState();
    await loadRoute();
  }

  return {
    recorderState,
    startRecording,
    stopRecording,
    saveRecording,
  };
}
