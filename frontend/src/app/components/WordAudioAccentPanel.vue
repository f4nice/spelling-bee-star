<script setup>
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
    <div class="audio-actions">
      <button type="button" class="secondary-button" @click="playAudio(`audio-${accent.key}`)">{{ accent.actionLabel }}</button>
      <audio :id="`audio-${accent.key}`" controls preload="none" :src="data.audio_sources[accent.key]"></audio>
      <button v-if="data.can_edit" type="button" class="secondary-button" @click="fetchAudioOptions(accent.key)">重新获取音频</button>
      <button v-if="data.can_edit" type="button" class="secondary-button" @click="startRecording(accent.key)">录制音源</button>
    </div>
    <div v-if="options.length" class="audio-options">
      <div v-for="option in options" :key="option.url" class="audio-option">
        <strong>{{ option.label }}</strong>
        <audio controls :src="option.url"></audio>
        <button type="button" class="secondary-button" @click="chooseAudio(accent.key, option.url)">选这个</button>
      </div>
    </div>
  </label>
</template>
