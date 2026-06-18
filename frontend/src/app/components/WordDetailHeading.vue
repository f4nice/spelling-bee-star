<script setup>
import WordDetailHeadingActions from "./WordDetailHeadingActions.vue";
import WordDetailTitleStack from "./WordDetailTitleStack.vue";

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
  refreshWord: {
    type: Function,
    required: true,
  },
});
</script>

<template>
  <div class="detail-heading">
    <WordDetailTitleStack
      :data="data"
      :word-edit="wordEdit"
      :save-word-field="saveWordField"
    />
    <WordDetailHeadingActions :can-edit="data.can_edit" :refresh-word="refreshWord" />
  </div>
</template>
