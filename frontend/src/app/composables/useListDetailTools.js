import { ref } from "vue";
import { generateWordListAiImages, renameWordList } from "../listDetailActions.js";
import { deleteCurrentWordList } from "../listDeleteBinding.js";
import { createDeleteListState } from "../listDeleteState.js";
import { syncListImagesForDetail } from "../listImageSyncBinding.js";

export function useListDetailTools({ data, go, loadRoute }) {
  const deleteListState = ref(createDeleteListState());
  const aiImageJob = ref(null);

  async function renameList() {
    await renameWordList({ wordList: data.value.word_list });
  }

  async function deleteList() {
    await deleteCurrentWordList({ data, deleteListState, go });
  }

  async function syncListImages() {
    await syncListImagesForDetail({ data, loadRoute });
  }

  async function generateListAiImages() {
    await generateWordListAiImages({
      wordListId: data.value.word_list.id,
      setJob: (job) => {
        aiImageJob.value = job;
      },
      onComplete: loadRoute,
    });
  }

  return {
    deleteListState,
    aiImageJob,
    renameList,
    deleteList,
    syncListImages,
    generateListAiImages,
  };
}
