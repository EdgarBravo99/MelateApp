# melate-evaluator-brain

Use this skill when implementing the MelateApp evaluator brain.

Goal:
Combine:
- draw_trace
- postmortem
- memory
- relation_graph
- montecarlo_stress
- LLMAnalystStub

Output:
- diagnosis_es
- what_worked_es
- what_was_missed_es
- next_cycle_review_thesis_es
- risk_notes_es

Rules:
- The brain is a review integrator.
- It does not predict.
- It does not produce scores for future outcomes.
- It does not modify the main repo.
- It does not modify crunchers, priors, replay memory, or resultados.json.
- It can read local memory and produce local reports.
