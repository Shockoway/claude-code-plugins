"""Apple Calendar integration via AppleScript."""

import subprocess
import sys
from datetime import datetime, timedelta


CALENDAR_NAME = "Language Learning"


def _run_applescript(script: str):
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def ensure_calendar():
    """Create the Language Learning calendar if it doesn't exist."""
    script = f"""
tell application "Calendar"
    if not (exists calendar "{CALENDAR_NAME}") then
        make new calendar with properties {{name:"{CALENDAR_NAME}"}}
    end if
end tell
"""
    _run_applescript(script)


def create_event(title: str, start_iso: str, duration_minutes: int = 30, notes: str = ""):
    """Create an event. start_iso: 'YYYY-MM-DD HH:MM' or ISO datetime."""
    ensure_calendar()

    # Parse to AppleScript date string: "Monday, April 7, 2026 at 09:00:00 AM"
    dt = datetime.fromisoformat(start_iso)
    end_dt = dt + timedelta(minutes=duration_minutes)

    def as_date(d: datetime) -> str:
        return d.strftime("%A, %B %-d, %Y at %I:%M:%S %p")

    notes_prop = f', description:"{notes}"' if notes else ""
    script = f"""
tell application "Calendar"
    tell calendar "{CALENDAR_NAME}"
        make new event with properties {{summary:"{title}", start date:date "{as_date(dt)}", end date:date "{as_date(end_dt)}"{notes_prop}}}
    end tell
end tell
"""
    _run_applescript(script)
    return {"created": True, "title": title, "start": start_iso, "duration_minutes": duration_minutes}


def create_recurring_events(title: str, days_of_week: list[str], time_str: str, duration_minutes: int = 30, weeks: int = 4):
    """Create recurring events for the next N weeks."""
    from datetime import date, timedelta

    day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    today = date.today()
    created = []

    for w in range(weeks):
        for day_name in days_of_week:
            target_weekday = day_map.get(day_name[:3])
            if target_weekday is None:
                continue
            days_ahead = (target_weekday - today.weekday()) % 7 + w * 7
            event_date = today + timedelta(days=days_ahead)
            start_iso = f"{event_date.isoformat()} {time_str}"
            create_event(title, start_iso, duration_minutes)
            created.append(start_iso)

    return {"created_count": len(created), "events": created}


def notify(message: str, title: str = "Language Learning"):
    """Send a macOS notification."""
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script])
