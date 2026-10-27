"""Append-only festival earnings, capped per learner and Beijing calendar day."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CatWorldFestivalEarning


BEIJING = timezone(timedelta(hours=8))
DAILY_BONUS_CAP = 1500
FESTIVALS = (
    ("mid-autumn-2026", "中秋", date(2026, 9, 25), date(2026, 9, 27)),
    ("national-day-2026", "国庆", date(2026, 10, 1), date(2026, 10, 7)),
    ("halloween-2026", "万圣节", date(2026, 10, 31), date(2026, 11, 2)),
)
ELIGIBLE_SOURCES = frozenset({"spelling", "challenge_round", "essay", "debate"})


def festival_now(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(BEIJING)


def festival_for_day(day: date, festivals=FESTIVALS):
    return next((event for event in festivals if event[2] <= day <= event[3]), None)


def reward_multiplier(now: datetime | date | None = None, festivals=FESTIVALS) -> int:
    """Return the learning reward multiplier for a Beijing calendar day.

    The multiplier is applied only to the newly recorded learning events.  A
    festival takes precedence over the weekend rule, so a Halloween weekend
    is still 3x rather than 2x.  The caller records only the extra portion in
    the append-only bonus ledger; historical ordinary-day rewards are never
    recalculated.
    """
    if isinstance(now, datetime):
        current = festival_now(now)
        day = current.date()
    elif isinstance(now, date):
        day = now
    else:
        day = festival_now().date()
    if festival_for_day(day, festivals):
        return 3
    return 2 if day.weekday() >= 5 else 1


def festival_sale_window(festival_id: str | None, now: datetime | None = None) -> dict:
    if not festival_id:
        return {"saleState": "active", "saleLabel": "长期开放", "timeLimited": False}
    event = next(event for event in FESTIVALS if event[0] == festival_id)
    current = festival_now(now)
    opens = datetime.combine(event[2], time.min, BEIJING)
    closes = datetime.combine(event[3] + timedelta(days=1), time.min, BEIJING)
    state = "upcoming" if current < opens else "ended" if current >= closes else "active"
    return {
        "saleState": state, "timeLimited": True,
        "opensAt": opens.isoformat(), "closesAt": closes.isoformat(),
        "saleLabel": f"{event[2].month}月{event[2].day}日–{event[3].month}月{event[3].day}日 · 北京时间",
    }


def festival_blind_box_series() -> list[dict]:
    themes = (
        ("mid-autumn-2026", "月满团圆", "中秋", (
            ("festival-moon", "月光团子猫", "Moonlight Cat", "银白月光", "月亮圆圆的，今天也陪你读一个小故事。"),
            ("festival-osmanthus", "桂花奶糖猫", "Osmanthus Cat", "暖金桂花", "桂花香飘进窗户啦，学完就来歇一会儿。"),
        )),
        ("national-day-2026", "金秋漫游", "国庆", (
            ("festival-lantern", "灯笼暖暖猫", "Lantern Cat", "暖红灯笼", "小灯笼亮起来啦，今天也为你的进步开心。"),
            ("festival-maple", "枫叶旅行猫", "Maple Cat", "橘红枫叶", "带上一个新单词，我们一起去看秋天。"),
        )),
        ("halloween-2026", "南瓜夜巡", "万圣节", (
            ("festival-pumpkin", "南瓜灯猫", "Pumpkin Lantern Cat", "南瓜橙", "今晚的南瓜灯亮起来啦，陪你把新单词读成咒语。"),
            ("festival-ghost", "幽灵披风猫", "Ghost Cloak Cat", "月影紫", "披上小斗篷，悄悄陪你完成今天的学习挑战。"),
        )),
    )
    series = []
    for key, label, holiday, cats in themes:
        series.append({
            "key": key, "festivalId": key, "label": f"{label} · {holiday}限定",
            "region": "节庆", "issue": f"2026 {holiday}",
            "shopItemId": f"{key}-blind-box", "unlimitedStock": True,
            "description": f"{holiday}期间可用学习能量兑换，每个账号限开一次，两款猫咪机会均等。获得后永久保留。",
            "cats": [{
                "totalStock": 0,
                "cat": {
                    "id": cat_id, "label": name, "englishName": english,
                    "rarity": "SR", "limited": True, "region": "节庆",
                    "description": f"2026 {holiday}纪念伙伴，拥有{color}配色，喜欢陪你一起学习。",
                    "personality": "温柔的节日陪读员",
                    "traits": {"activity": "gentle", "movement": 0.95, "energyDrain": 0.8,
                               "moodDrain": 0.7, "playMoodGain": 1.1, "foodEnergyGain": 1.1,
                               "restThreshold": 30, "sleepStart": 22, "sleepEnd": 8,
                               "nightOwl": False, "routine": "在窗边听你读故事",
                               "temperament": "gentle", "label": "温柔亲近，喜欢安静陪读。"},
                    "thoughts": [thought, "学一点，休息一下，我们慢慢来。"],
                },
            } for cat_id, name, english, color, thought in cats],
        })
    return series


def record_festival_earning(
    db: Session, *, phone: str, source: str, event_key: str,
    base_energy: int, now: datetime | None = None,
) -> bool:
    """Record the extra part of a newly earned learning reward.

    ``base_energy`` remains the caller's ordinary reward.  The row stores only
    ``base_energy * (multiplier - 1)`` so the normal sources stay unchanged and
    the same event can be replayed safely.  The existing daily cap therefore
    limits only the bonus portion, as it did for the original festival rule.
    """
    current = festival_now(now)
    multiplier = reward_multiplier(current)
    if not phone or source not in ELIGIBLE_SOURCES or base_energy <= 0 or multiplier <= 1:
        return False
    bonus_energy = int(base_energy) * (multiplier - 1)
    if bonus_energy <= 0:
        return False
    existing = db.scalar(select(CatWorldFestivalEarning.id).where(
        CatWorldFestivalEarning.phone == phone,
        CatWorldFestivalEarning.event_key == event_key,
    ))
    if existing is not None:
        return False
    try:
        with db.begin_nested():
            db.add(CatWorldFestivalEarning(
                phone=phone, source=source, event_key=event_key,
                earned_date=current.date(), base_energy=bonus_energy,
                created_at=current.astimezone(timezone.utc).replace(tzinfo=None),
            ))
            db.flush()
    except IntegrityError:
        # Only ignore a concurrent replay of this exact event, not other DB errors.
        if db.scalar(select(CatWorldFestivalEarning.id).where(
            CatWorldFestivalEarning.phone == phone,
            CatWorldFestivalEarning.event_key == event_key,
        )) is None:
            raise
        return False
    return True


def festival_energy_source(db: Session, phone: str, now: datetime | None = None) -> dict:
    current = festival_now(now)
    today = current.date()
    daily_base = dict(db.execute(
        select(CatWorldFestivalEarning.earned_date, func.sum(CatWorldFestivalEarning.base_energy))
        .where(CatWorldFestivalEarning.phone == phone, CatWorldFestivalEarning.earned_date <= today)
        .group_by(CatWorldFestivalEarning.earned_date)
    ).all())
    daily_bonus = {day: min(max(int(amount), 0), DAILY_BONUS_CAP) for day, amount in daily_base.items()}
    total = sum(daily_bonus.values())
    today_bonus = daily_bonus.get(today, 0)
    active = festival_for_day(today)
    upcoming = next((event for event in FESTIVALS if today < event[2]), None)
    event = active or upcoming
    status = "active" if active else "upcoming" if upcoming else "ended"
    date_label = " · ".join(
        f"{event[2].month}月{event[2].day}–"
        f"{str(event[3].month) + '月' if event[2].month != event[3].month else ''}{event[3].day}日"
        for event in FESTIVALS
    )
    multiplier = reward_multiplier(today)
    campaign = {
        "visible": FESTIVALS[0][2] - timedelta(days=1) <= today <= FESTIVALS[-1][3],
        "status": status,
        "name": event[1] if event else "双节",
        "dateLabel": date_label,
        "startDate": event[2].isoformat() if event else "",
        "endDate": event[3].isoformat() if event else "",
        "today": today.isoformat(),
        "dailyCap": DAILY_BONUS_CAP,
        "todayMultiplier": multiplier,
        "multiplierLabel": f"今日 {multiplier} 倍" if multiplier > 1 else "今日普通倍率",
        "todayBonus": today_bonus,
        "remainingBonus": max(DAILY_BONUS_CAP - today_bonus, 0) if multiplier > 1 else DAILY_BONUS_CAP,
        "totalBonus": total,
        "nextUpdateAt": datetime.combine(today + timedelta(days=1), time.min, BEIJING).isoformat(),
        "rule": f"节庆日新获得的拼写、整轮挑战、作文和 AI 英语辩论积分 3 倍；普通周末 2 倍；每天额外加成最多 {DAILY_BONUS_CAP} 能量。",
        "note": "按北京时间，完成学习后自动到账。节庆优先于周末；只放大学习来源，学习习惯奖励和特别赠送不叠加；已有加成活动结束后仍可使用。",
    }
    return {
        "key": "festival_bonus", "label": "节庆/周末学习加成", "unit": "能量",
        "energyPerUnit": 1, "value": total, "energy": total,
        "todayValue": today_bonus, "todayEnergy": today_bonus,
        "todayDetail": f"{multiplier}倍学习加成 +{today_bonus} · 每日最多 {DAILY_BONUS_CAP}",
        "campaign": campaign,
    }
