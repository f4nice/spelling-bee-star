<script setup>
defineProps({
  section: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="newspaper-section-head">
    <h2>{{ section.name }}</h2>
    <span>{{ section.articles?.length || 0 }} articles</span>
  </div>
</template>
