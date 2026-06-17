import { onMounted, ref } from 'vue';
import { buildChallengeAnswerForm } from './challengeAnswerForm.js';

export function useChallengeSession(wordListId) {
  const initialParams = new URLSearchParams(window.location.search);
  const state = ref(null);
  const spelling = ref('');
  const loading = ref(true);
  const submitting = ref(false);
  const errorMessage = ref('');

  async function loadState(params = initialParams) {
    loading.value = true;
    errorMessage.value = '';
    try {
      const response = await fetch(`/api/challenge/${wordListId}/state?${params.toString()}`);
      if (!response.ok) throw new Error('加载挑战失败');
      state.value = await response.json();
      spelling.value = '';
    } catch (error) {
      errorMessage.value = error.message || '加载挑战失败';
    } finally {
      loading.value = false;
    }
  }

  async function submitSpelling() {
    if (!spelling.value.trim() || submitting.value) return;
    submitting.value = true;
    errorMessage.value = '';
    const form = buildChallengeAnswerForm({ state: state.value, spelling: spelling.value });
    try {
      const response = await fetch(`/api/challenge/${wordListId}/answer`, {
        method: 'POST',
        body: form,
      });
      if (!response.ok) throw new Error('提交失败');
      const result = await response.json();
      const nextParams = new URLSearchParams(result.query);
      history.replaceState(null, '', `${window.location.pathname}?${nextParams.toString()}`);
      await loadState(nextParams);
    } catch (error) {
      errorMessage.value = error.message || '提交失败';
    } finally {
      submitting.value = false;
    }
  }

  function stripDigits() {
    spelling.value = spelling.value.replace(/[0-9]/g, '');
  }

  onMounted(() => loadState());

  return {
    state,
    spelling,
    loading,
    submitting,
    errorMessage,
    submitSpelling,
    stripDigits,
  };
}
