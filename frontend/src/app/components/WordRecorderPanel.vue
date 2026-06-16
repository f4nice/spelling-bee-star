<script setup>
defineProps({
  recorderState: {
    type: Object,
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
</script>

<template>
  <div v-if="recorderState.status" class="record-audio-panel">
    <p>{{ recorderState.status }}</p>
    <button type="button" class="secondary-button" @click="stopRecording">停止录音</button>
    <audio v-if="recorderState.preview" controls :src="recorderState.preview"></audio>
    <button v-if="recorderState.blob" type="button" @click="saveRecording">确认替换</button>
  </div>
</template>
