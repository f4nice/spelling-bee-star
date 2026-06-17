<script setup>
import { wordAudioAccentPanelProps } from "../props/wordAudioAccentPanelProps.js";
import WordAudioActions from "./WordAudioActions.vue";
import WordAudioOptionList from "./WordAudioOptionList.vue";

defineProps(wordAudioAccentPanelProps);
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
