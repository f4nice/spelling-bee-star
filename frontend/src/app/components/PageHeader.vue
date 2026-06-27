<script setup>
import { computed } from "vue";

const props = defineProps({
  routeTitle: {
    type: String,
    required: true,
  },
  route: {
    type: Object,
    default: null,
  },
  data: {
    type: Object,
    default: null,
  },
  go: {
    type: Function,
    default: null,
  },
});

const returnList = computed(() => {
  if (props.route?.name !== "wordDetail") return null;
  const nav = props.data?.navigation || {};
  if (!nav.list_id) return null;
  return {
    id: nav.list_id,
    name: nav.word_list_name || "单词表",
  };
});

function goBackToList(event) {
  if (!returnList.value || !props.go) return;
  event.preventDefault();
  props.go(`/lists/${returnList.value.id}`);
}
</script>

<template>
  <section class="panel app-page-heading">
    <div class="page-heading-title">
      <p class="section-kicker">SpeakEasy</p>
      <h1>{{ routeTitle }}</h1>
    </div>
    <a
      v-if="returnList"
      class="secondary-button page-heading-return-button"
      :href="`/lists/${returnList.id}`"
      @click="goBackToList"
    >
      返回{{ returnList.name }}
    </a>
  </section>
</template>

<style scoped>
.app-page-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-heading-title {
  min-width: 0;
}

.page-heading-return-button {
  flex: 0 0 auto;
  margin-left: auto;
  border-color: rgba(16, 128, 91, 0.32);
  background: #eaf7f1;
  color: #0b6f4c;
  text-decoration: none;
  white-space: nowrap;
}

.page-heading-return-button:hover,
.page-heading-return-button:focus-visible {
  border-color: #0f7f59;
  background: #0f7f59;
  color: #fff;
}

@media (max-width: 720px) {
  .app-page-heading {
    align-items: flex-start;
  }
}
</style>
