export function getPreviewRowSelection(preview, checked) {
  return checked ? preview.rows.map((row) => row.index) : [];
}

export function getPreviewColumnSelection(preview, checked) {
  return checked ? [...preview.columns] : [];
}
