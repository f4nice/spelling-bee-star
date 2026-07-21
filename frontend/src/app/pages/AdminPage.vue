<script setup>
import { computed, ref } from "vue";
import { Eye, EyeOff } from "lucide-vue-next";
import VersionStamp from "../components/VersionStamp.vue";
import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
});

const users = ref((props.data.users || []).map(createEditableUser));
const savingPhones = ref([]);
const visiblePasswordPhones = ref([]);
const notice = ref("");
const newUser = ref({ phone: "", username: "", role: "viewer", loginPassword: "" });
const catWorldPricing = ref(normalizeCatWorldPricing(props.data.catWorldPricing || {}));
const savingPriceItemId = ref("");
const savingCatWorldSettings = ref(false);
const catWorldResetPassword = ref("");
const resettingCatWorld = ref(false);
const catMovementSpeedDraft = ref(Number(catWorldPricing.value.settings?.movementSpeed || 1));
const priceDrafts = ref(
  Object.fromEntries((catWorldPricing.value.items || []).map((item) => [item.id, Number(item.cost || 0)])),
);
const adminSections = [
  { key: "planning", label: "规划", description: "登录、权限、AI 和积分体系的管理蓝图。" },
  { key: "users", label: "用户中心", description: "管理昵称、登录密码、角色和后台权限。" },
  { key: "site", label: "网站管理", description: "查看站点版本、登录方式和默认服务。" },
  { key: "catShop", label: "猫咪商城", description: "规划猫咪世界商品和积分价格。" },
];
const activeAdminSection = ref("planning");
const activeSection = computed(
  () => adminSections.find((section) => section.key === activeAdminSection.value) || adminSections[0],
);
const pricingItemsByCategory = computed(() => {
  const groups = {};
  for (const item of catWorldPricing.value.items || []) {
    groups[item.category] = [...(groups[item.category] || []), item];
  }
  return groups;
});
const activePricingCategory = ref(catWorldPricing.value.plans?.[0]?.category || "");
const activePricingPlan = computed(
  () => (catWorldPricing.value.plans || []).find((plan) => plan.category === activePricingCategory.value)
    || catWorldPricing.value.plans?.[0]
    || null,
);
const activePricingItems = computed(
  () => (activePricingPlan.value ? pricingItemsByCategory.value[activePricingPlan.value.category] || [] : []),
);
const catMovementSpeedLimits = computed(() => ({
  min: Number(catWorldPricing.value.settings?.limits?.movementSpeed?.min ?? 0.4),
  max: Number(catWorldPricing.value.settings?.limits?.movementSpeed?.max ?? 2),
  step: Number(catWorldPricing.value.settings?.limits?.movementSpeed?.step ?? 0.05),
}));
const catMovementSpeedLabel = computed(() => `${clampCatMovementSpeed(catMovementSpeedDraft.value).toFixed(2)}x`);
const siteSummaryCards = computed(() => [
  { label: "登录方式", value: "手机号 + 密码", detail: "手机号仍是唯一登录标识，页面只展示昵称。" },
  { label: "图片 AI", value: `${props.data.imageAiOptions?.length || 0} 项`, detail: "在用户中心为不同用户选择默认图片 AI。" },
  { label: "音频 AI", value: `${props.data.audioAiOptions?.length || 0} 项`, detail: "在用户中心为不同用户选择默认音频服务。" },
  { label: "声音", value: `${props.data.voiceOptions?.length || 0} 项`, detail: "可配置女声或男声作为默认声音。" },
]);

function finiteNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizedSpeed(value, fallback = 1, min = 0.4, max = 2) {
  const lower = finiteNumber(min, 0.4);
  const upper = finiteNumber(max, 2);
  const number = Number(value);
  const speed = Number.isFinite(number) ? number : fallback;
  return Math.round(Math.min(Math.max(speed, lower), upper) * 100) / 100;
}

function normalizeCatWorldPricing(source = {}) {
  const rawSettings = source.settings || {};
  const rawLimits = rawSettings.limits?.movementSpeed || {};
  const speedLimits = {
    min: finiteNumber(rawLimits.min, 0.4),
    max: finiteNumber(rawLimits.max, 2),
    step: finiteNumber(rawLimits.step, 0.05),
  };
  return {
    plans: Array.isArray(source.plans) ? source.plans : [],
    items: Array.isArray(source.items) ? source.items : [],
    settings: {
      ...rawSettings,
      movementSpeed: normalizedSpeed(rawSettings.movementSpeed, 1, speedLimits.min, speedLimits.max),
      defaults: {
        movementSpeed: 1,
        ...(rawSettings.defaults || {}),
      },
      limits: {
        ...(rawSettings.limits || {}),
        movementSpeed: speedLimits,
      },
    },
  };
}

function clampCatMovementSpeed(value) {
  const limits = catMovementSpeedLimits.value;
  return normalizedSpeed(value, catWorldPricing.value.settings?.movementSpeed || 1, limits.min, limits.max);
}

function applyCatWorldPricing(nextPricing) {
  catWorldPricing.value = normalizeCatWorldPricing(nextPricing || catWorldPricing.value);
  priceDrafts.value = Object.fromEntries((catWorldPricing.value.items || []).map((item) => [item.id, Number(item.cost || 0)]));
  catMovementSpeedDraft.value = Number(catWorldPricing.value.settings?.movementSpeed || 1);
  if (!(catWorldPricing.value.plans || []).some((plan) => plan.category === activePricingCategory.value)) {
    activePricingCategory.value = catWorldPricing.value.plans?.[0]?.category || "";
  }
}

function createEditableUser(user) {
  return {
    ...user,
    permissions: { ...(user.permissions || {}) },
    loginPassword: "",
  };
}

function isSaving(phone) {
  return savingPhones.value.includes(phone);
}

function isPasswordVisible(phone) {
  return visiblePasswordPhones.value.includes(phone);
}

function setSaving(phone, saving) {
  savingPhones.value = saving
    ? [...new Set([...savingPhones.value, phone])]
    : savingPhones.value.filter((item) => item !== phone);
}

function togglePasswordVisibility(phone) {
  visiblePasswordPhones.value = isPasswordVisible(phone)
    ? visiblePasswordPhones.value.filter((item) => item !== phone)
    : [...new Set([...visiblePasswordPhones.value, phone])];
}

function defaultPermissions(role) {
  const keys = (props.data.permissionOptions || []).map((item) => item.key);
  if (role === "admin") return Object.fromEntries(keys.map((key) => [key, true]));
  if (role === "teacher") {
    return Object.fromEntries(
      keys.map((key) => [
        key,
        ["word_edit", "image_manage", "audio_manage", "import_manage", "challenge_manage"].includes(key),
      ]),
    );
  }
  return Object.fromEntries(keys.map((key) => [key, key === "challenge_manage"]));
}

function applyRoleDefaults(user) {
  user.permissions = defaultPermissions(user.role);
}

async function saveUser(user) {
  setSaving(user.phone, true);
  notice.value = "";
  try {
    const result = await fetchJson("/api/vue/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(user),
    });
    users.value = (result.users || []).map(createEditableUser);
    notice.value = `${result.user?.username || user.phone} 已保存。`;
    return true;
  } catch (error) {
    notice.value = error.message || "保存失败。";
    return false;
  } finally {
    setSaving(user.phone, false);
  }
}

async function addUser() {
  const phone = newUser.value.phone.trim();
  if (!phone) {
    notice.value = "请输入手机号。";
    return;
  }
  const draft = {
    phone,
    username: newUser.value.username.trim(),
    role: newUser.value.role,
    loginPassword: newUser.value.loginPassword.trim(),
    permissions: defaultPermissions(newUser.value.role),
    imageAiValue: props.data.imageAiOptions?.[0]?.value || "dashscope:wan2.7-image-pro",
    audioAiProvider: props.data.audioAiOptions?.[0]?.provider || "openai",
    audioVoiceGender: "female",
    isActive: true,
  };
  if (await saveUser(draft)) {
    newUser.value = { phone: "", username: "", role: "viewer", loginPassword: "" };
  }
}

function resetPrice(item) {
  priceDrafts.value = { ...priceDrafts.value, [item.id]: Number(item.defaultCost || item.cost || 0) };
}

function selectPricingCategory(plan) {
  activePricingCategory.value = plan.category;
}

async function savePrice(item) {
  const cost = Number(priceDrafts.value[item.id]);
  if (!Number.isFinite(cost) || cost < 0) {
    notice.value = "请输入有效积分价格。";
    return;
  }
  savingPriceItemId.value = item.id;
  notice.value = "";
  try {
    const result = await fetchJson(routeApiPaths.adminCatWorldPricing(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ itemId: item.id, cost: Math.round(cost) }),
    });
    applyCatWorldPricing(result.catWorldPricing);
    notice.value = `${item.label} 价格已更新。`;
  } catch (error) {
    notice.value = error.message || "价格保存失败。";
  } finally {
    savingPriceItemId.value = "";
  }
}

async function saveCatWorldSettings() {
  const speed = clampCatMovementSpeed(catMovementSpeedDraft.value);
  catMovementSpeedDraft.value = speed;
  savingCatWorldSettings.value = true;
  notice.value = "";
  try {
    const result = await fetchJson(routeApiPaths.adminCatWorldSettings(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ movementSpeed: speed }),
    });
    applyCatWorldPricing(result.catWorldPricing);
    notice.value = `猫咪移动速度已更新为 ${speed.toFixed(2)}x。`;
  } catch (error) {
    notice.value = error.message || "猫咪移动速度保存失败。";
  } finally {
    savingCatWorldSettings.value = false;
  }
}

async function resetCatWorldData() {
  const password = catWorldResetPassword.value.trim();
  if (!password) {
    notice.value = "请输入当前后台账号的登录密码。";
    return;
  }
  resettingCatWorld.value = true;
  notice.value = "";
  try {
    const result = await fetchJson(routeApiPaths.adminCatWorldReset(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    applyCatWorldPricing(result.catWorldPricing);
    const deleted = result.deleted || {};
    notice.value = `猫咪世界测试数据已清零：状态 ${deleted.state || 0} 条，每日日志 ${deleted.dailyLogs || 0} 条。`;
    catWorldResetPassword.value = "";
  } catch (error) {
    notice.value = error.message || "猫咪世界清零失败。";
  } finally {
    resettingCatWorld.value = false;
  }
}
</script>

<template>
  <section class="admin-page">
    <div class="admin-workspace">
      <aside class="panel admin-section-nav" aria-label="后台管理分区">
        <div class="admin-nav-account">
          <span>当前账号</span>
          <strong>{{ data.currentUser.username || "管理员" }}</strong>
        </div>
        <button
          v-for="section in adminSections"
          :key="section.key"
          type="button"
          :class="{ active: activeAdminSection === section.key }"
          @click="activeAdminSection = section.key"
        >
          <strong>{{ section.label }}</strong>
          <span>{{ section.description }}</span>
        </button>
      </aside>

      <main class="admin-main-panel">
        <header class="panel admin-hero">
          <div>
            <p class="section-kicker">ADMIN</p>
            <h1>{{ activeSection.label }}</h1>
            <p>{{ activeSection.description }}</p>
          </div>
          <div class="admin-current-user">
            <span>当前账号</span>
            <strong>{{ data.currentUser.username || data.currentUser.phoneMasked }}</strong>
            <em>{{ data.currentUser.phoneMasked }}</em>
          </div>
        </header>

        <p v-if="notice" class="notice admin-notice">{{ notice }}</p>

        <section v-if="activeAdminSection === 'planning'" class="panel admin-planning-panel">
          <div class="admin-section-head">
            <div>
              <p class="section-kicker">PLAN</p>
              <h2>后台规划</h2>
              <p>这里先做全局策略总览，后续新的管理模块都从左侧栏拆进来。</p>
            </div>
          </div>
          <div class="admin-planning-grid">
            <article>
              <strong>登录规划</strong>
              <span>手机号 + 密码</span>
              <p>手机号作为唯一登录标识，页面入口只显示后台设置的昵称。</p>
            </article>
            <article>
              <strong>权限规划</strong>
              <span>{{ data.roleOptions?.length || 0 }} 类角色</span>
              <p>管理员、老师、只读角色分别控制后台和业务功能权限。</p>
            </article>
            <article>
              <strong>AI 规划</strong>
              <span>图片 / 音频</span>
              <p>图片 AI、音频 AI、默认声音都按用户独立配置。</p>
            </article>
            <article>
              <strong>猫咪经济</strong>
              <span>{{ catWorldPricing.items?.length || 0 }} 个商品</span>
              <p>猫咪商城价格从后台维护，前台实时显示积分扣取。</p>
            </article>
          </div>
        </section>

        <section v-if="activeAdminSection === 'users'" class="admin-section-stack">
          <section class="panel admin-create-panel">
            <div>
              <h2>新增用户</h2>
              <p>手机号是唯一登录标识，昵称用于前台右上角显示。</p>
            </div>
            <input v-model="newUser.phone" type="tel" inputmode="numeric" placeholder="手机号">
            <input v-model="newUser.loginPassword" type="password" autocomplete="new-password" placeholder="登录密码">
            <input v-model="newUser.username" type="text" placeholder="昵称">
            <select v-model="newUser.role">
              <option v-for="role in data.roleOptions" :key="role.key" :value="role.key">{{ role.label }}</option>
            </select>
            <button class="challenge-button" type="button" @click="addUser">添加</button>
          </section>

          <section class="admin-user-list" aria-label="后台用户权限">
            <article v-for="user in users" :key="user.phone" class="panel admin-user-card">
              <header class="admin-user-head">
                <div class="admin-user-identity">
                  <span>{{ user.phoneMasked }}</span>
                  <div class="admin-user-head-fields">
                    <input v-model="user.username" type="text" aria-label="昵称">
                    <label class="admin-header-password">
                      <span>登录密码 · {{ user.hasLoginPassword ? "已设置" : "未设置" }}</span>
                      <div class="admin-password-field">
                        <input
                          v-model="user.loginPassword"
                          :type="isPasswordVisible(user.phone) ? 'text' : 'password'"
                          autocomplete="new-password"
                          :placeholder="user.hasLoginPassword ? '留空不改' : '设置登录密码'"
                        >
                        <button
                          class="admin-password-toggle"
                          type="button"
                          :aria-label="isPasswordVisible(user.phone) ? '隐藏登录密码' : '显示登录密码'"
                          :title="isPasswordVisible(user.phone) ? '隐藏登录密码' : '显示登录密码'"
                          @click="togglePasswordVisibility(user.phone)"
                        >
                          <EyeOff v-if="isPasswordVisible(user.phone)" :size="18" aria-hidden="true" />
                          <Eye v-else :size="18" aria-hidden="true" />
                        </button>
                      </div>
                    </label>
                  </div>
                </div>
                <label class="admin-active-switch">
                  <input v-model="user.isActive" type="checkbox">
                  <span>{{ user.isActive ? "启用" : "停用" }}</span>
                </label>
              </header>

              <div class="admin-user-grid">
                <label>
                  <span>角色</span>
                  <select v-model="user.role" @change="applyRoleDefaults(user)">
                    <option v-for="role in data.roleOptions" :key="role.key" :value="role.key">{{ role.label }}</option>
                  </select>
                </label>
                <label>
                  <span>图片 AI</span>
                  <select v-model="user.imageAiValue" class="admin-model-select">
                    <option v-for="option in data.imageAiOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
                <label>
                  <span>音频 AI</span>
                  <select v-model="user.audioAiProvider">
                    <option v-for="option in data.audioAiOptions" :key="option.provider" :value="option.provider">{{ option.label }}</option>
                  </select>
                </label>
                <label>
                  <span>默认声音</span>
                  <select v-model="user.audioVoiceGender">
                    <option v-for="option in data.voiceOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
                  </select>
                </label>
              </div>

              <div class="admin-permission-grid">
                <label v-for="permission in data.permissionOptions" :key="permission.key" class="admin-permission-chip">
                  <input v-model="user.permissions[permission.key]" type="checkbox">
                  <span>{{ permission.label }}</span>
                </label>
              </div>

              <footer class="admin-user-actions">
                <span>{{ user.role === "admin" ? "管理员拥有全部权限" : "按勾选项控制后台权限" }}</span>
                <button class="challenge-button" type="button" :disabled="isSaving(user.phone)" @click="saveUser(user)">
                  {{ isSaving(user.phone) ? "保存中..." : "保存设置" }}
                </button>
              </footer>
            </article>
          </section>
        </section>

        <section v-if="activeAdminSection === 'site'" class="panel admin-site-panel">
          <div class="admin-section-head">
            <div>
              <p class="section-kicker">SITE</p>
              <h2>网站管理</h2>
              <p>当前先集中展示站点策略和默认服务，后续可继续拆入备案、版本和全局开关。</p>
            </div>
          </div>
          <div class="admin-site-grid">
            <article v-for="card in siteSummaryCards" :key="card.label">
              <span>{{ card.label }}</span>
              <strong>{{ card.value }}</strong>
              <p>{{ card.detail }}</p>
            </article>
          </div>
          <VersionStamp label="后台管理" />
        </section>

        <section v-if="activeAdminSection === 'catShop'" class="panel admin-pricing-panel">
          <div class="admin-section-head">
            <div>
              <p class="section-kicker">CAT WORLD</p>
              <h2>猫咪商品定价</h2>
              <p>按积分规划商品价格，前台购买时会显示扣除积分和剩余积分。</p>
            </div>
          </div>

          <div class="admin-pricing-plans" role="tablist" aria-label="猫咪商品分类">
            <button
              v-for="plan in catWorldPricing.plans || []"
              :key="plan.category"
              class="admin-pricing-plan-card"
              :class="{ active: activePricingPlan?.category === plan.category }"
              type="button"
              role="tab"
              :aria-selected="activePricingPlan?.category === plan.category"
              @click="selectPricingCategory(plan)"
            >
              <strong>{{ plan.label }}</strong>
              <span>{{ plan.range }} 积分</span>
              <p>{{ plan.strategy }}</p>
            </button>
          </div>

          <div v-if="activePricingPlan" class="admin-pricing-groups">
            <section class="admin-pricing-group admin-pricing-group-active">
              <header class="admin-pricing-group-head">
                <div>
                  <h3>{{ activePricingPlan.label }}</h3>
                  <p>{{ activePricingPlan.strategy }}</p>
                </div>
                <span>{{ activePricingItems.length }} 个商品</span>
              </header>
              <div class="admin-pricing-list">
                <article v-for="item in activePricingItems" :key="item.id" class="admin-price-row">
                  <div>
                    <strong>{{ item.label }}</strong>
                    <span>{{ item.englishName }} · 默认 {{ item.defaultCost }} 积分</span>
                    <em v-if="item.targetDecorLabel">用于 {{ item.targetDecorLabel }}</em>
                  </div>
                  <label>
                    <span>当前价格</span>
                    <input v-model.number="priceDrafts[item.id]" type="number" min="0" max="99999" step="10">
                  </label>
                  <button class="secondary-button compact-button" type="button" @click="resetPrice(item)">默认价</button>
                  <button class="challenge-button compact-button" type="button" :disabled="savingPriceItemId === item.id" @click="savePrice(item)">
                    {{ savingPriceItemId === item.id ? "保存中" : "保存" }}
                  </button>
                </article>
              </div>
            </section>
          </div>
          <p v-else class="empty-state compact-empty-state">还没有可配置的猫咪商品分类。</p>
        </section>

        <section v-if="activeAdminSection === 'catShop'" class="panel admin-cat-world-operations-panel">
          <div class="admin-section-head">
            <div>
              <p class="section-kicker">CAT WORLD SETTINGS</p>
              <h2>猫咪世界设置</h2>
              <p>调整活动室运行参数，或清理当前账号的测试数据。</p>
            </div>
          </div>

          <section class="admin-cat-world-settings-panel">
            <div>
              <strong>猫咪移动速度</strong>
              <p>控制活动室里所有猫走动、靠近喜欢道具和回休息点的整体速度。</p>
            </div>
            <label class="admin-cat-speed-slider">
              <span>速度倍率</span>
              <input
                v-model.number="catMovementSpeedDraft"
                type="range"
                :min="catMovementSpeedLimits.min"
                :max="catMovementSpeedLimits.max"
                :step="catMovementSpeedLimits.step"
              >
            </label>
            <label class="admin-cat-speed-number">
              <span>当前值</span>
              <input
                v-model.number="catMovementSpeedDraft"
                type="number"
                :min="catMovementSpeedLimits.min"
                :max="catMovementSpeedLimits.max"
                :step="catMovementSpeedLimits.step"
              >
            </label>
            <button class="challenge-button compact-button" type="button" :disabled="savingCatWorldSettings" @click="saveCatWorldSettings">
              {{ savingCatWorldSettings ? "保存中" : `保存 ${catMovementSpeedLabel}` }}
            </button>
          </section>

          <section class="admin-reset-panel">
            <div>
              <strong>测试数据清零</strong>
              <p>删除当前账号的猫咪、库存、布局、食物和每日日志，商品价格不会受影响。</p>
            </div>
            <input
              v-model="catWorldResetPassword"
              type="password"
              autocomplete="current-password"
              placeholder="输入后台登录密码"
            >
            <button class="danger-button compact-button" type="button" :disabled="resettingCatWorld" @click="resetCatWorldData">
              {{ resettingCatWorld ? "清零中..." : "一键清零" }}
            </button>
          </section>
        </section>
      </main>
    </div>
  </section>
</template>
