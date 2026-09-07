import {
  formatCatWorldLearningMemoryDate,
  normalizeCatWorldLearningMemory,
} from "./catWorldLearningMemory.js";

const MINIMUM_SPELLING_TARGET = 20;
const STARTER_SPELLING_TARGET = 5;
const WEEKLY_TOUCHPOINT_TARGET = 5;
const WEEKLY_LOOP_TARGET = 3;

const ROOM_LEARNING_STEPS = Object.freeze([
  Object.freeze({ key: "warmup", label: "练20词" }),
  Object.freeze({ key: "output", label: "用英语" }),
  Object.freeze({ key: "loop", label: "都完成" }),
]);

const HABIT_GARDEN_STAGES = Object.freeze([
  Object.freeze({ key: "seed", label: "种子", threshold: 0 }),
  Object.freeze({ key: "sprout", label: "冒芽", threshold: 1 }),
  Object.freeze({ key: "leaves", label: "舒叶", threshold: 4 }),
  Object.freeze({ key: "bloom", label: "开花", threshold: 8 }),
  Object.freeze({ key: "crown", label: "满冠", threshold: 16 }),
]);

const LEARNING_RITUAL_TARGET_LABELS = Object.freeze({
  "learning-garden": "单词芽",
  "study-desk": "英文书桌",
  "book-shelf": "英文书架",
  "reading-lamp": "阅读台灯",
  "word-gallery": "单词挂画",
});

const LEARNING_RITUALS = Object.freeze({
  "gentle-starter": Object.freeze({
    label: "五词轻启动",
    animation: "blink",
    targetItemIds: Object.freeze(["learning-garden", "reading-lamp", "word-gallery"]),
    cues: Object.freeze({
      warmup: "先只做 5 个词，完成后合上答案回想最熟的 1 个。",
      output: "先说或写最短的 3 句，正确比华丽更重要。",
      loop: "用 30 秒回想今天最熟的 1 个词和 1 句话。",
    }),
  }),
  "story-builder": Object.freeze({
    label: "三词成段法",
    animation: "book",
    targetItemIds: Object.freeze(["study-desk", "word-gallery", "book-shelf", "learning-garden"]),
    cues: Object.freeze({
      warmup: "练词时挑出 3 个想写进句子的词。",
      output: "把这 3 个词写进同一段英文，先完整表达再润色。",
      loop: "读一遍今天写下的段落，留下最想记住的一句。",
    }),
  }),
  "idea-sparring": Object.freeze({
    label: "观点理由法",
    animation: "chirp",
    targetItemIds: Object.freeze(["reading-lamp", "study-desk", "word-gallery", "learning-garden"]),
    cues: Object.freeze({
      warmup: "从新词里挑 2 个，想想它们能支持什么观点。",
      output: "先说 I think...，再用 because 补上一个理由。",
      loop: "用一句反方观点检查自己的理由是否说清楚。",
    }),
  }),
  "loop-keeper": Object.freeze({
    label: "练词表达接力",
    animation: "paw",
    targetItemIds: Object.freeze(["word-gallery", "study-desk", "learning-garden", "book-shelf"]),
    cues: Object.freeze({
      warmup: "练词时选 3 个今天一定要用出来的词。",
      output: "不看答案，先用刚练的词表达一遍，再回头修正。",
      loop: "看看练过的词，确认至少有 1 个新词真的用进句子了。",
    }),
  }),
  "streak-keeper": Object.freeze({
    label: "每天记一点",
    animation: "heart",
    targetItemIds: Object.freeze(["learning-garden", "book-shelf", "reading-lamp", "word-gallery"]),
    cues: Object.freeze({
      warmup: "今天有点累也没关系，先做 5 个词，留下今天的学习记录。",
      output: "完成一次最短表达，给今天留下一条真实记录。",
      loop: "记住今天最小但真实的一步，明天从这里继续。",
    }),
  }),
  "review-organizer": Object.freeze({
    label: "遮住答案想一想",
    animation: "book",
    targetItemIds: Object.freeze(["book-shelf", "word-gallery", "study-desk", "learning-garden"]),
    cues: Object.freeze({
      warmup: "先看词义，再遮住答案自己想一想。",
      output: "挑 3 个容易忘的词，各用一句英文把它们叫回来。",
      loop: "离开页面前再回想一轮，答不出的词留给明天。",
    }),
  }),
  balanced: Object.freeze({
    label: "练词表达交替",
    animation: "book",
    targetItemIds: Object.freeze(["learning-garden", "study-desk", "book-shelf", "reading-lamp", "word-gallery"]),
    cues: Object.freeze({
      warmup: "先做一小组词，再停下来自己想一想。",
      output: "把刚练过的词用进一句自己的英文。",
      loop: "用 30 秒想想今天练过的词和句子。",
    }),
  }),
});

const WEEK_MEMORY_TONES = {
  calm: ["不用赶，我们稳稳积累。", "我把这格安静收好了。"],
  clingy: ["下一步也让我陪在旁边。", "这格我贴着你一起记住了。"],
  guardian: ["这份记录我替你守好了。", "下一步也交给我一起看着。"],
  chatty: ["下次也让我听见你的英语。", "这格有你的英语声音，我记得。"],
  gentle: ["慢慢来，我一直在旁边。", "这一步很稳，我会安静陪着你。"],
  adventurous: ["我们又往前探索了一小步。", "这一格探索完成，下一格继续。"],
  balanced: ["我会陪你把下一步走完。", "这格脚印已经好好留下来了。"],
};

const WEEK_MEMORY_OPENINGS = {
  unavailable: "这天还没有启用陪学记录。",
  rest: "这天留白也没关系。",
  started: "这天已经迈出第一步。",
  input: "这天的词汇热身完成了。",
  output: "这天已经把英语用出来了。",
  loop: "这天练了单词，也用过英语了。",
};

const WEEKLY_RHYTHM_TONES = {
  calm: "留两天休息也没关系，稳定回来比每天满格更重要。",
  clingy: "我会把休息日也留在身边，下一次回来再一起接上。",
  guardian: "一周学五天就很棒，另外两天放心交给我守着。",
  chatty: "不用天天说很多，五天里让我听见一点英语就很好。",
  gentle: "给自己留两天空白，轻松一点反而更容易坚持。",
  adventurous: "一周探索五天就够了，休息两天再出发也很好。",
  balanced: "最近七天学五天、休两天，会比硬撑每天更容易坚持。",
};

const RETURN_PROMISE_RHYTHMS = Object.freeze({
  "observe-then-decide": "我会先翻开旧脚印，等你想起一点再看答案。",
  "study-signal-first": "学习灯一亮，我会先来提醒我们这次回想。",
  "companion-seeker": "我会先来找你，再一起把这页慢慢想起来。",
  "familiar-corner-first": "我会在熟悉的学习角等你，再慢慢翻回这一页。",
  "new-route-scout": "我会替旧词找一个新句子，再听你把它用出来。",
  "play-before-rest": "先陪我活动一小会儿，再安静完成这次回想。",
  balanced: "我会替你收好这一页，下次回来再一起想起来。",
});

const RETURN_PROMISE_RECALL_CUES = Object.freeze({
  "gentle-starter": "只找回 1 个熟词，再写最短的 1 句自己的英语。",
  "story-builder": "找回 1 个词，再把它接回自己的 1 句话。",
  "idea-sparring": "找回 1 个词，再用它说清 1 个小观点。",
  "loop-keeper": "先遮住答案，找回 1 个词和 1 句话。",
  "streak-keeper": "只留下一枚回想爪印，不追加新的任务。",
  "review-organizer": "翻开共同手册，整理 1 个词和 1 句话。",
  balanced: "先不看答案，找回 1 个词和 1 句话。",
});

function safeCount(value) {
  return Math.max(Number(value || 0), 0);
}

function habitTodayDate(habit = {}) {
  const today = Array.isArray(habit.recentDays)
    ? habit.recentDays.find((day) => day?.today)?.date
    : "";
  return String(today || habit.date || "").trim();
}

function shiftIsoDate(value, days) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return "";
  const shifted = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + days));
  return shifted.toISOString().slice(0, 10);
}

function returnPromiseDateLabel(targetDate, todayDate) {
  if (!targetDate) return "下次有空时";
  const formatted = formatCatWorldLearningMemoryDate(targetDate);
  if (targetDate === todayDate) return "今天";
  if (targetDate === shiftIsoDate(todayDate, 1)) return `明天 · ${formatted}`;
  return formatted || targetDate;
}

export function buildCatWorldLearningPace(habit = {}) {
  const spellingCount = safeCount(habit.todaySpellingCount);
  const hasOutput = Boolean(habit.todayHasEssay || habit.todayHasDebate);
  const loopComplete = Boolean(habit.todayBalanceComplete) || (spellingCount >= MINIMUM_SPELLING_TARGET && hasOutput);
  const recentDays = Array.isArray(habit.recentDays)
    ? habit.recentDays.filter((day) => day?.statusKey !== "unavailable")
    : [];
  const todayIndex = recentDays.findIndex((day) => day?.today);
  const priorDays = todayIndex >= 0 ? recentDays.slice(0, todayIndex) : recentDays;
  const yesterday = priorDays.at(-1) || {};
  const returning = spellingCount === 0
    && !hasOutput
    && priorDays.some((day) => day?.active)
    && yesterday.statusKey === "rest";
  const coreGoalLabel = `${MINIMUM_SPELLING_TARGET} 词 + 说写一次`;

  if (loopComplete) {
    return {
      key: "complete",
      label: "安心收工",
      timeLabel: "今日已完成",
      coreGoalLabel,
      detail: "今天要做的两件事都完成了，不用为了数字一直练。",
      roomCue: "今天已经完整收好啦，接下来放心休息和陪猫就好。",
    };
  }
  if (returning) {
    return {
      key: "returning",
      label: "轻轻回来",
      timeLabel: "约 2 分钟",
      coreGoalLabel,
      detail: "不用补昨天，今天先练 5 个词；还有精神再继续。",
      roomCue: "昨天休息了也没关系，我先陪你做 5 个词，把今天轻轻接上。",
    };
  }
  if (hasOutput && spellingCount < MINIMUM_SPELLING_TARGET) {
    return {
      key: "vocabulary",
      label: "再练几个词",
      timeLabel: `还差 ${MINIMUM_SPELLING_TARGET - spellingCount} 词`,
      coreGoalLabel,
      detail: `表达已经完成，今天只需把词汇热身补到 ${MINIMUM_SPELLING_TARGET} 词。`,
      roomCue: `表达已经完成，我陪你再练 ${MINIMUM_SPELLING_TARGET - spellingCount} 个词就收工。`,
    };
  }
  if (spellingCount >= MINIMUM_SPELLING_TARGET) {
    return {
      key: "output",
      label: "再说写一次",
      timeLabel: "约 5-10 分钟",
      coreGoalLabel,
      detail: "今天的词已经练够了，再写一小段或说几句英语就完成了。",
      roomCue: "今天的词已经练够了，我陪你把其中几个用进一句自己的英语。",
    };
  }
  if (spellingCount > 0) {
    return {
      key: "steady",
      label: "继续练一点",
      timeLabel: `还差 ${MINIMUM_SPELLING_TARGET - spellingCount} 词`,
      coreGoalLabel,
      detail: `已经开始啦，今天做到 ${MINIMUM_SPELLING_TARGET} 个词就好，不用一下做很多。`,
      roomCue: `已经开始就很好，我陪你再走 ${MINIMUM_SPELLING_TARGET - spellingCount} 个词。`,
    };
  }
  return {
    key: "starter",
    label: "轻轻开始",
    timeLabel: "约 2 分钟",
    coreGoalLabel,
    detail: "先完成 5 个词，让开始足够轻；做完再决定要不要继续。",
    roomCue: "我们先做 5 个词，今天只需要一个很轻的开始。",
  };
}

export function buildCatWorldReturnPromise(habit = {}, cat = {}, memory = {}) {
  const normalizedMemory = normalizeCatWorldLearningMemory(memory);
  const pace = buildCatWorldLearningPace(habit);
  const todayDate = habitTodayDate(habit);
  const rhythmKey = String(cat.actionRhythm?.key || "balanced");
  const rhythmLine = RETURN_PROMISE_RHYTHMS[rhythmKey] || RETURN_PROMISE_RHYTHMS.balanced;
  const styleKey = String(cat.learningStyle?.key || "balanced");
  const recallCue = RETURN_PROMISE_RECALL_CUES[styleKey] || RETURN_PROMISE_RECALL_CUES.balanced;
  const catName = String(cat.nickname || cat.displayLabel || cat.label || cat.breedLabel || "今日陪学猫");
  const base = {
    visible: normalizedMemory.hasMemory || pace.key === "complete",
    catName,
    rhythmLabel: String(cat.actionRhythm?.label || "按自己的步子"),
    message: "",
    sourceDate: "",
    targetDate: "",
  };

  if (normalizedMemory.reviewDueToday && !normalizedMemory.reviewedToday) {
    const stageLabel = normalizedMemory.suggestedReviewStageLabel || "自己想一想";
    const detail = `${recallCue} 做完今天就可以安心停下。`;
    return {
      ...base,
      key: "review-due",
      eyebrow: "今日约定",
      dateLabel: "现在",
      title: `${stageLabel} · 30 秒`,
      detail,
      actionKind: "review",
      actionLabel: "打开共同手册",
      sourceDate: normalizedMemory.suggestedReviewDate,
      targetDate: todayDate,
      message: `${rhythmLine}${recallCue}`,
    };
  }

  if (normalizedMemory.nextReviewDate) {
    const reviewDay = normalizedMemory.recentDays.find(
      (day) => day.nextReviewDate === normalizedMemory.nextReviewDate,
    ) || {};
    const stageLabel = reviewDay.reviewStageLabel || "自己想一想";
    const dateLabel = returnPromiseDateLabel(normalizedMemory.nextReviewDate, todayDate);
    const detail = pace.key === "complete"
      ? `今天已经收好。${recallCue}`
      : `${recallCue} 下次只完成这一小步，再决定要不要继续。`;
    return {
      ...base,
      key: "scheduled",
      eyebrow: "下次见面",
      dateLabel,
      title: `${stageLabel} · 30 秒`,
      detail,
      actionKind: "listen",
      actionLabel: `听听${catName}的约定`,
      sourceDate: String(reviewDay.date || ""),
      targetDate: normalizedMemory.nextReviewDate,
      message: `${dateLabel}，${rhythmLine}${recallCue}`,
    };
  }

  const tomorrowDate = shiftIsoDate(todayDate, 1);
  if (pace.key === "complete") {
    const dateLabel = returnPromiseDateLabel(tomorrowDate, todayDate);
    return {
      ...base,
      key: "rest",
      eyebrow: "明日约定",
      dateLabel,
      title: "明天先练 5 词",
      detail: "今天已经完成啦；明天先练 5 个词，不用多做。",
      actionKind: "listen",
      actionLabel: `听听${catName}的约定`,
      targetDate: tomorrowDate,
      message: `${dateLabel}，${rhythmLine}我们先用 5 个词轻轻接上。`,
    };
  }

  return {
    ...base,
    key: "continue",
    eyebrow: "下次接上",
    dateLabel: "有空时",
    title: pace.label,
    detail: `${pace.detail} 中途离开也没关系，回来从这里继续。`,
    actionKind: "listen",
    actionLabel: `听听${catName}怎么说`,
    message: `${rhythmLine}${pace.roomCue}`,
  };
}

export function buildCatWorldLearningRitual(learningStyle = {}, stepKey = "warmup") {
  const requestedStyleKey = String(learningStyle?.key || "balanced");
  const styleKey = LEARNING_RITUALS[requestedStyleKey] ? requestedStyleKey : "balanced";
  const ritual = LEARNING_RITUALS[styleKey];
  const normalizedStepKey = stepKey === "output" ? "output" : ["loop", "wrapup"].includes(stepKey) ? "loop" : "warmup";
  const targetItemIds = [...ritual.targetItemIds];
  const primaryTargetId = targetItemIds[0] || "learning-garden";
  return {
    styleKey,
    label: ritual.label,
    cue: ritual.cues[normalizedStepKey] || ritual.cues.warmup,
    stepKey: normalizedStepKey,
    animation: ritual.animation,
    targetItemIds,
    primaryTargetId,
    destinationLabel: LEARNING_RITUAL_TARGET_LABELS[primaryTargetId] || "学习角",
  };
}

export function buildCatWorldHabitGarden(habit = {}) {
  const recentDays = Array.isArray(habit.recentDays) ? habit.recentDays : [];
  const hasTotalActiveDays = Number.isFinite(Number(habit.totalActiveDays));
  const hasTotalLoopDays = Number.isFinite(Number(habit.totalLoopDays));
  const activeDays = hasTotalActiveDays
    ? safeCount(habit.totalActiveDays)
    : recentDays.filter((day) => day?.active).length;
  const loopDays = hasTotalLoopDays
    ? safeCount(habit.totalLoopDays)
    : recentDays.filter((day) => day?.loopComplete).length;
  const growthPoints = activeDays + loopDays;
  const stageIndex = HABIT_GARDEN_STAGES.reduce(
    (current, stage, index) => (growthPoints >= stage.threshold ? index : current),
    0,
  );
  const stage = HABIT_GARDEN_STAGES[stageIndex];
  const nextStage = HABIT_GARDEN_STAGES[stageIndex + 1] || null;
  return {
    key: stage.key,
    stageIndex,
    stageLabel: stage.label,
    growthPoints,
    activeDays,
    loopDays,
    bestStreak: safeCount(habit.bestStreak ?? habit.currentStreak),
    nextStageLabel: nextStage?.label || "",
    nextThreshold: nextStage?.threshold ?? growthPoints,
    nextRemaining: nextStage ? Math.max(nextStage.threshold - growthPoints, 0) : 0,
  };
}

export function buildCatWorldLearningRoute(habit = {}, cat = {}) {
  const spellingCount = safeCount(habit.todaySpellingCount);
  const streak = safeCount(habit.currentStreak);
  const hasEssay = Boolean(habit.todayHasEssay);
  const hasDebate = Boolean(habit.todayHasDebate);
  const hasOutput = hasEssay || hasDebate;
  const starterComplete = spellingCount >= STARTER_SPELLING_TARGET;
  const warmupComplete = spellingCount >= MINIMUM_SPELLING_TARGET;
  const learningLoopComplete = Boolean(habit.todayBalanceComplete) || (warmupComplete && hasOutput);
  const guideName = cat.nickname || cat.label || cat.breedLabel || cat.displayLabel || "主猫";
  const nextAction = String(habit.nextAction || "今天先练 20 个拼写词");
  const learningStyle = cat.learningStyle || {};
  const preferredOutput = learningStyle.preferredOutput === "debate" ? "debate" : "essay";
  const essayAction = hasEssay ? "再写一篇" : "去写作文";
  const debateAction = hasDebate ? "再辩一场" : "去做英语辩论";
  const outputAction = preferredOutput === "debate"
    ? { action: debateAction, href: "/debate", alternateAction: essayAction, alternateHref: "/essays" }
    : { action: essayAction, href: "/essays", alternateAction: debateAction, alternateHref: "/debate" };
  const garden = buildCatWorldHabitGarden(habit);
  const pace = buildCatWorldLearningPace(habit);
  const weeklyRhythm = buildCatWorldWeeklyRhythm(habit, cat);

  const steps = [
    {
      key: "warmup",
      label: "20 词热身",
      detail: warmupComplete
        ? `已完成 ${spellingCount} 词，今天顺利启动`
        : starterComplete
          ? `已点亮起步爪印 · ${spellingCount}/${MINIMUM_SPELLING_TARGET} 词，继续小步积累`
          : `${spellingCount}/${STARTER_SPELLING_TARGET} 词，先点亮起步爪印`,
      action: warmupComplete ? "继续积累" : "去练单词",
      href: "/lists",
      completed: warmupComplete,
    },
    {
      key: "output",
      label: "把英语用出来",
      detail: hasEssay && hasDebate
        ? "作文和 AI 英语辩论都完成了"
        : hasEssay
          ? "英文作文已完成"
          : hasDebate
            ? "AI 英语辩论已完成"
            : preferredOutput === "debate"
              ? "先完成一次 AI 英语辩论，也可以写一篇英文作文"
              : "先写一篇英文作文，也可以完成一次 AI 英语辩论",
      ...outputAction,
      completed: hasOutput,
    },
    {
      key: "wrapup",
      label: "今天全部完成",
      detail: learningLoopComplete
        ? `练词和英语表达都完成，最近七天已有 ${weeklyRhythm.activeDays} 天学习`
        : warmupComplete
          ? "再写一写或说一说英语，今天就完成了"
          : hasOutput
            ? "再完成 20 词热身，就能收好今天的成果"
            : "完成前两步，今天的学习就全部做完啦",
      action: "查看今日能量",
      actionKind: "energy",
      completed: learningLoopComplete,
    },
  ];
  const firstIncompleteIndex = steps.findIndex((step) => !step.completed);
  const activeIndex = firstIncompleteIndex >= 0 ? firstIncompleteIndex : steps.length - 1;
  const baseRitual = buildCatWorldLearningRitual(learningStyle, steps[activeIndex]?.key);
  const ritual = ["returning", "complete"].includes(pace.key)
    ? { ...baseRitual, cue: pace.roomCue }
    : baseRitual;

  return {
    guideName,
    title: `${guideName}的今日学习计划`,
    coachLine: nextAction,
    learningStyleLabel: learningStyle.label || "平衡陪学搭档",
    learningFocusLabel: learningStyle.focusLabel || "先练一点词，再说写一次",
    learningStyleDescription: learningStyle.description || "陪你按舒服的步子完成今天的英语学习。",
    preferredOutput,
    pace,
    ritual,
    streak,
    garden,
    weeklyRhythm,
    starterTarget: STARTER_SPELLING_TARGET,
    starterCount: Math.min(spellingCount, STARTER_SPELLING_TARGET),
    starterRemaining: Math.max(STARTER_SPELLING_TARGET - spellingCount, 0),
    starterComplete,
    completedCount: steps.filter((step) => step.completed).length,
    steps: steps.map((step, index) => ({ ...step, active: index === activeIndex })),
  };
}

export function buildCatWorldRoomLearningSignal(habit = {}, cat = {}, companion = {}) {
  const spellingCount = safeCount(habit.todaySpellingCount);
  const starterComplete = spellingCount >= STARTER_SPELLING_TARGET;
  const warmupComplete = spellingCount >= MINIMUM_SPELLING_TARGET;
  const outputComplete = Boolean(habit.todayHasEssay || habit.todayHasDebate);
  const loopComplete = Boolean(habit.todayBalanceComplete) || (warmupComplete && outputComplete);
  const completedByKey = {
    warmup: warmupComplete,
    output: outputComplete,
    loop: loopComplete,
  };
  const steps = ROOM_LEARNING_STEPS.map((step) => ({
    ...step,
    completed: completedByKey[step.key],
  }));
  const firstIncompleteIndex = steps.findIndex((step) => !step.completed);
  const activeIndex = firstIncompleteIndex >= 0 ? firstIncompleteIndex : steps.length - 1;
  const completedCount = steps.filter((step) => step.completed).length;
  const guideCatId = String(companion.catId || cat.id || cat.profileId || "");
  const guideName = cat.nickname || cat.label || cat.displayLabel || cat.breedLabel || "今日陪学猫";
  const currentDay = Array.isArray(habit.recentDays)
    ? habit.recentDays.find((day) => day?.today)?.date
    : "";
  const stageKey = loopComplete
    ? "loop"
    : warmupComplete
      ? "warmup"
      : outputComplete
        ? "output"
        : starterComplete
          ? "started"
          : "starting";
  const fallbackMessages = {
    started: `${guideName}看到起步爪印亮起来了，再慢慢走到 20 词吧。`,
    warmup: `${guideName}看到第一格亮起来了，再把英语用出来吧。`,
    output: `${guideName}看到表达格亮起来了，再练 20 个词就完整啦。`,
    loop: `${guideName}看到三格都亮了，今天的学习全部完成啦。`,
  };
  const garden = buildCatWorldHabitGarden(habit);
  const pace = buildCatWorldLearningPace(habit);
  const learningMemory = normalizeCatWorldLearningMemory(cat.learningMemory || companion.memory || {});
  const baseRitual = buildCatWorldLearningRitual(
    cat.learningStyle || {},
    loopComplete ? "loop" : steps[activeIndex]?.key,
  );
  const ritual = ["returning", "complete"].includes(pace.key)
    ? { ...baseRitual, cue: pace.roomCue }
    : baseRitual;

  return {
    token: `${currentDay || "today"}:${guideCatId || "cat"}:${starterComplete ? 1 : 0}:${stageKey}:${completedCount}`,
    date: String(currentDay || companion.date || ""),
    guideCatId,
    guideName,
    spellingCount,
    starterTarget: STARTER_SPELLING_TARGET,
    starterCount: Math.min(spellingCount, STARTER_SPELLING_TARGET),
    starterRemaining: Math.max(STARTER_SPELLING_TARGET - spellingCount, 0),
    starterComplete,
    completedCount,
    stageKey,
    statusLabel: loopComplete
      ? "今天全部完成"
      : warmupComplete
        ? `${spellingCount} 词已热身`
        : outputComplete
          ? "已经完成表达"
          : starterComplete
            ? "5 词起步完成"
            : `再 ${Math.max(STARTER_SPELLING_TARGET - spellingCount, 0)} 词点亮起步爪印`,
    celebrationMessage: String(companion.message || fallbackMessages[stageKey] || "").trim(),
    garden,
    pace,
    learningMemory,
    ritual,
    steps: steps.map((step, index) => ({ ...step, active: index === activeIndex })),
  };
}

export function buildCatWorldWeekTrail(habit = {}) {
  const sourceDays = Array.isArray(habit.recentDays) ? habit.recentDays.slice(-7) : [];
  const days = sourceDays.map((day) => {
    const statusKey = ["unavailable", "rest", "started", "input", "output", "loop"].includes(day?.statusKey)
      ? day.statusKey
      : "rest";
    return {
      date: String(day?.date || ""),
      weekdayLabel: String(day?.weekdayLabel || ""),
      dayLabel: String(day?.dayLabel || ""),
      statusKey,
      statusLabel: String(day?.statusLabel || "休息"),
      detail: String(day?.detail || "这天没有学习记录"),
      spellingCount: safeCount(day?.spellingCount),
      hasEssay: Boolean(day?.hasEssay),
      hasDebate: Boolean(day?.hasDebate),
      active: Boolean(day?.active),
      loopComplete: Boolean(day?.loopComplete),
      today: Boolean(day?.today),
    };
  });
  const activeDays = days.filter((day) => day.active).length;
  const loopDays = days.filter((day) => day.loopComplete).length;
  const today = days.find((day) => day.today) || days.at(-1) || {};
  const todayMessage = today.statusKey === "loop"
    ? "今天全部完成"
    : today.statusKey === "input"
      ? "今天已完成练词热身"
      : today.statusKey === "output"
        ? "今天已经练过英语表达"
        : today.statusKey === "started"
          ? "今天已经开始"
          : "今天可以从 20 词热身开始";
  return {
    days,
    activeDays,
    loopDays,
    summary: `${activeDays} 天有学习 · ${loopDays} 天练词和表达都做了`,
    todayMessage,
  };
}

export function buildCatWorldWeeklyRhythm(habit = {}, cat = {}) {
  const trail = buildCatWorldWeekTrail(habit);
  const todaySpellingCount = safeCount(habit.todaySpellingCount);
  const todayHasOutput = Boolean(habit.todayHasEssay || habit.todayHasDebate);
  const activeDays = trail.days.length
    ? trail.activeDays
    : Number(todaySpellingCount >= STARTER_SPELLING_TARGET || todayHasOutput);
  const loopDays = trail.days.length
    ? trail.loopDays
    : Number(Boolean(habit.todayBalanceComplete) || (todaySpellingCount >= MINIMUM_SPELLING_TARGET && todayHasOutput));
  const activeRemaining = Math.max(WEEKLY_TOUCHPOINT_TARGET - activeDays, 0);
  const loopRemaining = Math.max(WEEKLY_LOOP_TARGET - loopDays, 0);
  const touchpointComplete = activeRemaining === 0;
  const loopComplete = loopRemaining === 0;
  const statusKey = touchpointComplete && loopComplete
    ? "complete"
    : touchpointComplete
      ? "touchpoint"
      : loopComplete
        ? "loop"
        : activeDays || loopDays
          ? "steady"
          : "starter";
  const statusLabels = {
    complete: "这周做得真棒",
    touchpoint: "已经学习五天",
    loop: "两项都做够三天",
    steady: "正在养成好习惯",
    starter: "从今天开始",
  };
  let detail = `再学 ${activeRemaining} 天，其中 ${loopRemaining} 天既练单词，也写一写或说一说英语。`;
  if (statusKey === "complete") {
    detail = "这周已经学了五天，其中三天两项都做了；今天可以放心休息。";
  } else if (statusKey === "touchpoint") {
    detail = `这周已经学够五天；有精神时，再用 ${loopRemaining} 天把练词和表达都做完。`;
  } else if (statusKey === "loop") {
    detail = `已经有三天把两项都做完了；再用 ${activeRemaining} 天各练 5 个词就很棒。`;
  } else if (statusKey === "starter") {
    detail = "今天先练 5 个词，留下第一枚学习爪印，不用一次做很多。";
  }
  const temperament = String(cat?.traits?.temperament || cat?.temperament || "balanced");
  const catName = cat.nickname || cat.displayLabel || cat.label || cat.breedLabel || "今日陪学猫";
  return {
    statusKey,
    statusLabel: statusLabels[statusKey],
    detail,
    activeDays,
    activeTarget: WEEKLY_TOUCHPOINT_TARGET,
    activeRemaining,
    activePercent: Math.min(Math.round((activeDays / WEEKLY_TOUCHPOINT_TARGET) * 100), 100),
    loopDays,
    loopTarget: WEEKLY_LOOP_TARGET,
    loopRemaining,
    loopPercent: Math.min(Math.round((loopDays / WEEKLY_LOOP_TARGET) * 100), 100),
    restAllowance: 2,
    catLine: `${catName}：${WEEKLY_RHYTHM_TONES[temperament] || WEEKLY_RHYTHM_TONES.balanced}`,
  };
}

function stableWeekMemoryIndex(seed, length) {
  if (length <= 1) return 0;
  let hash = 0;
  for (const character of String(seed || "")) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return hash % length;
}

export function catWorldWeekMemory(day = {}, cat = {}) {
  const statusKey = WEEK_MEMORY_OPENINGS[day?.statusKey] ? day.statusKey : "rest";
  const temperament = String(cat?.traits?.temperament || cat?.temperament || "balanced");
  const tones = WEEK_MEMORY_TONES[temperament] || WEEK_MEMORY_TONES.balanced;
  const catName = cat.nickname || cat.displayLabel || cat.label || cat.breedLabel || "今日陪学猫";
  const toneIndex = stableWeekMemoryIndex(`${cat.id || cat.profileId || catName}:${day.date}:${statusKey}`, tones.length);
  const catMessage = statusKey === "unavailable"
    ? "那时还没有陪学记录。从现在开始，我会陪你留下新的脚印。"
    : `${WEEK_MEMORY_OPENINGS[statusKey]}${tones[toneIndex]}`;
  return {
    dateLabel: [day.weekdayLabel, day.dayLabel].filter(Boolean).join(" ") || "学习记忆",
    detail: String(day.detail || "这天没有学习记录"),
    catName,
    catMessage,
  };
}

export function catWorldLearningCompanionToken(companion = {}) {
  const day = String(companion.date || "").trim();
  const catId = String(companion.catId || "").trim();
  const statusKey = String(companion.statusKey || "").trim();
  if (!day || !catId || !statusKey || statusKey === "starting") return "";
  return `${day}:${catId}:${statusKey}`;
}

export function catWorldLearningCompanionGrowthLabel(companion = {}) {
  const moodGain = safeCount(companion.earnedMoodGain);
  const bondGain = safeCount(companion.earnedBondGain);
  if (!moodGain && !bondGain) return "等待今天的第一步";
  return [`心情 +${moodGain}`, `信任 +${bondGain}`].join(" · ");
}
