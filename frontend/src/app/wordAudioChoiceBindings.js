import {
  generateAiWordAudio,
  generateWordDefinitionAudio,
  generateWordExampleAudio,
  loadWordAudioOptions,
  saveUploadedWordAudio,
  saveWordAudioChoice,
} from "./wordAudioActions.js";

export async function updateWordAudioOptions({ wordId, audioOptions, accent, source = "dictionary", listId = "" }) {
  audioOptions.value[accent] = await loadWordAudioOptions({ wordId, accent, source, listId });
}

export async function chooseWordAudioOption({ wordId, accent, url, loadRoute }) {
  const result = await saveWordAudioChoice({ wordId, accent, url });
  if (!result?.media_sources) await loadRoute();
  return result;
}

export async function uploadWordAudioOption({ wordId, accent, file, loadRoute }) {
  const result = await saveUploadedWordAudio({ wordId, accent, file });
  if (!result?.media_sources) await loadRoute();
  return result;
}

export async function generateWordAiAudioOption({ wordId, accent, voiceGender, textMode = "word", loadRoute }) {
  const result = await generateAiWordAudio({ wordId, accent, voiceGender, textMode });
  if (result?.committed) await loadRoute();
  return result;
}

export async function generateDefinitionAudioOption({ data, source = "auto" }) {
  const result = await generateWordDefinitionAudio({
    wordId: data.value.word.id,
    listId: data.value.navigation?.list_id || "",
    source,
  });
  if (result?.word) {
    data.value.word = result.word;
  } else if (result?.audio_url) {
    data.value.word.english_definition_audio_url = result.audio_url;
  }
  if (result?.media_sources) data.value.media_sources = result.media_sources;
  return result;
}

export async function generateExampleAudioOption({ data, source = "auto" }) {
  const result = await generateWordExampleAudio({
    wordId: data.value.word.id,
    listId: data.value.navigation?.list_id || "",
    source,
  });
  if (result?.word) {
    data.value.word = result.word;
  } else if (result?.audio_url) {
    data.value.word.english_example_audio_url = result.audio_url;
  }
  if (result?.media_sources) data.value.media_sources = result.media_sources;
  return result;
}
