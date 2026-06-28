<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="challenge-day-word-body">
    <div>
      <h2>{{ item.word }}</h2>
    </div>
    <p>{{ item.chinese_definition || item.english_definition || "暂无定义" }}</p>
    <div class="challenge-day-counts">
      <span>对 {{ item.correct_count }}</span>
      <span>错 {{ item.wrong_count }}</span>
      <span v-if="item.corrected" class="is-corrected">已纠正</span>
    </div>
  </div>
</template>
