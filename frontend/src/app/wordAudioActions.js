import { fetchJson } from "./utils.js";
import { wordApiPaths } from "./wordApiPaths.js";
import { createAudioChoiceForm, createAudioOptionsForm } from "./wordAudioForms.js";

export async function loadWordAudioOptions({ wordId, accent }) {
  const form = createAudioOptionsForm(accent);
  const result = await fetchJson(wordApiPaths.audioOptions(wordId), { method: "POST", body: form });
  return result.options || [];
}

export async function saveWordAudioChoice({ wordId, accent, url }) {
  const form = createAudioChoiceForm(accent, url);
  await fetchJson(wordApiPaths.audioChoice(wordId), { method: "POST", body: form });
}
