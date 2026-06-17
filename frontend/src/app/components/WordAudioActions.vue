<script setup>
import { ref } from "vue";

const props = defineProps({
  accent: {
    type: Object,
    required: true,
  },
  audioSrc: {
    type: String,
    default: "",
  },
  canEdit: {
    type: Boolean,
    default: false,
  },
  playAudio: {
    type: Function,
    required: true,
  },
  fetchAudioOptions: {
    type: Function,
    required: true,
  },
  startRecording: {
    type: Function,
    required: true,
  },
});

const loadingOptions = ref(false);

async function loadOptions() {
  if (loadingOptions.value) return;
  loadingOptions.value = true;
  try {
    await props.fetchAudioOptions(props.accent.key);
  } finally {
    loadingOptions.value = false;
  }
}
</script>

<template>
  <div class="audio-actions">
    <button type="button" class="secondary-button" @click="playAudio(`audio-${accent.key}`)">
      {{ accent.actionLabel }}
    </button>
    <audio :id="`audio-${accent.key}`" controls preload="none" :src="audioSrc" />
    <button
      v-if="canEdit"
      type="button"
      class="secondary-button"
      :disabled="loadingOptions"
      @click="loadOptions"
    >
      {{ loadingOptions ? "获取中..." : "重新获取音频" }}
    </button>
    <button v-if="canEdit" type="button" class="secondary-button" @click="startRecording(accent.key)">录制音源</button>
  </div>
</template>
