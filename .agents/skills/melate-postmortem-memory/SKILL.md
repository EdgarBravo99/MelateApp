# melate-postmortem-memory

Use this skill when implementing postmortem, memory, or learning audit logic.

Goal:
After a draw is known, compare played tickets against the result and store audit learning locally.

This is learning memory, not prediction memory.

Required outputs:
- best_matches
- captured_numbers
- missed_numbers
- overused_played_numbers
- result_trace
- lessons_es
- next_review_actions_es

SQLite tables:
- draws
- played_tickets
- postmortems
- lessons
- trace_patterns

Fixture:
Result:
2 18 22 38 51 52

Played:
A: 7 15 29 41 42 48
B: 7 16 18 23 29 39
C: 9 13 18 30 45 52
D: 7 15 20 30 36 53

Expected:
A = 0
B = 1 hit: 18
C = 2 hits: 18, 52
D = 0
captured_numbers = [18, 52]
missed_numbers = [2, 22, 38, 51]

Rules:
- Store local memory only in data/melate_app_memory.sqlite.
- Do not write into any external repo.
- Do not modify historical source data.
