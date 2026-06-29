import { challengeApiPaths } from "./challengeApiPaths.js";
import { buildChallengeAnswerForm } from "./challengeAnswerForm.js";
import { invalidateApiCacheForMutation } from "../app/apiCache.js";

export const challengeMessages = {
  loadFailed: "加载挑战失败",
  submitFailed: "提交失败",
};

async function responseErrorMessage(response, fallback) {
  const status = response.status ? `HTTP ${response.status}` : "网络异常";
  const traceId = response.headers.get("x-speakeasy-trace-id") || "";
  let detail = "";
  try {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const payload = await response.json();
      detail = payload?.detail || payload?.error || "";
    } else {
      detail = await response.text();
    }
  } catch {
    detail = "";
  }
  const cleanDetail = String(detail || "").replace(/\s+/g, " ").trim().slice(0, 120);
  const traceSuffix = traceId && !cleanDetail.includes(traceId) ? `，追踪码：${traceId}` : "";
  return cleanDetail ? `${fallback}（${status}：${cleanDetail}${traceSuffix}）` : `${fallback}（${status}${traceSuffix}）`;
}

export async function fetchChallengeState(wordListId, params) {
  const url = challengeApiPaths.state(wordListId, params);
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(await responseErrorMessage(response, challengeMessages.loadFailed));
  return response.json();
}

export async function postChallengeAnswer({ wordListId, state, spelling }) {
  const form = buildChallengeAnswerForm({ state, spelling });
  const traceId = String(form.get("client_trace_id") || "");
  const url = challengeApiPaths.answer(wordListId);
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      body: form,
    });
  } catch (error) {
    const detail = error?.message ? `：${error.message}` : "";
    const traceSuffix = traceId ? `，追踪码：${traceId}` : "";
    throw new Error(`${challengeMessages.submitFailed}（网络异常${detail}${traceSuffix}）`);
  }
  if (!response.ok) throw new Error(await responseErrorMessage(response, challengeMessages.submitFailed));
  invalidateApiCacheForMutation(url, { wrongDate: state?.wrong_date });
  return response.json();
}
