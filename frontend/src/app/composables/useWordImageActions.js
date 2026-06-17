import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";

export function useWordImageActions({ data, loadRoute }) {
  async function uploadWordImage(file) {
    const form = new FormData();
    form.append("edit_token", "1");
    form.append("file", file);
    await fetchJson(wordApiPaths.image(data.value.word.id), { method: "POST", body: form });
    await loadRoute();
  }

  async function chooseNetworkImage(url) {
    const form = new FormData();
    form.append("edit_token", "1");
    form.append("image_url", url);
    await fetchJson(wordApiPaths.networkImage(data.value.word.id), { method: "POST", body: form });
    await loadRoute();
  }

  return {
    uploadWordImage,
    chooseNetworkImage,
  };
}
