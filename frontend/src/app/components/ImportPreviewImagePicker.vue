<script setup>
defineProps({
  importForm: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <label>
    批量图片
    <input
      type="file"
      accept="image/*"
      multiple
      webkitdirectory
      directory
      @change="importForm.image_files = Array.from($event.target.files || [])"
    >
  </label>
</template>
