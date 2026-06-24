const DEFAULT_SHELL_CONTEXT = {
  appName: "SpeakEasy",
  dailyQuote: null,
  wrongWordCount: 0,
  sidebarChallenges: [],
  versionMatrix: {
    version: "BIZ-REL-20260624-011",
    releaseName: "Vue 全站版",
    pageVersion: "v20260624.0",
    footerText: "SpeakEasy",
    modules: [],
  },
};

export function defaultShellContext() {
  return { ...DEFAULT_SHELL_CONTEXT, sidebarChallenges: [] };
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
