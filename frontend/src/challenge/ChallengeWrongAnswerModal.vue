<script setup>
import { nextTick, onMounted, onUnmounted, ref } from "vue";

const props = defineProps({
  answer: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["confirm"]);
const confirmButton = ref(null);

function confirm() {
  emit("confirm");
}

function handleKeydown(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    confirm();
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
  nextTick(() => confirmButton.value?.focus());
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <div class="challenge-answer-modal-backdrop" role="presentation">
    <section class="challenge-answer-modal" role="dialog" aria-modal="true" aria-labelledby="wrongAnswerTitle">
      <p class="section-kicker">拼写错误</p>
      <h2 id="wrongAnswerTitle">正确答案是</h2>
      <strong class="challenge-correct-answer">{{ props.answer.correct_spelling }}</strong>
      <p v-if="props.answer.typed" class="challenge-typed-answer">
        你输入的是：<span>{{ props.answer.typed }}</span>
      </p>
      <button ref="confirmButton" type="button" class="challenge-answer-confirm" @click="confirm">
        我知道了
      </button>
    </section>
  </div>
</template>
