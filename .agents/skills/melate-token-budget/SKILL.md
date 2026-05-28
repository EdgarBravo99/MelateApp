# melate-token-budget

Use this skill when working on MelateApp with Codex or subagents and the task needs efficient context usage.

Goal:
Reduce token usage without sacrificing logic.

Rules:
- Do not load full project history unless explicitly needed.
- Each subagent receives only assigned files, module contract, expected tests, shared fixture, and guardrails.
- The integrator is the only agent that should hold the full architecture.
- Prefer contracts over full source files.
- Prefer fixtures over long explanations.
- Do not paste previous conversations unless they define current requirements.
- Keep output focused: changed files, validation run, risks, next action.

Shared fixture:
Revancha draw 4218:
2 18 22 38 51 52

Played tickets:
A: 7 15 29 41 42 48
B: 7 16 18 23 29 39
C: 9 13 18 30 45 52
D: 7 15 20 30 36 53

Expected:
A = 0 hits
B = 1 hit: 18
C = 2 hits: 18, 52
D = 0 hits
captured_numbers = [18, 52]
missed_numbers = [2, 22, 38, 51]
sum = 183
sum_band = high_tail
block_signature = 1-1-1-1-2
block_presence_signature = 1-1-1-1-1
