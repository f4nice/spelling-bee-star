<script setup>
import { computed } from "vue";

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const title = computed(() => props.item.title || props.item.query_text || props.item.query || `记录 #${props.item.id}`);
const coverUrl = computed(() => props.item.coverUrl || props.item.cover_url || props.item.book?.coverUrl || "");
const detailUrl = computed(() => `/booklearner/detail/${props.item.id}`);
const coverSeed = computed(() => Number(props.item.coverSeed || props.item.cover_seed || 0) % 6);

function openDetail(event) {
  event.preventDefault();
  props.go(detailUrl.value);
}
</script>

<template>
  <article class="word-card list-card">
    <a class="list-card-link book-history-link" :href="detailUrl" @click="openDetail">
      <img v-if="coverUrl" class="book-history-cover" :src="coverUrl" :alt="title" loading="lazy">
      <div v-else class="book-history-cover-fallback" :class="`cover-seed-${coverSeed}`">
        <span>书摘</span>
        <strong>{{ title.slice(0, 1).toUpperCase() }}</strong>
      </div>
      <div class="word-card-body">
        <div class="word-card-title">
          <strong>{{ title }}</strong>
          <span class="status">书摘</span>
        </div>
        <p>{{ item.createdAt || item.created_at }}</p>
      </div>
    </a>
  </article>
</template>
