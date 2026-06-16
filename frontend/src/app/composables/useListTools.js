import { ref } from 'vue';
import { fetchJson } from '../utils.js';

export function useListTools({ data, go, loadRoute }) {
  const uploadOptions = ref({ word_lists: [] });
  const uploadForm = ref({ word_list_id: '', word_list_name: '', file: null });

  function setUploadOptionsFromCards(cards = []) {
    uploadOptions.value = { word_lists: cards.map((card) => card.list) };
  }

  async function loadUploadOptions() {
    uploadOptions.value = await fetchJson('/api/vue/upload/options');
  }

  async function submitUpload() {
    if (!uploadForm.value.file) return;
    const form = new FormData();
    form.append('file', uploadForm.value.file);
    form.append('word_list_id', uploadForm.value.word_list_id || '');
    form.append('word_list_name', uploadForm.value.word_list_name || '');
    const result = await fetchJson('/api/vue/upload', { method: 'POST', body: form });
    go(`/upload/preview/${result.preview_id}`);
  }

  async function renameList() {
    const form = new FormData();
    form.append('name', data.value.word_list.name);
    await fetchJson(`/lists/${data.value.word_list.id}/rename`, {
      method: 'POST',
      body: form,
      headers: { 'x-requested-with': 'fetch' },
    });
  }

  async function syncListImages() {
    const job = await fetchJson(`/lists/${data.value.word_list.id}/sync-images/start`, { method: 'POST' });
    data.value.sync_job = job;
    const timer = window.setInterval(async () => {
      const next = await fetchJson(`/lists/${data.value.word_list.id}/sync-images/${job.id}`);
      data.value.sync_job = next;
      if (['done', 'failed'].includes(next.status)) {
        window.clearInterval(timer);
        await loadRoute();
      }
    }, 1200);
  }

  return {
    uploadOptions,
    uploadForm,
    setUploadOptionsFromCards,
    loadUploadOptions,
    submitUpload,
    renameList,
    syncListImages,
  };
}
