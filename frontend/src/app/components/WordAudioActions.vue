<script setup>
import { useLoadingAction } from "../composables/useLoadingAction.js";
import { wordAudioActionsProps } from "../props/wordAudioActionsProps.js";
import { wordAudioActionLabels } from "../wordAudioActionLabels.js";

const props = defineProps(wordAudioActionsProps);

const { loading: loadingOptions, run: loadOptions } = useLoadingAction(() =>
  props.fetchAudioOptions(props.accent.key),
);
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
      {{ loadingOptions ? wordAudioActionLabels.loadingOptions : wordAudioActionLabels.reloadOptions }}
    </button>
    <button v-if="canEdit" type="button" class="secondary-button" @click="startRecording(accent.key)">
      {{ wordAudioActionLabels.recordSource }}
    </button>
  </div>
</template>
