import { ref } from "vue";

export function useSelectedWordImage({ uploadWordImage }) {
  const selectedImageFile = ref(null);

  function selectImageFile(file) {
    selectedImageFile.value = file;
  }

  async function saveSelectedImage() {
    if (!selectedImageFile.value) return;
    await uploadWordImage(selectedImageFile.value);
    selectedImageFile.value = null;
  }

  return {
    selectedImageFile,
    selectImageFile,
    saveSelectedImage,
  };
}
