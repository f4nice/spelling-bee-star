import { onScopeDispose, ref, watch } from "vue";
import { inferImageSourceMeta } from "../mediaSourceLabels.js";

export function useWordImageReplacement({ getWordId, getFile }) {
  const selectedReplacement = ref(null);
  let previewUrl = "";

  function clearPreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = "";
  }

  // A refresh can replace the word object without changing the actual word.
  // Only a real word change should discard a pending replacement.
  watch(getWordId, () => {
    clearPreview();
    selectedReplacement.value = null;
  }, { flush: "sync" });

  watch(getFile, (file) => {
    clearPreview();
    if (file) {
      previewUrl = URL.createObjectURL(file);
      selectedReplacement.value = {
        type: "upload",
        imageUrl: previewUrl,
        label: "上传图片",
        sourceMeta: inferImageSourceMeta({ source: "upload" }, previewUrl),
      };
    } else if (selectedReplacement.value?.type === "upload") {
      selectedReplacement.value = null;
    }
  }, { immediate: true, flush: "sync" });

  onScopeDispose(clearPreview);
  return { selectedReplacement };
}
