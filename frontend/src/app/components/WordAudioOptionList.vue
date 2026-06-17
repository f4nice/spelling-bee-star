<script setup>
import { ref } from "vue";

const props = defineProps({
  accent: {
    type: Object,
    required: true,
  },
  options: {
    type: Array,
    default: () => [],
  },
  chooseAudio: {
    type: Function,
    required: true,
  },
});

const choosingUrl = ref("");

async function chooseOption(url) {
  if (!url || choosingUrl.value) return;
  choosingUrl.value = url;
  try {
    await props.chooseAudio(props.accent.key, url);
  } finally {
    choosingUrl.value = "";
  }
}
</script>

<template>
  <div class="audio-options">
    <div v-for="option in options" :key="option.url" class="audio-option">
      <strong>{{ option.label }}</strong>
      <audio controls :src="option.url" />
      <button
        type="button"
        class="secondary-button"
        :disabled="Boolean(choosingUrl)"
        @click="chooseOption(option.url)"
      >
        {{ choosingUrl === option.url ? "保存中..." : "选这个" }}
      </button>
    </div>
  </div>
</template>
