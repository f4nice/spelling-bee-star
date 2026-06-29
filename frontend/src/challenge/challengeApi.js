import { challengeApiPaths } from "./challengeApiPaths.js";
import { buildChallengeAnswerForm } from "./challengeAnswerForm.js";
import { invalidateApiCacheForMutation } from "../app/apiCache.js";

export const challengeMessages = {
  loadFailed: "加载挑战失败",
  submitFailed: "提交失败",
};

export async function fetchChallengeState(wordListId, params) {
  const url = challengeApiPaths.state(wordListId, params);
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(challengeMessages.loadFailed);
  return response.json();
}

export async function postChallengeAnswer({ wordListId, state, spelling }) {
  const form = buildChallengeAnswerForm({ state, spelling });
  const url = challengeApiPaths.answer(wordListId);
  const response = await fetch(url, {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error(challengeMessages.submitFailed);
  invalidateApiCacheForMutation(url, { wrongDate: state?.wrong_date });
  return response.json();
}
