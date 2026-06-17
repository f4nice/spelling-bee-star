import { fetchJson } from "../utils.js";

export function useWordImageActions({ data, loadRoute }) {
  async function uploadWordImage(file) {
    const form = new FormData();
    form.append("edit_token", "1");
    form.append("file", file);
    await fetchJson(`/api/vue/words/${data.value.word.id}/image`, { method: "POST", body: form });
    await loadRoute();
  }

  async function chooseNetworkImage(url) {
    const form = new FormData();
    form.append("edit_token", "1");
    form.append("image_url", url);
    await fetchJson(`/api/vue/words/${data.value.word.id}/network-image`, { method: "POST", body: form });
    await loadRoute();
  }

  return {
    uploadWordImage,
    chooseNetworkImage,
  };
}
