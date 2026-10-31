import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const page = await readFile(new URL("../src/app/pages/AdminPage.vue", import.meta.url), "utf8");

function functionSource(name) {
  const result = page.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}`));
  assert.ok(result, `Missing ${name}`);
  return result[0];
}

function passwordControls() {
  const hiddenPasswordPhones = { value: [] };
  return new Function("hiddenPasswordPhones", `
    ${functionSource("isPasswordVisible")}
    ${functionSource("togglePasswordVisibility")}
    return { isPasswordVisible, togglePasswordVisibility };
  `)(hiddenPasswordPhones);
}

test("new-user password is visible without changing its new-password autocomplete", () => {
  assert.match(page, /<input[^>]*v-model="newUser\.loginPassword"[^>]*type="text"[^>]*autocomplete="new-password"/);
});

test("each existing-user password draft is visible by default", () => {
  const controls = passwordControls();
  assert.equal(controls.isPasswordVisible("synthetic-user-a"), true);
  assert.equal(controls.isPasswordVisible("synthetic-user-b"), true);
  assert.match(page, /:type="isPasswordVisible\(user\.phone\) \? 'text' : 'password'"/);
});

test("optional hiding is reversible and does not affect another account", () => {
  const controls = passwordControls();
  controls.togglePasswordVisibility("synthetic-user-a");
  assert.equal(controls.isPasswordVisible("synthetic-user-a"), false);
  assert.equal(controls.isPasswordVisible("synthetic-user-b"), true);
  controls.togglePasswordVisibility("synthetic-user-a");
  assert.equal(controls.isPasswordVisible("synthetic-user-a"), true);
});

test("saved passwords are not copied into editable password drafts", () => {
  const createEditableUser = new Function(`${functionSource("createEditableUser")}; return createEditableUser;`)();
  const source = { phone: "synthetic-user", loginPassword: "synthetic-value-not-for-display", permissions: { admin: true } };
  const editable = createEditableUser(source);
  assert.equal(editable.loginPassword, "");
  assert.equal(source.loginPassword, "synthetic-value-not-for-display");
  assert.notEqual(editable.permissions, source.permissions);
});

test("destructive administrative confirmation still hides the current credential", () => {
  assert.match(page, /<input[\s\S]*?v-model="catWorldResetPassword"[\s\S]*?type="password"/);
});
