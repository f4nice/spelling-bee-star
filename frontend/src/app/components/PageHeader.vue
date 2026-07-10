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

function safeInternalReturnPath(value) {
  const text = String(value || "").trim();
  if (!text.startsWith("/") || text.startsWith("//")) return "";
  if (/[\r\n]/.test(text)) return "";
  return text;
}

const returnTarget = computed(() => {
  if (props.route?.name !== "wordDetail") return null;
  const returnTo = safeInternalReturnPath(props.route?.query?.return_to);
  if (returnTo) {
    return {
      href: returnTo,
      label: String(props.route?.query?.return_label || "上一页").trim() || "上一页",
    };
  }
  if (!returnList.value) return null;
  return {
    href: `/lists/${returnList.value.id}`,
    label: returnList.value.name,
  };
});

function goBack(event) {
  if (!returnTarget.value || !props.go) return;
  event.preventDefault();
  props.go(returnTarget.value.href);
}
</script>

<template>
  <section class="panel app-page-heading" :class="{ 'has-return-link': returnTarget }">
    <div class="page-heading-title">
      <p class="section-kicker">SpeakEasy</p>
      <h1>{{ routeTitle }}</h1>
    </div>
    <a
      v-if="returnTarget"
      class="secondary-button page-heading-return-button"
      :href="returnTarget.href"
      @click="goBack"
    >
      返回{{ returnTarget.label }}
    </a>
  </section>
</template>

<style scoped>
.app-page-heading {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 96px;
  overflow: hidden;
  padding: 20px 22px;
  border-color: rgba(29, 127, 91, 0.14);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(239, 248, 243, 0.94));
}

.app-page-heading::after {
  content: "";
  position: absolute;
  right: 22px;
  bottom: 0;
  left: 22px;
  height: 3px;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(90deg, rgba(29, 127, 91, 0.54), rgba(29, 127, 91, 0));
}

.page-heading-title {
  display: grid;
  gap: 8px;
  flex: 1 1 auto;
  min-width: 0;
}

.page-heading-title .section-kicker {
  width: fit-content;
  margin: 0;
  border-radius: 999px;
  padding: 3px 8px;
  color: var(--accent-dark);
  background: #e9f8f1;
  font-size: 11px;
  line-height: 1.2;
}

.page-heading-title h1 {
  margin: 0;
  color: var(--ink);
  font-size: 34px;
  line-height: 1.08;
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
    min-height: auto;
    padding: 18px;
  }

  .page-heading-title h1 {
    font-size: 30px;
  }
}
</style>
