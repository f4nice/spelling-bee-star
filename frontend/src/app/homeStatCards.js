export function buildHomeStatCards(stats) {
  return [
    {
      label: "我的单词表",
      value: stats.word_lists,
      detail: `${stats.words} 个单词`,
      path: "/lists",
    },
    {
      label: "英文小报",
      value: "Today",
      detail: "China Daily 今日泛读",
      path: "/newspaper",
    },
    {
      label: "好词好句",
      value: "Books",
      detail: "书摘与难点词",
      path: "/booklearner",
    },
    {
      label: "我的生词本",
      value: stats.wrong_words,
      detail: `今日 ${stats.today_wrong_count} 个`,
      path: "/wrong-words",
    },
  ];
}
