export function challengeDayWordUrl(item) {
  const query = item.word_list_id ? `?edit=1&list_id=${item.word_list_id}` : "?edit=1";
  return `/words/${item.id}${query}`;
}
