export function isChallengeRoute(route) {
  return route.name === "challenge";
}

export function isWordDetailRoute(route) {
  return route.name === "wordDetail";
}

export function isImportRoute(route) {
  return route.name === "upload" || route.name === "preview";
}

export function isBooklearnerRoute(route) {
  return route.name.startsWith("booklearner");
}
