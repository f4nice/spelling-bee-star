<script setup>
import { ref } from "vue";
import WordAudioOptionList from "./WordAudioOptionList.vue";

const props = defineProps({
  accent: {
    type: Object,
    required: true,
  },
  data: {
    type: Object,
    required: true,
  },
  options: {
    type: Array,
    default: () => [],
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
  chooseAudio: {
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
  <label>
    {{ accent.label }}
    <div class="audio-actions">
      <button type="button" class="secondary-button" @click="playAudio(`audio-${accent.key}`)">
        {{ accent.actionLabel }}
      </button>
      <audio :id="`audio-${accent.key}`" controls preload="none" :src="data.audio_sources[accent.key]" />
      <button
        v-if="data.can_edit"
        type="button"
        class="secondary-button"
        :disabled="loadingOptions"
        @click="loadOptions"
      >
        {{ loadingOptions ? "获取中..." : "重新获取音频" }}
      </button>
      <button v-if="data.can_edit" type="button" class="secondary-button" @click="startRecording(accent.key)">录制音源</button>
    </div>
    <WordAudioOptionList
      v-if="options.length"
      :accent="accent"
      :options="options"
      :choose-audio="chooseAudio"
    />
  </label>
</template>
