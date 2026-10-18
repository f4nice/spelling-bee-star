const AUDIO_FIELDS = {
  us: "american_audio_url",
  gb: "british_audio_url",
};

export function resolveWordAudioSource(data, accent) {
  const field = AUDIO_FIELDS[accent];
  if (!field) return "";
  return String(data?.audio_sources?.[accent] || data?.word?.[field] || "").trim();
}
