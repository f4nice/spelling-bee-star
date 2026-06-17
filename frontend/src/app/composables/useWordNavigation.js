import { wordDetailEditUrl } from "../appRouteUrls.js";

export function useWordNavigation({ data }) {
  function wordNavUrl(wordId) {
    return wordDetailEditUrl(wordId);
  }

  function handleWordKeydown(event, route) {
    if (route.name !== 'wordDetail' || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    const active = document.activeElement;
    if (active?.matches('input, textarea, select, button, audio') || active?.isContentEditable) return;
    const nav = data.value?.navigation;
    if (!nav) return;
    window.location.href = wordNavUrl(event.key === 'ArrowLeft' ? nav.previous_word_id : nav.next_word_id);
  }

  return {
    wordNavUrl,
    handleWordKeydown,
  };
}
