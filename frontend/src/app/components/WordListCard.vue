<script setup>
import { ref } from "vue";
import WordListCardBody from "./WordListCardBody.vue";
import WordListCardMedia from "./WordListCardMedia.vue";
import WordListChallengeProgress from "./WordListChallengeProgress.vue";

const props = defineProps({
  card: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
  fallbackLetter: {
    type: Function,
    required: true,
  },
  showChallenge: {
    type: Boolean,
    default: false,
  },
});

const suppressOpen = ref(false);
let suppressOpenTimer = 0;

function markDragIntent() {
  window.clearTimeout(suppressOpenTimer);
  suppressOpen.value = true;
}

function releaseDragIntent() {
  window.clearTimeout(suppressOpenTimer);
  suppressOpenTimer = window.setTimeout(() => {
    suppressOpen.value = false;
  }, 260);
}

function openList() {
  if (suppressOpen.value) return;
  props.go(`/lists/${props.card.list.id}`);
}
</script>

<template>
  <article class="word-card list-card" @dragstart.capture="markDragIntent" @dragend.capture="releaseDragIntent">
    <button class="list-card-link plain-card-button" type="button" @click="openList">
      <WordListCardMedia :card="card" :fallback-letter="fallbackLetter" />
      <WordListCardBody :card="card" :show-challenge="showChallenge" />
    </button>

    <WordListChallengeProgress v-if="showChallenge" :card="card" :go="go" />
  </article>
</template>
