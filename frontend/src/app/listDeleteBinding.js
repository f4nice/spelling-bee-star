import {
  deleteWordList,
  LIST_DELETE_FALLBACK_ERROR,
} from "./listDetailActions.js";
import {
  resetDeleteListState,
  setDeleteListNotice,
} from "./listDeleteState.js";

export async function deleteCurrentWordList({ data, deleteListState, go }) {
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
