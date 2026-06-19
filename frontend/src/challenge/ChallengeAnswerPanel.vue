<script setup>
import { nextTick, onMounted, ref, watch } from "vue";

const props = defineProps({
  spelling: {
    type: String,
    required: true,
  },
  submitting: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:spelling", "submit"]);
const spellingInput = ref(null);

function submitAnswer() {
  if (!props.spelling.trim() || props.submitting) return;
  emit("submit");
}

function focusInput() {
  spellingInput.value?.focus();
}

onMounted(() => {
  nextTick(focusInput);
});

watch(
  () => props.spelling,
  (value) => {
    if (value === "") nextTick(focusInput);
  },
);
</script>

<template>
  <div class="challenge-answer-panel" role="group" aria-label="拼写答案">
    <input
      ref="spellingInput"
      :value="spelling"
      class="challenge-spelling-input"
      autocomplete="off"
      autocapitalize="off"
      spellcheck="false"
      placeholder="输入英文拼写"
      @input="emit('update:spelling', $event.target.value)"
      @keydown.enter.prevent="submitAnswer"
    >
    <div class="challenge-actions">
      <button type="button" :disabled="submitting || !spelling.trim()" @click="submitAnswer">
        {{ submitting ? "提交中..." : "提交答案" }}
      </button>
    </div>
  </div>
</template>
