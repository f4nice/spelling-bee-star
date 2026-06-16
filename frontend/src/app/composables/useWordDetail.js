import { ref } from 'vue';
import { fetchJson } from '../utils.js';

export function useWordDetail({ data, loadRoute }) {
  const wordEdit = ref({});
  const wordSaving = ref('');
  const imageCandidates = ref([]);
  const audioOptions = ref({ us: [], gb: [] });
  const recorderState = ref({ accent: '', status: '', blob: null, preview: '' });
  let mediaRecorder = null;
  let mediaStream = null;
  let mediaChunks = [];

  function resetWordTools() {
    imageCandidates.value = [];
    audioOptions.value = { us: [], gb: [] };
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

  async function uploadWordImage(file) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('file', file);
    await fetch(`/words/${data.value.word.id}/image`, { method: 'POST', body: form });
    await loadRoute();
  }

  async function findImages() {
    const form = new FormData();
    form.append('edit_token', '1');
    const result = await fetchJson(`/words/${data.value.word.id}/image-candidates`, { method: 'POST', body: form });
    imageCandidates.value = result.images || [];
  }

  async function chooseNetworkImage(url) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('image_url', url);
    await fetchJson(`/words/${data.value.word.id}/network-image`, { method: 'POST', body: form });
    await loadRoute();
  }

  function playAudio(id) {
    const audio = document.getElementById(id);
    if (!audio) return;
    audio.load();
    audio.currentTime = 0;
    audio.play().catch(() => { audio.controls = true; });
  }

  async function fetchAudioOptions(accent) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('accent', accent);
    const result = await fetchJson(`/words/${data.value.word.id}/audio-options`, { method: 'POST', body: form });
    audioOptions.value[accent] = result.options || [];
  }

  async function chooseAudio(accent, url) {
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('accent', accent);
    form.append('audio_url', url);
    await fetchJson(`/words/${data.value.word.id}/audio-choice`, { method: 'POST', body: form });
    await loadRoute();
  }

  async function startRecording(accent) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      recorderState.value = { accent, status: '当前浏览器不支持在线录音，或需要 HTTPS 后才能使用麦克风。', blob: null, preview: '' };
      return;
    }
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaChunks = [];
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data?.size) mediaChunks.push(event.data);
    });
    mediaRecorder.addEventListener('stop', () => {
      const blob = new Blob(mediaChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
      recorderState.value = { accent, status: '录音完成，可以先回听，再确认替换。', blob, preview: URL.createObjectURL(blob) };
      mediaStream?.getTracks().forEach((track) => track.stop());
    });
    recorderState.value = { accent, status: '录音中...', blob: null, preview: '' };
    mediaRecorder.start();
  }

  function stopRecording() {
    if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
  }

  async function saveRecording() {
    if (!recorderState.value.blob) return;
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('accent', recorderState.value.accent);
    form.append('audio_file', recorderState.value.blob, `recorded-${recorderState.value.accent}.webm`);
    await fetchJson(`/words/${data.value.word.id}/recorded-audio`, { method: 'POST', body: form });
    recorderState.value = { accent: '', status: '录音已保存', blob: null, preview: '' };
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
