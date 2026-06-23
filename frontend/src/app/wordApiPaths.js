export const wordApiPaths = {
  audioOptions: (wordId) => `/api/vue/words/${wordId}/audio-options`,
  audioChoice: (wordId) => `/api/vue/words/${wordId}/audio-choice`,
  aiAudio: (wordId) => `/api/vue/words/${wordId}/ai-audio`,
  aiImage: (wordId) => `/api/vue/words/${wordId}/ai-image`,
  field: (wordId) => `/api/vue/words/${wordId}/field`,
  image: (wordId) => `/api/vue/words/${wordId}/image`,
  imageCandidates: (wordId) => `/api/vue/words/${wordId}/image-candidates`,
  networkImage: (wordId) => `/api/vue/words/${wordId}/network-image`,
  recordedAudio: (wordId) => `/api/vue/words/${wordId}/recorded-audio`,
  refresh: (wordId) => `/api/vue/words/${wordId}/refresh`,
};
