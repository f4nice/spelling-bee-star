const DEFAULT_LEARNING_GROWTH = {
  title: "成长成就",
  subtitle: "像闯关一样完成每天学习",
  level: 1,
  points: 0,
  trophyImageUrl: "/static/icons/challenge-crown-transparent.png",
  metrics: [],
  dailyMissions: [],
};

const DEFAULT_SHELL_CONTEXT = {
  appName: "SpeakEasy",
  dailyQuote: null,
  wrongWordCount: 0,
  sidebarChallenges: [],
  learningGrowth: DEFAULT_LEARNING_GROWTH,
  versionMatrix: {
    version: "BIZ-REL-20260627-012",
    releaseName: "Vue 全站版",
    pageVersion: "v20260627.1",
    footerText: "SpeakEasy",
    modules: [],
  },
};

export function defaultShellContext() {
  return {
    ...DEFAULT_SHELL_CONTEXT,
    sidebarChallenges: [],
    learningGrowth: { ...DEFAULT_LEARNING_GROWTH, metrics: [], dailyMissions: [] },
  };
}

export function parseShellContext(text) {
  if (!text) return defaultShellContext();
  try {
    return JSON.parse(text);
  } catch {
    return defaultShellContext();
  }
}

export function readShellContextElementText(documentRef = document) {
  return documentRef.getElementById("speakeasy-shell-context")?.textContent || "";
}
