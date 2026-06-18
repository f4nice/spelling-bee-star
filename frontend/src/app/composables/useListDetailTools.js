import { ref } from "vue";
import {
  deleteWordList,
  LIST_DELETE_FALLBACK_ERROR,
  renameWordList,
} from "../listDetailActions.js";
import {
  createDeleteListState,
  resetDeleteListState,
  setDeleteListNotice,
} from "../listDeleteState.js";
import { syncListImagesForDetail } from "../listImageSyncBinding.js";

export function useListDetailTools({ data, go, loadRoute }) {
  const deleteListState = ref(createDeleteListState());

  async function renameList() {
    await renameWordList({ wordList: data.value.word_list });
  }

  async function deleteList() {
    const wordListId = data.value?.word_list?.id;
    if (!wordListId || !deleteListState.value.password) return;
    try {
      await deleteWordList({ wordListId, password: deleteListState.value.password });
      resetDeleteListState(deleteListState);
      go("/lists");
    } catch (error) {
      setDeleteListNotice(deleteListState, error.message || LIST_DELETE_FALLBACK_ERROR);
    }
  }

  async function syncListImages() {
    await syncListImagesForDetail({ data, loadRoute });
  }

  return {
    deleteListState,
    renameList,
    deleteList,
    syncListImages,
  };
}
