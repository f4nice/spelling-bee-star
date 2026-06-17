import { ref } from "vue";
import {
  deleteWordList,
  LIST_DELETE_FALLBACK_ERROR,
  renameWordList,
  syncWordListImages,
} from "../listDetailActions.js";

export function useListDetailTools({ data, go, loadRoute }) {
  const deleteListState = ref({ password: "", notice: "" });

  async function renameList() {
    await renameWordList({ wordList: data.value.word_list });
  }

  async function deleteList() {
    const wordListId = data.value?.word_list?.id;
    if (!wordListId || !deleteListState.value.password) return;
    try {
      await deleteWordList({ wordListId, password: deleteListState.value.password });
      deleteListState.value = { password: "", notice: "" };
      go("/lists");
    } catch (error) {
      deleteListState.value.notice = error.message || LIST_DELETE_FALLBACK_ERROR;
    }
  }

  async function syncListImages() {
    await syncWordListImages({
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
