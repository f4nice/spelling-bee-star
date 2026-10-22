import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";
import { createWordAiImageForm, createWordImageUploadForm, createWordNetworkImageForm } from "../wordImageForms.js";
import { prepareImageUpload } from "../imageUpload.js";

export function useWordImageActions({ data, loadRoute }, { request = fetchJson, prepareUpload = prepareImageUpload } = {}) {
  async function uploadWordImage(file) {
    const wordId = data.value.word.id;
    const form = createWordImageUploadForm(await prepareUpload(file));
    const result = await request(wordApiPaths.image(wordId), { method: "POST", body: form });
    if (data.value?.word?.id !== wordId) return result;
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.image_url) data.value.word.image_url = result.image_url;
    if (!result?.media_sources) await loadRoute();
    return result;
  }

  async function chooseNetworkImage(url) {
    const wordId = data.value.word.id;
    const form = createWordNetworkImageForm(url);
    const result = await request(wordApiPaths.networkImage(wordId), { method: "POST", body: form });
    if (data.value?.word?.id !== wordId) return result;
    if (result?.media_sources) data.value.media_sources = result.media_sources;
    if (result?.image_url) data.value.word.image_url = result.image_url;
    if (!result?.media_sources) await loadRoute();
    return result;
  }

  async function generateAiImage(option, controls = {}) {
    const wordId = data.value.word.id;
    const form = createWordAiImageForm(option, controls);
    const result = await request(wordApiPaths.aiImage(wordId), { method: "POST", body: form });
    if (data.value?.word?.id !== wordId) return result;
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
