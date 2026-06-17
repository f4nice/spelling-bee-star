<script setup>
import WordAudioActions from "./WordAudioActions.vue";
import WordAudioOptionList from "./WordAudioOptionList.vue";

defineProps({
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
</script>

<template>
  <label>
    {{ accent.label }}
    <WordAudioActions
      :accent="accent"
      :audio-src="data.audio_sources[accent.key]"
      :can-edit="data.can_edit"
      :play-audio="playAudio"
      :fetch-audio-options="fetchAudioOptions"
      :start-recording="startRecording"
    />
    <WordAudioOptionList
      v-if="options.length"
      :accent="accent"
      :options="options"
      :choose-audio="chooseAudio"
    />
  </label>
</template>
