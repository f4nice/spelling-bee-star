export function challengeDayWordUrl(item, day = "") {
  const params = new URLSearchParams({ edit: "1" });
  if (item.word_list_id) params.set("list_id", item.word_list_id);
  if (day) params.set("challenge_day", day);
  if (item.status) params.set("challenge_status", item.status);
  return `/words/${item.id}?${params.toString()}`;
}
