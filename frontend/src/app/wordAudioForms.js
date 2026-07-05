export function createAudioOptionsForm(accent, source = "dictionary", listId = "") {
  const form = new FormData();
  form.append("edit_token", "1");
  form.append("accent", accent);
  form.append("source", source || "dictionary");
  if (listId) form.append("list_id", listId);
  return form;
}

export function createAudioChoiceForm(accent, url) {
  const form = createAudioOptionsForm(accent);
  form.append("audio_url", url);
  return form;
}

export function createAiAudioForm(accent, voiceGender = "female", textMode = "word") {
  const form = createAudioOptionsForm(accent);
  form.append("voice_gender", voiceGender);
  form.append("text_mode", textMode);
  form.append("commit", "0");
  return form;
}

export function createUploadedAudioForm(accent, file) {
  const form = createAudioOptionsForm(accent);
  form.append("audio_file", file, file.name || `uploaded-${accent}.webm`);
  return form;
}
