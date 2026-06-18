<script setup>
defineEmits(["select-image"]);
</script>

<template>
  <label>
    上传图片
    <input
      type="file"
      accept="image/*"
      @change="$emit('select-image', $event.target.files[0] || null)"
    >
  </label>
</template>
