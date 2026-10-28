const FINAL_STATUSES = new Set(["correct", "incorrect", "expired"]);

export function isMathQuestionFinished(question) {
  return FINAL_STATUSES.has(question?.status);
}

export function mathClockAnchor(serverNow, monotonicNow) {
  const serverMs = Date.parse(serverNow || "");
  return { serverMs: Number.isFinite(serverMs) ? serverMs : null, monotonicMs: monotonicNow };
}

export function mathServerTime(anchor, monotonicNow) {
  if (anchor?.serverMs == null) return null;
  return anchor.serverMs + Math.max(0, monotonicNow - anchor.monotonicMs);
}

export function mathSecondsRemaining(question, serverTime) {
  const deadline = Date.parse(question?.deadlineAt || "");
  if (question?.status !== "active" || serverTime == null || !Number.isFinite(deadline)) return 0;
  return Math.max(0, Math.ceil((deadline - serverTime) / 1000));
}

export function mathCountdownLabel(seconds) {
  const safeSeconds = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${String(Math.floor(safeSeconds / 60)).padStart(2, "0")}:${String(safeSeconds % 60).padStart(2, "0")}`;
}

export function validMathAnswer(value) {
  return /^\d{1,6}$/.test(String(value ?? "").trim());
}

export function mathQuestionLabel(question) {
  return { pending: "待开始", active: "作答中", correct: "答对了", incorrect: "未答对", expired: "已超时" }[question?.status] || "待开始";
}

export function currentMathQuestion(payload, selectedId = null) {
  const questions = payload?.questions || [];
  return questions.find((question) => question.id === selectedId)
    || questions.find((question) => question.id === payload?.activeQuestionId)
    || questions.find((question) => question.id === payload?.nextQuestionId)
    || questions.at(-1)
    || null;
}

export function canStartMathQuestion(payload, question) {
  return question?.status === "pending" && question.id === payload?.nextQuestionId && !payload?.activeQuestionId;
}
