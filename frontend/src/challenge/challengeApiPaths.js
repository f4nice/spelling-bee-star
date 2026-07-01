export const challengeApiPaths = {
  answer: (wordListId) => `/api/challenge/${wordListId}/answer`,
  audioIssue: (wordId) => `/api/challenge/words/${wordId}/audio-issue`,
  state: (wordListId, params) => `/api/challenge/${wordListId}/state?${params.toString()}`,
};
