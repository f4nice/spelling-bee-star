export const CAT_BUBBLE_HOLD_MS = 4500;
export const CAT_BUBBLE_FADE_MS = 2500;
export const CAT_BUBBLE_TOTAL_MS = CAT_BUBBLE_HOLD_MS + CAT_BUBBLE_FADE_MS;

export function createCatBubbleReaction(message, now = Date.now()) {
  return {
    message,
    expiresAt: now + CAT_BUBBLE_TOTAL_MS,
  };
}

export function resolveCatBubbleTiming(reaction, now = Date.now()) {
  const remainingMs = Math.max(Number(reaction?.expiresAt || 0) - now, 0);
  const fadeDuration = Math.min(CAT_BUBBLE_FADE_MS, remainingMs);
  return {
    active: remainingMs > 0,
    remainingMs,
    holdDelay: Math.max(remainingMs - fadeDuration, 0),
    fadeDuration,
    initialAlpha: remainingMs < CAT_BUBBLE_FADE_MS
      ? Math.max(remainingMs / CAT_BUBBLE_FADE_MS, 0.08)
      : 1,
  };
}
