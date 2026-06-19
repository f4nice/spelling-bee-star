import { challengeApiPaths } from "./challengeApiPaths.js";
import { buildChallengeAnswerForm } from "./challengeAnswerForm.js";
import { invalidateApiCacheForMutation, readApiCache, writeApiCache } from "../app/apiCache.js";

export const challengeMessages = {
  loadFailed: "加载挑战失败",
  submitFailed: "提交失败",
};

export async function fetchChallengeState(wordListId, params) {
  const url = challengeApiPaths.state(wordListId, params);
  const cached = readApiCache(url);
  if (cached) return cached;

  const response = await fetch(url);
  if (!response.ok) throw new Error(challengeMessages.loadFailed);
  const payload = await response.json();
  writeApiCache(url, payload);
  return payload;
}

export async function postChallengeAnswer({ wordListId, state, spelling }) {
  const form = buildChallengeAnswerForm({ state, spelling });
  const url = challengeApiPaths.answer(wordListId);
  const response = await fetch(url, {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error(challengeMessages.submitFailed);
  invalidateApiCacheForMutation(url);
  return response.json();
}
