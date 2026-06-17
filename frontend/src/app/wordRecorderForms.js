export function createRecordedAudioForm({ accent, blob }) {
  const form = new FormData();
  form.append("edit_token", "1");
  form.append("accent", accent);
  form.append("audio_file", blob, `recorded-${accent}.webm`);
  return form;
}
