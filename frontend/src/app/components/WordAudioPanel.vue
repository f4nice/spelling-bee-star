<script setup>
import { wordAudioPanelProps } from "../props/wordAudioPanelProps.js";
import { wordAudioAccents } from "../wordAudioAccents.js";
import { buildWordAudioAccentListProps, buildWordRecorderPanelProps } from "../wordAudioPanelBindings.js";
import WordAudioAccentList from "./WordAudioAccentList.vue";
import WordRecorderPanel from "./WordRecorderPanel.vue";

const props = defineProps(wordAudioPanelProps);
</script>

<template>
  <WordAudioAccentList v-bind="buildWordAudioAccentListProps(props, wordAudioAccents)" />

  <WordRecorderPanel v-bind="buildWordRecorderPanelProps(props)" />
</template>
