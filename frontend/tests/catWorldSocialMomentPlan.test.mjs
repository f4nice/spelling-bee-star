import assert from "node:assert/strict";
import test from "node:test";

import {
  catWorldSocialKindLabel,
  catWorldSocialMomentPlan,
} from "../src/app/catWorldSocialMoment.js";

const cats = {
  calm: { id: "cat-calm", traits: { temperament: "calm" } },
  clingy: { id: "cat-clingy", traits: { temperament: "clingy" } },
  adventurous: { id: "cat-adventurous", traits: { temperament: "adventurous" } },
};

test("relationship preference produces a stable named social moment", () => {
  const context = {
    periodKey: "2026-09-07:18",
    sourceBehavior: { temperament: "calm", activityBias: 40, socialNeed: 55 },
    partnerBehavior: { temperament: "clingy", activityBias: 45, socialNeed: 80 },
  };
  const first = catWorldSocialMomentPlan(cats.calm, cats.clingy, { preferredKind: "nuzzle" }, context);
  const second = catWorldSocialMomentPlan(cats.calm, cats.clingy, { preferredKind: "nuzzle" }, context);

  assert.deepEqual(first, second);
  assert.equal(first.key, "nuzzle");
  assert.equal(first.label, "猫咪贴贴");
  assert.equal(catWorldSocialKindLabel(first.key), first.label);
  assert.match(first.sourceLine, /。|！/);
  assert.match(first.partnerLine, /。|！/);
  assert.ok(first.holdMs >= 4700 && first.holdMs <= 5020);
});

test("fallback social style follows both cats instead of breed", () => {
  const chase = catWorldSocialMomentPlan(cats.adventurous, cats.calm, {}, {
    periodKey: "active",
    sourceBehavior: { activityBias: 84, socialNeed: 45 },
    partnerBehavior: { activityBias: 72, socialNeed: 48 },
  });
  const nuzzle = catWorldSocialMomentPlan(cats.clingy, cats.calm, {}, {
    periodKey: "social",
    sourceBehavior: { activityBias: 36, socialNeed: 78 },
    partnerBehavior: { activityBias: 42, socialNeed: 70 },
  });
  const greet = catWorldSocialMomentPlan(cats.calm, { id: "cat-balanced" }, {}, {
    periodKey: "quiet",
    sourceBehavior: { activityBias: 44, socialNeed: 46 },
    partnerBehavior: { activityBias: 48, socialNeed: 50 },
  });

  assert.equal(chase.key, "chase");
  assert.ok(chase.gapPx >= 110);
  assert.equal(nuzzle.key, "nuzzle");
  assert.equal(greet.key, "greet");
});

test("same-temperament cats still receive individual dialogue and motion", () => {
  const partner = { id: "shared-partner", traits: { temperament: "gentle" } };
  const context = {
    periodKey: "2026-09-07:19",
    sourceBehavior: { temperament: "chatty", activityBias: 68, socialNeed: 64 },
    partnerBehavior: { temperament: "gentle", activityBias: 45, socialNeed: 62 },
  };
  const first = catWorldSocialMomentPlan(
    { id: "chatty-profile-a", traits: { temperament: "chatty" } },
    partner,
    { preferredKind: "chase" },
    context,
  );
  const second = catWorldSocialMomentPlan(
    { id: "chatty-profile-b", traits: { temperament: "chatty" } },
    partner,
    { preferredKind: "chase" },
    context,
  );

  assert.notDeepEqual(
    [first.sourceLine, first.sourceBobPx, first.travelPx, first.holdMs],
    [second.sourceLine, second.sourceBobPx, second.travelPx, second.holdMs],
  );
});
