<script setup>
defineProps({
  group: {
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
          <span class="status failed">{{ group.count }} 词</span>
        </div>
        <p class="wrong-list-summary">错 {{ group.wrong_total }} 次</p>
      </div>
    </button>
  </article>
</template>
