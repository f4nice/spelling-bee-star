<script setup>
import { ref } from "vue";
import { useSelectedWordImage } from "../composables/useSelectedWordImage.js";
import { wordMediaPanelProps } from "../props/wordMediaPanelProps.js";
import WordImageFrame from "./WordImageFrame.vue";
import WordImageManagerModal from "./WordImageManagerModal.vue";

const props = defineProps(wordMediaPanelProps);
const isImageModalOpen = ref(false);

const { selectedImageFile, selectImageFile, saveSelectedImage } = useSelectedWordImage({
  uploadWordImage: props.uploadWordImage,
});

async function saveUploadedImage() {
  await saveSelectedImage();
  isImageModalOpen.value = false;
}

async function chooseNetworkImageAndClose(url) {
  await props.chooseNetworkImage(url);
  isImageModalOpen.value = false;
}
</script>

<template>
  <aside class="panel media-panel">
    <WordImageFrame :word="data.word" :image-url="imageForWord(data.word)" />

    <button
      v-if="data.can_edit"
      class="secondary-button image-manager-trigger"
      type="button"
      @click="isImageModalOpen = true"
    >
      图片管理
    </button>

    <WordImageManagerModal
      v-if="isImageModalOpen"
      :word="data.word"
      :image-url="imageForWord(data.word)"
      :selected-image-file="selectedImageFile"
      :image-candidates="imageCandidates"
      :find-images="findImages"
      :save-selected-image="saveUploadedImage"
      :choose-network-image="chooseNetworkImageAndClose"
      @select-image="selectImageFile"
      @close="isImageModalOpen = false"
    />
  </aside>
</template>
