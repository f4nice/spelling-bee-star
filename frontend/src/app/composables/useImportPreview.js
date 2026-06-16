import { ref } from 'vue';
import { fetchJson } from '../utils.js';

export function useImportPreview({ data, route, go, loadRoute, setError }) {
  const importForm = ref({ word_list_name: '', word_columns: [], selected_rows: [], selected_columns: [], image_files: [] });

  function resetImportForm() {
    const preview = data.value?.preview;
    if (!preview) return;
    importForm.value = {
      word_list_name: preview.word_list_name || '',
      word_columns: [...(preview.inferred_word_columns || [preview.inferred_word_column].filter(Boolean))],
      selected_rows: preview.rows.map((row) => row.index),
      selected_columns: [...preview.columns],
      image_files: [],
    };
  }

  function setAllRows(checked) {
    importForm.value.selected_rows = checked ? data.value.preview.rows.map((row) => row.index) : [];
  }

  function setAllColumns(checked) {
    importForm.value.selected_columns = checked ? [...data.value.preview.columns] : [];
  }

  async function changePreviewSheet(sheetName) {
    const params = new URLSearchParams({
      sheet_name: sheetName,
      word_list_name: importForm.value.word_list_name || data.value.preview.word_list_name || '',
      word_list_id: data.value.preview.word_list_id || '',
    });
    history.replaceState(null, '', `/vue/upload/preview/${route.value.params.id}?${params.toString()}`);
    await loadRoute();
  }

  async function submitImport() {
    if (!importForm.value.word_columns.length) {
      setError('请至少选择一个英文单词列');
      return;
    }
    const form = new FormData();
    form.append('preview_id', route.value.params.id);
    form.append('word_list_id', data.value.preview.word_list_id || '');
    form.append('word_list_name', importForm.value.word_list_name);
    importForm.value.word_columns.forEach((item) => form.append('word_columns', item));
    importForm.value.selected_rows.forEach((item) => form.append('selected_rows', item));
    importForm.value.selected_columns.forEach((item) => form.append('selected_columns', item));
    importForm.value.image_files.forEach((item) => form.append('image_files', item));
    const result = await fetchJson('/api/vue/import-preview', { method: 'POST', body: form });
    go(`/lists/${result.word_list_id}`);
  }

  return {
    importForm,
    resetImportForm,
    setAllRows,
    setAllColumns,
    changePreviewSheet,
    submitImport,
  };
}
