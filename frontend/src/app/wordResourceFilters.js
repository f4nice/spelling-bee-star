const DICTIONARY_TEXT_FIELDS = [
  "phonetic",
  "part_of_speech",
  "english_definition",
  "chinese_definition",
  "english_example",
];

export function isWordIncomplete(word) {
  return DICTIONARY_TEXT_FIELDS.some((field) => {
    const value = word?.[field];
    return typeof value !== "string" || !value.trim();
  });
}

const resourceFilters = {
  all: () => true,
  incomplete: isWordIncomplete,
  missingImage: (word) => !word?.image_url,
  missingAudio: (word) => !(word?.has_playable_audio || word?.has_audio),
  imageIssue: (word) => Boolean(word?.image_issue),
  audioIssue: (word) => Boolean(word?.audio_issue),
  missingAny: (word) => (
    resourceFilters.missingImage(word)
    || resourceFilters.missingAudio(word)
    || resourceFilters.imageIssue(word)
    || resourceFilters.audioIssue(word)
  ),
};

export function wordMatchesResourceFilter(word, key) {
  const predicate = Object.hasOwn(resourceFilters, key)
    ? resourceFilters[key]
    : resourceFilters.all;
  return predicate(word);
}

export function countWordResources(words = []) {
  const counts = Object.fromEntries(Object.keys(resourceFilters).map((key) => [key, 0]));
  for (const word of words || []) {
    for (const key of Object.keys(counts)) {
      if (wordMatchesResourceFilter(word, key)) counts[key] += 1;
    }
  }
  return counts;
}
