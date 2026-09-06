const GAIT_STYLES = Object.freeze({
  calm: Object.freeze({ key: "soft", label: "轻轻踱步", bobPx: 2.2, cadenceMs: 470, stridePx: 50, swayPx: 0.7, ease: "Sine.easeInOut" }),
  gentle: Object.freeze({ key: "cloud", label: "软绵慢步", bobPx: 2.5, cadenceMs: 500, stridePx: 52, swayPx: 0.8, ease: "Sine.easeInOut" }),
  chatty: Object.freeze({ key: "quick", label: "碎步小跑", bobPx: 4.2, cadenceMs: 320, stridePx: 40, swayPx: 1.3, ease: "Sine.easeInOut" }),
  guardian: Object.freeze({ key: "patrol", label: "稳稳巡逻", bobPx: 3, cadenceMs: 410, stridePx: 48, swayPx: 0.6, ease: "Sine.easeInOut" }),
  clingy: Object.freeze({ key: "close", label: "贴贴小碎步", bobPx: 3.8, cadenceMs: 350, stridePx: 42, swayPx: 1.1, ease: "Sine.easeInOut" }),
  adventurous: Object.freeze({ key: "bounce", label: "弹跳探索", bobPx: 5.4, cadenceMs: 290, stridePx: 38, swayPx: 1.5, ease: "Quad.easeInOut" }),
  balanced: Object.freeze({ key: "stroll", label: "自在散步", bobPx: 3.2, cadenceMs: 390, stridePx: 46, swayPx: 0.9, ease: "Sine.easeInOut" }),
});

const MOOD_GAIT_MODIFIERS = Object.freeze({
  bright: Object.freeze({ label: "轻快", bobDelta: 1.2, cadenceScale: 0.84, strideScale: 0.92 }),
  curious: Object.freeze({ label: "探头", bobDelta: 0.8, cadenceScale: 0.91, strideScale: 0.96 }),
  clingy: Object.freeze({ label: "贴近", bobDelta: 0.5, cadenceScale: 0.95, strideScale: 0.94 }),
  lazy: Object.freeze({ label: "慢悠悠", bobDelta: -0.8, cadenceScale: 1.2, strideScale: 1.12 }),
  quiet: Object.freeze({ label: "轻手轻脚", bobDelta: -0.5, cadenceScale: 1.1, strideScale: 1.06 }),
  grumpy: Object.freeze({ label: "闷闷", bobDelta: -0.2, cadenceScale: 1.06, strideScale: 1.02 }),
});

const PAW_TONES = Object.freeze(["rose", "sky", "sun", "mint"]);

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

function stableHash(value = "") {
  let hash = 2166136261;
  for (const character of String(value || "")) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

function stableRatio(seed = "") {
  return stableHash(seed) / 4294967295;
}

export function catWorldGaitProfile(cat = {}, behavior = {}) {
  const catId = String(cat.id || cat.profileId || cat.breedId || "cat");
  const temperament = String(
    behavior.temperament
    || cat.traits?.temperament
    || "balanced",
  );
  const activity = String(behavior.activity || cat.traits?.activity || "");
  const styleKey = activity === "adventurous" ? "adventurous" : temperament;
  const base = GAIT_STYLES[styleKey] || GAIT_STYLES.balanced;
  const moodKey = String(behavior.dailyMoodKey || "");
  const mood = MOOD_GAIT_MODIFIERS[moodKey] || {};
  const bobJitter = (stableRatio(`${catId}:gait:bob`) - 0.5) * 1.4;
  const cadenceJitter = 0.9 + stableRatio(`${catId}:gait:cadence`) * 0.2;
  const strideJitter = 0.9 + stableRatio(`${catId}:gait:stride`) * 0.2;
  const restThreshold = clamp(behavior.restThreshold ?? cat.traits?.restThreshold ?? 34, 1, 99);
  const energy = clamp(behavior.energy ?? 70, 0, 100);
  const moodScore = clamp(behavior.mood ?? 65, 0, 100);
  const tired = energy < restThreshold + 10;
  const lowMood = moodScore < 38;
  const bodyScale = tired ? 0.68 : lowMood ? 0.8 : 1;
  const paceScale = tired ? 1.22 : lowMood ? 1.1 : 1;
  const bobPx = clamp((base.bobPx + Number(mood.bobDelta || 0) + bobJitter) * bodyScale, 1.2, 6.8);
  const cadenceMs = clamp(Math.round(base.cadenceMs * Number(mood.cadenceScale || 1) * cadenceJitter * paceScale), 210, 680);
  const stridePx = clamp(Math.round(base.stridePx * Number(mood.strideScale || 1) * strideJitter), 32, 68);
  const pawTone = PAW_TONES[stableHash(`${catId}:gait:paw`) % PAW_TONES.length];
  const stateLabel = tired ? "省力" : lowMood ? "没精打采" : String(mood.label || "");

  return {
    key: base.key,
    label: [stateLabel, base.label].filter(Boolean).join(" · "),
    baseLabel: base.label,
    moodKey,
    bobPx: Math.round(bobPx * 10) / 10,
    cadenceMs,
    stridePx,
    swayPx: Math.round(clamp(base.swayPx + (stableRatio(`${catId}:gait:sway`) - 0.5) * 0.6, 0.4, 1.8) * 10) / 10,
    phase: Math.round(stableRatio(`${catId}:gait:phase`) * 1000) / 1000,
    pawTone,
    pawAlpha: tired || lowMood ? 0.16 : moodKey === "bright" ? 0.3 : 0.23,
    ease: base.ease,
  };
}
