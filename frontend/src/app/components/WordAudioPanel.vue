<script setup>
defineProps({
  data: {
    type: Object,
    required: true,
  },
  audioOptions: {
    type: Object,
    required: true,
  },
  recorderState: {
    type: Object,
    required: true,
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
  stopRecording: {
    type: Function,
    required: true,
  },
  saveRecording: {
    type: Function,
    required: true,
  },
});

const accents = [
  { key: 'us', label: '美式发音', actionLabel: '朗读美式' },
  { key: 'gb', label: '英式发音', actionLabel: '朗读英式' },
];
</script>

<template>
  <div class="audio-row">
    <label v-for="accent in accents" :key="accent.key">
      {{ accent.label }}
      <div class="audio-actions">
        <button type="button" class="secondary-button" @click="playAudio(`audio-${accent.key}`)">{{ accent.actionLabel }}</button>
        <audio :id="`audio-${accent.key}`" controls preload="none" :src="data.audio_sources[accent.key]"></audio>
        <button v-if="data.can_edit" type="button" class="secondary-button" @click="fetchAudioOptions(accent.key)">重新获取音频</button>
        <button v-if="data.can_edit" type="button" class="secondary-button" @click="startRecording(accent.key)">录制音源</button>
      </div>
      <div v-if="audioOptions[accent.key]?.length" class="audio-options">
        <div v-for="option in audioOptions[accent.key]" :key="option.url" class="audio-option">
          <strong>{{ option.label }}</strong>
          <audio controls :src="option.url"></audio>
          <button type="button" class="secondary-button" @click="chooseAudio(accent.key, option.url)">选这个</button>
        </div>
      </div>
    </label>
  </div>

  <div v-if="recorderState.status" class="record-audio-panel">
    <p>{{ recorderState.status }}</p>
    <button type="button" class="secondary-button" @click="stopRecording">停止录音</button>
    <audio v-if="recorderState.preview" controls :src="recorderState.preview"></audio>
    <button v-if="recorderState.blob" type="button" @click="saveRecording">确认替换</button>
  </div>
</template>
