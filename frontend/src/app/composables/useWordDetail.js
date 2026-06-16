import { fetchJson } from '../utils.js';
import { useWordAudio } from './useWordAudio.js';
import { useWordEditing } from './useWordEditing.js';
import { useWordImages } from './useWordImages.js';
import { useWordNavigation } from './useWordNavigation.js';

export function useWordDetail({ data, loadRoute }) {
  const {
    wordEdit,
    wordSaving,
    setWordEdit,
    saveWordField,
  } = useWordEditing({ data });
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
  const {
    wordNavUrl,
    handleWordKeydown,
  } = useWordNavigation({ data });

  function resetWordTools() {
    resetImageTools();
    resetAudioTools();
  }

  async function refreshWord() {
    const form = new FormData();
    form.append('edit_token', '1');
    await fetchJson(`/api/vue/words/${data.value.word.id}/refresh`, { method: 'POST', body: form });
    await loadRoute();
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
