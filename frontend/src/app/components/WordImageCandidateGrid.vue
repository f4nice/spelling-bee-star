<script setup>
defineProps({
  word: {
    type: Object,
    required: true,
  },
  imageCandidates: {
    type: Array,
    required: true,
  },
  selectImageCandidate: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="image-picker-grid inline-image-grid">
    <button
      v-for="(item, index) in imageCandidates"
      :key="item.url || index"
      type="button"
      class="image-candidate-button"
      @click="selectImageCandidate(item)"
    >
      <img :src="item.url" :alt="`${word.word} 候选图 ${index + 1}`">
    </button>
  </div>
</template>
