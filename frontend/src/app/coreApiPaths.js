export const coreApiPaths = {
  importPreview: () => "/api/vue/import-preview",
  importPreviewStatus: (jobId) => `/api/vue/import-preview/${encodeURIComponent(jobId)}/status`,
  shell: () => "/api/vue/shell",
};
