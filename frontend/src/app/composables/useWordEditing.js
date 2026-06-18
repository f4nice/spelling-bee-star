import { ref } from "vue";
import { createWordEditSnapshot, saveWordEditField } from "../wordEditingActions.js";

export function useWordEditing({ data }) {
  const wordEdit = ref({});
  const wordSaving = ref("");

  function setWordEdit(word) {
    wordEdit.value = createWordEditSnapshot(word);
  }

  async function saveWordField(field) {
    await saveWordEditField({
      wordId: data.value.word.id,
      field,
      value: wordEdit.value[field],
      setSaving: (value) => {
        wordSaving.value = value;
      },
      applySavedValue: (value) => {
        data.value.word[field] = value;
      },
    });
  }

  return {
    wordEdit,
    wordSaving,
    setWordEdit,
    saveWordField,
  };
}
