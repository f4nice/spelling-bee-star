import { challengeApiPaths } from "./challengeApiPaths.js";
import { buildChallengeAnswerForm } from "./challengeAnswerForm.js";

export const challengeMessages = {
  loadFailed: "加载挑战失败",
  submitFailed: "提交失败",
};

export async function fetchChallengeState(wordListId, params) {
  const response = await fetch(challengeApiPaths.state(wordListId, params));
  if (!response.ok) throw new Error(challengeMessages.loadFailed);
  return response.json();
}

export async function postChallengeAnswer({ wordListId, state, spelling }) {
  const form = buildChallengeAnswerForm({ state, spelling });
  const response = await fetch(challengeApiPaths.answer(wordListId), {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error(challengeMessages.submitFailed);
  return response.json();
}
