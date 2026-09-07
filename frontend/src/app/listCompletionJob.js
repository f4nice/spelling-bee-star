import { fetchJson } from "./utils.js";

export const COMPLETION_ACTIVE_STATUSES = new Set(["queued", "running", "stopping"]);

// A controller belongs to one mounted list. Generation checks discard late
// responses when the user navigates away or switches to a different list.
export function createListCompletionController({
  request = fetchJson,
  schedule = (fn, delay) => setTimeout(fn, delay),
  unschedule = (timer) => clearTimeout(timer),
  onState,
  onRefresh = async () => {},
}) {
  let generation = 0;
  let listId = null;
  let timer = null;
  let job = null;
  let busy = false;
  let failures = 0;
  let lastRefreshDone = -1;
  let lastRefreshAt = 0;
  let pendingRefresh = false;

  function emit(notice = "", loading = busy) {
    onState({ job, busy: loading, notice });
  }

  function clearTimer() {
    if (timer != null) unschedule(timer);
    timer = null;
  }

  function path() {
    return `/api/vue/lists/${listId}/completion`;
  }

  async function accept(next, epoch) {
    if (epoch !== generation) return;
    const previous = job;
    job = next;
    failures = 0;
    emit(previous && !next ? "服务已重启，任务记录已失效；已保存的内容不受影响，可重新补全剩余词。" : "");
    const active = COMPLETION_ACTIVE_STATUSES.has(next?.status);
    const becameTerminal = previous && COMPLETION_ACTIVE_STATUSES.has(previous.status) && !active;
    const changed = next && Number(next.done) !== lastRefreshDone;
    let refreshFailed = false;
    if (pendingRefresh || becameTerminal || (changed && (!active || Date.now() - lastRefreshAt >= 8000)) || (previous && !next)) {
      pendingRefresh = false;
      lastRefreshDone = Number(next?.done ?? -1);
      lastRefreshAt = Date.now();
      try {
        await onRefresh(listId);
      } catch {
        if (epoch !== generation) return;
        emit("进度已更新，词表暂时刷新失败；稍后会重试。");
        lastRefreshDone = -1;
        pendingRefresh = true;
        refreshFailed = true;
      }
    }
    if (epoch === generation && (active || refreshFailed)) queuePoll(epoch, refreshFailed ? 10000 : 2200);
  }

  function queuePoll(epoch, delay = 2200) {
    clearTimer();
    timer = schedule(() => read(epoch), delay);
  }

  async function read(epoch) {
    try {
      const next = await request(path(), { skipCache: true });
      if (epoch !== generation) return;
      busy = false;
      await accept(next, epoch);
    } catch (error) {
      if (epoch !== generation) return;
      busy = false;
      failures += 1;
      emit(error.status === 401 ? "登录已失效，请重新登录后查看进度。" : "暂时无法读取补全进度，正在重连；不会重复创建任务。");
      if (error.status !== 401 && error.status !== 404) queuePoll(epoch, Math.min(30000, failures * 3000));
    }
  }

  function setList(id) {
    generation += 1;
    clearTimer();
    listId = id;
    job = null;
    failures = 0;
    lastRefreshDone = -1;
    lastRefreshAt = 0;
    pendingRefresh = false;
    busy = Boolean(id);
    emit();
    if (id) void read(generation);
  }

  async function mutate(suffix) {
    if (!listId || busy) return;
    // A GET already in flight must not overwrite a newer stop/start response.
    const epoch = ++generation;
    busy = true;
    clearTimer();
    emit();
    const form = new FormData();
    form.append("edit_token", "1");
    try {
      const next = await request(`${path()}/${suffix}`, { method: "POST", body: form, skipCache: true });
      if (epoch !== generation) return;
      busy = false;
      await accept(next, epoch);
    } catch (error) {
      if (epoch !== generation) return;
      busy = false;
      emit(error.message || "操作未成功，请稍后重试。");
      // An ambiguous response may still have started/stopped the job. GET is
      // safe; never repeat a POST automatically.
      if (error.status !== 401) queuePoll(epoch);
    }
  }

  return {
    setList,
    start: () => COMPLETION_ACTIVE_STATUSES.has(job?.status) ? Promise.resolve() : mutate("start"),
    stop: () => job && COMPLETION_ACTIVE_STATUSES.has(job.status) ? mutate(`${job.id}/stop`) : Promise.resolve(),
    dispose() { generation += 1; clearTimer(); listId = null; },
  };
}
