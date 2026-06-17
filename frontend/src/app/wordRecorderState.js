import { wordRecorderMessages } from "./wordRecorderMessages.js";

export function createRecorderState({ accent = "", status = "", blob = null, preview = "" } = {}) {
  return { accent, status, blob, preview };
}

export function createUnsupportedRecorderState(accent) {
  return createRecorderState({ accent, status: wordRecorderMessages.unsupported });
}

export function createRecordingRecorderState(accent) {
  return createRecorderState({ accent, status: wordRecorderMessages.recording });
}

export function createReadyRecorderState(accent, { blob, preview }) {
  return createRecorderState({ accent, status: wordRecorderMessages.ready, blob, preview });
}

export function createSavedRecorderState() {
  return createRecorderState({ status: wordRecorderMessages.saved });
}
