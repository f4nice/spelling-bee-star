import { ref } from "vue";
import { fetchJson } from "./utils.js";

const DEFAULT_SHELL_CONTEXT = {
  appName: "SpeakEasy",
  dailyQuote: null,
  wrongWordCount: 0,
  sidebarChallenges: [],
};

function defaultShellContext() {
  return { ...DEFAULT_SHELL_CONTEXT, sidebarChallenges: [] };
}

export function readShellContext() {
  const element = document.getElementById("speakeasy-shell-context");
  if (!element?.textContent) {
    return defaultShellContext();
  }
  try {
    return JSON.parse(element.textContent);
  } catch {
    return defaultShellContext();
  }
}

export function useShellContext() {
  const shellContext = ref(readShellContext());

  async function refreshShellContext() {
    try {
      shellContext.value = await fetchJson("/api/vue/shell");
    } catch {
      // Keep the server-rendered shell context if the lightweight refresh fails.
    }
  }

  return {
    shellContext,
    refreshShellContext,
  };
}
