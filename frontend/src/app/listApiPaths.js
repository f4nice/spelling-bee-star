export const listApiPaths = {
  batchImages: () => "/api/vue/lists/batch-images",
  delete: (wordListId) => `/api/vue/lists/${wordListId}/delete`,
  rename: (wordListId) => `/api/vue/lists/${wordListId}/rename`,
  syncImagesStart: (wordListId) => `/api/vue/lists/${wordListId}/sync-images/start`,
  syncImagesStatus: (wordListId, jobId) => `/api/vue/lists/${wordListId}/sync-images/${jobId}`,
  upload: () => "/api/vue/upload",
  uploadOptions: () => "/api/vue/upload/options",
};
