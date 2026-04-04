#!/usr/bin/env python3
"""
lang-tutor CLI — data layer for the /lang skill.

Usage:
    lang.py db init
    lang.py profile get
    lang.py profile save '<json>'
    lang.py roadmap get
    lang.py roadmap save '<json_array_of_topics>'
    lang.py queue [--n=5]
    lang.py session save '<json>'
    lang.py session get [--date=YYYY-MM-DD]
    lang.py attempt record '<json>'
    lang.py mastery update <topic_id> <score>
    lang.py analytics [--layer=all|outcomes|competency|memory|strand]
    lang.py dashboard
    lang.py calendar event '<json>'
    lang.py calendar recurring '<json>'
    lang.py notify '<message>'
"""

import sys
import json
import os
from datetime import date, datetime

# Allow imports from same directory
sys.path.insert(0, os.path.dirname(__file__))

import db
import scheduler
import analytics
import calendar as cal

VALID_ERROR_TYPES = frozenset({
    "article_omission",
    "article_misuse",
    "tense_error",
    "aspect_error",
    "word_order",
    "collocation_misuse",
    "preposition_error",
    "register_mismatch",
    "vocabulary_gap",
    "spelling",
    "grammar_agreement",
    "other",
})


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _err(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def cmd_db(args: list[str]):
    sub = args[0] if args else ""
    if sub == "init":
        db.init_db()
        _out({"status": "ok", "db": str(db.get_db_path())})
    else:
        _err(f"unknown db subcommand: {sub}")


def cmd_profile(args: list[str]):
    sub = args[0] if args else ""
    conn = db.get_conn()

    if sub == "get":
        row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
        conn.close()
        if not row:
            _out(None)
        else:
            d = dict(row)
            d["schedule"] = json.loads(d.pop("schedule_json", "{}"))
            _out(d)

    elif sub == "save":
        if len(args) < 2:
            _err("profile save requires JSON argument")
        p = json.loads(args[1])
        conn.execute("""
            INSERT INTO profile (id, language, level_cefr, goal, target_level, daily_minutes, schedule_json, onboarded_at)
            VALUES (1, :language, :level_cefr, :goal, :target_level, :daily_minutes, :schedule_json, :onboarded_at)
            ON CONFLICT(id) DO UPDATE SET
                language=excluded.language,
                level_cefr=excluded.level_cefr,
                goal=excluded.goal,
                target_level=excluded.target_level,
                daily_minutes=excluded.daily_minutes,
                schedule_json=excluded.schedule_json,
                onboarded_at=excluded.onboarded_at
        """, {
            "language": p["language"],
            "level_cefr": p["level_cefr"],
            "goal": p["goal"],
            "target_level": p["target_level"],
            "daily_minutes": p.get("daily_minutes", 30),
            "schedule_json": json.dumps(p.get("schedule", {})),
            "onboarded_at": p.get("onboarded_at", date.today().isoformat()),
        })
        conn.commit()
        conn.close()
        _out({"status": "saved"})

    else:
        _err(f"unknown profile subcommand: {sub}")


def cmd_roadmap(args: list[str]):
    sub = args[0] if args else ""
    conn = db.get_conn()

    if sub == "get":
        rows = conn.execute("SELECT * FROM topics ORDER BY priority ASC, cefr_milestone").fetchall()
        conn.close()
        topics = []
        for r in rows:
            t = dict(r)
            t["prerequisites"] = json.loads(t.pop("prerequisites_json", "[]"))
            topics.append(t)
        _out({"topics": topics})

    elif sub == "save":
        if len(args) < 2:
            _err("roadmap save requires JSON array argument")
        topics = json.loads(args[1])
        for t in topics:
            conn.execute("""
                INSERT INTO topics (id, title, category, cefr_milestone, strand, prerequisites_json, mastery_prob, last_practiced, priority)
                VALUES (:id, :title, :category, :cefr_milestone, :strand, :prerequisites_json, :mastery_prob, :last_practiced, :priority)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    category=excluded.category,
                    cefr_milestone=excluded.cefr_milestone,
                    strand=excluded.strand,
                    prerequisites_json=excluded.prerequisites_json,
                    priority=excluded.priority
            """, {
                "id": t["id"],
                "title": t["title"],
                "category": t.get("category", "general"),
                "cefr_milestone": t.get("cefr_milestone"),
                "strand": t.get("strand"),
                "prerequisites_json": json.dumps(t.get("prerequisites", [])),
                "mastery_prob": t.get("mastery_prob", 0.0),
                "last_practiced": t.get("last_practiced"),
                "priority": t.get("priority", 5),
            })
        conn.commit()
        conn.close()
        strand_check = analytics.roadmap_strand_check(topics)
        _out({"status": "saved", "count": len(topics), "strand_check": strand_check})

    else:
        _err(f"unknown roadmap subcommand: {sub}")


def cmd_queue(args: list[str]):
    n = 5
    for a in args:
        if a.startswith("--n="):
            n = int(a.split("=")[1])

    conn = db.get_conn()
    rows = conn.execute("SELECT id, title, category, mastery_prob, last_practiced FROM topics").fetchall()
    conn.close()

    scored = []
    for r in rows:
        urgency = scheduler.compute_urgency(r["mastery_prob"], r["last_practiced"])
        mode = scheduler.interleaving_mode(r["mastery_prob"])
        scored.append({
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "mastery_prob": round(r["mastery_prob"], 3),
            "urgency": round(urgency, 3),
            "mode": mode,
        })

    scored.sort(key=lambda x: x["urgency"], reverse=True)

    # Top n by urgency + 1-2 strong topics for reinforcement
    strong = [s for s in scored if s["mastery_prob"] >= 0.8]
    due = scored[:n]
    if strong and len(due) < n + 2:
        import random
        reinforce = random.sample(strong, min(2, len(strong)))
        due = due + [r for r in reinforce if r not in due]

    raw_queue = due[:n + 2]

    # Fetch daily_minutes from profile
    conn2 = db.get_conn()
    profile_row = conn2.execute("SELECT daily_minutes FROM profile WHERE id = 1").fetchone()
    conn2.close()
    daily_minutes = profile_row["daily_minutes"] if profile_row else 30

    # Strand stats for warning (14-day window)
    strand_stats = analytics.strand_balance(days=14)

    session_plan = scheduler.compose_session_plan(
        queue_topics=scored,
        daily_minutes=daily_minutes,
        strand_stats=strand_stats,
    )

    _out({"queue": raw_queue, "session_plan": session_plan})


def cmd_session(args: list[str]):
    sub = args[0] if args else ""
    conn = db.get_conn()

    if sub == "save":
        if len(args) < 2:
            _err("session save requires JSON argument")
        s = json.loads(args[1])
        now = datetime.now().isoformat()
        cur = conn.execute("""
            INSERT INTO sessions (date, topics_json, adherence_planned, adherence_actual, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            s.get("date", date.today().isoformat()),
            json.dumps(s.get("topics", [])),
            s.get("adherence_planned", 1),
            s.get("adherence_actual", 0),
            now,
        ))
        conn.commit()
        _out({"status": "saved", "session_id": cur.lastrowid})
        conn.close()

    elif sub == "get":
        target_date = date.today().isoformat()
        for a in args[1:]:
            if a.startswith("--date="):
                target_date = a.split("=")[1]
        row = conn.execute("SELECT * FROM sessions WHERE date = ? ORDER BY id DESC LIMIT 1", (target_date,)).fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["topics"] = json.loads(d.pop("topics_json", "[]"))
            _out(d)
        else:
            _out(None)

    else:
        _err(f"unknown session subcommand: {sub}")


def cmd_attempt(args: list[str]):
    sub = args[0] if args else ""
    if sub == "record":
        if len(args) < 2:
            _err("attempt record requires JSON argument")
        a = json.loads(args[1])

        score = a.get("score")
        if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
            _err(f"score must be a number in [0.0, 1.0], got: {score!r}")

        error_type = a.get("error_type")
        if error_type is not None and error_type not in VALID_ERROR_TYPES:
            _err(
                f"error_type {error_type!r} is not valid. "
                f"Must be one of: {', '.join(sorted(VALID_ERROR_TYPES))}"
            )

        conn = db.get_conn()
        conn.execute("""
            INSERT INTO attempts (item_id, topic_id, session_id, ts, score, latency_ms, exercise_type, error_type, error_context)
            VALUES (:item_id, :topic_id, :session_id, :ts, :score, :latency_ms, :exercise_type, :error_type, :error_context)
        """, {
            "item_id": a.get("item_id"),
            "topic_id": a["topic_id"],
            "session_id": a.get("session_id"),
            "ts": a.get("ts", datetime.now().isoformat()),
            "score": a["score"],
            "latency_ms": a.get("latency_ms"),
            "exercise_type": a["exercise_type"],
            "error_type": a.get("error_type"),
            "error_context": a.get("error_context"),
        })
        conn.commit()
        conn.close()
        _out({"status": "recorded"})
    else:
        _err(f"unknown attempt subcommand: {sub}")


def cmd_mastery(args: list[str]):
    sub = args[0] if args else ""
    if sub == "update":
        if len(args) < 3:
            _err("mastery update requires <topic_id> <score>")
        topic_id = args[1]
        score = float(args[2])

        conn = db.get_conn()
        row = conn.execute("SELECT mastery_prob FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if not row:
            conn.close()
            _err(f"topic not found: {topic_id}")

        new_mastery = scheduler.bkt_update(row["mastery_prob"], score)
        conn.execute(
            "UPDATE topics SET mastery_prob = ?, last_practiced = ? WHERE id = ?",
            (new_mastery, datetime.now().isoformat(), topic_id),
        )
        conn.commit()
        conn.close()
        _out({
            "topic_id": topic_id,
            "old_mastery": round(row["mastery_prob"], 3),
            "new_mastery": round(new_mastery, 3),
            "delta": round(new_mastery - row["mastery_prob"], 3),
        })
    else:
        _err(f"unknown mastery subcommand: {sub}")


def cmd_analytics(args: list[str]):
    layer = "all"
    for a in args:
        if a.startswith("--layer="):
            layer = a.split("=")[1]
    _out(analytics.full_report(layer))


def cmd_dashboard(args: list[str]):
    import subprocess
    from pathlib import Path

    data = analytics.dashboard_data()
    if data.get("error") == "no_profile":
        _err("No profile found. Run /lang first to set up.")

    json_path = Path("lang-analytics.json")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    template_path = Path(__file__).parent.parent / "templates" / "dashboard.html"
    html = template_path.read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False))
    html_path = Path("lang-dashboard.html")
    html_path.write_text(html)

    if sys.platform == "darwin":
        subprocess.run(["open", str(html_path)])

    _out({
        "dashboard": str(html_path.resolve()),
        "data": str(json_path.resolve()),
    })


def cmd_calendar(args: list[str]):
    if sys.platform != "darwin":
        _err(
            f"calendar commands require macOS (Darwin). "
            f"Current platform: {sys.platform}. "
            "Calendar integration uses AppleScript and is not available on this OS."
        )
    sub = args[0] if args else ""
    if sub == "event":
        if len(args) < 2:
            _err("calendar event requires JSON argument")
        ev = json.loads(args[1])
        result = cal.create_event(
            title=ev["title"],
            start_iso=ev["start"],
            duration_minutes=ev.get("duration_minutes", 30),
            notes=ev.get("notes", ""),
        )
        _out(result)
    elif sub == "recurring":
        if len(args) < 2:
            _err("calendar recurring requires JSON argument")
        ev = json.loads(args[1])
        result = cal.create_recurring_events(
            title=ev["title"],
            days_of_week=ev["days"],
            time_str=ev["time"],
            duration_minutes=ev.get("duration_minutes", 30),
            weeks=ev.get("weeks", 4),
        )
        _out(result)
    else:
        _err(f"unknown calendar subcommand: {sub}")


def cmd_notify(args: list[str]):
    if sys.platform != "darwin":
        _err(
            f"notify requires macOS (Darwin). "
            f"Current platform: {sys.platform}."
        )
    message = args[0] if args else "Time to practice!"
    cal.notify(message)
    _out({"status": "sent"})


COMMANDS = {
    "db": cmd_db,
    "profile": cmd_profile,
    "roadmap": cmd_roadmap,
    "queue": cmd_queue,
    "session": cmd_session,
    "attempt": cmd_attempt,
    "mastery": cmd_mastery,
    "analytics": cmd_analytics,
    "dashboard": cmd_dashboard,
    "calendar": cmd_calendar,
    "notify": cmd_notify,
}


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]
    rest = args[1:]

    if cmd not in COMMANDS:
        _err(f"unknown command: {cmd}\nAvailable: {', '.join(COMMANDS)}")

    COMMANDS[cmd](rest)


if __name__ == "__main__":
    main()
