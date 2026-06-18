import { ref } from "vue";
import { saveWordRecording } from "../wordRecorderActions.js";
import { createRecorderState } from "../wordRecorderState.js";
import { prepareWordRecorderSession, stopWordRecorderSession } from "../wordRecorderSession.js";

export function useWordRecorder({ data, loadRoute }) {
  const recorderState = ref(createRecorderState());
  let mediaRecorder = null;

  async function startRecording(accent) {
    const session = await prepareWordRecorderSession({
      accent,
      setReadyState: (state) => {
        recorderState.value = state;
      },
    });
    recorderState.value = session.state;
    mediaRecorder = session.recorder;
    if (session.canStart) mediaRecorder.start();
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
