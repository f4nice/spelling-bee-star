import { onMounted, ref } from 'vue';
import {
  challengeMessages,
  fetchChallengeState,
  postChallengeAnswer,
  postChallengeAudioIssue,
  postChallengeImageIssue,
} from './challengeApi.js';
import { currentChallengeParams, paramsFromChallengeResult, replaceChallengeParams } from './challengeRouteState.js';

export function useChallengeSession(wordListId) {
  const initialParams = currentChallengeParams();
  const state = ref(null);
  const spelling = ref('');
  const loading = ref(true);
  const submitting = ref(false);
  const markingAudioIssue = ref(false);
  const markingImageIssue = ref(false);
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

  async function markAudioIssue(audioIssue) {
    const wordId = state.value?.current_word?.id;
    if (!wordId || markingAudioIssue.value) return;
    markingAudioIssue.value = true;
    errorMessage.value = '';
    try {
      const result = await postChallengeAudioIssue({ wordId, audioIssue });
      if (state.value?.current_word?.id === wordId) {
        state.value.current_word.audio_issue = Boolean(result.audio_issue);
      }
    } catch (error) {
      errorMessage.value = error.message || '音频标记失败';
    } finally {
      markingAudioIssue.value = false;
    }
  }

  async function markImageIssue(imageIssue) {
    const wordId = state.value?.current_word?.id;
    if (!wordId || markingImageIssue.value) return;
    markingImageIssue.value = true;
    errorMessage.value = '';
    try {
      const result = await postChallengeImageIssue({ wordId, imageIssue });
      if (state.value?.current_word?.id === wordId) {
        state.value.current_word.image_issue = Boolean(result.image_issue);
      }
    } catch (error) {
      errorMessage.value = error.message || '图片标记失败';
    } finally {
      markingImageIssue.value = false;
    }
  }

  onMounted(() => loadState());

  return {
    state,
    spelling,
    loading,
    submitting,
    markingAudioIssue,
    markingImageIssue,
    errorMessage,
    wrongAnswer,
    submitSpelling,
    acknowledgeWrongAnswer,
    markAudioIssue,
    markImageIssue,
  };
}
