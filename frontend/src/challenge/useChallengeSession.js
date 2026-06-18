import { onMounted, ref } from 'vue';
import { challengeMessages, fetchChallengeState, postChallengeAnswer } from './challengeApi.js';
import { currentChallengeParams, paramsFromChallengeResult, replaceChallengeParams } from './challengeRouteState.js';

export function useChallengeSession(wordListId) {
  const initialParams = currentChallengeParams();
  const state = ref(null);
  const spelling = ref('');
  const loading = ref(true);
  const submitting = ref(false);
  const errorMessage = ref('');

  async function loadState(params = initialParams, { showLoading = true } = {}) {
    if (showLoading) loading.value = true;
    errorMessage.value = '';
    try {
      state.value = await fetchChallengeState(wordListId, params);
      spelling.value = '';
    } catch (error) {
      errorMessage.value = error.message || challengeMessages.loadFailed;
    } finally {
      loading.value = false;
    }
  }

  async function submitSpelling() {
    if (!spelling.value.trim() || submitting.value) return;
    submitting.value = true;
    errorMessage.value = '';
    try {
      const result = await postChallengeAnswer({ wordListId, state: state.value, spelling: spelling.value });
      const nextParams = paramsFromChallengeResult(result);
      replaceChallengeParams(nextParams);
      if (result.state) {
        state.value = result.state;
        spelling.value = '';
      } else {
        await loadState(nextParams, { showLoading: false });
      }
    } catch (error) {
      errorMessage.value = error.message || challengeMessages.submitFailed;
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
