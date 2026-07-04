<script setup>
import { computed, ref } from "vue";
import { Settings } from "lucide-vue-next";
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
  sequence: {
    type: Number,
    default: 0,
  },
  showManage: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["manage"]);
const suppressOpen = ref(false);
let suppressOpenTimer = 0;
const sequenceLabel = computed(() => (props.sequence > 0 ? String(props.sequence).padStart(2, "0") : ""));

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

function manageList() {
  emit("manage", props.card);
}
</script>

<template>
  <article class="word-card list-card" @dragstart.capture="markDragIntent" @dragend.capture="releaseDragIntent">
    <span v-if="sequenceLabel" class="list-sequence-badge">#{{ sequenceLabel }}</span>
    <button
      v-if="showManage"
      class="list-card-manage-button"
      type="button"
      :aria-label="`管理 ${card.list.name}`"
      @click.stop="manageList"
    >
      <Settings :size="15" aria-hidden="true" />
      <span>管理</span>
    </button>
    <button class="list-card-link plain-card-button" type="button" @click="openList">
      <WordListCardMedia :card="card" :fallback-letter="fallbackLetter" />
      <WordListCardBody :card="card" :show-challenge="showChallenge" />
    </button>

    <WordListChallengeProgress v-if="showChallenge" :card="card" :go="go" />
  </article>
</template>
