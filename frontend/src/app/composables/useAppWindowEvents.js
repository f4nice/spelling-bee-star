import { onMounted, onUnmounted } from "vue";

export function useAppWindowEvents({ onPopState, onKeydown, loadRoute }) {
  onMounted(() => {
    window.addEventListener("popstate", onPopState);
    window.addEventListener("keydown", onKeydown);
    loadRoute();
  });

  onUnmounted(() => {
    window.removeEventListener("popstate", onPopState);
    window.removeEventListener("keydown", onKeydown);
  });
}
