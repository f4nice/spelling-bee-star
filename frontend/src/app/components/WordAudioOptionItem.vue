<script setup>
import { wordAudioOptionItemProps } from "../props/wordAudioOptionItemProps.js";

defineProps(wordAudioOptionItemProps);

defineEmits(["choose"]);
</script>

<template>
  <div class="audio-option">
    <strong>{{ option.label }}</strong>
    <audio controls :src="option.url" />
    <button
      type="button"
      class="secondary-button"
      :disabled="isDisabled"
      @click="$emit('choose', option.url)"
    >
      {{ isChoosing ? "保存中..." : "选这个" }}
    </button>
  </div>
</template>
