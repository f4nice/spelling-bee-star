export function buildChallengeAnswerForm({ state, spelling }) {
  const form = new FormData();
  form.append('action', 'spell');
  form.append('daily_count', String(state.today_challenge.daily_count));
  form.append('start_count', String(state.today_challenge.start_count));
  form.append('session_correct', String(state.today_challenge.correct));
  form.append('session_wrong', String(state.today_challenge.wrong));
  form.append('spelling', spelling);
  if (state.wrong_date) form.append('wrong_date', state.wrong_date);
  return form;
}
