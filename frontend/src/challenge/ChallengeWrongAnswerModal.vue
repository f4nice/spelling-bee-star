<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";

const props = defineProps({
  answer: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["confirm"]);
const confirmButton = ref(null);

const diffLetters = computed(() => {
  const correct = String(props.answer.correct_spelling || "");
  const typed = String(props.answer.typed || "");
  return Array.from(correct).map((letter, index) => {
    const typedLetter = typed[index] || "";
    if (!typedLetter) return { letter, status: "missing" };
    if (typedLetter.toLowerCase() === letter.toLowerCase()) return { letter, status: "match" };
    return { letter, status: "wrong", typed: typedLetter };
  });
});

const extraLetters = computed(() => {
  const correctLength = Array.from(String(props.answer.correct_spelling || "")).length;
  return Array.from(String(props.answer.typed || "")).slice(correctLength);
});

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
      <strong class="challenge-correct-answer challenge-answer-diff" :aria-label="props.answer.correct_spelling">
        <span
          v-for="(item, index) in diffLetters"
          :key="`${item.letter}-${index}`"
          class="challenge-answer-letter"
          :class="`is-${item.status}`"
          :title="item.status === 'wrong' ? `你输入了 ${item.typed}` : ''"
        >{{ item.letter }}</span>
      </strong>
      <p v-if="props.answer.typed" class="challenge-typed-answer">
        你输入的是：<span>{{ props.answer.typed }}</span>
      </p>
      <p v-if="extraLetters.length" class="challenge-extra-answer">
        多输入：<span>{{ extraLetters.join("") }}</span>
      </p>
      <button ref="confirmButton" type="button" class="challenge-answer-confirm" @click="confirm">
        我知道了
      </button>
    </section>
  </div>
</template>
