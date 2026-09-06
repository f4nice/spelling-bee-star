const MINIMUM_SPELLING_TARGET = 20;

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
