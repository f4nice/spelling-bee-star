import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { runListImageSyncJob } from "../listImageSyncJob.js";

export function useListDetailTools({ data, go, loadRoute }) {
  const deleteListState = ref({ password: "", notice: "" });

  async function renameList() {
    const form = new FormData();
    form.append("name", data.value.word_list.name);
    await fetchJson(`/api/vue/lists/${data.value.word_list.id}/rename`, {
      method: "POST",
      body: form,
    });
  }

  async function deleteList() {
    if (!data.value?.word_list?.id || !deleteListState.value.password) return;
    const form = new FormData();
    form.append("password", deleteListState.value.password);
    try {
      await fetchJson(`/api/vue/lists/${data.value.word_list.id}/delete`, { method: "POST", body: form });
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
