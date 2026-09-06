<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import NewspaperHero from "../components/NewspaperHero.vue";
import NewspaperSection from "../components/NewspaperSection.vue";
import { writeApiCache } from "../apiCache.js";
import { fetchJson } from "../utils.js";

const props = defineProps([
  "data",
  "go"
]);
const newspaper = ref(props.data);
const busy = ref(false);
const notice = ref("");
let timer;
let disposed = false;
const refreshing = computed(() => busy.value || Boolean(newspaper.value.cache?.refreshing));
const status = computed(() => {
  if (notice.value) return notice.value;
  if (refreshing.value) return "正在后台更新，已有内容可以继续阅读。";
  if (newspaper.value.cache?.error) return newspaper.value.cache.error;
  const loaded = newspaper.value.loaded_at;
  return loaded ? `已缓存 · 上次更新 ${new Date(loaded).toLocaleString("zh-CN", { hour12: false })}` : "暂无缓存内容，点击更新小报获取。";
});

function schedulePoll() {
  clearTimeout(timer);
  if (!disposed && newspaper.value.cache?.refreshing) timer = setTimeout(() => updateNewspaper(false), 2500);
}

async function updateNewspaper(force = true) {
  if (busy.value || disposed) return;
  clearTimeout(timer);
  busy.value = true;
  notice.value = "";
  try {
    const result = await fetchJson(force ? "/api/vue/newspaper/refresh" : "/api/vue/newspaper", {
      method: force ? "POST" : "GET", skipCache: true,
    });
    if (disposed) return;
    newspaper.value = result;
    writeApiCache("/api/vue/newspaper", result);
  } catch (error) {
    notice.value = error?.message || "更新暂时失败，已有内容可以继续阅读。";
  } finally {
    busy.value = false;
    schedulePoll();
  }
}

watch(() => props.data, (value) => { newspaper.value = value; schedulePoll(); }, { immediate: true });
onBeforeUnmount(() => { disposed = true; clearTimeout(timer); });
</script>

<template>
  <NewspaperHero :source-url="newspaper.source_url || 'https://www.chinadaily.com.cn/'" :refreshing="refreshing" :status="status" @refresh="updateNewspaper(true)" />
  <section class="newspaper-layout">
    <NewspaperSection
      v-for="section in newspaper.sections"
      :key="section.key"
      :section="section"
      :go="go"
    />
  </section>
</template>
