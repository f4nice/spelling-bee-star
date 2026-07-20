export function challengeDayWordUrl(item, day = "") {
  const params = new URLSearchParams({ edit: "1" });
  if (item.word_list_id) params.set("list_id", item.word_list_id);
  if (day) {
    params.set("challenge_day", day);
    const returnTo = item.word_list_id ? `/challenge-calendar/${day}?list_id=${item.word_list_id}` : `/challenge-calendar/${day}`;
    params.set("return_to", returnTo);
    params.set("return_label", `${day} 挑战词汇`);
  }
  if (item.status) params.set("challenge_status", item.status);
  return `/words/${item.id}?${params.toString()}`;
}
