/**
 * Apply a committed word-audio response to the detail payload immediately.
 *
 * The detail page keeps a versioned `audio_sources` map for the <audio>
 * controls, while the editable word object stores the canonical URL.  A
 * successful upload/choice used to update only the latter, so the page kept
 * playing the previous audio until a full reload.  Keep both views in sync
 * after every committed word-audio mutation.
 */
export function applyCommittedWordAudio(data, accent, result) {
  if (!data || !result?.committed || !result.audio_url || !["us", "gb"].includes(accent)) return;

  const audioUrl = result.audio_url;
  data.word = data.word || {};
  if (accent === "gb") data.word.british_audio_url = audioUrl;
  else data.word.american_audio_url = audioUrl;

  data.audio_sources = {
    ...(data.audio_sources || {}),
    [accent]: audioUrl,
  };
}
