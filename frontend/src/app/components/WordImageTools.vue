<script setup>
import WordImageActionButtons from "./WordImageActionButtons.vue";
import WordImageUploadField from "./WordImageUploadField.vue";

defineProps({
  selectedImageFile: {
    type: Object,
    default: null,
  },
  findImages: {
    type: Function,
    required: true,
  },
  saveSelectedImage: {
    type: Function,
    required: true,
  },
});

defineEmits(["select-image"]);
</script>

<template>
  <div class="media-tools" role="group" aria-label="单词图片工具">
    <WordImageUploadField @select-image="$emit('select-image', $event)" />
    <WordImageActionButtons
      :selected-image-file="selectedImageFile"
      :find-images="findImages"
      :save-selected-image="saveSelectedImage"
    />
  </div>
</template>
