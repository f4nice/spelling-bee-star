import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { listApiPaths } from "../listApiPaths.js";
import { runListImageSyncJob } from "../listImageSyncJob.js";
import { createDeleteListForm, createRenameListForm } from "../listForms.js";

export function useListDetailTools({ data, go, loadRoute }) {
  const deleteListState = ref({ password: "", notice: "" });

  async function renameList() {
    const form = createRenameListForm(data.value.word_list.name);
    await fetchJson(listApiPaths.rename(data.value.word_list.id), {
      method: "POST",
      body: form,
    });
  }

  async function deleteList() {
    if (!data.value?.word_list?.id || !deleteListState.value.password) return;
    const form = createDeleteListForm(deleteListState.value.password);
    try {
      await fetchJson(listApiPaths.delete(data.value.word_list.id), { method: "POST", body: form });
      deleteListState.value = { password: "", notice: "" };
      go("/lists");
    } catch (error) {
      deleteListState.value.notice = error.message || "删除失败";
    }
  }

  async function syncListImages() {
    await runListImageSyncJob({
      wordListId: data.value.word_list.id,
      setJob: (job) => {
        data.value.sync_job = job;
      },
      onComplete: loadRoute,
    });
  }

  return {
    deleteListState,
    renameList,
    deleteList,
    syncListImages,
  };
}
