import { ref } from "vue";
import { coreApiPaths } from "./coreApiPaths.js";
import { parseShellContext, readShellContextElementText } from "./shellContextState.js";
import { fetchJson } from "./utils.js";

export function readShellContext() {
  return parseShellContext(readShellContextElementText());
}

export function useShellContext() {
  const shellContext = ref(readShellContext());

  async function refreshShellContext() {
    try {
      shellContext.value = await fetchJson(coreApiPaths.shell());
    } catch {
      // Keep the server-rendered shell context if the lightweight refresh fails.
    }
  }

  return {
    shellContext,
    refreshShellContext,
  };
}
