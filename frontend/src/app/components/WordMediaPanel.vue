<script setup>
import { useSelectedWordImage } from "../composables/useSelectedWordImage.js";
import { wordMediaPanelProps } from "../props/wordMediaPanelProps.js";
import WordImageCandidateGrid from "./WordImageCandidateGrid.vue";
import WordImageFrame from "./WordImageFrame.vue";
import WordImageTools from "./WordImageTools.vue";

const props = defineProps(wordMediaPanelProps);

const { selectedImageFile, selectImageFile, saveSelectedImage } = useSelectedWordImage({
  uploadWordImage: props.uploadWordImage,
});
</script>

<template>
  <aside class="panel media-panel">
    <WordImageFrame :word="data.word" :image-url="imageForWord(data.word)" />

    <WordImageTools
      v-if="data.can_edit"
      :selected-image-file="selectedImageFile"
      :find-images="findImages"
      :save-selected-image="saveSelectedImage"
      @select-image="selectImageFile"
    />

    <WordImageCandidateGrid
      v-if="imageCandidates.length"
      :word="data.word"
      :image-candidates="imageCandidates"
      :choose-network-image="chooseNetworkImage"
    />
  </aside>
</template>
