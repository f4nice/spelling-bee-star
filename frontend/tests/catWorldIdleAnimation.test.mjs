import assert from "node:assert/strict";
import test from "node:test";

import {
  catWorldDailyMoodExpression,
  catWorldIdleAnimationPlan,
} from "../src/app/catWorldIdleAnimation.js";

test("all six daily moods have a visible pixel expression", () => {
  const expected = {
    bright: ["sparkle", "hop", "heart"],
    curious: ["question", "lookout", "ear"],
    clingy: ["heart", "tail", "listen"],
    lazy: ["yawn", "breathe", "blink"],
    quiet: ["ellipsis", "blink", "breathe"],
    grumpy: ["huff", "tail", "ear"],
  };

  for (const [moodKey, animationKinds] of Object.entries(expected)) {
    const expression = catWorldDailyMoodExpression(moodKey);
    const plans = Array.from({ length: 8 }, (_, index) => catWorldIdleAnimationPlan(
      { id: `cat-${moodKey}`, individualHabit: { animation: "groom", toneLabel: "认真派" } },
      { dailyMoodKey: moodKey, temperament: "balanced" },
      index + 1,
    ));
    assert.equal(expression.key, moodKey);
    assert.ok(expression.label.length >= 3);
    assert.deepEqual(expression.animationKinds, animationKinds);
    assert.ok(plans.some((plan) => plan.source === "daily-mood"));
    assert.ok(plans.filter((plan) => plan.source === "daily-mood").every((plan) => animationKinds.includes(plan.kind)));
  }
});

test("idle animation rhythms stay individual and deterministic", () => {
  const cat = {
    id: "cat-8ac2",
    individualHabit: { animation: "book", toneLabel: "安静派" },
  };
  const behavior = { dailyMoodKey: "curious", temperament: "adventurous" };
  const first = Array.from({ length: 12 }, (_, index) => catWorldIdleAnimationPlan(cat, behavior, index + 1));
  const replay = Array.from({ length: 12 }, (_, index) => catWorldIdleAnimationPlan(cat, behavior, index + 1));

  assert.deepEqual(first, replay);
  assert.ok(first.some((plan) => plan.source === "daily-mood"));
  assert.ok(first.some((plan) => plan.source === "individual-habit" && plan.kind === "book"));
  assert.ok(first.some((plan) => plan.source === "temperament" && ["hop", "lookout", "tail", "stretch"].includes(plan.kind)));
});

test("an adventurous activity style stays visible alongside an individual temperament", () => {
  const cat = {
    id: "cat-independent-adventurer",
    traits: { temperament: "calm", activity: "adventurous" },
    individualHabit: { animation: "listen", toneLabel: "观察派" },
  };
  const plans = Array.from({ length: 12 }, (_, index) => catWorldIdleAnimationPlan(
    cat,
    { dailyMoodKey: "quiet", temperament: "calm", activity: "adventurous" },
    index + 1,
  ));

  assert.ok(plans.some((plan) => plan.source === "individual-habit" && plan.kind === "listen"));
  assert.ok(plans.some((plan) => plan.source === "temperament" && ["hop", "lookout", "tail", "stretch"].includes(plan.kind)));
});

test("sleep and wake animations override mood and personal habits", () => {
  const cat = { id: "cat-sleepy", individualHabit: { animation: "chirp" } };
  const sleeping = catWorldIdleAnimationPlan(cat, { sleeping: true, dailyMoodKey: "bright" }, 3);
  const waking = catWorldIdleAnimationPlan(cat, { key: "waking", dailyMoodKey: "grumpy" }, 3);

  assert.equal(sleeping.source, "sleep");
  assert.ok(["breathe", "dream", "ear"].includes(sleeping.kind));
  assert.equal(waking.source, "wake");
  assert.ok(["stretch", "blink", "groom"].includes(waking.kind));
});
