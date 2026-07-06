import { fetchJson } from "./utils.js";
import { wordApiPaths } from "./wordApiPaths.js";
import { createAiAudioForm, createAudioChoiceForm, createAudioOptionsForm, createUploadedAudioForm } from "./wordAudioForms.js";

export async function loadWordAudioOptions({ wordId, accent, source = "dictionary", listId = "" }) {
  const form = createAudioOptionsForm(accent, source, listId);
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

export async function generateAiWordAudio({ wordId, accent, voiceGender = "female", textMode = "word" }) {
  const form = createAiAudioForm(accent, voiceGender, textMode);
  return fetchJson(wordApiPaths.aiAudio(wordId), { method: "POST", body: form });
}

export async function generateWordDefinitionAudio({ wordId, listId = "", source = "auto" }) {
  const form = new FormData();
  form.append("edit_token", "1");
  if (listId) form.append("list_id", listId);
  if (source) form.append("source", source);
  return fetchJson(wordApiPaths.definitionAudio(wordId), { method: "POST", body: form });
}

export async function generateWordExampleAudio({ wordId, listId = "" }) {
  const form = new FormData();
  form.append("edit_token", "1");
  if (listId) form.append("list_id", listId);
  return fetchJson(wordApiPaths.exampleAudio(wordId), { method: "POST", body: form });
}
