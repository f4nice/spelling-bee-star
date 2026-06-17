import { listApiPaths } from "./listApiPaths.js";
import { runListImageSyncJob } from "./listImageSyncJob.js";
import { createDeleteListForm, createRenameListForm } from "./listForms.js";
import { fetchJson } from "./utils.js";

export const LIST_DELETE_FALLBACK_ERROR = "删除失败";

export async function renameWordList({ wordList }) {
  const form = createRenameListForm(wordList.name);
  await fetchJson(listApiPaths.rename(wordList.id), {
    method: "POST",
    body: form,
  });
}

export async function deleteWordList({ wordListId, password }) {
  const form = createDeleteListForm(password);
  await fetchJson(listApiPaths.delete(wordListId), { method: "POST", body: form });
}

export async function syncWordListImages({ wordListId, setJob, onComplete }) {
  await runListImageSyncJob({ wordListId, setJob, onComplete });
}
