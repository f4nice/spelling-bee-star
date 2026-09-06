"""Bounded page-read work; learning mutations stay in the existing handlers."""

from copy import deepcopy
from datetime import date
from threading import RLock
from time import monotonic

from sqlalchemy import and_, case, func, or_, select
from starlette.middleware.gzip import GZipMiddleware

from app.models import (
    ChallengeDailyWord, ChallengeProgress, ChallengeSpellingAttempt,
    Word, WordList, WordListItem, WrongWord,
)


class PublicStatsCache:
    """Cache only serialized, account-independent statistics, never ORM/users."""

    def __init__(self, ttl=10):
        self.ttl = ttl
        self._values = {}
        self._lock = RLock()

    def get(self, key, producer):
        with self._lock:
            entry = self._values.get(key)
            if entry and entry[0] > monotonic():
                return deepcopy(entry[1])
            value = producer()
            if len(self._values) >= 16:
                self._values.clear()
            self._values[key] = (monotonic() + self.ttl, deepcopy(value))
            return value

    def clear(self):
        with self._lock:
            self._values.clear()


public_stats_cache = PublicStatsCache()


class TextAssetGZipMiddleware:
    """Compress text assets/API data, not audio, range downloads or auth HTML."""

    def __init__(self, app):
        self.app = app
        self.compressed = GZipMiddleware(app, minimum_size=1000, compresslevel=5)

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        headers = dict(scope.get("headers", []))
        eligible = (
            scope["type"] == "http"
            and b"range" not in headers
            and (
                path.startswith("/static/") and path.endswith((".js", ".css", ".svg", ".json"))
                or path.startswith("/api/vue/") and scope.get("method") == "GET"
            )
        )
        await (self.compressed if eligible else self.app)(scope, receive, send)


def list_counts_and_covers(db, list_ids):
    if not list_ids:
        return {}, {}
    rows = db.execute(
        select(
            WordListItem.word_list_id,
            func.count(WordListItem.id),
            func.coalesce(
                func.max(case((and_(Word.image_url.is_not(None), Word.image_url != ""), Word.id))),
                func.max(Word.id),
            ),
        )
        .join(Word, Word.id == WordListItem.word_id)
        .where(WordListItem.word_list_id.in_(list_ids))
        .group_by(WordListItem.word_list_id)
    ).all()
    return ({row[0]: int(row[1]) for row in rows}, {row[0]: row[2] for row in rows})


def batch_challenge_states(db, word_lists, fallback, counts=None):
    list_ids = [word_list.id for word_list in word_lists]
    if not list_ids:
        return {}
    if counts is None:
        counts = dict(db.execute(
            select(WordListItem.word_list_id, func.count(WordListItem.id))
            .where(WordListItem.word_list_id.in_(list_ids))
            .group_by(WordListItem.word_list_id)
        ).all())
    # Scalar snapshots survive a rare legacy progress rollover committing below.
    progress = {
        row.word_list_id: (int(row.completed_count or 0), int(row.completed_rounds or 0))
        for row in db.execute(
            select(ChallengeProgress.word_list_id, ChallengeProgress.completed_count, ChallengeProgress.completed_rounds)
            .where(ChallengeProgress.word_list_id.in_(list_ids))
        )
    }
    history_ids = [key for key in list_ids if counts.get(key) and not progress.get(key, (0, 0))[1]]
    historical = {}
    if history_ids:
        for model in (ChallengeDailyWord, ChallengeSpellingAttempt):
            rows = db.execute(
                select(WordListItem.word_list_id, func.count(func.distinct(model.word_id)))
                .join(model, and_(
                    model.word_id == WordListItem.word_id,
                    or_(model.word_list_id == WordListItem.word_list_id, model.word_list_id.is_(None)),
                ))
                .where(WordListItem.word_list_id.in_(history_ids))
                .group_by(WordListItem.word_list_id)
            ).all()
            for list_id, count in rows:
                historical[list_id] = max(historical.get(list_id, 0), int(count))
    states = {}
    for word_list in word_lists:
        list_id = word_list.id
        total = int(counts.get(list_id, 0))
        done, rounds = progress.get(list_id, (0, 0))
        completed = min(max(done, historical.get(list_id, 0)), total)
        if total and (list_id not in progress or completed >= total):
            # Preserve creation/round advancement exactly, without duplicating it.
            states[list_id] = fallback(db, word_list)
        else:
            states[list_id] = {
                "completed": completed, "total": total,
                "percent": round(completed / total * 100) if total else 0,
                "is_complete": False, "completed_rounds": rounds if total else 0,
            }
    return states


def batch_word_list_cards(db, word_lists, fallback):
    counts, cover_ids = list_counts_and_covers(db, [item.id for item in word_lists])
    states = batch_challenge_states(db, word_lists, fallback, counts)
    ids = set(cover_ids.values()) - {None}
    covers = {word.id: word for word in db.scalars(select(Word).where(Word.id.in_(ids))).all()} if ids else {}
    return [
        {"list": item, "count": counts.get(item.id, 0),
         "cover_word": covers.get(cover_ids.get(item.id)), "challenge": states[item.id]}
        for item in word_lists
    ]


def batch_pending_wrong_word_count(db, parse_list_date):
    wrong = set(db.execute(select(WrongWord.wrong_date, WrongWord.word_id)).all())
    wrong.update(db.execute(
        select(ChallengeDailyWord.challenge_date, ChallengeDailyWord.word_id)
        .where(ChallengeDailyWord.wrong_count > 0)
    ).all())
    seen_lists = {}
    for list_id, name, word_id in db.execute(
        select(WordList.id, WordList.name, WordListItem.word_id)
        .outerjoin(WordListItem, WordListItem.word_list_id == WordList.id)
        .where(WordList.name.like("生词本 %")).order_by(WordList.id)
    ):
        day = parse_list_date(name)
        if not day or name != f"生词本 {day.isoformat()}":
            continue
        # Match get_wrong_word_list's first list if a legacy duplicate exists.
        if seen_lists.setdefault(day, list_id) == list_id and word_id is not None:
            wrong.add((day, word_id))
    corrected = dict(db.execute(
        select(ChallengeDailyWord.word_id, func.max(ChallengeDailyWord.challenge_date))
        .where(ChallengeDailyWord.correct_count > 0).group_by(ChallengeDailyWord.word_id)
    ).all())
    return sum(1 for day, word_id in wrong if day and corrected.get(word_id, date.min) < day)
