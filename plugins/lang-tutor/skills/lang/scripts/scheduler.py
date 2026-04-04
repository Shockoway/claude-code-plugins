"""Spaced repetition and BKT scheduling for lang-tutor."""

import math
from datetime import datetime, date
from typing import Optional


# ── Layer B: Topic-level scheduling ──────────────────────────────────────────

def compute_urgency(mastery_prob: float, last_practiced: Optional[str]) -> float:
    """Higher = more urgently needs practice."""
    if last_practiced is None:
        days_since = 999
    else:
        try:
            last = datetime.fromisoformat(last_practiced).date()
            days_since = (date.today() - last).days
        except ValueError:
            days_since = 999
    return (1.0 - mastery_prob) * math.log(days_since + 1)


def bkt_update(
    mastery_prob: float,
    score: float,
    p_slip: float = 0.1,
    p_guess: float = 0.2,
) -> float:
    """Bayesian Knowledge Tracing update. Returns new mastery probability."""
    if score >= 0.6:
        p_obs_known = 1.0 - p_slip
        p_obs_unknown = p_guess
    else:
        p_obs_known = p_slip
        p_obs_unknown = 1.0 - p_guess

    denom = mastery_prob * p_obs_known + (1.0 - mastery_prob) * p_obs_unknown
    if denom == 0:
        return mastery_prob

    posterior = (mastery_prob * p_obs_known) / denom
    # Exponential smoothing: don't jump too fast
    new_mastery = 0.7 * mastery_prob + 0.3 * posterior
    return max(0.0, min(1.0, new_mastery))


def interleaving_mode(mastery_prob: float) -> str:
    """blocking = learn one topic deeply first; interleaving = mix confusables."""
    return "blocking" if mastery_prob < 0.6 else "interleaving"


# ── Layer A: Item-level scheduling (SM-2) ────────────────────────────────────

def sm2_update(
    interval_days: float,
    ease_factor: float,
    score: float,
) -> tuple[float, float]:
    """SM-2 algorithm. Returns (new_interval_days, new_ease_factor)."""
    if score >= 0.6:
        new_interval = max(1.0, interval_days * ease_factor)
        new_ease = max(1.3, ease_factor + 0.1 - (1.0 - score) * 0.8)
    else:
        new_interval = 1.0  # Reset on failure
        new_ease = max(1.3, ease_factor - 0.2)
    return new_interval, new_ease


def _slots_for_budget(daily_minutes: int) -> list[dict]:
    """Return exercise slot counts for a single topic based on daily time budget."""
    if daily_minutes <= 20:
        return [
            {"strand": "input", "count": 1},
            {"strand": "language_focused", "count": 1},
            {"strand": "output", "count": 1},
            {"strand": "fluency", "count": 5},
        ]
    elif daily_minutes <= 30:
        return [
            {"strand": "input", "count": 2},
            {"strand": "language_focused", "count": 1},
            {"strand": "output", "count": 2},
            {"strand": "fluency", "count": 5},
        ]
    else:
        return [
            {"strand": "input", "count": 2},
            {"strand": "language_focused", "count": 1},
            {"strand": "output", "count": 2},
            {"strand": "fluency", "count": 8},
        ]


def compose_session_plan(
    queue_topics: list[dict],
    daily_minutes: int,
    strand_stats: dict | None,
) -> dict:
    """
    Compute a deterministic session plan from the urgency-sorted queue.

    queue_topics: list of {id, title, category, mastery_prob, urgency, mode}
    daily_minutes: from profile
    strand_stats: output of analytics.strand_balance(), or None

    Returns a session plan dict that tells ExerciseAgent exactly what to generate.
    """
    if not queue_topics:
        return {
            "mode": "interleaving",
            "time_budget_minutes": daily_minutes,
            "strand_warning": None,
            "topics": [],
        }

    top = queue_topics[0]
    mode = "blocking" if top["mastery_prob"] < 0.6 else "interleaving"

    if mode == "blocking":
        selected = queue_topics[:1]
    else:
        selected = queue_topics[:3] if len(queue_topics) >= 3 else queue_topics[:max(2, len(queue_topics))]

    slots = _slots_for_budget(daily_minutes)

    topics_out = [
        {
            "id": t["id"],
            "title": t["title"],
            "mastery_prob": t["mastery_prob"],
            "mode": t["mode"],
            "exercise_slots": slots,
        }
        for t in selected
    ]

    warnings = strand_stats.get("warnings") if strand_stats else None
    strand_warning = warnings if warnings else None

    return {
        "mode": mode,
        "time_budget_minutes": daily_minutes,
        "strand_warning": strand_warning,
        "topics": topics_out,
    }
