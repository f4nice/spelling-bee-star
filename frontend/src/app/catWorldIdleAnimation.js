const DAILY_MOOD_ANIMATIONS = Object.freeze({
  bright: Object.freeze(["sparkle", "hop", "heart"]),
  curious: Object.freeze(["question", "lookout", "ear"]),
  clingy: Object.freeze(["heart", "tail", "listen"]),
  lazy: Object.freeze(["yawn", "breathe", "blink"]),
  quiet: Object.freeze(["ellipsis", "blink", "breathe"]),
  grumpy: Object.freeze(["huff", "tail", "ear"]),
});

const DAILY_MOOD_EXPRESSION_LABELS = Object.freeze({
  bright: "亮晶晶",
  curious: "好奇探头",
  clingy: "想贴贴",
  lazy: "慢慢打哈欠",
  quiet: "安静发呆",
  grumpy: "轻轻闹脾气",
});

const TEMPERAMENT_ANIMATIONS = Object.freeze({
  calm: Object.freeze(["blink", "breathe", "listen", "groom"]),
  gentle: Object.freeze(["blink", "groom", "breathe", "tail"]),
  chatty: Object.freeze(["chirp", "listen", "tail", "stretch"]),
  guardian: Object.freeze(["lookout", "listen", "ear", "stretch"]),
  clingy: Object.freeze(["heart", "tail", "blink", "listen"]),
  adventurous: Object.freeze(["hop", "lookout", "tail", "stretch"]),
  balanced: Object.freeze(["blink", "tail", "groom", "stretch", "listen", "breathe"]),
});

function stableHash(value = "") {
  let hash = 2166136261;
  for (const character of String(value || "")) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

function stablePick(values = [], seed = "") {
  if (!values.length) return "blink";
  return values[stableHash(seed) % values.length];
}

export function catWorldDailyMoodExpression(moodKey = "") {
  const key = DAILY_MOOD_ANIMATIONS[moodKey] ? moodKey : "";
  return {
    key,
    label: DAILY_MOOD_EXPRESSION_LABELS[key] || "自然放松",
    animationKinds: [...(DAILY_MOOD_ANIMATIONS[key] || [])],
  };
}

export function catWorldIdleAnimationPlan(cat = {}, behavior = {}, cycle = 1) {
  const catId = String(cat.id || cat.profileId || cat.breedId || "cat");
  const safeCycle = Math.max(Math.trunc(Number(cycle) || 1), 1);
  if (behavior.sleeping) {
    return {
      kind: stablePick(["breathe", "dream", "ear"], `${catId}:sleep:${safeCycle}`),
      source: "sleep",
      expressionLabel: "睡梦中",
    };
  }
  if (behavior.key === "waking") {
    return {
      kind: stablePick(["stretch", "blink", "groom"], `${catId}:wake:${safeCycle}`),
      source: "wake",
      expressionLabel: "刚睡醒",
    };
  }

  const mood = catWorldDailyMoodExpression(String(behavior.dailyMoodKey || ""));
  const habitAnimation = String(cat.individualHabit?.animation || "").trim();
  const temperament = String(
    behavior.temperament
    || cat.traits?.temperament
    || "balanced",
  );
  const activity = String(behavior.activity || cat.traits?.activity || "");
  const animationStyle = activity === "adventurous" ? activity : temperament;
  const temperamentPool = TEMPERAMENT_ANIMATIONS[animationStyle] || TEMPERAMENT_ANIMATIONS.balanced;
  const phase = (safeCycle + stableHash(`${catId}:idle-phase`)) % 4;

  if (mood.animationKinds.length && (phase === 0 || phase === 2)) {
    return {
      kind: stablePick(mood.animationKinds, `${catId}:${mood.key}:mood:${Math.floor(safeCycle / 4)}`),
      source: "daily-mood",
      moodKey: mood.key,
      expressionLabel: mood.label,
    };
  }
  if (habitAnimation && phase === 1) {
    return {
      kind: habitAnimation,
      source: "individual-habit",
      moodKey: mood.key,
      expressionLabel: String(cat.individualHabit?.toneLabel || "个人小习惯"),
    };
  }
  return {
    kind: stablePick(temperamentPool, `${catId}:${animationStyle}:temperament:${safeCycle}`),
    source: "temperament",
    moodKey: mood.key,
    expressionLabel: mood.label,
  };
}
