import { ref } from "vue";
import { saveRecordedAudio } from "../wordRecorderApi.js";
import { canRecordAudio, createWordRecorderCapture } from "../wordRecorderCapture.js";
import {
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
    await saveRecordedAudio({ wordId: data.value.word.id, recorderState: recorderState.value });
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
