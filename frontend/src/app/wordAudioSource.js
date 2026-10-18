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

export function wordAudioCandidates(data) {
  const word = String(data?.word?.word || "");
  const preferred = preferredWordAudioAccent(data);
  const accents = preferred === "gb" ? ["gb", "us"] : ["us", "gb"];
  const local = accents
    .map((accent) => ({
      accent,
      source: resolveWordAudioSource(data, accent),
      lang: accent === "gb" ? "en-GB" : "en-US",
    }))
    .filter((candidate) => candidate.source.startsWith("/media/audio/"));
  const tts = accents.map((accent) => ({
    accent,
    source: `/tts?word=${encodeURIComponent(word)}&accent=${accent}&v=2`,
    lang: accent === "gb" ? "en-GB" : "en-US",
  }));
  return [...local, ...tts].filter((candidate, index, all) => (
    candidate.source && all.findIndex((item) => item.source === candidate.source) === index
  ));
}
