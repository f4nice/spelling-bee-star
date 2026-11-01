<script setup>
import { computed, ref } from "vue";
import { clearApiCache } from "../apiCache.js";
import AppBrandLink from "./AppBrandLink.vue";
import AppDailyQuote from "./AppDailyQuote.vue";
import { buildSidebarNavItems } from "../sidebarNav.js";

const props = defineProps({
  route: {
    type: Object,
    required: true,
  },
  shell: {
    type: Object,
    required: true,
  },
  go: {
    type: Function,
    required: true,
  },
});

const accountName = computed(() => props.shell.currentUser?.username || "我的账号");
const phoneLabel = computed(() => props.shell.currentUser?.phoneMasked || "");
const navItems = computed(() => buildSidebarNavItems({ route: props.route, shell: props.shell }));
const activeNavLabel = computed(() => navItems.value.find((item) => item.active)?.label || "导航");
const scopeNotice = ref("");
const switchingScope = ref(false);
async function changeDataScope(event) {
  switchingScope.value = true;
  scopeNotice.value = "";
  try {
    const response = await fetch("/api/vue/data-scope", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerId: Number(event.target.value) }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "切换失败");
    clearApiCache();
    window.location.assign("/");
  } catch (error) {
    scopeNotice.value = error.message;
    event.target.value = String(props.shell.dataScope.ownerId);
  } finally { switchingScope.value = false; }
}
</script>

<template>
  <header class="app-topbar">
    <AppBrandLink :app-name="shell.appName" :go="go" />
    <nav class="topbar-nav" aria-label="主导航">
      <a
        v-for="item in navItems"
        :key="item.path"
        :class="{ active: item.active }"
        :href="item.path"
        @click.prevent="go(item.path)"
      >
        <span>{{ item.label }}</span>
        <em v-if="Number(item.count || 0) > 0">{{ item.count }}</em>
      </a>
    </nav>
    <details class="mobile-nav-menu">
      <summary aria-label="打开主导航">
        <strong>{{ activeNavLabel }}</strong>
      </summary>
      <nav class="mobile-nav-grid" aria-label="移动端主导航">
        <a
          v-for="item in navItems"
          :key="item.path"
          :class="{ active: item.active }"
          :href="item.path"
          @click.prevent="go(item.path); $event.currentTarget.closest('details').open = false"
        >
          <span>{{ item.label }}</span>
          <em v-if="Number(item.count || 0) > 0">{{ item.count }}</em>
        </a>
      </nav>
    </details>
    <AppDailyQuote :quote="shell.dailyQuote" />
    <details class="topbar-account-menu">
      <summary>
        <span>{{ accountName }}</span>
      </summary>
      <div class="topbar-account-panel">
        <strong>{{ accountName }}</strong>
        <span v-if="phoneLabel">{{ phoneLabel }}</span>
        <label v-if="shell.dataScope?.options?.length > 1" class="data-scope-picker">
          查看数据
          <select :value="shell.dataScope.ownerId" :disabled="switchingScope" @change="changeDataScope">
            <option v-for="owner in shell.dataScope.options" :key="owner.id" :value="owner.id">{{ owner.name }}{{ owner.isSelf ? '（我的数据）' : '（只读）' }}</option>
          </select>
        </label>
        <span v-if="scopeNotice" role="alert">{{ scopeNotice }}</span>
        <button
          v-if="shell.currentUser?.canAdmin"
          class="topbar-admin-link"
          type="button"
          @click="go('/admin')"
        >
          后台管理
        </button>
        <form method="post" action="/logout">
          <button type="submit">退出登录</button>
        </form>
      </div>
    </details>
  </header>
  <aside v-if="shell.dataScope?.readOnly" class="panel data-scope-banner" role="status">
    正在只读查看 {{ shell.dataScope.ownerName }} 的数据；不能修改或上传。可在右上角切回“我的数据”。
  </aside>
</template>
