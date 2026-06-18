import { ref } from "vue";
import { saveWordRecording, startWordRecording } from "../wordRecorderActions.js";
import { createRecorderState } from "../wordRecorderState.js";
import { stopWordRecorderSession } from "../wordRecorderSession.js";

export function useWordRecorder({ data, loadRoute }) {
  const recorderState = ref(createRecorderState());
  let mediaRecorder = null;

  async function startRecording(accent) {
    await startWordRecording({
      accent,
      setRecorderState: (state) => {
        recorderState.value = state;
      },
      setMediaRecorder: (recorder) => {
        mediaRecorder = recorder;
      },
    });
  }

  function stopRecording() {
    stopWordRecorderSession(mediaRecorder);
  }

  async function saveRecording() {
    await saveWordRecording({
      wordId: data.value.word.id,
      recorderState: recorderState.value,
      setRecorderState: (state) => {
        recorderState.value = state;
      },
      loadRoute,
    });
  }

  return {
    recorderState,
    startRecording,
    stopRecording,
    saveRecording,
  };
}
