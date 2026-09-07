"""Low-concurrency, process-local jobs for filling gaps in a word list."""

import asyncio
from collections import deque
from copy import deepcopy
from threading import Lock, Thread
from uuid import uuid4

from sqlalchemy import event, select

from app.models import Word, WordListItem


TEXT_FIELDS = (
    "phonetic", "part_of_speech", "english_definition", "chinese_definition", "english_example",
)
ACTIVE_STATUSES = frozenset({"queued", "running", "stopping"})
MEDIA_FIELDS = (
    "american_audio_url", "british_audio_url", "english_definition_audio_url",
    "english_example_audio_url", "image_url",
)


def incomplete_reason(word, fields):
    """User-facing reasons, never raw upstream errors or credential-bearing URLs."""
    labels = dict(zip(TEXT_FIELDS, ("音标", "词性", "英文释义", "中文释义", "英文例句")))
    locked = [field for field in fields if getattr(word, field + "_locked", False)]
    reasons = []
    if locked:
        reasons.append("手动锁定：" + "、".join(labels[field] for field in locked))
    missing = set(fields) - set(locked)
    error = word.enrichment_error or ""
    if "历史释义疑似百科内容" in error:
        return "历史释义疑似百科内容，请先核对词性和英文释义，再补全缺项。已获取的内容已保存。"
    if "phonetic" in missing:
        reasons.append("词典未返回完整音标")
    if "part_of_speech" in missing:
        reasons.append("词典未返回词性")
    if "english_definition" in missing:
        reasons.append("词典未返回匹配的英文释义")
    if "chinese_definition" in missing:
        reasons.append("中文翻译服务暂不可用或限流" if "翻译" in error else "未取得匹配当前词义的中文释义")
    if "english_example" in missing:
        reasons.append("未查到同义项例句，自编服务暂未补上" if word.english_definition else "缺少可信英文释义，未自编例句")
    return "；".join(reasons) + "。已获取的内容已保存。"


def has_text(value):
    return isinstance(value, str) and bool(value.strip())


def missing_text_fields(word):
    """Match the list UI, including empty fields that are deliberately locked."""
    return [field for field in TEXT_FIELDS if not has_text(getattr(word, field, None))]


def protected_word_values(word):
    """Batch completion never replaces existing text/media or explicit locks."""
    values = {}
    for field in TEXT_FIELDS + MEDIA_FIELDS:
        lock_field = field.removesuffix("_url") + "_locked"
        locked = bool(getattr(word, lock_field, False))
        if has_text(getattr(word, field, None)) or locked or field == "image_url":
            values[field] = getattr(word, field, None)
            if hasattr(word, lock_field):
                values[lock_field] = getattr(word, lock_field)
    # Existing text and its audio must remain a matching pair. Do not attach a
    # different SPB sense's audio to retained definitions/examples.
    for field in ("english_definition", "english_example"):
        if field in values:
            values[field + "_audio_url"] = getattr(word, field + "_audio_url", None)
    return values


def restore_word_values(word, values):
    for field, value in values.items():
        setattr(word, field, value)


class PreserveWordValues:
    """Guard internal commits and merge edits made while a provider is awaited.

    The row is re-read with a locking Core query immediately before every flush,
    outside the ORM identity map. This is a current read on MySQL as well as an
    atomic read/merge/write, so a long upstream request cannot undo manual edits.
    """

    def __init__(self, db, word):
        self.db = db
        self.word = word
        self.values = protected_word_values(word)
        self.fields = list(TEXT_FIELDS + MEDIA_FIELDS)
        self.fields += [
            field.removesuffix("_url") + "_locked" for field in TEXT_FIELDS + MEDIA_FIELDS
            if hasattr(word, field.removesuffix("_url") + "_locked")
        ]
        self.baseline = {field: getattr(word, field, None) for field in self.fields}
        table = Word.__table__
        self.current_row = select(*(table.c[field] for field in self.fields)).where(table.c.id == word.id)

    def restore(self, *_):
        restore_word_values(self.word, self.values)

    def _before_flush(self, session, *_):
        fresh = session.connection().execute(self.current_row.with_for_update()).mappings().first()
        if fresh is None:
            raise RuntimeError("Word no longer exists")
        # Dependent text generated during an await belongs to the old sense.
        # If the user changes that sense meanwhile, keep only their fresh values.
        dependencies = set()
        if fresh["english_definition"] != self.baseline["english_definition"]:
            dependencies.update(("chinese_definition", "english_example"))
        if fresh["part_of_speech"] != self.baseline["part_of_speech"]:
            dependencies.update(("english_definition", "chinese_definition", "english_example"))
        for field in dependencies:
            if not has_text(self.baseline[field]):
                self.values[field] = fresh[field]
                if field in ("english_definition", "english_example"):
                    self.values[field + "_audio_url"] = fresh[field + "_audio_url"]
                lock_field = field + "_locked"
                if lock_field in self.baseline:
                    self.values[lock_field] = fresh[lock_field]
        for field in TEXT_FIELDS + MEDIA_FIELDS:
            lock_field = field.removesuffix("_url") + "_locked"
            changed = fresh[field] != self.baseline[field]
            if lock_field in self.baseline:
                changed = changed or fresh[lock_field] != self.baseline[lock_field]
            if not changed:
                continue
            # Even an externally cleared/unlocked field belongs to that edit;
            # do not fill or relock it from this older provider response.
            self.values[field] = fresh[field]
            if lock_field in self.baseline:
                self.values[lock_field] = fresh[lock_field]
            if field in ("english_definition", "english_example"):
                self.values[field + "_audio_url"] = fresh[field + "_audio_url"]
        self.restore()

    def _after_flush(self, session, *_):
        # Advance only after our own write, not an ordinary refresh: a provider
        # may refresh the ORM object before another protective flush occurs.
        fresh = session.connection().execute(self.current_row).mappings().first()
        if fresh is not None:
            self.baseline = dict(fresh)

    def __enter__(self):
        event.listen(self.db, "before_flush", self._before_flush)
        event.listen(self.db, "after_flush_postexec", self._after_flush)
        return self

    def __exit__(self, *_):
        event.remove(self.db, "before_flush", self._before_flush)
        event.remove(self.db, "after_flush_postexec", self._after_flush)
        self.restore()


class ListCompletionJobs:
    """One worker for all lists; each word has its own short-lived DB session.

    Jobs survive page reloads, not application restarts. No database schema or
    external queue is required. A restart leaves already committed words intact.
    """

    def __init__(self, session_factory, complete_word, *, word_timeout=120, thread_factory=Thread):
        self.session_factory = session_factory
        self.complete_word = complete_word
        self.word_timeout = word_timeout
        self.thread_factory = thread_factory
        self.lock = Lock()
        self.jobs = {}
        self.latest = {}
        self.queue = deque()
        self.worker_running = False

    def current(self, word_list_id):
        with self.lock:
            return deepcopy(self.jobs.get(self.latest.get(word_list_id)))

    def start(self, word_list_id, word_ids):
        with self.lock:
            previous = self.jobs.get(self.latest.get(word_list_id))
            if previous and previous["status"] in ACTIVE_STATUSES:
                return deepcopy(previous)
            # Keep a bounded amount of completed job history in memory.
            terminal_ids = [key for key, job in self.jobs.items() if job["status"] not in ACTIVE_STATUSES]
            for key in terminal_ids[:-99]:
                old = self.jobs.pop(key)
                if self.latest.get(old["word_list_id"]) == key:
                    self.latest.pop(old["word_list_id"], None)
            ids = list(dict.fromkeys(word_ids))
            job = {
                "id": uuid4().hex, "word_list_id": word_list_id,
                "status": "queued" if ids else "complete", "total": len(ids), "done": 0,
                "completed": 0, "partial": 0, "failed": 0, "skipped": 0,
                "current_word": "", "message": "已排队，等待批量补全。" if ids else "当前单词表没有未补全的单词。",
                "results": [],
            }
            self.jobs[job["id"]] = job
            self.latest[word_list_id] = job["id"]
            if ids:
                self.queue.append((job["id"], ids))
                if not self.worker_running:
                    self.worker_running = True
                    try:
                        self.thread_factory(target=self._work, daemon=True).start()
                    except Exception:
                        self.worker_running = False
                        job["status"] = "failed"
                        job["message"] = "补全任务暂时无法启动，请稍后重试。"
            return deepcopy(job)

    def stop(self, word_list_id, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job["word_list_id"] != word_list_id:
                return None
            if job["status"] == "queued":
                job.update(status="stopped", message="已停止排队，未开始处理。")
            elif job["status"] == "running":
                job.update(status="stopping", message="正在停止，将在当前单词处理完后结束。")
            return deepcopy(job)

    def _work(self):
        while True:
            with self.lock:
                if not self.queue:
                    self.worker_running = False
                    return
                job_id, ids = self.queue.popleft()
                job = self.jobs.get(job_id)
                if not job or job["status"] != "queued":
                    continue
                job.update(status="running", message="正在补全单词…")
            try:
                # One event loop per list avoids creating one executor per word.
                asyncio.run(self._run(job_id, ids))
            except Exception:
                with self.lock:
                    self.jobs[job_id].update(status="failed", current_word="", message="任务异常结束，已保存完成的单词，可重试剩余缺项。")

    async def _run(self, job_id, word_ids):
        for word_id in word_ids:
            with self.lock:
                job = self.jobs[job_id]
                if job["status"] == "stopping":
                    break
                list_id = job["word_list_id"]
            result = await self._process_word(job_id, list_id, word_id)
            with self.lock:
                job = self.jobs[job_id]
                job["results"].append(result)
                job["done"] += 1
                job[result["status"]] += 1
                if job["status"] != "stopping":
                    job["message"] = f"已处理 {job['done']} / {job['total']} 个单词。"
        with self.lock:
            job = self.jobs[job_id]
            stopped = job["status"] == "stopping"
            job.update(status="stopped" if stopped else "complete", current_word="",
                       message="已停止，已补全的内容已保存，可继续处理剩余缺项。" if stopped else "批量补全结束，已保存结果；仍有缺项的单词可再次尝试。")

    async def _process_word(self, job_id, list_id, word_id):
        result = {"word_id": word_id, "word": "", "status": "failed", "missing_fields": [], "message": ""}
        db = None
        interrupted = False
        try:
            db = self.session_factory()
            word = db.scalar(select(Word).join(WordListItem, WordListItem.word_id == Word.id).where(
                Word.id == word_id, WordListItem.word_list_id == list_id,
            ))
            if not word:
                result.update(status="skipped", message="单词已移出此表，已跳过。")
                return result
            result["word"] = word.word
            missing = missing_text_fields(word)
            result["missing_fields"] = missing
            with self.lock:
                self.jobs[job_id]["current_word"] = word.word
            if not missing:
                result.update(status="skipped", message="文字内容已经完整，已跳过。")
                return result
            if all(getattr(word, field + "_locked", False) for field in missing):
                result.update(status="skipped", message="剩余缺项已锁定，保留手动设置。")
                return result
            await asyncio.wait_for(self.complete_word(db, word, list_id=list_id), timeout=self.word_timeout)
            remaining = missing_text_fields(word)
            status = "completed" if not remaining else (
                "failed" if word.enrichment_status == "failed" and len(remaining) >= len(missing) else "partial"
            )
            result.update(status=status, missing_fields=remaining,
                          message="文字内容已补全。" if not remaining else incomplete_reason(word, remaining))
        except asyncio.TimeoutError:
            interrupted = True
            self._rollback(db)
            result["message"] = "查询超时，已跳过并继续下一个单词，可稍后重试。"
        except Exception:
            interrupted = True
            self._rollback(db)
            # Never return upstream exception text: it may contain credentials.
            result["message"] = "本次查询失败，已跳过并继续下一个单词，可稍后重试。"
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    # A broken connection must not poison the next word's
                    # independent session or abort the entire list.
                    pass
        if interrupted and result["word"]:
            # SPB can commit useful text before an optional later provider times
            # out. Report what is actually saved, not the pre-request snapshot.
            try:
                with self.session_factory() as reader:
                    saved = reader.get(Word, word_id)
                    if saved is not None:
                        remaining = missing_text_fields(saved)
                        if not remaining:
                            result.update(status="completed", message="文字内容已补全并保存；其他资源查询未完成。")
                        elif len(remaining) < len(result["missing_fields"]):
                            result.update(status="partial", message="已保存部分文字内容，其余缺项可稍后重试。")
                        result["missing_fields"] = remaining
            except Exception:
                pass
        return result

    @staticmethod
    def _rollback(db):
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
