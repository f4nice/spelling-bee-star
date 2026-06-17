import { ref } from 'vue';
import { fetchJson } from '../utils.js';
import { wordApiPaths } from '../wordApiPaths.js';
import { useWordImageActions } from './useWordImageActions.js';

export function useWordImages({ data, loadRoute }) {
  const imageCandidates = ref([]);
  const { uploadWordImage, chooseNetworkImage } = useWordImageActions({ data, loadRoute });

  function resetImageTools() {
    imageCandidates.value = [];
  }

  async function findImages() {
    const form = new FormData();
    form.append('edit_token', '1');
    const result = await fetchJson(wordApiPaths.imageCandidates(data.value.word.id), { method: 'POST', body: form });
    imageCandidates.value = result.images || [];
  }

  return {
    imageCandidates,
    resetImageTools,
    uploadWordImage,
    findImages,
    chooseNetworkImage,
  };
}
