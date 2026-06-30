import { ref } from "vue";
import { routeApiPaths } from "../routeApiPaths.js";
import { generateWordListAiImages, renameWordList } from "../listDetailActions.js";
import { deleteCurrentWordList } from "../listDeleteBinding.js";
import { createDeleteListState } from "../listDeleteState.js";
import { syncListImagesForDetail } from "../listImageSyncBinding.js";
import { fetchJson } from "../utils.js";

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

  async function refreshCurrentListDetail() {
    const wordListId = data.value?.word_list?.id;
    if (!wordListId) return;
    data.value = await fetchJson(routeApiPaths.listDetail({ params: { id: wordListId } }), {
      skipCache: true,
    });
  }

  async function generateListAiImages({ allowPaid = false } = {}) {
    await generateWordListAiImages({
      wordListId: data.value.word_list.id,
      setJob: (job) => {
        aiImageJob.value = job;
      },
      onProgress: refreshCurrentListDetail,
      onComplete: refreshCurrentListDetail,
      allowPaid,
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
