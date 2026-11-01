<script setup>
import { ref } from "vue";
import { fetchJson } from "../utils.js";

const props = defineProps({ settings: { type: Object, required: true } });
const currentSettings = ref({ ...props.settings });
const passwordDraft = ref({ newPassword: "", confirmPassword: "", adminPassword: "" });
const saving = ref(false);
const notice = ref("");
const failed = ref(false);

async function saveDeletePassword() {
  if (saving.value) return;
  notice.value = "";
  failed.value = false;
  const draft = passwordDraft.value;
  if (!draft.newPassword && !draft.confirmPassword) {
    draft.adminPassword = "";
    notice.value = "未填写新密码，现有删除密码保持不变。";
    return;
  }
  if (draft.newPassword.length < 6 || draft.newPassword.length > 128 || draft.newPassword !== draft.confirmPassword) {
    failed.value = true;
    notice.value = "请输入 6–128 位新密码，并确保两次输入一致。";
    return;
  }
  if (!draft.adminPassword) {
    failed.value = true;
    notice.value = "请输入当前管理员的登录密码确认修改。";
    return;
  }
  saving.value = true;
  try {
    const response = await fetchJson("/api/vue/admin/site/delete-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...draft }),
    });
    currentSettings.value = response.deletePassword;
    passwordDraft.value = { newPassword: "", confirmPassword: "", adminPassword: "" };
    notice.value = response.changed ? "删除密码已更新，立即生效。" : "现有删除密码保持不变。";
  } catch (error) {
    failed.value = true;
    notice.value = error.message || "保存失败，现有删除密码保持不变。";
  } finally {
    passwordDraft.value.adminPassword = "";
    saving.value = false;
  }
}
</script>

<template>
  <section class="site-delete-security" aria-labelledby="site-delete-security-heading">
    <div class="site-delete-security-heading">
      <div>
        <p class="section-kicker">SECURITY</p>
        <h3 id="site-delete-security-heading">删除安全设置</h3>
        <p>用于删除单词表和单词组，全站共用。只有管理员可以修改，与账号登录密码相互独立。</p>
      </div>
      <span class="site-delete-security-status">{{ currentSettings.usesServerPassword ? "沿用现有服务器密码" : "已设置后台专用密码" }}</span>
    </div>
    <p class="site-delete-security-note">不填写新密码就不会更改；现有密码不会显示或回填。修改不会影响词表、学习记录、图片和音频。</p>
    <form @submit.prevent="saveDeletePassword">
      <div class="site-delete-security-fields">
        <label>
          <span>新删除密码</span>
          <input v-model="passwordDraft.newPassword" type="password" autocomplete="new-password" maxlength="128" placeholder="6–128 位，留空不修改" :disabled="saving || !currentSettings.canChange">
        </label>
        <label>
          <span>确认新删除密码</span>
          <input v-model="passwordDraft.confirmPassword" type="password" autocomplete="new-password" maxlength="128" placeholder="再次输入新密码" :disabled="saving || !currentSettings.canChange">
        </label>
        <label>
          <span>管理员登录密码</span>
          <input v-model="passwordDraft.adminPassword" type="password" autocomplete="current-password" maxlength="128" placeholder="确认当前管理员身份" :disabled="saving || !currentSettings.canChange">
        </label>
      </div>
      <footer>
        <span v-if="!currentSettings.canChange">持久化存储尚未配置，请联系服务器管理员。</span>
        <span v-else-if="currentSettings.updatedAt">最近更新：{{ currentSettings.updatedAt }}</span>
        <span v-else>当前密码保持不变，保存新密码后立即生效。</span>
        <button class="challenge-button" type="submit" :disabled="saving || !currentSettings.canChange">{{ saving ? "保存中…" : "保存删除密码" }}</button>
      </footer>
    </form>
    <p v-if="notice" class="site-delete-security-notice" :class="{ 'is-error': failed }" role="status">{{ notice }}</p>
  </section>
</template>

<style scoped>
.site-delete-security { margin-top: 24px; padding: 24px; border: 1px solid #bdddd1; border-radius: 16px; background: linear-gradient(135deg, #f2faf7, #fff); }
.site-delete-security-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.site-delete-security h3 { margin: 5px 0 8px; font-size: 22px; }
.site-delete-security p { color: #52687b; line-height: 1.65; }
.site-delete-security-status { flex-shrink: 0; padding: 7px 12px; border-radius: 999px; background: #e0f4eb; color: #126b53; font-size: 12px; font-weight: 700; }
.site-delete-security-note { margin: 12px 0 18px; font-size: 13px; }
.site-delete-security-fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.site-delete-security-fields label { display: grid; gap: 8px; color: #324c60; font-weight: 600; }
.site-delete-security-fields input { width: 100%; min-width: 0; }
.site-delete-security footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 18px; color: #52687b; font-size: 13px; }
.site-delete-security-notice { margin: 14px 0 0; color: #126b53 !important; }
.site-delete-security-notice.is-error { color: #b43424 !important; }
@media (max-width: 900px) { .site-delete-security-heading, .site-delete-security footer { flex-direction: column; align-items: stretch; } .site-delete-security-fields { grid-template-columns: 1fr; } .site-delete-security-status { align-self: flex-start; } }
</style>
