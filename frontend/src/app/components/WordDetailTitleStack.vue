<script setup>
import { computed, nextTick, ref } from "vue";

const props = defineProps({
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

const alternateInput = ref(null);
const isEditingAlternate = ref(false);
const alternateSpellingsText = computed(() => props.wordEdit.alternate_spellings || props.data.word.alternate_spellings || "");
const hasAlternateSpellings = computed(() => Boolean(String(alternateSpellingsText.value).trim()));

async function startAlternateEdit() {
  if (!props.data.can_edit) return;
  isEditingAlternate.value = true;
  await nextTick();
  alternateInput.value?.focus();
}

async function finishAlternateEdit() {
  await props.saveWordField("alternate_spellings");
  isEditingAlternate.value = false;
}
</script>

<template>
  <div class="word-title-stack" @dblclick="startAlternateEdit">
    <h1>{{ data.word.word }}</h1>
    <p v-if="data.word.phonetic" class="phonetic">/{{ data.word.phonetic }}/</p>
    <textarea
      v-if="data.can_edit && isEditingAlternate"
      ref="alternateInput"
      v-model="wordEdit.alternate_spellings"
      class="inline-edit-input title-alternate-edit"
      rows="1"
      placeholder="其他拼法"
      @blur="finishAlternateEdit"
    ></textarea>
    <strong v-else-if="hasAlternateSpellings" class="title-alternate-text">{{ alternateSpellingsText }}</strong>
  </div>
</template>
