import { canRecordAudio, createWordRecorderCapture } from "./wordRecorderCapture.js";
import {
  createReadyRecorderState,
  createRecordingRecorderState,
  createUnsupportedRecorderState,
} from "./wordRecorderState.js";

export async function prepareWordRecorderSession({ accent, setReadyState }) {
  if (!canRecordAudio()) {
    return {
      recorder: null,
      state: createUnsupportedRecorderState(accent),
      canStart: false,
    };
  }

  const recorder = await createWordRecorderCapture({
    onReady: (recording) => {
      setReadyState(createReadyRecorderState(accent, recording));
    },
  });

  return {
    recorder,
    state: createRecordingRecorderState(accent),
    canStart: true,
  };
}

export function stopWordRecorderSession(recorder) {
  if (recorder?.state === "recording") recorder.stop();
}
