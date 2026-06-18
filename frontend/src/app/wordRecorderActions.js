import { saveRecordedAudio } from "./wordRecorderApi.js";
import { createSavedRecorderState } from "./wordRecorderState.js";

export async function saveWordRecording({ wordId, recorderState, setRecorderState, loadRoute }) {
  if (!recorderState.blob) return;
  await saveRecordedAudio({ wordId, recorderState });
  setRecorderState(createSavedRecorderState());
  await loadRoute();
}
