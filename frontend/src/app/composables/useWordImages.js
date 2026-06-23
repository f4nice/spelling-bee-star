import { ref } from 'vue';
import { fetchJson } from '../utils.js';
import { wordApiPaths } from '../wordApiPaths.js';
import { useWordImageActions } from './useWordImageActions.js';
import { createWordEditTokenForm } from '../wordImageForms.js';

export function useWordImages({ data, loadRoute }) {
  const imageCandidates = ref([]);
  const { uploadWordImage, chooseNetworkImage, generateAiImage } = useWordImageActions({ data, loadRoute });

  function resetImageTools() {
    imageCandidates.value = [];
  }

  async function findImages() {
    const form = createWordEditTokenForm();
    const result = await fetchJson(wordApiPaths.imageCandidates(data.value.word.id), { method: 'POST', body: form });
    imageCandidates.value = result.images || [];
  }

  return {
    imageCandidates,
    resetImageTools,
    uploadWordImage,
    findImages,
    chooseNetworkImage,
    generateAiImage,
  };
}
