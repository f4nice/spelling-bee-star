function challengeTraceId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `chg-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function pageVersionText() {
  const shell = document.querySelector("main.shell");
  return shell?.dataset?.quantRadarPageVersionText || shell?.getAttribute("data-quant-radar-page-version-text") || "";
}

export function buildChallengeAnswerForm({ state, spelling }) {
  const form = new FormData();
  form.append('action', 'spell');
  form.append('daily_count', String(state.today_challenge.daily_count));
  form.append('start_count', String(state.today_challenge.start_count));
  form.append('session_correct', String(state.today_challenge.correct));
  form.append('session_wrong', String(state.today_challenge.wrong));
  form.append('spelling', spelling);
  if (state.current_word?.id) form.append('word_id', String(state.current_word.id));
  if (state.wrong_date) form.append('wrong_date', state.wrong_date);
  form.append('client_trace_id', challengeTraceId());
  form.append('client_page_url', window.location.href);
  form.append('client_page_version', pageVersionText());
  return form;
}
