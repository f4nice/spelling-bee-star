<script setup>
defineProps({
  word: {
    type: Object,
    required: true,
  },
  maskedExample: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <div class="challenge-word-prompt">
    <p class="section-kicker">当前单词</p>
    <div class="challenge-prompt-list">
      <div class="challenge-prompt-item">
        <span class="challenge-prompt-label">音标</span>
        <strong class="challenge-prompt-value phonetic">{{ word.phonetic || "暂无" }}</strong>
      </div>
      <div class="challenge-prompt-item">
        <span class="challenge-prompt-label">词性</span>
        <strong class="challenge-prompt-value">{{ word.part_of_speech || "暂无" }}</strong>
      </div>
      <div class="challenge-prompt-item is-highlight">
        <span class="challenge-prompt-label">英文定义</span>
        <strong class="challenge-prompt-value">{{ word.english_definition || "暂无" }}</strong>
      </div>
      <div class="challenge-prompt-item">
        <span class="challenge-prompt-label">中文定义</span>
        <strong class="challenge-prompt-value">{{ word.chinese_definition || "暂无" }}</strong>
      </div>
      <div class="challenge-prompt-item">
        <span class="challenge-prompt-label">英文例句</span>
        <strong class="challenge-prompt-value">{{ maskedExample || word.english_example || "暂无" }}</strong>
      </div>
    </div>
  </div>
</template>
