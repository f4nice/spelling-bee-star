import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { useCatWorldInteractionTarget } from "../src/app/composables/useCatWorldInteractionTarget.js";

const cats = [{ id: "mimi-a", breedId: "mimi" }, { id: "mimi-b", breedId: "mimi" }];
const toy = { id: "rolling-ball", category: "toy" };

test("without an explicit selection, toy requests retain the server default", () => {
  const target = useCatWorldInteractionTarget();
  assert.deepEqual(target.buildPlayPayload(toy, cats), { itemId: "rolling-ball" });
});

test("a clicked cat instance wins even when another cat has the same breed", () => {
  const target = useCatWorldInteractionTarget();
  target.selectInteractionCat(cats[1]);
  assert.deepEqual(target.buildPlayPayload(toy, cats), { itemId: "rolling-ball", catId: "mimi-b" });
});

test("the last explicit click wins, but a pending request keeps its captured target", () => {
  const target = useCatWorldInteractionTarget();
  target.selectInteractionCat(cats[1]);
  const pending = target.buildPlayPayload(toy, cats);
  target.selectInteractionCat(cats[0]);
  assert.equal(pending.catId, "mimi-b");
  assert.equal(target.buildPlayPayload(toy, cats).catId, "mimi-a");
});

test("an older selection response cannot overwrite a later clicked cat", () => {
  const target = useCatWorldInteractionTarget();
  const firstVersion = target.selectInteractionCat(cats[0]);
  const laterVersion = target.selectInteractionCat(cats[1]);
  assert.ok(laterVersion > firstVersion);
  assert.equal(target.completeInteractionSelection(firstVersion, cats[0]), false);
  assert.equal(target.interactionCatId.value, "mimi-b");
  assert.deepEqual(target.buildPlayPayload(toy, cats), { itemId: "rolling-ball", catId: "mimi-b" });
});

test("clearing the target on a room change invalidates a pending selection response", () => {
  const target = useCatWorldInteractionTarget();
  const pendingVersion = target.selectInteractionCat(cats[1]);
  target.clearInteractionCat();
  assert.equal(target.completeInteractionSelection(pendingVersion, cats[1]), false);
  assert.equal(target.interactionCatId.value, "");
  assert.deepEqual(target.buildPlayPayload(toy, [cats[0]]), { itemId: "rolling-ball" });
});

test("an unchanged selection response can resolve a breed to its exact profile", () => {
  const target = useCatWorldInteractionTarget();
  const pendingVersion = target.selectInteractionCat({ id: "mimi" });
  assert.equal(target.interactionCatId.value, "mimi");
  assert.equal(target.completeInteractionSelection(pendingVersion, cats[1]), true);
  assert.equal(target.interactionCatId.value, "mimi-b");
  assert.deepEqual(target.buildPlayPayload(toy, cats), { itemId: "rolling-ball", catId: "mimi-b" });
});

test("a selected cat that leaves the room is rejected instead of replaced", () => {
  const target = useCatWorldInteractionTarget();
  target.selectInteractionCat(cats[1]);
  assert.throws(() => target.buildPlayPayload(toy, [cats[0]]), /不在当前房间/);
  assert.equal(target.interactionCatId.value, "mimi-b");
});

test("food remains server-selected even when an explicit cat is no longer in the room", () => {
  const target = useCatWorldInteractionTarget();
  target.selectInteractionCat(cats[1]);
  assert.deepEqual(target.buildPlayPayload({ id: "fish", category: "food" }, [cats[0]]), { itemId: "fish" });
});

test("changing rooms clears the explicit interaction target", () => {
  const target = useCatWorldInteractionTarget();
  target.selectInteractionCat(cats[1]);
  target.clearInteractionCat();
  assert.deepEqual(target.buildPlayPayload(toy, [cats[0]]), { itemId: "rolling-ball" });
});

test("the page selects explicitly and automatic reactions cannot steal the toy target", async () => {
  const page = await readFile(new URL("../src/app/pages/CatWorldPage.vue", import.meta.url), "utf8");
  const click = page.slice(page.indexOf("function openCatActionMenu("), page.indexOf("function closeCatActionMenu("));
  assert.match(click, /selectInteractionCat\(cat\)/);
  const reaction = page.slice(page.indexOf("function showCatReaction("), page.indexOf("function selectLearningWeekDay("));
  assert.doesNotMatch(reaction, /selectInteractionCat|interactionCatId/);
  assert.match(page, /JSON\.stringify\(buildPlayPayload\(item, roomCats\.value\)\)/);
  assert.match(page, /watch\(\(\) => currentScene\.value\.id, clearInteractionCat/);
  assert.match(page, /interactionCatId: interactionCatId\.value/);
});

async function wandScene(selectedId, { resting = false } = {}) {
  const source = await readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8");
  const start = source.indexOf("  toggleFeatherWandMode(itemId) {");
  const end = source.indexOf("  pointerHitsFeatherWand(pointer) {", start);
  assert.ok(start >= 0 && end > start);
  const Scene = Function(`return class { ${source.slice(start, end)} }`)();
  const scene = new Scene();
  const entries = cats.map((cat, index) => ({ cat: { ...cat, label: cat.id }, container: {}, behavior: { canWalk: !(resting && index === 1) } }));
  scene.owner = { snapshot: { interactionCatId: selectedId }, wandMode: false, catItemActions: new Map() };
  scene.roomCatEntries = () => entries;
  // A is the favorite; selecting B must not automatically dispatch A.
  scene.favoriteCatEntries = () => [entries[0]];
  scene.interruptCatAutonomy = () => {};
  scene.spawnCatBubble = () => {};
  scene.toyContainers = new Map();
  scene.setFeatherWandCursor = () => {};
  return scene;
}

test("feather wand starts with the explicitly selected cat, not a different favorite", async () => {
  const scene = await wandScene("mimi-b");
  assert.equal(scene.toggleFeatherWandMode("feather-wand").active, true);
  assert.deepEqual([...scene.owner.wandCatIds], ["mimi-b"]);
});

test("a resting selected cat does not cause another cat to chase instead", async () => {
  const scene = await wandScene("mimi-b", { resting: true });
  const result = scene.toggleFeatherWandMode("feather-wand");
  assert.equal(result.active, false);
  assert.match(result.message, /mimi-b.*休息/);
  assert.equal(scene.owner.wandMode, false);
});

test("a missing selected cat does not fall back to a favorite for the wand", async () => {
  const scene = await wandScene("missing");
  assert.equal(scene.toggleFeatherWandMode("feather-wand").active, false);
  assert.equal(scene.owner.wandMode, false);
});

test("without explicit selection the wand keeps its existing favorite-cat behavior", async () => {
  const scene = await wandScene("");
  assert.equal(scene.toggleFeatherWandMode("feather-wand").active, true);
  assert.deepEqual([...scene.owner.wandCatIds], ["mimi-a"]);
});
