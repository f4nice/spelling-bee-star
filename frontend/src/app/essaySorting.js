function essayCreatedAtValue(essay) {
  const timestamp = Date.parse(String(essay?.createdAt || ""));
  return Number.isFinite(timestamp) ? timestamp : 0;
}

export function sortEssaysNewestFirst(essays) {
  return [...(Array.isArray(essays) ? essays : [])].sort(
    (left, right) =>
      essayCreatedAtValue(right) - essayCreatedAtValue(left)
      || Number(right?.id || 0) - Number(left?.id || 0),
  );
}
