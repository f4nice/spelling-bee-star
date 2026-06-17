export const routeApiPaths = {
  home: () => "/api/vue/home",
  lists: () => "/api/vue/lists",
  listDetail: (route) => `/api/vue/lists/${route.params.id}`,
  wrongWords: () => "/api/vue/wrong-words",
  challengeDay: (route) => `/api/vue/challenge-calendar/${route.params.day}`,
  wordDetail: (route) => `/api/vue/words/${route.params.id}${window.location.search}`,
  preview: (route) => `/api/vue/upload/preview/${route.params.id}${window.location.search}`,
  newspaper: () => "/api/vue/newspaper",
  newspaperArticle: (route) => `/api/vue/newspaper/${route.params.section}/${route.params.index}`,
};
