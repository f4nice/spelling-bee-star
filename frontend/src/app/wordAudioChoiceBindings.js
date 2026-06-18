import { loadWordAudioOptions, saveWordAudioChoice } from "./wordAudioActions.js";

export async function updateWordAudioOptions({ wordId, audioOptions, accent }) {
  audioOptions.value[accent] = await loadWordAudioOptions({ wordId, accent });
}

export async function chooseWordAudioOption({ wordId, accent, url, loadRoute }) {
  await saveWordAudioChoice({ wordId, accent, url });
  await loadRoute();
}
