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
    <div>
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

.page-heading-return-button {
  flex: 0 0 auto;
  text-decoration: none;
  white-space: nowrap;
}
</style>
