import { syncWordListImages } from "./listDetailActions.js";

export async function syncListImagesForDetail({ data, loadRoute }) {
  await syncWordListImages({
    wordListId: data.value.word_list.id,
    setJob: (job) => {
      data.value.sync_job = job;
    },
    onComplete: loadRoute,
  });
}
