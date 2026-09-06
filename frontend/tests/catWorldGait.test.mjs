import assert from "node:assert/strict";
import test from "node:test";

import { catWorldGaitProfile } from "../src/app/catWorldGait.js";

const livelyBehavior = {
  temperament: "chatty",
  activity: "chatty",
  dailyMoodKey: "bright",
  energy: 80,
  mood: 80,
  restThreshold: 34,
};

test("a cat keeps a stable individual gait across redraws", () => {
  const cat = { id: "siamese-profile-4b3e", traits: { temperament: "chatty" } };

  assert.deepEqual(
    catWorldGaitProfile(cat, livelyBehavior),
    catWorldGaitProfile(cat, livelyBehavior),
  );
});

test("two cats with the same temperament still move differently", () => {
  const first = catWorldGaitProfile({ id: "cat-a" }, livelyBehavior);
  const second = catWorldGaitProfile({ id: "cat-b" }, livelyBehavior);

  assert.equal(first.key, second.key);
  assert.notDeepEqual(
    [first.bobPx, first.cadenceMs, first.stridePx, first.phase, first.pawTone],
    [second.bobPx, second.cadenceMs, second.stridePx, second.phase, second.pawTone],
  );
});

test("daily mood and energy visibly tune the same cat's gait", () => {
  const cat = { id: "cat-a" };
  const bright = catWorldGaitProfile(cat, livelyBehavior);
  const lazy = catWorldGaitProfile(cat, { ...livelyBehavior, dailyMoodKey: "lazy" });
  const tired = catWorldGaitProfile(cat, { ...livelyBehavior, energy: 35 });

  assert.match(bright.label, /轻快/);
  assert.match(lazy.label, /慢悠悠/);
  assert.ok(bright.bobPx > lazy.bobPx);
  assert.ok(bright.cadenceMs < lazy.cadenceMs);
  assert.match(tired.label, /省力/);
  assert.ok(tired.bobPx < bright.bobPx);
  assert.ok(tired.cadenceMs > bright.cadenceMs);
  assert.ok(tired.pawAlpha < bright.pawAlpha);
});

test("an adventurous activity style remains visible beyond temperament", () => {
  const gait = catWorldGaitProfile(
    { id: "calm-adventurer", traits: { temperament: "calm", activity: "adventurous" } },
    { temperament: "calm", activity: "adventurous", dailyMoodKey: "curious", energy: 76, mood: 68 },
  );

  assert.equal(gait.key, "bounce");
  assert.match(gait.label, /弹跳探索/);
  assert.equal(gait.ease, "Quad.easeInOut");
});
