import { ref } from "vue";
import { routeApiPaths } from "../routeApiPaths.js";
import { listApiPaths } from "../listApiPaths.js";
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

  async function moveListToGroup(groupId) {
    const wordListId = data.value?.word_list?.id;
    if (!wordListId) return;
    await fetchJson(listApiPaths.moveToGroup(wordListId), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ group_id: groupId || null }),
      skipCache: true,
    });
    await refreshCurrentListDetail();
  }

  async function createWordInList(formState) {
    const wordListId = data.value?.word_list?.id;
    if (!wordListId) throw new Error("没有找到当前单词表。");
    const form = new FormData();
    if (formState?.existing_word_id) {
      form.append("existing_word_id", formState.existing_word_id);
    }
    ["word", "phonetic", "part_of_speech", "english_definition", "chinese_definition", "english_example", "note"].forEach((field) => {
      form.append(field, formState?.[field] || "");
    });
    const result = await fetchJson(listApiPaths.createWord(wordListId), { method: "POST", body: form });
    await refreshCurrentListDetail();
    return result;
  }

  async function findWordCandidates(word) {
    const wordListId = data.value?.word_list?.id;
    if (!wordListId) throw new Error("没有找到当前单词表。");
    const result = await fetchJson(listApiPaths.wordCandidates(wordListId, word), { skipCache: true });
    return result.candidates || [];
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
    moveListToGroup,
    createWordInList,
    findWordCandidates,
    generateListAiImages,
  };
}
