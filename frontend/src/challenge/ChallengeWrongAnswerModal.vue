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

function buildSpellingDiff(correctValue, typedValue) {
  const correct = Array.from(String(correctValue || ""));
  const typed = Array.from(String(typedValue || ""));
  const rows = correct.length + 1;
  const cols = typed.length + 1;
  const dp = Array.from({ length: rows }, () => Array(cols).fill(0));

  for (let i = 0; i < rows; i += 1) dp[i][0] = i;
  for (let j = 0; j < cols; j += 1) dp[0][j] = j;

  for (let i = 1; i < rows; i += 1) {
    for (let j = 1; j < cols; j += 1) {
      const same = correct[i - 1].toLowerCase() === typed[j - 1].toLowerCase();
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + (same ? 0 : 1),
      );
    }
  }

  const aligned = [];
  const extras = [];
  let i = correct.length;
  let j = typed.length;

  while (i > 0 || j > 0) {
    const current = dp[i][j];
    if (
      i > 0 &&
      j > 0 &&
      current === dp[i - 1][j - 1] + (correct[i - 1].toLowerCase() === typed[j - 1].toLowerCase() ? 0 : 1)
    ) {
      const status = correct[i - 1].toLowerCase() === typed[j - 1].toLowerCase() ? "match" : "wrong";
      aligned.unshift({ letter: correct[i - 1], status, typed: typed[j - 1] });
      i -= 1;
      j -= 1;
    } else if (i > 0 && current === dp[i - 1][j] + 1) {
      aligned.unshift({ letter: correct[i - 1], status: "missing" });
      i -= 1;
    } else {
      extras.unshift(typed[j - 1]);
      j -= 1;
    }
  }

  return { aligned, extras };
}

const spellingDiff = computed(() => buildSpellingDiff(props.answer.correct_spelling, props.answer.typed));
const diffLetters = computed(() => spellingDiff.value.aligned);
const extraLetters = computed(() => spellingDiff.value.extras);

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
          :title="item.status === 'wrong' ? `你输入了 ${item.typed}` : item.status === 'missing' ? '这里少输入了一个字母' : ''"
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
