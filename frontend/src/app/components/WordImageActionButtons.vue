<script setup>
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
</script>

<template>
  <button
    type="button"
    class="secondary-button"
    :disabled="!selectedImageFile"
    @click="saveSelectedImage"
  >
    保存图片
  </button>
  <button type="button" class="secondary-button" @click="findImages">网络找图</button>
</template>
