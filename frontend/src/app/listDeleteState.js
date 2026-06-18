export function createDeleteListState() {
  return { password: "", notice: "" };
}

export function resetDeleteListState(deleteListState) {
  deleteListState.value = createDeleteListState();
}

export function setDeleteListNotice(deleteListState, notice) {
  deleteListState.value.notice = notice;
}
