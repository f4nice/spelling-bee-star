<script setup>
import { inferImageSourceMeta, sourceText } from "../mediaSourceLabels.js";

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

function candidateSourceText(candidate) {
  return sourceText(inferImageSourceMeta(candidate?.source_meta || { source: candidate?.source || candidate?.provider || "" }, candidate?.url || ""));
}
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
      <small class="image-source-chip">{{ candidateSourceText(item) }}</small>
    </button>
  </div>
</template>

<style scoped>
.image-candidate-button {
  position: relative;
  overflow: hidden;
}

.image-source-chip {
  position: absolute;
  left: 8px;
  bottom: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #087452;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
  padding: 5px 9px;
  box-shadow: 0 8px 18px rgba(9, 70, 50, 0.14);
}
</style>
