const MINIMUM_SPELLING_TARGET = 20;
const STARTER_SPELLING_TARGET = 5;

const ROOM_LEARNING_STEPS = Object.freeze([
  Object.freeze({ key: "warmup", label: "20词" }),
  Object.freeze({ key: "output", label: "说写" }),
  Object.freeze({ key: "loop", label: "闭环" }),
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
    label: "输入输出接力",
    animation: "paw",
    targetItemIds: Object.freeze(["word-gallery", "study-desk", "learning-garden", "book-shelf"]),
    cues: Object.freeze({
      warmup: "练词时选 3 个今天一定要用出来的词。",
      output: "不看答案，先用刚练的词表达一遍，再回头修正。",
      loop: "对照输入和输出，确认至少有 1 个新词真正用过。",
    }),
  }),
  "streak-keeper": Object.freeze({
    label: "最低可行记录",
    animation: "heart",
    targetItemIds: Object.freeze(["learning-garden", "book-shelf", "reading-lamp", "word-gallery"]),
    cues: Object.freeze({
      warmup: "状态一般也只做 5 个词，先保住今天的学习触点。",
      output: "完成一次最短表达，给今天留下一条真实记录。",
      loop: "记住今天最小但真实的一步，明天从这里继续。",
    }),
  }),
  "review-organizer": Object.freeze({
    label: "遮答主动回想",
    animation: "book",
    targetItemIds: Object.freeze(["book-shelf", "word-gallery", "study-desk", "learning-garden"]),
    cues: Object.freeze({
      warmup: "先看词义，再遮住答案主动回想一次。",
      output: "挑 3 个容易忘的词，各用一句英文把它们叫回来。",
      loop: "离开页面前再回想一轮，答不出的词留给明天。",
    }),
  }),
  balanced: Object.freeze({
    label: "输入输出交替",
    animation: "book",
    targetItemIds: Object.freeze(["learning-garden", "study-desk", "book-shelf", "reading-lamp", "word-gallery"]),
    cues: Object.freeze({
      warmup: "先做一小组词，再停下来主动回想一次。",
      output: "把刚练过的词用进一句自己的英文。",
      loop: "用 30 秒回顾今天的输入和表达。",
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
  loop: "这天输入和表达都完成了。",
};

function safeCount(value) {
  return Math.max(Number(value || 0), 0);
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
  const coreGoalLabel = `${MINIMUM_SPELLING_TARGET} 词 + 1 次输出`;

  if (loopComplete) {
    return {
      key: "complete",
      label: "安心收工",
      timeLabel: "今日已完成",
      coreGoalLabel,
      detail: "今天的习惯目标已经完成，不必为了连续记录继续刷量。",
      roomCue: "今天已经完整收好啦，接下来放心休息和陪猫就好。",
    };
  }
  if (returning) {
    return {
      key: "returning",
      label: "轻量回归",
      timeLabel: "约 2 分钟",
      coreGoalLabel,
      detail: "不用补昨天，先用 5 个词把今天重新接上；状态不错再继续。",
      roomCue: "昨天休息了也没关系，我先陪你做 5 个词，把今天轻轻接上。",
    };
  }
  if (hasOutput && spellingCount < MINIMUM_SPELLING_TARGET) {
    return {
      key: "vocabulary",
      label: "词汇收尾",
      timeLabel: `还差 ${MINIMUM_SPELLING_TARGET - spellingCount} 词`,
      coreGoalLabel,
      detail: `表达已经完成，今天只需把词汇热身补到 ${MINIMUM_SPELLING_TARGET} 词。`,
      roomCue: `表达已经完成，我陪你再练 ${MINIMUM_SPELLING_TARGET - spellingCount} 个词就收工。`,
    };
  }
  if (spellingCount >= MINIMUM_SPELLING_TARGET) {
    return {
      key: "output",
      label: "表达收尾",
      timeLabel: "约 5-10 分钟",
      coreGoalLabel,
      detail: "词汇热身已经够了，完成一小段英语输出就可以收工。",
      roomCue: "今天的词已经练够了，我陪你把其中几个用进一句自己的英语。",
    };
  }
  if (spellingCount > 0) {
    return {
      key: "steady",
      label: "稳步推进",
      timeLabel: `还差 ${MINIMUM_SPELLING_TARGET - spellingCount} 词`,
      coreGoalLabel,
      detail: `已经开始，今天稳定走到 ${MINIMUM_SPELLING_TARGET} 词就好，不需要追求堆量。`,
      roomCue: `已经开始就很好，我陪你再走 ${MINIMUM_SPELLING_TARGET - spellingCount} 个词。`,
    };
  }
  return {
    key: "starter",
    label: "轻量启动",
    timeLabel: "约 2 分钟",
    coreGoalLabel,
    detail: "先完成 5 个词，让开始足够轻；做完再决定要不要继续。",
    roomCue: "我们先做 5 个词，今天只需要一个很轻的开始。",
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
  const nextAction = String(habit.nextAction || "先完成 20 个拼写词，开启今天的学习节奏");
  const learningStyle = cat.learningStyle || {};
  const preferredOutput = learningStyle.preferredOutput === "debate" ? "debate" : "essay";
  const essayAction = hasEssay ? "再写一篇" : "去写作文";
  const debateAction = hasDebate ? "再辩一场" : "去做 Debate";
  const outputAction = preferredOutput === "debate"
    ? { action: debateAction, href: "/debate", alternateAction: essayAction, alternateHref: "/essays" }
    : { action: essayAction, href: "/essays", alternateAction: debateAction, alternateHref: "/debate" };
  const garden = buildCatWorldHabitGarden(habit);
  const pace = buildCatWorldLearningPace(habit);

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
        ? "作文和 AI Debate 都完成了"
        : hasEssay
          ? "英文作文已完成"
          : hasDebate
            ? "AI Debate 已完成"
            : preferredOutput === "debate"
              ? "先完成一次 AI Debate，也可以写一篇英文作文"
              : "先写一篇英文作文，也可以完成一次 AI Debate",
      ...outputAction,
      completed: hasOutput,
    },
    {
      key: "wrapup",
      label: "完成今日闭环",
      detail: learningLoopComplete
        ? `输入和输出都完成，已连续学习 ${streak || 1} 天`
        : warmupComplete
          ? "再完成一次英语输出，就能收好今天的成果"
          : hasOutput
            ? "再完成 20 词热身，就能收好今天的成果"
            : "完成前两步，形成一次完整的学习闭环",
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
    title: `${guideName}的今日陪学路线`,
    coachLine: nextAction,
    learningStyleLabel: learningStyle.label || "平衡陪学搭档",
    learningFocusLabel: learningStyle.focusLabel || "少量输入，再完成一次表达",
    learningStyleDescription: learningStyle.description || "陪你用适合自己的节奏完成今天的英语学习。",
    preferredOutput,
    pace,
    ritual,
    streak,
    garden,
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
    loop: `${guideName}看到三格都亮了，今天的英语闭环完成啦。`,
  };
  const garden = buildCatWorldHabitGarden(habit);
  const pace = buildCatWorldLearningPace(habit);
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
      ? "今日闭环"
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
    ? "今天闭环完成"
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
    summary: `${activeDays} 天有学习 · ${loopDays} 天完成闭环`,
    todayMessage,
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
