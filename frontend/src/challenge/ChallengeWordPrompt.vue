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
    <h2>{{ word.chinese_definition || word.english_definition || "听音拼写" }}</h2>
    <p v-if="word.phonetic" class="phonetic">{{ word.phonetic }}</p>
    <dl class="definition-list compact challenge-hints">
      <template v-if="word.part_of_speech">
        <dt>词性</dt>
        <dd>{{ word.part_of_speech }}</dd>
      </template>
      <template v-if="word.english_definition">
        <dt>英文定义</dt>
        <dd>{{ word.english_definition }}</dd>
      </template>
      <template v-if="maskedExample || word.english_example">
        <dt>英文例句</dt>
        <dd>{{ maskedExample || word.english_example }}</dd>
      </template>
    </dl>
  </div>
</template>
