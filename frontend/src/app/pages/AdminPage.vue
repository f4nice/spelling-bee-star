<script setup>
import { ref } from "vue";
import { Eye, EyeOff } from "lucide-vue-next";
import VersionStamp from "../components/VersionStamp.vue";
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
</script>

<template>
  <section class="admin-page">
    <div class="panel admin-hero">
      <div>
        <p class="section-kicker">ADMIN</p>
        <h1>后台管理</h1>
        <p>按手机号、密码管理登录用户、权限和默认 AI 服务。</p>
      </div>
      <div class="admin-current-user">
        <span>当前账号</span>
        <strong>{{ data.currentUser.username || data.currentUser.phoneMasked }}</strong>
        <em>{{ data.currentUser.phoneMasked }}</em>
      </div>
    </div>

    <section class="panel admin-create-panel">
      <div>
        <h2>新增用户</h2>
        <p>手机号是唯一登录标识，用户名只用于后台显示。</p>
      </div>
      <input v-model="newUser.phone" type="tel" inputmode="numeric" placeholder="手机号">
      <input v-model="newUser.loginPassword" type="password" autocomplete="new-password" placeholder="登录密码">
      <input v-model="newUser.username" type="text" placeholder="用户名">
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
              <input v-model="user.username" type="text" aria-label="用户名">
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
            <select v-model="user.imageAiValue">
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

    <p v-if="notice" class="notice admin-notice">{{ notice }}</p>
    <VersionStamp label="后台管理" />
  </section>
</template>
