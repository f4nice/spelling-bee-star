import { buildChallengeAnswerForm } from './challengeAnswerForm.js';

export const challengeMessages = {
  loadFailed: '加载挑战失败',
  submitFailed: '提交失败',
};

export async function fetchChallengeState(wordListId, params) {
  const response = await fetch(`/api/challenge/${wordListId}/state?${params.toString()}`);
  if (!response.ok) throw new Error(challengeMessages.loadFailed);
  return response.json();
}

export async function postChallengeAnswer({ wordListId, state, spelling }) {
  const form = buildChallengeAnswerForm({ state, spelling });
  const response = await fetch(`/api/challenge/${wordListId}/answer`, {
    method: 'POST',
    body: form,
  });
  if (!response.ok) throw new Error(challengeMessages.submitFailed);
  return response.json();
}
