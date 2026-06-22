const DEFAULT_SHELL_CONTEXT = {
  appName: "SpeakEasy",
  dailyQuote: null,
  wrongWordCount: 0,
  sidebarChallenges: [],
  versionMatrix: {
    version: "v0.1.0",
    releaseName: "Vue 全站版",
    machineCode: "",
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
