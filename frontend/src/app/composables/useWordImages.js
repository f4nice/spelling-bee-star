import { ref } from 'vue';
import { fetchJson } from '../utils.js';
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
    const result = await fetchJson(`/api/vue/words/${data.value.word.id}/image-candidates`, { method: 'POST', body: form });
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
