import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { createWordEditTokenForm } from "../wordImageForms.js";
import { invalidateApiCacheForMutation } from "../apiCache.js";
import { requestWordRefresh } from "../wordRefreshRequest.js";

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
    const refreshUrl = wordApiPaths.refresh(wordId);
    return requestWordRefresh({
      request: fetchJson, refreshUrl, detailUrl: `/api/vue/words/${wordId}${query}`, form,
      invalidate: () => invalidateApiCacheForMutation(refreshUrl),
      onWord: (word) => {
        if (data.value.word?.id !== wordId) return;
        data.value = { ...data.value, word: { ...data.value.word, ...word },
          audio_sources: { ...data.value.audio_sources,
            ...(word.american_audio_url ? { us: word.american_audio_url } : {}),
            ...(word.british_audio_url ? { gb: word.british_audio_url } : {}),
          },
        };
      },
      onDetail: (updated) => {
        if (data.value.word?.id === wordId) data.value = updated;
      },
    });
  }

  return {
    resetWordTools,
    refreshWord,
  };
}
