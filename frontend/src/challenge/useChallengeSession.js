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
  const wrongAnswer = ref(null);
  let pendingChallengeResult = null;

  function applyChallengeResult(result) {
    const nextParams = paramsFromChallengeResult(result);
    replaceChallengeParams(nextParams);
    if (result.state) {
      state.value = result.state;
      spelling.value = '';
      return;
    }
    return loadState(nextParams, { showLoading: false });
  }

  async function loadState(params = initialParams, { showLoading = true } = {}) {
    if (showLoading) loading.value = true;
    errorMessage.value = '';
    wrongAnswer.value = null;
    pendingChallengeResult = null;
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
      if (result.answer && result.answer.is_correct === false) {
        pendingChallengeResult = result;
        wrongAnswer.value = result.answer;
        return;
      }
      await applyChallengeResult(result);
    } catch (error) {
      errorMessage.value = error.message || challengeMessages.submitFailed;
    } finally {
      submitting.value = false;
    }
  }

  async function acknowledgeWrongAnswer() {
    if (!pendingChallengeResult) return;
    const result = pendingChallengeResult;
    pendingChallengeResult = null;
    wrongAnswer.value = null;
    await applyChallengeResult(result);
  }

  onMounted(() => loadState());

  return {
    state,
    spelling,
    loading,
    submitting,
    errorMessage,
    wrongAnswer,
    submitSpelling,
    acknowledgeWrongAnswer,
  };
}
