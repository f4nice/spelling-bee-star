<script setup>
import { wordAudioActionsProps } from "../props/wordAudioActionsProps.js";

defineProps(wordAudioActionsProps);
defineEmits(["manage-audio"]);
</script>

<template>
  <div class="audio-actions">
    <button type="button" class="secondary-button" @click="playAudio(`audio-${accent.key}`)">
      {{ accent.actionLabel }}
    </button>
    <audio :id="`audio-${accent.key}`" controls preload="metadata" :src="audioSrc" />
    <button
      v-if="canEdit"
      type="button"
      class="secondary-button"
      @click="$emit('manage-audio')"
    >
      音频管理
    </button>
  </div>
</template>
