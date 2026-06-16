import { ref } from 'vue';
import { fetchJson } from '../utils.js';
import { useWordAudio } from './useWordAudio.js';
import { useWordImages } from './useWordImages.js';

export function useWordDetail({ data, loadRoute }) {
  const wordEdit = ref({});
  const wordSaving = ref('');
  const {
    imageCandidates,
    resetImageTools,
    uploadWordImage,
    findImages,
    chooseNetworkImage,
  } = useWordImages({ data, loadRoute });
  const {
    audioOptions,
    recorderState,
    resetAudioTools,
    playAudio,
    fetchAudioOptions,
    chooseAudio,
    startRecording,
    stopRecording,
    saveRecording,
  } = useWordAudio({ data, loadRoute });

  function resetWordTools() {
    resetImageTools();
    resetAudioTools();
  }

  function setWordEdit(word) {
    wordEdit.value = {
      alternate_spellings: word.alternate_spellings || '',
      english_definition: word.english_definition || '',
      chinese_definition: word.chinese_definition || '',
      english_example: word.english_example || '',
    };
  }

  async function saveWordField(field) {
    wordSaving.value = field;
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('field', field);
    form.append('value', wordEdit.value[field] || '');
    try {
      const result = await fetchJson(`/api/vue/words/${data.value.word.id}/field`, { method: 'POST', body: form });
      data.value.word[field] = result.value;
    } finally {
      wordSaving.value = '';
    }
  }

  async function refreshWord() {
    const form = new FormData();
    form.append('edit_token', '1');
    await fetchJson(`/api/vue/words/${data.value.word.id}/refresh`, { method: 'POST', body: form });
    await loadRoute();
  }

  function wordNavUrl(wordId) {
    const params = new URLSearchParams(window.location.search);
    params.set('edit', '1');
    return `/vue/words/${wordId}?${params.toString()}`;
  }

  function handleWordKeydown(event, route) {
    if (route.name !== 'wordDetail' || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    const active = document.activeElement;
    if (active?.matches('input, textarea, select, button, audio') || active?.isContentEditable) return;
    const nav = data.value?.navigation;
    if (!nav) return;
    window.location.href = wordNavUrl(event.key === 'ArrowLeft' ? nav.previous_word_id : nav.next_word_id);
  }

  return {
    wordEdit,
    wordSaving,
    imageCandidates,
    audioOptions,
    recorderState,
    resetWordTools,
    setWordEdit,
    saveWordField,
    refreshWord,
    uploadWordImage,
    findImages,
    chooseNetworkImage,
    playAudio,
    fetchAudioOptions,
    chooseAudio,
    startRecording,
    stopRecording,
    saveRecording,
    wordNavUrl,
    handleWordKeydown,
  };
}
