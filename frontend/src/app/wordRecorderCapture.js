export function canRecordAudio() {
  return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
}

export async function createWordRecorderCapture({ onReady }) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const chunks = [];
  const recorder = new MediaRecorder(stream);

  recorder.addEventListener("dataavailable", (event) => {
    if (event.data?.size) chunks.push(event.data);
  });
  recorder.addEventListener("stop", () => {
    const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
    onReady({
      blob,
      preview: URL.createObjectURL(blob),
    });
    stream.getTracks().forEach((track) => track.stop());
  });

  return recorder;
}
