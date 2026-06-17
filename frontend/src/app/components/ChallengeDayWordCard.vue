<script setup>
import { challengeDayWordUrl } from "../challengeDayWordUrl.js";
import ChallengeDayWordBody from "./ChallengeDayWordBody.vue";
import ChallengeDayWordMedia from "./ChallengeDayWordMedia.vue";
import ChallengeDayWordResult from "./ChallengeDayWordResult.vue";

defineProps({
  item: {
    type: Object,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <a
    class="panel challenge-day-word"
    :class="item.status === 'correct' ? 'is-correct' : 'is-wrong'"
    :href="challengeDayWordUrl(item)"
  >
    <ChallengeDayWordResult :item="item" />
    <ChallengeDayWordMedia :item="item" :fallback-letter="fallbackLetter" />
    <ChallengeDayWordBody :item="item" />
  </a>
</template>
