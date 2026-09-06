const SOCIAL_KINDS = new Set(["greet", "nuzzle", "chase"]);

const SOCIAL_MOMENT_STYLES = Object.freeze({
  greet: Object.freeze({
    key: "greet",
    label: "碰鼻问候",
    holdMs: 3900,
    motionMs: 460,
    travelPx: 14,
    liftPx: 3,
    repeats: 1,
    cueTone: "sky",
  }),
  nuzzle: Object.freeze({
    key: "nuzzle",
    label: "猫咪贴贴",
    holdMs: 4700,
    motionMs: 620,
    travelPx: 20,
    liftPx: 5,
    repeats: 2,
    cueTone: "rose",
  }),
  chase: Object.freeze({
    key: "chase",
    label: "伙伴追逐",
    holdMs: 5600,
    motionMs: 760,
    travelPx: 112,
    gapPx: 118,
    liftPx: 10,
    repeats: 1,
    cueTone: "sun",
  }),
});

const SOCIAL_LINES = Object.freeze({
  greet: Object.freeze({
    source: Object.freeze(["闻闻你，今天也见面啦。", "碰个鼻子，巡逻交接完成。", "你好呀，一起看看房间吧。"]),
    partner: Object.freeze(["闻到了，是熟悉的小伙伴。", "你好呀，今天也请多关照。", "碰鼻成功，我继续陪你走走。"]),
  }),
  nuzzle: Object.freeze({
    source: Object.freeze(["靠近一点，今天一起待着。", "轻轻蹭一下，我就很安心。", "把软乎乎的拥抱分给你。"]),
    partner: Object.freeze(["好呀，我也靠过来一点。", "收到贴贴，心情暖起来了。", "就这样安静待一会儿吧。"]),
  }),
  chase: Object.freeze({
    source: Object.freeze(["我先冲啦，快来追我！", "绕过地毯，看谁更快！", "追逐路线启动，跟紧我呀！"]),
    partner: Object.freeze(["等等我，我马上追上来！", "这次我可不会落后。", "接到邀请，一起跑一小圈！"]),
  }),
});

const TEMPERAMENT_LINES = Object.freeze({
  calm: Object.freeze({
    greet: "慢慢碰个鼻子就很好。",
    nuzzle: "安静靠一会儿，我很喜欢。",
    chase: "别跑太快，我稳稳跟着。",
  }),
  gentle: Object.freeze({
    greet: "轻轻打招呼，不吓到你。",
    nuzzle: "我把最轻的贴贴留给你。",
    chase: "慢一点跑，也很好玩呀。",
  }),
  chatty: Object.freeze({
    greet: "你好你好，我有好多话想说。",
    nuzzle: "贴贴的时候也要聊两句。",
    chase: "来呀来呀，下一圈换你领跑！",
  }),
  guardian: Object.freeze({
    greet: "房间安全，过来交接巡逻。",
    nuzzle: "靠近我，这里很安全。",
    chase: "我守后面，你放心往前跑。",
  }),
  clingy: Object.freeze({
    greet: "见到你啦，再靠近一点点。",
    nuzzle: "今天也想和你贴在一起。",
    chase: "你去哪里，我就追到哪里。",
  }),
  adventurous: Object.freeze({
    greet: "发现伙伴，一起探索新路线！",
    nuzzle: "先补一个拥抱，再去探险。",
    chase: "新的追逐路线，我先出发啦！",
  }),
});

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

function stablePick(values = [], seed = "") {
  if (!values.length) return "";
  return values[stableHash(seed) % values.length];
}

function catId(cat = {}, fallback = "cat") {
  return String(cat.id || cat.profileId || cat.breedId || fallback);
}

function temperament(cat = {}, behavior = {}) {
  return String(behavior.temperament || cat.traits?.temperament || "balanced");
}

function fallbackSocialKind(sourceCat = {}, partnerCat = {}, context = {}) {
  const sourceBehavior = context.sourceBehavior || {};
  const partnerBehavior = context.partnerBehavior || {};
  const combinedActivity = clamp(sourceBehavior.activityBias ?? 50, 0, 100)
    + clamp(partnerBehavior.activityBias ?? 50, 0, 100);
  const combinedSocial = clamp(sourceBehavior.socialNeed ?? 50, 0, 100)
    + clamp(partnerBehavior.socialNeed ?? 50, 0, 100);
  const temperaments = new Set([
    temperament(sourceCat, sourceBehavior),
    temperament(partnerCat, partnerBehavior),
  ]);
  if (combinedActivity >= 142 || temperaments.has("adventurous")) return "chase";
  if (combinedSocial >= 132 || temperaments.has("clingy") || temperaments.has("gentle")) return "nuzzle";
  return "greet";
}

export function catWorldSocialKindLabel(kind = "") {
  return SOCIAL_MOMENT_STYLES[String(kind || "")]?.label || "伙伴互动";
}

export function catWorldSocialMomentPlan(sourceCat = {}, partnerCat = {}, target = {}, context = {}) {
  const sourceId = catId(sourceCat, "source");
  const partnerId = catId(partnerCat, "partner");
  const preferredKind = String(target.preferredKind || "");
  const kind = SOCIAL_KINDS.has(preferredKind)
    ? preferredKind
    : fallbackSocialKind(sourceCat, partnerCat, context);
  const style = SOCIAL_MOMENT_STYLES[kind];
  const periodKey = String(context.periodKey || "today");
  const pairKey = [sourceId, partnerId].sort().join(":");
  const sourceTemperament = temperament(sourceCat, context.sourceBehavior);
  const partnerTemperament = temperament(partnerCat, context.partnerBehavior);
  const sourcePool = [
    ...SOCIAL_LINES[kind].source,
    TEMPERAMENT_LINES[sourceTemperament]?.[kind],
  ].filter(Boolean);
  const partnerPool = [
    ...SOCIAL_LINES[kind].partner,
    TEMPERAMENT_LINES[partnerTemperament]?.[kind],
  ].filter(Boolean);
  const motionJitter = stableHash(`${pairKey}:${periodKey}:${kind}:motion`) % 17;

  return {
    ...style,
    sourceLine: stablePick(sourcePool, `${sourceId}:${partnerId}:${periodKey}:${kind}:source`),
    partnerLine: stablePick(partnerPool, `${partnerId}:${sourceId}:${periodKey}:${kind}:partner`),
    holdMs: style.holdMs + motionJitter * 20,
    travelPx: style.travelPx + (kind === "chase" ? motionJitter : motionJitter % 5),
    sourceBobPx: 2 + (stableHash(`${sourceId}:${periodKey}:social-bob`) % 5),
    partnerBobPx: 2 + (stableHash(`${partnerId}:${periodKey}:social-bob`) % 5),
    pairKey,
  };
}
