import { ref } from "vue";
import { renameWordList } from "../listDetailActions.js";
import { deleteCurrentWordList } from "../listDeleteBinding.js";
import { createDeleteListState } from "../listDeleteState.js";
import { syncListImagesForDetail } from "../listImageSyncBinding.js";

export function useListDetailTools({ data, go, loadRoute }) {
  const deleteListState = ref(createDeleteListState());

  async function renameList() {
    await renameWordList({ wordList: data.value.word_list });
  }

  async function deleteList() {
    await deleteCurrentWordList({ data, deleteListState, go });
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
