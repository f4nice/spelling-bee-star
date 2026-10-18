<script setup>
import { ref } from "vue";

defineProps({
  word: {
    type: Object,
    required: true,
  },
  imageUrl: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["swipe"]);
const touchStart = ref(null);

function handleTouchStart(event) {
  const touch = event.touches?.[0];
  if (!touch) return;
  touchStart.value = { x: touch.clientX, y: touch.clientY };
}

function handleTouchEnd(event) {
  const start = touchStart.value;
  touchStart.value = null;
  const touch = event.changedTouches?.[0];
  if (!start || !touch) return;
  const dx = touch.clientX - start.x;
  const dy = touch.clientY - start.y;
  if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy) * 1.2) return;
  emit("swipe", dx < 0 ? "next" : "previous");
}
</script>

<template>
  <div
    class="word-image-frame"
    @touchstart.passive="handleTouchStart"
    @touchend.passive="handleTouchEnd"
  >
    <img v-if="imageUrl" :src="imageUrl" :alt="word.word">
    <div v-else class="image-fallback">{{ word.word.slice(0, 1).toUpperCase() }}</div>
  </div>
</template>
