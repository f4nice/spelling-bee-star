import { fetchJson } from "./utils.js";
import { wordApiPaths } from "./wordApiPaths.js";
import { createAudioChoiceForm, createAudioOptionsForm, createUploadedAudioForm } from "./wordAudioForms.js";

export async function loadWordAudioOptions({ wordId, accent }) {
  const form = createAudioOptionsForm(accent);
  const result = await fetchJson(wordApiPaths.audioOptions(wordId), { method: "POST", body: form });
  if (result.error) throw new Error(result.error);
  return result.options || [];
}

export async function saveWordAudioChoice({ wordId, accent, url }) {
  const form = createAudioChoiceForm(accent, url);
  await fetchJson(wordApiPaths.audioChoice(wordId), { method: "POST", body: form });
}

export async function saveUploadedWordAudio({ wordId, accent, file }) {
  const form = createUploadedAudioForm(accent, file);
  await fetchJson(wordApiPaths.recordedAudio(wordId), { method: "POST", body: form });
}
