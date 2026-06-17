import { fetchJson } from "./utils.js";
import { wordApiPaths } from "./wordApiPaths.js";
import { createRecordedAudioForm } from "./wordRecorderForms.js";

export async function saveRecordedAudio({ wordId, recorderState }) {
  const form = createRecordedAudioForm(recorderState);
  await fetchJson(wordApiPaths.recordedAudio(wordId), { method: "POST", body: form });
}
