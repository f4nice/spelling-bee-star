const MINIMUM_SPELLING_TARGET = 20;

const ROOM_LEARNING_STEPS = Object.freeze([
  Object.freeze({ key: "warmup", label: "20词" }),
  Object.freeze({ key: "output", label: "说写" }),
  Object.freeze({ key: "loop", label: "闭环" }),
]);

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

export function buildCatWorldLearningRoute(habit = {}, cat = {}) {
  const spellingCount = safeCount(habit.todaySpellingCount);
  const streak = safeCount(habit.currentStreak);
  const hasEssay = Boolean(habit.todayHasEssay);
  const hasDebate = Boolean(habit.todayHasDebate);
  const hasOutput = hasEssay || hasDebate;
  const warmupComplete = spellingCount >= MINIMUM_SPELLING_TARGET;
  const learningLoopComplete = Boolean(habit.todayBalanceComplete) || (warmupComplete && hasOutput);
  const guideName = cat.nickname || cat.label || cat.breedLabel || cat.displayLabel || "主猫";
  const nextAction = String(habit.nextAction || "先完成 20 个拼写词，开启今天的学习节奏");

  const steps = [
    {
      key: "warmup",
      label: "20 词热身",
      detail: warmupComplete
        ? `已完成 ${spellingCount} 词，今天顺利启动`
        : `${spellingCount}/${MINIMUM_SPELLING_TARGET} 词，先做一小份`,
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
            : "完成一篇作文或一次 AI Debate",
      action: hasOutput ? "再写一篇" : "去写作文",
      href: "/essays",
      alternateAction: hasOutput ? "再辩一场" : "AI Debate",
      alternateHref: "/debate",
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

  return {
    guideName,
    title: `${guideName}的今日陪学路线`,
    coachLine: nextAction,
    streak,
    completedCount: steps.filter((step) => step.completed).length,
    steps: steps.map((step, index) => ({ ...step, active: index === activeIndex })),
  };
}

export function buildCatWorldRoomLearningSignal(habit = {}, cat = {}, companion = {}) {
  const spellingCount = safeCount(habit.todaySpellingCount);
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
  const stageKey = loopComplete ? "loop" : warmupComplete ? "warmup" : outputComplete ? "output" : "starting";
  const fallbackMessages = {
    warmup: `${guideName}看到第一格亮起来了，再把英语用出来吧。`,
    output: `${guideName}看到表达格亮起来了，再练 20 个词就完整啦。`,
    loop: `${guideName}看到三格都亮了，今天的英语闭环完成啦。`,
  };

  return {
    token: `${currentDay || "today"}:${guideCatId || "cat"}:${stageKey}:${completedCount}`,
    date: String(currentDay || companion.date || ""),
    guideCatId,
    guideName,
    spellingCount,
    completedCount,
    stageKey,
    statusLabel: loopComplete
      ? "今日闭环"
      : warmupComplete
        ? `${spellingCount} 词已热身`
        : outputComplete
          ? "已经完成表达"
          : "等待今日开始",
    celebrationMessage: String(companion.message || fallbackMessages[stageKey] || "").trim(),
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
