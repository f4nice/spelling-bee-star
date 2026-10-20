const MAX_UPLOAD_BYTES = 900 * 1024;
const MAX_UPLOAD_DIMENSION = 1600;

function canvasBlob(canvas, quality) {
  return new Promise((resolve) => {
    canvas.toBlob(resolve, "image/webp", quality);
  });
}

/**
 * Keep browser uploads below the small reverse-proxy request limit while
 * preserving the aspect ratio. The server performs a second, smaller
 * normalization before saving the image.
 */
export async function prepareImageUpload(file) {
  if (!file || file.size <= MAX_UPLOAD_BYTES || !String(file.type || "").startsWith("image/")) {
    return file;
  }
  if (typeof document === "undefined" || typeof createImageBitmap !== "function") {
    return file;
  }

  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_UPLOAD_DIMENSION / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

    let blob = null;
    for (const quality of [0.82, 0.7, 0.58, 0.46]) {
      const candidate = await canvasBlob(canvas, quality);
      if (candidate && (!blob || candidate.size < blob.size)) blob = candidate;
      if (candidate && candidate.size <= MAX_UPLOAD_BYTES) break;
    }
    if (!blob || blob.size >= file.size) return file;
    const stem = String(file.name || "image").replace(/\.[^.]+$/, "") || "image";
    return new File([blob], `${stem}.webp`, {
      type: "image/webp",
      lastModified: file.lastModified || Date.now(),
    });
  } catch {
    return file;
  } finally {
    bitmap?.close?.();
  }
}

export function splitImageFiles(files, maxBytes = 700 * 1024) {
  const batches = [];
  let batch = [];
  let bytes = 0;
  for (const file of files || []) {
    const size = Math.max(Number(file?.size) || 0, 1);
    if (batch.length && bytes + size > maxBytes) {
      batches.push(batch);
      batch = [];
      bytes = 0;
    }
    batch.push(file);
    bytes += size;
  }
  if (batch.length) batches.push(batch);
  return batches;
}
