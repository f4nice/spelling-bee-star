<script setup>
defineProps({
  notice: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <p v-if="notice" class="notice">{{ notice }}</p>
</template>
