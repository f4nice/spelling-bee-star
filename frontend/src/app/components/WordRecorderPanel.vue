<script setup>
import { computed, ref } from "vue";

const props = defineProps({
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

const saving = ref(false);
const isRecording = computed(() => props.recorderState.status === "录音中...");

async function saveRecordedAudio() {
  if (!props.recorderState.blob || saving.value) return;
  saving.value = true;
  try {
    await props.saveRecording();
  } finally {
    saving.value = false;
  }
}
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
