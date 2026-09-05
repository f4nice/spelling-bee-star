import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { createWordEditTokenForm } from "../wordImageForms.js";

export function useWordDetailLifecycle({ data, loadRoute, resetImageTools, resetAudioTools }) {
  function resetWordTools() {
    resetImageTools();
    resetAudioTools();
  }

  async function refreshWord() {
    const wordId = data.value.word.id;
    const query = window.location.search;
    const form = createWordEditTokenForm();
    if (data.value.navigation?.list_id) {
      form.append("list_id", data.value.navigation.list_id);
    }
    const result = await fetchJson(wordApiPaths.refresh(wordId), { method: "POST", body: form });
    const updated = await fetchJson(`/api/vue/words/${wordId}${query}`, { skipCache: true });
    if (data.value.word?.id === wordId) data.value = updated;
    return result;
  }

  return {
    resetWordTools,
    refreshWord,
  };
}
