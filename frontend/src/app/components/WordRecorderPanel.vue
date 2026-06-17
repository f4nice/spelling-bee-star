<script setup>
import { computed } from "vue";
import { useLoadingAction } from "../composables/useLoadingAction.js";
import { wordRecorderPanelProps } from "../props/wordRecorderPanelProps.js";
import { wordRecorderMessages } from "../wordRecorderMessages.js";

const props = defineProps(wordRecorderPanelProps);

const isRecording = computed(() => props.recorderState.status === wordRecorderMessages.recording);
const { loading: saving, run: saveRecordedAudio } = useLoadingAction(() => props.saveRecording());
</script>

<template>
  <div v-if="recorderState.status" class="record-audio-panel">
    <p>{{ recorderState.status }}</p>
    <button
      v-if="isRecording"
      type="button"
      class="secondary-button"
      @click="stopRecording"
    >
      停止录音
    </button>
    <audio v-if="recorderState.preview" controls :src="recorderState.preview" />
    <button
      v-if="recorderState.blob"
      type="button"
      :disabled="saving"
      @click="saveRecordedAudio"
    >
      {{ saving ? "保存中..." : "确认替换" }}
    </button>
  </div>
</template>
