const AUDIO_FIELDS = {
  us: "american_audio_url",
  gb: "british_audio_url",
};

export function resolveWordAudioSource(data, accent) {
  const field = AUDIO_FIELDS[accent];
  if (!field) return "";
  return String(data?.audio_sources?.[accent] || data?.word?.[field] || "").trim();
}

export function preferredWordAudioAccent(data) {
  const sources = data?.audio_sources || {};
  const american = String(data?.word?.american_audio_url || "");
  const british = String(data?.word?.british_audio_url || "");
  if (american.startsWith("/media/audio/") && sources.us) return "us";
  if (british.startsWith("/media/audio/") && sources.gb) return "gb";
  if (sources.us) return "us";
  if (sources.gb) return "gb";
  return "us";
}
