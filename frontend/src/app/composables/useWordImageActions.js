import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { createWordImageUploadForm, createWordNetworkImageForm } from "../wordImageForms.js";

export function useWordImageActions({ data, loadRoute }) {
  async function uploadWordImage(file) {
    const form = createWordImageUploadForm(file);
    await fetchJson(wordApiPaths.image(data.value.word.id), { method: "POST", body: form });
    await loadRoute();
  }

  async function chooseNetworkImage(url) {
    const form = createWordNetworkImageForm(url);
    await fetchJson(wordApiPaths.networkImage(data.value.word.id), { method: "POST", body: form });
    await loadRoute();
  }

  return {
    uploadWordImage,
    chooseNetworkImage,
  };
}
