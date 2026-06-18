import { saveRecordedAudio } from "./wordRecorderApi.js";
import { createSavedRecorderState } from "./wordRecorderState.js";
import { prepareWordRecorderSession } from "./wordRecorderSession.js";

export async function startWordRecording({ accent, setRecorderState, setMediaRecorder }) {
  const session = await prepareWordRecorderSession({
    accent,
    setReadyState: setRecorderState,
  });
  setRecorderState(session.state);
  setMediaRecorder(session.recorder);
  if (session.canStart) session.recorder.start();
}

export async function saveWordRecording({ wordId, recorderState, setRecorderState, loadRoute }) {
  if (!recorderState.blob) return;
  await saveRecordedAudio({ wordId, recorderState });
  setRecorderState(createSavedRecorderState());
  await loadRoute();
}
