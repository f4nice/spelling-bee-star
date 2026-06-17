export function wordDetailEditUrl(wordId, search = window.location.search) {
  const params = new URLSearchParams(search);
  params.set("edit", "1");
  return `/words/${wordId}?${params.toString()}`;
}

export function importPreviewSheetUrl({ previewId, sheetName, wordListName, wordListId }) {
  const params = new URLSearchParams({
    sheet_name: sheetName,
    word_list_name: wordListName || "",
    word_list_id: wordListId || "",
  });
  return `/upload/preview/${previewId}?${params.toString()}`;
}
