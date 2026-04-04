"""Three-layer progress analytics for lang-tutor."""

import json
from datetime import datetime, date, timedelta
from collections import defaultdict
from db import get_conn


# ── Helpers ──────────────────────────────────────────────────────────────────

def _rows(query: str, params=()):
    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _scalar(query: str, params=(), default=None):
    conn = get_conn()
    row = conn.execute(query, params).fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else default


# ── Layer 1: Outcomes (CEFR can-do checklist) ─────────────────────────────────

def outcomes_layer() -> dict:
    topics = _rows("SELECT id, title, cefr_milestone, mastery_prob FROM topics ORDER BY cefr_milestone, mastery_prob DESC")

    by_milestone = defaultdict(list)
    for t in topics:
        milestone = t["cefr_milestone"] or "General"
        by_milestone[milestone].append({
            "id": t["id"],
            "title": t["title"],
            "mastery": round(t["mastery_prob"], 2),
            "status": _mastery_label(t["mastery_prob"]),
        })

    return {"milestones": dict(by_milestone)}


def _mastery_label(prob: float) -> str:
    if prob >= 0.85:
        return "mastered"
    elif prob >= 0.6:
        return "proficient"
    elif prob >= 0.3:
        return "learning"
    else:
        return "not_started"


# ── Layer 2: Competency (mastery + error clusters) ────────────────────────────

def competency_layer() -> dict:
    topics = _rows("SELECT id, title, category, mastery_prob, last_practiced FROM topics ORDER BY mastery_prob ASC")

    # Top error types from recent attempts (last 30 days)
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    errors = _rows(
        """
        SELECT error_type, COUNT(*) as count
        FROM attempts
        WHERE error_type IS NOT NULL AND ts >= ?
        GROUP BY error_type
        ORDER BY count DESC
        LIMIT 5
        """,
        (cutoff,),
    )

    weak = [t for t in topics if t["mastery_prob"] < 0.5]
    strong = [t for t in topics if t["mastery_prob"] >= 0.85]

    return {
        "weak_topics": weak[:5],
        "strong_topics": strong[:5],
        "error_clusters": errors,
        "total_topics": len(topics),
        "mastered_count": len(strong),
    }


# ── Layer 3: Memory health (spaced rep backlog) ───────────────────────────────

def memory_layer() -> dict:
    today = date.today().isoformat()

    overdue = _rows(
        "SELECT id, topic_id, content, item_type, due_at FROM items WHERE due_at <= ? ORDER BY due_at ASC",
        (today,),
    )
    upcoming = _rows(
        """
        SELECT id, topic_id, content, item_type, due_at FROM items
        WHERE due_at > ? ORDER BY due_at ASC LIMIT 20
        """,
        (today,),
    )

    # Streak calculation
    sessions = _rows("SELECT date FROM sessions ORDER BY date DESC LIMIT 60")
    streak = _compute_streak([s["date"] for s in sessions])

    return {
        "overdue_items": len(overdue),
        "overdue_list": overdue[:10],
        "upcoming_count": len(upcoming),
        "current_streak_days": streak,
    }


def _compute_streak(dates: list[str]) -> int:
    if not dates:
        return 0
    today = date.today()
    streak = 0
    current = today
    date_set = set(dates)
    while current.isoformat() in date_set:
        streak += 1
        current -= timedelta(days=1)
    return streak


# ── Strand balance check ──────────────────────────────────────────────────────

def strand_balance(days: int = 14) -> dict:
    """Check if Four Strands are balanced in recent attempts."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = _rows(
        """
        SELECT t.strand, COUNT(*) as count
        FROM attempts a
        JOIN topics t ON a.topic_id = t.id
        WHERE a.ts >= ?
        GROUP BY t.strand
        """,
        (cutoff,),
    )
    total = sum(r["count"] for r in rows) or 1
    balance = {r["strand"] or "unknown": round(r["count"] / total, 2) for r in rows}

    # Warn if any strand > 60% or input/output < 15%
    warnings = []
    for strand, ratio in balance.items():
        if ratio > 0.6:
            warnings.append(f"{strand} is overrepresented ({int(ratio*100)}%)")
    for strand in ("input", "output"):
        if balance.get(strand, 0) < 0.15:
            warnings.append(f"{strand} is underrepresented — add more {strand} practice")

    return {"balance": balance, "warnings": warnings}


# ── Roadmap strand check ─────────────────────────────────────────────────────

STRAND_TARGETS = {
    "language-focused": 0.25,
    "input": 0.30,
    "output": 0.25,
    "fluency": 0.20,
}
STRAND_TOLERANCE = 0.08


def roadmap_strand_check(topics: list[dict]) -> dict:
    """
    Check Four Strands distribution across a list of topic dicts.
    Distinct from strand_balance() which reads historical attempts.
    Returns {"pass": bool, "distribution": {...}, "warnings": [...]}.
    """
    from collections import Counter
    counts = Counter(t.get("strand") or "unknown" for t in topics)
    total = len(topics) or 1

    distribution = {strand: round(count / total, 3) for strand, count in counts.items()}

    warnings = []
    for strand, target in STRAND_TARGETS.items():
        actual = distribution.get(strand, 0.0)
        if abs(actual - target) > STRAND_TOLERANCE:
            direction = "above" if actual > target else "below"
            warnings.append(
                f"{strand} is {direction} target "
                f"({int(actual * 100)}% actual vs {int(target * 100)}% target)"
            )

    return {
        "pass": len(warnings) == 0,
        "distribution": distribution,
        "warnings": warnings,
    }


# ── Practice calendar ────────────────────────────────────────────────────────

def practice_calendar(days: int = 30) -> list:
    """Return daily session counts for the last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return _rows(
        """
        SELECT date, COUNT(*) as sessions, SUM(duration_s) as total_s
        FROM sessions
        WHERE date >= ?
        GROUP BY date
        ORDER BY date
        """,
        (cutoff,),
    )


# ── Dashboard aggregate ───────────────────────────────────────────────────────

def dashboard_data() -> dict:
    """Aggregate all layers into one object for the dashboard HTML."""
    try:
        conn = get_conn()
        profile_row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
        conn.close()
    except Exception:
        return {"error": "no_profile"}

    if not profile_row:
        return {"error": "no_profile"}

    profile = dict(profile_row)
    profile.pop("schedule_json", None)

    # Build urgency-sorted queue for session plan
    import scheduler as _sched
    topics_rows = _rows(
        "SELECT id, title, category, mastery_prob, last_practiced FROM topics"
    )
    scored = []
    for t in topics_rows:
        urgency = _sched.compute_urgency(t["mastery_prob"], t["last_practiced"])
        mode = _sched.interleaving_mode(t["mastery_prob"])
        scored.append({
            "id": t["id"],
            "title": t["title"],
            "category": t["category"],
            "mastery_prob": round(t["mastery_prob"], 3),
            "urgency": round(urgency, 3),
            "mode": mode,
        })
    scored.sort(key=lambda x: x["urgency"], reverse=True)

    strand_stats = strand_balance()
    session_plan = _sched.compose_session_plan(
        queue_topics=scored,
        daily_minutes=profile.get("daily_minutes", 30),
        strand_stats=strand_stats,
    )

    return {
        "generated_at": datetime.now().isoformat(),
        "profile": profile,
        "outcomes": outcomes_layer(),
        "competency": competency_layer(),
        "memory": memory_layer(),
        "strand_balance": strand_stats,
        "practice_calendar": practice_calendar(),
        "session_plan": session_plan,
    }


# ── Full report ───────────────────────────────────────────────────────────────

def full_report(layer: str = "all") -> dict:
    result = {}
    if layer in ("all", "outcomes"):
        result["outcomes"] = outcomes_layer()
    if layer in ("all", "competency"):
        result["competency"] = competency_layer()
    if layer in ("all", "memory"):
        result["memory"] = memory_layer()
    if layer in ("all", "strand"):
        result["strand_balance"] = strand_balance()
    return result
