export const challengeApiPaths = {
  answer: (wordListId) => `/api/challenge/${wordListId}/answer`,
  state: (wordListId, params) => `/api/challenge/${wordListId}/state?${params.toString()}`,
};
