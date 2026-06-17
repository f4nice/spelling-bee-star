import { ref } from 'vue';
import { fetchJson } from '../utils.js';
import { wordApiPaths } from '../wordApiPaths.js';

export function useWordEditing({ data }) {
  const wordEdit = ref({});
  const wordSaving = ref('');

  function setWordEdit(word) {
    wordEdit.value = {
      alternate_spellings: word.alternate_spellings || '',
      english_definition: word.english_definition || '',
      chinese_definition: word.chinese_definition || '',
      english_example: word.english_example || '',
    };
  }

  async function saveWordField(field) {
    wordSaving.value = field;
    const form = new FormData();
    form.append('edit_token', '1');
    form.append('field', field);
    form.append('value', wordEdit.value[field] || '');
    try {
      const result = await fetchJson(wordApiPaths.field(data.value.word.id), { method: 'POST', body: form });
      data.value.word[field] = result.value;
    } finally {
      wordSaving.value = '';
    }
  }

  return {
    wordEdit,
    wordSaving,
    setWordEdit,
    saveWordField,
  };
}
