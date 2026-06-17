import { ref } from "vue";

export function useLoadingAction(action) {
  const loading = ref(false);

  async function run(...args) {
    if (loading.value) return;
    loading.value = true;
    try {
      await action(...args);
    } finally {
      loading.value = false;
    }
  }

  return {
    loading,
    run,
  };
}
