export const listApiPaths = {
  aiImagesStart: (wordListId, allowPaid = false) =>
    `/api/vue/lists/${wordListId}/ai-images/start${allowPaid ? "?allow_paid=1" : ""}`,
  aiImagesStatus: (wordListId, jobId) => `/api/vue/lists/${wordListId}/ai-images/${jobId}`,
  batchImages: () => "/api/vue/lists/batch-images",
  createGroup: () => "/api/vue/lists/groups",
  createWord: (wordListId) => `/api/vue/lists/${wordListId}/words`,
  wordCandidates: (wordListId, query) => `/api/vue/lists/${wordListId}/words/candidates?q=${encodeURIComponent(query || "")}`,
  delete: (wordListId) => `/api/vue/lists/${wordListId}/delete`,
  deleteGroup: (groupId) => `/api/vue/lists/groups/${groupId}/delete`,
  moveToGroup: (wordListId) => `/api/vue/lists/${wordListId}/group`,
  rename: (wordListId) => `/api/vue/lists/${wordListId}/rename`,
  reorder: () => "/api/vue/lists/reorder",
  syncImagesStart: (wordListId) => `/api/vue/lists/${wordListId}/sync-images/start`,
  syncImagesStatus: (wordListId, jobId) => `/api/vue/lists/${wordListId}/sync-images/${jobId}`,
  upload: () => "/api/vue/upload",
  uploadOptions: () => "/api/vue/upload/options",
};
