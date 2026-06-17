import { computed } from "vue";
import {
  buildBooklearnerContext,
  buildImportPreviewContext,
  buildListToolsContext,
  buildWordDetailContext,
} from "./pageContextBuilders.js";
import { articleText, fallbackLetter, imageForWord, wordDetailUrl } from "./utils.js";

export function usePageContext({
  route,
  data,
  go,
  importPreview,
  wordDetail,
  booklearner,
  listTools,
}) {
  return computed(() => ({
    route: route.value,
    data: data.value,
    go,
    fallbackLetter,
    imageForWord,
    wordDetailUrl,
    articleText,
    ...buildImportPreviewContext(importPreview),
    ...buildWordDetailContext(wordDetail),
    ...buildBooklearnerContext(booklearner),
    ...buildListToolsContext(listTools),
  }));
}
