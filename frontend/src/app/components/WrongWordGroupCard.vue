<script setup>
import { computed } from "vue";

const props = defineProps({
  group: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const pendingCount = computed(() => Number(props.group.pending_count ?? props.group.count ?? 0));
const correctedCount = computed(() => Number(props.group.corrected_count || 0));
const isFullyCorrected = computed(() => pendingCount.value <= 0 && Number(props.group.count || 0) > 0);
</script>

<template>
  <article class="word-card list-card">
    <button
      class="list-card-link plain-card-button"
      type="button"
      @click="go(`/challenge-calendar/${group.date}`)"
    >
      <img v-if="group.cover_word?.image_url" :src="group.cover_word.image_url" :alt="group.date">
      <div v-else class="image-fallback">错</div>
      <div class="word-card-body">
        <div class="word-card-title">
          <strong>{{ group.date }}</strong>
          <span class="status" :class="isFullyCorrected ? 'done' : 'failed'">
            {{ isFullyCorrected ? '已纠正' : '待纠正' }} {{ isFullyCorrected ? correctedCount : pendingCount }}
          </span>
        </div>
        <p class="wrong-list-summary">错 {{ group.wrong_total }} 次 · 已纠正 {{ correctedCount }}</p>
      </div>
    </button>
  </article>
</template>
