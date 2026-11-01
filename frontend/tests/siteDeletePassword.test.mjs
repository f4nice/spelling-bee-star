import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const component = await readFile(new URL("../src/app/components/SiteDeletePasswordSettings.vue", import.meta.url), "utf8");
const page = await readFile(new URL("../src/app/pages/AdminPage.vue", import.meta.url), "utf8");
function controls(request) {
  const saving = { value: false }, notice = { value: "" }, failed = { value: false };
  const passwordDraft = { value: { newPassword: "", confirmPassword: "", adminPassword: "" } };
  const currentSettings = { value: { usesServerPassword: true } };
  const source = component.match(/async function saveDeletePassword\(\) \{[\s\S]*?\n\}/)[0];
  const save = new Function("fetchJson", "saving", "notice", "failed", "passwordDraft", "currentSettings", `${source}; return saveDeletePassword;`)(request, saving, notice, failed, passwordDraft, currentSettings);
  return { save, saving, notice, failed, passwordDraft, currentSettings };
}
test("only administrators render the site security component", () => {
  assert.match(page, /<SiteDeletePasswordSettings v-if="data\.currentUser\?\.role === 'admin' && data\.deletePassword"/);
});
test("all credential fields are empty and masked, never loaded from the server", () => {
  for (const field of ["newPassword", "confirmPassword", "adminPassword"]) {
    assert.match(component, new RegExp(`v-model="passwordDraft\.${field}" type="password"`));
  }
  assert.doesNotMatch(component, /localStorage|sessionStorage|passwordHash|settings\.password/);
});
test("empty save preserves current password without sending a request", async () => {
  const ui = controls(() => { throw new Error("must not send"); });
  await ui.save();assert.match(ui.notice.value, /保持不变/);assert.equal(ui.saving.value, false);
});
test("mismatched confirmation and missing admin login password never send", async () => {
  const ui = controls(() => { throw new Error("must not send"); });
  ui.passwordDraft.value = { newPassword: "synthetic-new", confirmPassword: "different", adminPassword: "" };
  await ui.save();assert.equal(ui.failed.value, true);
  ui.passwordDraft.value.confirmPassword = "synthetic-new";
  await ui.save();assert.match(ui.notice.value, /管理员/);
});
test("save sends only a POST and clears secret drafts after success", async () => {
  let count = 0;
  const ui = controls(async (url, options) => {
    count++;assert.equal(url,"/api/vue/admin/site/delete-password");assert.equal(options.method,"POST");
    assert.equal(JSON.parse(options.body).adminPassword,"synthetic-login");
    return { changed:true, deletePassword:{usesServerPassword:false,canChange:true} };
  });
  ui.passwordDraft.value = { newPassword:"synthetic-new",confirmPassword:"synthetic-new",adminPassword:"synthetic-login" };
  await ui.save();assert.equal(count,1);assert.equal(ui.currentSettings.value.usesServerPassword,false);
  assert.deepEqual(ui.passwordDraft.value,{newPassword:"",confirmPassword:"",adminPassword:""});
});
test("failure clears administrator confirmation and keeps current status", async () => {
  const ui = controls(async () => { throw new Error("synthetic denied"); });
  ui.passwordDraft.value = { newPassword:"synthetic-new",confirmPassword:"synthetic-new",adminPassword:"synthetic-login" };
  await ui.save();assert.equal(ui.passwordDraft.value.adminPassword,"");assert.equal(ui.currentSettings.value.usesServerPassword,true);
  assert.equal(ui.failed.value,true);assert.equal(ui.saving.value,false);
});
test("pending save cannot be double-submitted", async () => {
  const ui = controls(() => { throw new Error("must not send"); });ui.saving.value=true;
  await ui.save();assert.equal(ui.saving.value,true);
});
