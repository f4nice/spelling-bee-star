"""Daily, server-timed multiplication practice with atomic one-time rewards.

Importing this module registers its additive table on the application's Base.
Every public operation owns its transaction; callers must not have unrelated
uncommitted writes. Answers and future question operands stay server-side.
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base
from app.models import CatWorldEnergyGrant


BEIJING = timezone(timedelta(hours=8))
QUESTION_COUNT = 5
LIMIT_SECONDS = 600
REWARD_PER_QUESTION = 100
FUN_MATH_GRANT_SOURCE = "fun-math"
MAX_CONFLICT_RETRIES = 8
SETTLED_STATUSES = frozenset({"correct", "incorrect", "expired"})


class MathDailySession(Base):
    __tablename__ = "fun_math_daily_sessions"
    __table_args__ = (UniqueConstraint("phone", "practice_date", name="uq_fun_math_phone_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    practice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    questions_json: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


def _utc(now: datetime | None) -> datetime:
    instant = now or datetime.now(timezone.utc)
    # Existing application services use naive UTC datetimes.
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _next_midnight(day: date) -> datetime:
    return datetime.combine(day + timedelta(days=1), time.min, BEIJING).astimezone(timezone.utc)


def _new_questions() -> list[dict[str, Any]]:
    pairs: set[tuple[int, int]] = set()
    questions = []
    while len(questions) < QUESTION_COUNT:
        left, right = secrets.randbelow(900) + 100, secrets.randbelow(900) + 100
        pair = tuple(sorted((left, right)))
        if pair in pairs:
            continue
        pairs.add(pair)
        questions.append({"id": len(questions) + 1, "left": left, "right": right, "status": "pending"})
    return questions


def _encode(questions: list[dict[str, Any]]) -> str:
    return json.dumps(questions, ensure_ascii=False, separators=(",", ":"))


def _validate_identity(phone: str) -> None:
    if not isinstance(phone, str) or not phone.strip() or len(phone) > 32:
        raise HTTPException(status_code=401, detail="请先登录后再开始趣味数学。")


def _validate_request(day: str, question_id: Any, today: date) -> int:
    if not isinstance(day, str) or day != today.isoformat():
        raise HTTPException(status_code=409, detail="北京时间已跨天，请刷新页面领取今天的题目。")
    if isinstance(question_id, bool) or not isinstance(question_id, int) or not 1 <= question_id <= QUESTION_COUNT:
        raise HTTPException(status_code=400, detail="题目编号无效。")
    return question_id


def _validate_answer(answer: Any) -> int:
    if isinstance(answer, bool):
        raise HTTPException(status_code=400, detail="请输入非负整数答案。")
    if isinstance(answer, int):
        value = answer
    elif isinstance(answer, str) and re.fullmatch(r"[0-9]{1,6}", answer.strip()):
        value = int(answer.strip())
    else:
        raise HTTPException(status_code=400, detail="请输入非负整数答案，不支持小数或科学计数法。")
    if not 0 <= value <= 999999:
        raise HTTPException(status_code=400, detail="答案应为 0 到 999999 之间的整数。")
    return value


def _retryable_database_error(exc: OperationalError) -> bool:
    code = getattr(exc.orig, "args", (None,))[0]
    return code in (1205, 1213) or "database is locked" in str(exc.orig).lower() or "database is busy" in str(exc.orig).lower()


def _load_or_create(db: Session, phone: str, day: date, now: datetime):
    statement = select(MathDailySession.id, MathDailySession.version, MathDailySession.questions_json).where(
        MathDailySession.phone == phone, MathDailySession.practice_date == day
    )
    row = db.execute(statement).one_or_none()
    if row is not None:
        return row
    stamp = now.replace(tzinfo=None)
    db.add(MathDailySession(phone=phone, practice_date=day, questions_json=_encode(_new_questions()),
                            version=0, created_at=stamp, updated_at=stamp))
    try:
        db.commit()
    except IntegrityError:
        # Another request may already have created this user's immutable daily set.
        db.rollback()
    return db.execute(statement).one()


def _expire(questions: list[dict[str, Any]], now: datetime) -> None:
    for question in questions:
        if question["status"] == "active" and now >= datetime.fromisoformat(question["deadlineAt"].replace("Z", "+00:00")):
            question["status"] = "expired"
            question["finishedAt"] = _iso(now)


def _payload(day: date, now: datetime, questions: list[dict[str, Any]]) -> dict[str, Any]:
    visible = []
    for question in questions:
        item = {"id": question["id"], "status": question["status"],
                "reward": REWARD_PER_QUESTION if question["status"] == "correct" else 0}
        if question["status"] != "pending":
            item.update({key: question[key] for key in ("left", "right", "startedAt", "deadlineAt")})
        if question["status"] in SETTLED_STATUSES:
            item["answer"] = question["left"] * question["right"]
        if "submittedAnswer" in question:
            item["submittedAnswer"] = question["submittedAnswer"]
        visible.append(item)
    active = next((q["id"] for q in questions if q["status"] == "active"), None)
    correct = sum(q["status"] == "correct" for q in questions)
    return {
        "day": day.isoformat(), "serverNow": _iso(now), "nextRefreshAt": _iso(_next_midnight(day)),
        "limitSeconds": LIMIT_SECONDS, "rewardPerQuestion": REWARD_PER_QUESTION, "total": QUESTION_COUNT,
        "completed": sum(q["status"] in SETTLED_STATUSES for q in questions), "correct": correct,
        "earnedEnergy": correct * REWARD_PER_QUESTION, "questions": visible, "activeQuestionId": active,
        "nextQuestionId": None if active else next((q["id"] for q in questions if q["status"] == "pending"), None),
    }


def _operation(db: Session, phone: str, *, action: str, now: datetime | None,
               question_id: int | None = None, day: str | None = None, answer: Any = None) -> dict[str, Any]:
    _validate_identity(phone)
    instant = _utc(now)
    today = instant.astimezone(BEIJING).date()
    if action != "get":
        question_id = _validate_request(day, question_id, today)
    submitted = _validate_answer(answer) if action == "submit" else None

    for _ in range(MAX_CONFLICT_RETRIES):
        try:
            row = _load_or_create(db, phone, today, instant)
            questions = json.loads(row.questions_json)
            before = _encode(questions)
            _expire(questions, instant)
            grant = False
            result = None
            if action == "start":
                question = questions[question_id - 1]
                if question["status"] == "pending":
                    if any(q["status"] not in SETTLED_STATUSES for q in questions[:question_id - 1]):
                        raise HTTPException(status_code=409, detail="请先完成当前题，再开始下一题。")
                    question.update(status="active", startedAt=_iso(instant),
                                    deadlineAt=_iso(min(instant + timedelta(seconds=LIMIT_SECONDS), _next_midnight(today))))
                # Duplicate start is idempotent, including requests after expiry.
            elif action == "submit":
                question = questions[question_id - 1]
                if question["status"] == "pending":
                    raise HTTPException(status_code=409, detail="请先开始本题，才能提交答案。")
                if question["status"] == "active":
                    correct = submitted == question["left"] * question["right"]
                    question.update(status="correct" if correct else "incorrect", submittedAnswer=submitted,
                                    finishedAt=_iso(instant))
                    grant = correct
                messages = {"correct": "答对啦！100 猫咪能量已到账。" if grant else "本题已答对，奖励已领取，无需重复提交。",
                            "incorrect": "本题答案不正确，未获得能量。可以查看答案后继续下一题。",
                            "expired": "本题已超时，未获得能量。可以查看答案后继续下一题。"}
                result = {"status": question["status"], "awardedEnergy": REWARD_PER_QUESTION if grant else 0,
                          "message": messages[question["status"]]}

            after = _encode(questions)
            if after != before:
                changed = db.execute(update(MathDailySession).where(
                    MathDailySession.id == row.id, MathDailySession.version == row.version
                ).values(questions_json=after, version=row.version + 1, updated_at=instant.replace(tzinfo=None))
                  .execution_options(synchronize_session=False))
                if changed.rowcount != 1:
                    db.rollback()
                    continue
                if grant:
                    db.add(CatWorldEnergyGrant(phone=phone, amount=REWARD_PER_QUESTION,
                        reason=f"趣味数学 {today.isoformat()} 第 {question_id} 题答对",
                        granted_by_phone=FUN_MATH_GRANT_SOURCE, created_at=instant.replace(tzinfo=None)))
                db.commit()
            else:
                # End read transactions as well (important for MySQL repeatable-read).
                db.rollback()
            response = _payload(today, instant, questions)
            if result is not None:
                response["result"] = result
            return response
        except HTTPException:
            db.rollback()
            raise
        except OperationalError as exc:
            db.rollback()
            if not _retryable_database_error(exc):
                raise
        except Exception:
            db.rollback()
            raise
    raise HTTPException(status_code=409, detail="题目状态正在更新，请刷新后重试，不会重复发放奖励。")


def get_daily_payload(db: Session, phone: str, now: datetime | None = None) -> dict[str, Any]:
    return _operation(db, phone, action="get", now=now)


def start_question(db: Session, phone: str, question_id: int, day: str,
                   now: datetime | None = None) -> dict[str, Any]:
    return _operation(db, phone, action="start", question_id=question_id, day=day, now=now)


def submit_answer(db: Session, phone: str, question_id: int, day: str, answer: Any,
                  now: datetime | None = None) -> dict[str, Any]:
    return _operation(db, phone, action="submit", question_id=question_id, day=day, answer=answer, now=now)
