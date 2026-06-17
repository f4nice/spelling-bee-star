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

defineEmits(["select-image"]);
</script>

<template>
  <div class="media-tools" role="group" aria-label="单词图片工具">
    <label>
      上传图片
      <input
        type="file"
        accept="image/*"
        @change="$emit('select-image', $event.target.files[0] || null)"
      >
    </label>
    <button
      type="button"
      class="secondary-button"
      :disabled="!selectedImageFile"
      @click="saveSelectedImage"
    >
      保存图片
    </button>
    <button type="button" class="secondary-button" @click="findImages">网络找图</button>
  </div>
</template>
