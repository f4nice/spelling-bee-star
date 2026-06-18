<script setup>
defineProps({
  data: {
    type: Object,
    required: true,
  },
  wordEdit: {
    type: Object,
    required: true,
  },
  saveWordField: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="word-title-stack">
    <h1>{{ data.word.word }}</h1>
    <p v-if="data.word.phonetic" class="phonetic">/{{ data.word.phonetic }}/</p>
    <textarea
      v-if="data.can_edit"
      v-model="wordEdit.alternate_spellings"
      class="inline-edit-input"
      @blur="saveWordField('alternate_spellings')"
    ></textarea>
    <strong v-else>{{ data.word.alternate_spellings || "暂无" }}</strong>
  </div>
</template>
