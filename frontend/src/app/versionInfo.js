import { defaultShellContext, parseShellContext, readShellContextElementText } from "./shellContextState.js";

export function fallbackVersionMatrix() {
  return defaultShellContext().versionMatrix;
}

export function normalizeVersionMatrix(matrix) {
  const fallback = fallbackVersionMatrix();
  const source = matrix && typeof matrix === "object" ? matrix : fallback;
  return {
    version: source.version || fallback.version,
    releaseName: source.releaseName || fallback.releaseName,
    machineCode: source.machineCode || fallback.machineCode,
    footerText: source.footerText || fallback.footerText,
    modules: Array.isArray(source.modules) ? source.modules : [],
  };
}

export function readVersionMatrix() {
  return normalizeVersionMatrix(parseShellContext(readShellContextElementText()).versionMatrix);
}
