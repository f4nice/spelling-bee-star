export function createAudioOptionsForm(accent) {
  const form = new FormData();
  form.append("edit_token", "1");
  form.append("accent", accent);
  return form;
}

export function createAudioChoiceForm(accent, url) {
  const form = createAudioOptionsForm(accent);
  form.append("audio_url", url);
  return form;
}

export function createUploadedAudioForm(accent, file) {
  const form = createAudioOptionsForm(accent);
  form.append("audio_file", file, file.name || `uploaded-${accent}.webm`);
  return form;
}
