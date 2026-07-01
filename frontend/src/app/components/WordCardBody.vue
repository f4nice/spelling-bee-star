<script setup>
import WordChallengeStats from "./WordChallengeStats.vue";

defineProps({
  word: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="word-card-body">
    <div class="word-card-title">
      <span class="word-card-title-main">
        <strong>{{ word.word }}</strong>
        <span v-if="word.has_playable_audio" class="word-audio-badge" title="可朗读" aria-label="可朗读">🔊</span>
        <span v-if="word.image_issue" class="word-image-issue-badge" title="图片待修" aria-label="图片待修">图修</span>
        <span v-if="word.audio_issue" class="word-audio-issue-badge" title="音频待修" aria-label="音频待修">待修</span>
      </span>
      <WordChallengeStats :stats="word.challenge_stats" />
    </div>
    <p>{{ word.chinese_definition || word.english_definition || "等待补全" }}</p>
  </div>
</template>
