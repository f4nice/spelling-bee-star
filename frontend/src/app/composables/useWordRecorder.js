import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { wordRecorderMessages } from "../wordRecorderMessages.js";

export function useWordRecorder({ data, loadRoute }) {
  const recorderState = ref({ accent: "", status: "", blob: null, preview: "" });
  let mediaRecorder = null;
  let mediaStream = null;
  let mediaChunks = [];

  async function startRecording(accent) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      recorderState.value = {
        accent,
        status: wordRecorderMessages.unsupported,
        blob: null,
        preview: "",
      };
      return;
    }

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaChunks = [];
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) mediaChunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", () => {
      const blob = new Blob(mediaChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      recorderState.value = {
        accent,
        status: wordRecorderMessages.ready,
        blob,
        preview: URL.createObjectURL(blob),
      };
      mediaStream?.getTracks().forEach((track) => track.stop());
    });
    recorderState.value = { accent, status: wordRecorderMessages.recording, blob: null, preview: "" };
    mediaRecorder.start();
  }

  function stopRecording() {
    if (mediaRecorder?.state === "recording") mediaRecorder.stop();
  }

  async function saveRecording() {
    if (!recorderState.value.blob) return;
    const form = new FormData();
    form.append("edit_token", "1");
    form.append("accent", recorderState.value.accent);
    form.append("audio_file", recorderState.value.blob, `recorded-${recorderState.value.accent}.webm`);
    await fetchJson(`/api/vue/words/${data.value.word.id}/recorded-audio`, { method: "POST", body: form });
    recorderState.value = { accent: "", status: wordRecorderMessages.saved, blob: null, preview: "" };
    await loadRoute();
  }

  return {
    recorderState,
    startRecording,
    stopRecording,
    saveRecording,
  };
}
