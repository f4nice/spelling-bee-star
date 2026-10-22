import assert from "node:assert/strict";
import test from "node:test";
import { effectScope, shallowRef } from "vue";
import { useSelectedWordImage } from "../src/app/composables/useSelectedWordImage.js";
import { useWordImageReplacement } from "../src/app/composables/useWordImageReplacement.js";
import { useWordImageActions } from "../src/app/composables/useWordImageActions.js";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

const photo = (name) => new File(["photo"], `${name}.png`, { type: "image/png" });
const detail = (id) => ({ word: { id, image_url: `/media/images/old-${id}.webp` }, media_sources: {} });

test("a saved file clears its selection and permits closing the modal", async () => {
  const file = photo("a");
  let uploaded;
  const tools = useSelectedWordImage({ uploadWordImage: async (value) => { uploaded = value; } });
  tools.selectImageFile(file);
  assert.equal(await tools.saveSelectedImage(), true);
  assert.equal(uploaded, file);
  assert.equal(tools.selectedImageFile.value, null);
  assert.equal(await tools.saveSelectedImage(), false);
});

test("upload A cannot clear newly selected B or signal that the modal should close", async () => {
  const pending = deferred();
  const a = photo("a");
  const b = photo("b");
  const uploads = [];
  const tools = useSelectedWordImage({ uploadWordImage: async (file) => {
    uploads.push(file);
    if (file === a) await pending.promise;
  } });
  tools.selectImageFile(a);
  const saving = tools.saveSelectedImage();
  tools.selectImageFile(b);
  pending.resolve();
  assert.equal(await saving, false);
  assert.equal(tools.selectedImageFile.value, b);
  assert.equal(await tools.saveSelectedImage(), true);
  assert.deepEqual(uploads, [a, b]);
});

test("a failed upload preserves the selected photo for retry", async () => {
  const file = photo("retry");
  const tools = useSelectedWordImage({ uploadWordImage: async () => { throw new Error("upload failed"); } });
  tools.selectImageFile(file);
  await assert.rejects(tools.saveSelectedImage(), /upload failed/);
  assert.equal(tools.selectedImageFile.value, file);
});

function previewSetup(t, word, file) {
  const revoked = [];
  let sequence = 0;
  t.mock.method(URL, "createObjectURL", () => `blob:preview-${++sequence}`);
  t.mock.method(URL, "revokeObjectURL", (url) => revoked.push(url));
  const open = () => {
    const scope = effectScope();
    const state = scope.run(() => useWordImageReplacement({
      getWordId: () => word.value.id,
      getFile: () => file.value,
    }));
    t.after(() => scope.stop());
    return { ...state, close: () => scope.stop() };
  };
  return { open, revoked };
}

test("closing and reopening restores the selected upload preview and save target", (t) => {
  const word = shallowRef({ id: 1 });
  const file = shallowRef(photo("a"));
  const { open, revoked } = previewSetup(t, word, file);
  const first = open();
  assert.equal(first.selectedReplacement.value.type, "upload");
  first.close();
  assert.deepEqual(revoked, ["blob:preview-1"]);
  const reopened = open();
  assert.equal(reopened.selectedReplacement.value.type, "upload");
  assert.equal(reopened.selectedReplacement.value.imageUrl, "blob:preview-2");
});

test("refreshing the same word object does not discard a pending replacement", (t) => {
  const word = shallowRef({ id: 1 });
  const file = shallowRef(photo("a"));
  const { open } = previewSetup(t, word, file);
  const state = open();
  const replacement = state.selectedReplacement.value;
  word.value = { id: 1, image_url: "/media/images/refreshed.webp" };
  assert.equal(state.selectedReplacement.value, replacement);
  word.value = { id: 2 };
  assert.equal(state.selectedReplacement.value, null);
});

test("changing the selected file swaps and releases the previous preview", (t) => {
  const word = shallowRef({ id: 1 });
  const file = shallowRef(photo("a"));
  const { open, revoked } = previewSetup(t, word, file);
  const state = open();
  file.value = photo("b");
  assert.equal(state.selectedReplacement.value.imageUrl, "blob:preview-2");
  assert.deepEqual(revoked, ["blob:preview-1"]);
  file.value = null;
  assert.equal(state.selectedReplacement.value, null);
  assert.deepEqual(revoked, ["blob:preview-1", "blob:preview-2"]);
});

test("upload captures the target word before asynchronous photo preparation", async () => {
  const preparing = deferred();
  const data = shallowRef(detail(1));
  let requested;
  let reloads = 0;
  const actions = useWordImageActions({ data, loadRoute: async () => { reloads += 1; } }, {
    prepareUpload: () => preparing.promise,
    request: async (url) => {
      requested = url;
      return { ok: true, image_url: "/media/images/replacement-1.webp" };
    },
  });
  const saving = actions.uploadWordImage(photo("a"));
  data.value = detail(2);
  preparing.resolve(photo("prepared"));
  await saving;
  assert.equal(requested, "/api/vue/words/1/image");
  assert.equal(data.value.word.image_url, "/media/images/old-2.webp");
  assert.equal(reloads, 0);
});

test("a successful upload updates the current picture and source metadata immediately", async () => {
  const data = shallowRef(detail(1));
  const sources = { image: { source: "upload" } };
  const actions = useWordImageActions({ data, loadRoute: async () => assert.fail("unneeded reload") }, {
    prepareUpload: async (file) => file,
    request: async (url, options) => {
      assert.equal(url, "/api/vue/words/1/image");
      assert.equal(options.body.get("edit_token"), "1");
      assert.equal(options.body.get("file").name, "a.png");
      return { ok: true, image_url: "/media/images/new-1.webp", media_sources: sources };
    },
  });
  await actions.uploadWordImage(photo("a"));
  assert.equal(data.value.word.image_url, "/media/images/new-1.webp");
  assert.equal(data.value.media_sources, sources);
});

for (const action of ["upload", "network", "ai"]) {
  test(`${action} image response cannot replace another word after navigation`, async () => {
    const pending = deferred();
    const data = shallowRef(detail(1));
    let reloads = 0;
    const actions = useWordImageActions({ data, loadRoute: async () => { reloads += 1; } }, {
      prepareUpload: async (file) => file,
      request: () => pending.promise,
    });
    const saving = action === "upload"
      ? actions.uploadWordImage(photo("a"))
      : action === "network"
        ? actions.chooseNetworkImage("https://example.com/photo.png")
        : actions.generateAiImage({});
    await Promise.resolve();
    data.value = detail(2);
    pending.resolve({ committed: true, image_url: "/media/images/new-1.webp", media_sources: { image: { source: "upload" } } });
    await saving;
    assert.deepEqual(data.value, detail(2));
    assert.equal(reloads, 0);
  });
}

test("failed replacement leaves the current image and metadata intact", async () => {
  const data = shallowRef(detail(1));
  const actions = useWordImageActions({ data, loadRoute: async () => assert.fail("failure cannot reload") }, {
    prepareUpload: async (file) => file,
    request: async () => { throw new Error("storage rejected upload"); },
  });
  await assert.rejects(actions.uploadWordImage(photo("a")), /storage rejected upload/);
  assert.deepEqual(data.value, detail(1));
});
