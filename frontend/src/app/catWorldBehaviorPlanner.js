const URGENT_KINDS = new Set(["food", "rest", "care"]);

const DAILY_MOOD_AFFINITIES = Object.freeze({
  bright: Object.freeze({ social: 16, favorite: 7, habit: 4, learning: 3 }),
  curious: Object.freeze({ habit: 16, goal: 9, learning: 6, social: 2 }),
  clingy: Object.freeze({ social: 18, favorite: 8, habit: 3 }),
  lazy: Object.freeze({ favorite: 15, rest: 11, social: -5, learning: -6, habit: -2 }),
  quiet: Object.freeze({ learning: 16, favorite: 8, habit: 4, social: -8 }),
  grumpy: Object.freeze({ favorite: 18, habit: 8, goal: 4, social: -11, learning: -5 }),
});

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

function stableRatio(seed) {
  let hash = 2166136261;
  for (const char of String(seed || "")) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967295;
}

function candidateIdentity(candidate = {}) {
  const target = candidate.target || {};
  return [
    candidate.kind,
    target.itemId,
    target.decorId,
    target.partnerCatId,
    target.careKey,
    target.label,
  ].filter(Boolean).join(":");
}

function kindAffinity(kind, target, context) {
  const behavior = context.behavior || {};
  const energy = clamp(behavior.energy ?? 50, 0, 100);
  const mood = clamp(behavior.mood ?? 50, 0, 100);
  const attention = clamp(behavior.attention ?? 50, 0, 100);
  const curiosity = clamp(behavior.curiosity ?? 50, 0, 100);
  const activity = clamp(behavior.activityBias ?? 50, 0, 100);
  const socialNeed = clamp(behavior.socialNeed ?? 50, 0, 100);
  const restThreshold = clamp(behavior.restThreshold ?? 34, 1, 99);

  if (kind === "food") return energy < restThreshold + 12 ? 16 : -8;
  if (kind === "rest") return Math.max(restThreshold + 20 - energy, 0) * 0.7;
  if (kind === "care") return Number(target.priority || 0) >= 70 ? 9 : 0;
  if (kind === "learning") return 7 + (attention - 50) * 0.2;
  if (kind === "social") {
    return (socialNeed - 50) * 0.22 + (Number(target.chemistryScore || 50) - 50) * 0.08;
  }
  if (kind === "habit") return (curiosity - 50) * 0.17 + (activity - 50) * 0.08;
  if (kind === "favorite") return (mood < 58 ? 9 : 3) + (50 - activity) * 0.05;
  if (kind === "goal") return 6 + (attention - 50) * 0.08;
  return 0;
}

export function catDailyMoodAffinity(moodKey = "", kind = "") {
  return Number(DAILY_MOOD_AFFINITIES[String(moodKey || "")]?.[String(kind || "")] || 0);
}

export function catDailyMoodActionReason(moodKey = "", kind = "", target = {}) {
  const label = String(target.partnerLabel || target.label || "前面");
  if (moodKey === "bright" && kind === "social") return `今天心情亮晶晶，想去找${label}一起玩。`;
  if (moodKey === "bright" && kind === "favorite") return `今天心情很好，想去${label}旁边待一会儿。`;
  if (moodKey === "curious" && kind === "habit") return `今天特别好奇，想按自己的习惯去${label}看看。`;
  if (moodKey === "curious" && kind === "goal") return `今天特别好奇，想去${label}探个究竟。`;
  if (moodKey === "curious" && kind === "learning") return `今天特别好奇，想去${label}学点新的。`;
  if (moodKey === "clingy" && kind === "social") return `今天有点黏人，想去找${label}待一会儿。`;
  if (moodKey === "clingy" && kind === "favorite") return `今天有点黏人，想在熟悉的${label}旁边等你。`;
  if (moodKey === "lazy" && kind === "favorite") return `今天想慢慢来，先去${label}趴一会儿。`;
  if (moodKey === "lazy" && kind === "rest") return `今天想慢慢来，去${label}好好休息。`;
  if (moodKey === "quiet" && kind === "learning") return `今天想安静一点，去${label}陪你学一会儿。`;
  if (moodKey === "quiet" && kind === "favorite") return `今天想安静一点，去${label}独处一会儿。`;
  if (moodKey === "grumpy" && kind === "favorite") return `今天有点闹脾气，想先去${label}缓一缓。`;
  if (moodKey === "grumpy" && kind === "habit") return `今天有点闹脾气，想按自己的小习惯缓一缓。`;
  return "";
}

export function rankCatVisitPlans(candidates = [], context = {}) {
  const catId = String(context.cat?.id || context.catId || "cat");
  const cycle = Math.max(Number(context.cycle || 0), 0);
  const lastKind = String(context.lastKind || "");
  const repeatCount = Math.max(Number(context.repeatCount || 0), 0);

  return candidates
    .filter((candidate) => candidate?.kind && candidate?.target)
    .map((candidate) => {
      const kind = String(candidate.kind);
      const target = candidate.target;
      const priority = clamp(target.priority ?? 0, 0, 100);
      const urgent = URGENT_KINDS.has(kind) && priority >= 86;
      const repeatPenalty = !urgent && kind === lastKind ? Math.min(9 * Math.max(repeatCount, 1), 27) : 0;
      const jitter = (stableRatio(`${catId}:${cycle}:${candidateIdentity(candidate)}`) - 0.5) * 8;
      const moodKey = String(context.behavior?.dailyMoodKey || "");
      const moodBonus = urgent ? 0 : catDailyMoodAffinity(moodKey, kind);
      const score = priority + kindAffinity(kind, target, context) + moodBonus - repeatPenalty + jitter;
      return {
        kind,
        target,
        urgent,
        score: Math.round(score * 10) / 10,
        moodKey,
        moodBonus,
        moodReason: !urgent && moodBonus >= 6
          ? catDailyMoodActionReason(moodKey, kind, target)
          : "",
      };
    })
    .filter((candidate) => candidate.target && candidate.score > 0)
    .sort((left, right) => right.score - left.score || candidateIdentity(left).localeCompare(candidateIdentity(right)));
}

export function chooseCatVisitPlan(candidates = [], context = {}) {
  const ranked = rankCatVisitPlans(candidates, context);
  if (!ranked.length) return null;

  const urgent = ranked.filter((candidate) => candidate.urgent);
  if (urgent.length) return urgent[0];

  const requiredKind = String(context.requiredKind || "");
  const required = requiredKind ? ranked.find((candidate) => candidate.kind === requiredKind) : null;
  if (required) return required;

  const activity = clamp(context.behavior?.activityBias ?? 50, 0, 100);
  const wanderScore = 43 + (50 - activity) * 0.08;
  const bestScore = ranked[0].score;
  if (bestScore < wanderScore + 4) return null;

  const contenders = ranked.filter((candidate) => candidate.score >= bestScore - 13).slice(0, 4);
  const weighted = contenders.map((candidate) => ({
    candidate,
    weight: Math.max(candidate.score - wanderScore + 8, 1),
  }));
  const wanderWeight = Math.max(5 + (50 - activity) * 0.12, 2);
  const totalWeight = weighted.reduce((sum, entry) => sum + entry.weight, wanderWeight);
  const catId = String(context.cat?.id || context.catId || "cat");
  let roll = stableRatio(`${catId}:${Math.max(Number(context.cycle || 0), 0)}:visit-choice`) * totalWeight;
  if (roll < wanderWeight) return null;
  roll -= wanderWeight;
  for (const entry of weighted) {
    if (roll < entry.weight) return entry.candidate;
    roll -= entry.weight;
  }
  return weighted.at(-1)?.candidate || null;
}

export function catVisitPlanMessage(plan = {}) {
  const target = plan.target || {};
  const label = String(target.label || target.targetLabel || "前面");
  if (plan.moodReason) return String(plan.moodReason);
  if (plan.kind === "food") return `闻到${label}了，先去吃一点。`;
  if (plan.kind === "rest") return `体力有点低，去${label}趴一会儿。`;
  if (plan.kind === "care") return `现在最需要${label}，先过去看看。`;
  if (plan.kind === "learning") return String(target.message || `去${label}陪你学习。`);
  if (plan.kind === "social") return `想去找${target.partnerLabel || "猫咪伙伴"}打个招呼。`;
  if (plan.kind === "habit") return String(target.message || `按自己的习惯去${label}待一会儿。`);
  if (plan.kind === "favorite") return `想去喜欢的${label}旁边待一会儿。`;
  if (plan.kind === "goal") return String(target.message || `今天想去${label}看看。`);
  if (plan.kind === "sleep") return "到睡眠时间了，梦里也要陪你记一个单词。";
  if (plan.kind === "idle") return "先停下来看看你今天学到哪里了。";
  if (plan.kind === "wander") return `去${label}随心走走，顺便巡视学习角。`;
  return "";
}

const PLAN_STATUS = Object.freeze({
  food: { moving: "去吃东西", arrived: "正在进食", tone: "need" },
  rest: { moving: "去找地方休息", arrived: "正在休息", tone: "rest" },
  care: { moving: "去处理需求", arrived: "正在照顾自己", tone: "need" },
  learning: { moving: "去学习角等你", arrived: "正在陪你学习", tone: "learning" },
  social: { moving: "去找猫咪伙伴", arrived: "正在和伙伴相处", tone: "social" },
  goal: { moving: "去完成今日愿望", arrived: "正在实现愿望", tone: "goal" },
  habit: { moving: "按自己的习惯行动", arrived: "正在享受独处", tone: "habit" },
  favorite: { moving: "去找喜欢的物品", arrived: "正在享受喜欢的物品", tone: "favorite" },
  idle: { moving: "停下来观察", arrived: "正在原地观察", tone: "idle" },
  wander: { moving: "随心散步", arrived: "正在看看房间", tone: "wander" },
  sleep: { moving: "准备睡觉", arrived: "正在睡觉", tone: "rest" },
});

export function catVisitPlanStatus(plan = {}, phase = "moving") {
  const kind = String(plan.kind || "wander");
  const target = plan.target || {};
  const status = PLAN_STATUS[kind] || PLAN_STATUS.wander;
  const normalizedPhase = phase === "arrived" ? "arrived" : "moving";
  return {
    kind,
    phase: normalizedPhase,
    statusLabel: status[normalizedPhase],
    targetLabel: String(target.partnerLabel || target.label || "").trim(),
    message: catVisitPlanMessage(plan) || String(target.message || "正在按自己的节奏活动。"),
    tone: status.tone,
  };
}
