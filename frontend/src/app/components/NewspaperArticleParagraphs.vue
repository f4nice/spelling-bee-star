<script setup>
defineProps({
  paragraphs: {
    type: Array,
    required: true,
  },
});
</script>

<template>
  <article class="newspaper-article-body">
    <p v-for="(paragraph, index) in paragraphs" :key="index">{{ paragraph }}</p>
  </article>
</template>
