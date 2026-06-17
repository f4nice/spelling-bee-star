<script setup>
import { ref } from "vue";

import WordAudioOptionItem from "./WordAudioOptionItem.vue";
import { wordAudioOptionListProps } from "../props/wordAudioOptionListProps.js";

const props = defineProps(wordAudioOptionListProps);

const choosingUrl = ref("");

async function chooseOption(url) {
  if (!url || choosingUrl.value) return;
  choosingUrl.value = url;
  try {
    await props.chooseAudio(props.accent.key, url);
  } finally {
    choosingUrl.value = "";
  }
}
</script>

<template>
  <div class="audio-options">
    <WordAudioOptionItem
      v-for="option in options"
      :key="option.url"
      :option="option"
      :is-choosing="choosingUrl === option.url"
      :is-disabled="Boolean(choosingUrl)"
      @choose="chooseOption"
    />
  </div>
</template>
