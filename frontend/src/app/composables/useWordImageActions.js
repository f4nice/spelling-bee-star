import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { createWordAiImageForm, createWordImageUploadForm, createWordNetworkImageForm } from "../wordImageForms.js";

export function useWordImageActions({ data, loadRoute }) {
  async function uploadWordImage(file) {
    const form = createWordImageUploadForm(file);
    const result = await fetchJson(wordApiPaths.image(data.value.word.id), { method: "POST", body: form });
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.image_url) data.value.word.image_url = result.image_url;
    if (!result?.media_sources) await loadRoute();
    return result;
  }

  async function chooseNetworkImage(url) {
    const form = createWordNetworkImageForm(url);
    const result = await fetchJson(wordApiPaths.networkImage(data.value.word.id), { method: "POST", body: form });
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.image_url) data.value.word.image_url = result.image_url;
    if (!result?.media_sources) await loadRoute();
    return result;
  }

  async function generateAiImage(option, controls = {}) {
    const form = createWordAiImageForm(option, controls);
    const result = await fetchJson(wordApiPaths.aiImage(data.value.word.id), { method: "POST", body: form });
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.committed && result?.image_url) data.value.word.image_url = result.image_url;
    return result;
  }

  return {
    uploadWordImage,
    chooseNetworkImage,
    generateAiImage,
  };
}
