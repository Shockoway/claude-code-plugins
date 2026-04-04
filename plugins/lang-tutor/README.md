# lang-tutor

Adaptive language learning plugin for Claude Code. Generates personalized exercises using spaced repetition (BKT + SM-2), tracks mastery per topic, and schedules sessions via Apple Calendar.

## How it works

The plugin is built around a set of evidence-based learning principles. Understanding them helps you get more out of it.

**Spaced repetition.** Every topic you practice comes back for review. Intervals expand as mastery grows — things you know well appear rarely, things you're struggling with appear often. The scheduling uses two layers: BKT (Bayesian Knowledge Tracing) at the topic level to estimate mastery probability, and SM-2 at the item level for discrete facts and forms.

**Retrieval practice.** The session format prioritizes testing over re-reading. Research consistently shows that the act of retrieving information from memory — even imperfectly — strengthens retention more than additional study. Exercises are designed to make you produce language, not just recognize it.

**Blocking → interleaving.** When you're first learning a topic (mastery < 0.6), sessions focus on it exclusively — this is "blocking." Once you've stabilized basic competence, sessions start mixing confusable topics — this is "interleaving." Mixing feels harder but produces more durable learning. The switch happens automatically based on your mastery score.

**Four Strands.** Each session balances four types of practice, each serving a distinct role:
- **Input** (~30%) — comprehensible reading/listening at 95–98% known vocabulary
- **Output** (~25%) — producing language in context: fill-gaps, translation, writing
- **Language-focused** (~25%) — explicit grammar/vocabulary instruction with contrastive examples
- **Fluency** (~20%) — fast drills on already-known material to build automaticity

**Tiered corrective feedback.** When you make an error, feedback follows a fixed sequence: correct answer → error type (from a controlled taxonomy) → brief rule → memory hook. The error type is stored and influences future session composition — recurring errors get more practice.

**Implementation intentions.** Research on habit formation shows that pre-committing to a specific time and context ("Mon–Fri at 09:00 in this directory") significantly improves follow-through. The plugin creates calendar events and sends session-start reminders to anchor study to a stable routine.

## Prerequisites

- Python 3.9+
- macOS (calendar and notification features use AppleScript/osascript)

## Installation

1. Install the plugin via `/plugin`
2. Run `/reload-plugins`
3. Navigate to your language learning directory (any project folder works)
4. Run `/lang` — first launch runs onboarding

## First use

`/lang` will ask you six questions one at a time:

1. Language you're studying
2. Current CEFR level (A1–C1)
3. Goal (e.g. "professional English for IT")
4. Target level (B2–C2)
5. Minutes per day (15–60)
6. Preferred schedule (e.g. "Mon–Fri at 09:00")

After onboarding, the RoadmapAgent builds a 20–35 topic curriculum and saves it to `lang.db` in your current directory.

## Daily workflow

1. Notification fires at session start when topics are due
2. Run `/lang` → ExerciseAgent generates `sessions/YYYY-MM-DD.md`
3. Fill in your answers directly in the session file
4. Run `/lang` again → EvaluatorAgent scores answers and updates mastery

## Customization

Create `lang-guide.md` in your language learning directory before onboarding. The RoadmapAgent will incorporate it into the curriculum — useful for language-specific tracks (e.g. Japanese kana/kanji, German case system).

## Data files

All data is local to the working directory:

| File | Purpose |
|---|---|
| `lang.db` | SQLite database — topics, items, sessions, attempts |
| `sessions/YYYY-MM-DD.md` | Daily exercise files |
| `lang-guide.md` | Optional language-specific curriculum hints |

Override the database path: `export LANG_DB=/path/to/lang.db`

## Roadmap

Planned but not yet implemented:

- **Diagnostic placement** — short assessment at onboarding to measure actual CEFR level per skill (reading/listening/writing/speaking) instead of relying on self-report
- **Per-skill CEFR profile** — separate level tracking for each skill rather than a single global level
- **Weekly roadmap maintenance** — automatic weekly cycle to promote/delay topics, rebalance strands, inject remediation nodes based on accumulated error data
- **Re-test after feedback** — immediately re-queuing items where errors occurred, as the research recommends ("re-test soon, then later")
- **Latency tracking** — measuring time-to-answer as a proxy for automaticity; requires an interactive session format rather than a static markdown file
- **Adherence tracking** — recording actual vs planned sessions and surfacing adherence trends separately from learning performance
- **Retention interval targeting** — scheduling differently based on the user's goal horizon (e.g. "need this in 2 weeks" vs "want lifelong retention")
- **Cross-platform calendar** — current implementation uses AppleScript (macOS only); needs an abstraction layer for other platforms
