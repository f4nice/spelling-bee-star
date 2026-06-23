import { generateAiWordAudio, loadWordAudioOptions, saveUploadedWordAudio, saveWordAudioChoice } from "./wordAudioActions.js";

export async function updateWordAudioOptions({ wordId, audioOptions, accent }) {
  audioOptions.value[accent] = await loadWordAudioOptions({ wordId, accent });
}

export async function chooseWordAudioOption({ wordId, accent, url, loadRoute }) {
  await saveWordAudioChoice({ wordId, accent, url });
  await loadRoute();
}

export async function uploadWordAudioOption({ wordId, accent, file, loadRoute }) {
  await saveUploadedWordAudio({ wordId, accent, file });
  await loadRoute();
}

export async function generateWordAiAudioOption({ wordId, accent, voiceGender, loadRoute }) {
  const result = await generateAiWordAudio({ wordId, accent, voiceGender });
  if (result?.committed) await loadRoute();
  return result;
}
