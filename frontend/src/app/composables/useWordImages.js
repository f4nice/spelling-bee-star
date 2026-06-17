import { ref } from 'vue';
import { fetchJson } from '../utils.js';

export function useWordImages({ data, loadRoute }) {
  const imageCandidates = ref([]);

  function resetImageTools() {
    imageCandidates.value = [];
  }

  async function uploadWordImage(file) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('file', file);
    await fetchJson(`/api/vue/words/${data.value.word.id}/image`, { method: 'POST', body: form });
    await loadRoute();
  }

  async function findImages() {
    const form = new FormData();
    form.append('edit_token', '1');
    const result = await fetchJson(`/api/vue/words/${data.value.word.id}/image-candidates`, { method: 'POST', body: form });
    imageCandidates.value = result.images || [];
  }

  async function chooseNetworkImage(url) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('image_url', url);
    await fetchJson(`/api/vue/words/${data.value.word.id}/network-image`, { method: 'POST', body: form });
    await loadRoute();
  }

  return {
    imageCandidates,
    resetImageTools,
    uploadWordImage,
    findImages,
    chooseNetworkImage,
  };
}
