export function currentChallengeParams() {
  return new URLSearchParams(window.location.search);
}

export function paramsFromChallengeResult(result) {
  return new URLSearchParams(result.query);
}

export function replaceChallengeParams(params) {
  history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
}
