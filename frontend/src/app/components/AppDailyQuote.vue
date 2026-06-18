<script setup>
import { computed } from "vue";

const props = defineProps({
  quote: {
    type: Object,
    default: null,
  },
});

const quoteText = computed(() => props.quote?.content || "Every word is a new window.");
</script>

<template>
  <div class="daily-quote">
    {{ quoteText }}<span v-if="quote?.author"> - {{ quote.author }}</span>
  </div>
</template>
