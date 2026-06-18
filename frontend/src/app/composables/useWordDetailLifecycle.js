import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { createWordEditTokenForm } from "../wordImageForms.js";

export function useWordDetailLifecycle({ data, loadRoute, resetImageTools, resetAudioTools }) {
  function resetWordTools() {
    resetImageTools();
    resetAudioTools();
  }

  async function refreshWord() {
    const form = createWordEditTokenForm();
    await fetchJson(wordApiPaths.refresh(data.value.word.id), { method: "POST", body: form });
    await loadRoute();
  }

  return {
    resetWordTools,
    refreshWord,
  };
}
