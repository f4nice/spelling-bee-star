<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <article class="word-card list-card">
    <button class="list-card-link plain-card-button" type="button" @click="go(`/booklearner/detail/${item.id}`)">
      <div class="image-fallback">B</div>
      <div class="word-card-body">
        <div class="word-card-title">
          <strong>{{ item.title || item.query || `记录 #${item.id}` }}</strong>
          <span class="status">书摘</span>
        </div>
        <p>{{ item.createdAt || item.created_at }}</p>
      </div>
    </button>
  </article>
</template>
