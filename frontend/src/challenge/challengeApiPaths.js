export const challengeApiPaths = {
  answer: (wordListId) => `/api/challenge/${wordListId}/answer`,
  audioIssue: (wordId) => `/api/challenge/words/${wordId}/audio-issue`,
  imageIssue: (wordId) => `/api/challenge/words/${wordId}/image-issue`,
  state: (wordListId, params) => `/api/challenge/${wordListId}/state?${params.toString()}`,
};
