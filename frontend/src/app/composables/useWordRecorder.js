import { ref } from "vue";
import { saveRecordedAudio } from "../wordRecorderApi.js";
import { createRecorderState, createSavedRecorderState } from "../wordRecorderState.js";
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
