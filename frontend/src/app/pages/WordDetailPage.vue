<script setup>
import WordDetailContentPanel from "../components/WordDetailContentPanel.vue";
import WordMediaPanel from "../components/WordMediaPanel.vue";

defineProps({
  mediaPanel: {
    type: Object,
    required: true,
  },
  contentPanel: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <section class="detail-layout">
    <WordMediaPanel v-bind="mediaPanel" />
    <WordDetailContentPanel v-bind="contentPanel" />
  </section>
</template>
