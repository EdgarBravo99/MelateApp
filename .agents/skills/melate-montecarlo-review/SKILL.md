# melate-montecarlo-review

Use this skill when implementing Monte Carlo stress review.

Goal:
Stress-test structural coverage of played tickets and traces.

Allowed:
- Generate random valid tickets.
- Count structural coverage.
- Compare sum bands.
- Compare block signatures.
- Detect concentration and redundancy.
- Produce review alerts.

Forbidden:
- Do not call output probability.
- Do not say likely, winner, guaranteed, certain, more probable, or best pick.
- Do not rank tickets as future outcomes.
- Do not modify scores, priors, crunchers, or replay memory.

Output should focus on:
- structural coverage
- redundancy
- diversity
- missing coverage
- review alerts
- next review actions

Example wording:
"The played set is concentrated around repeated anchors and leaves low coverage for balanced high-tail forms."

Never:
"This structure is more probable."
