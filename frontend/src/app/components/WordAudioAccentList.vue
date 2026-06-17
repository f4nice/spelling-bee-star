<script setup>
import { wordAudioAccentListProps } from "../props/wordAudioAccentListProps.js";
import { buildWordAudioAccentPanelProps } from "../wordAudioAccentPanelProps.js";
import WordAudioAccentPanel from "./WordAudioAccentPanel.vue";

const props = defineProps(wordAudioAccentListProps);
</script>

<template>
  <div class="audio-row">
    <WordAudioAccentPanel
      v-for="accent in accents"
      :key="accent.key"
      v-bind="buildWordAudioAccentPanelProps(props, accent)"
    />
  </div>
</template>
