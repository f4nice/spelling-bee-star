import { ref } from "vue";

export function useSelectedWordImage({ uploadWordImage }) {
  const selectedImageFile = ref(null);

  function selectImageFile(file) {
    selectedImageFile.value = file;
  }

  async function saveSelectedImage() {
    const file = selectedImageFile.value;
    if (!file) return false;
    await uploadWordImage(file);
    // A different file may have been selected while this upload was pending.
    if (selectedImageFile.value !== file) return false;
    selectedImageFile.value = null;
    return true;
  }

  return {
    selectedImageFile,
    selectImageFile,
    saveSelectedImage,
  };
}
