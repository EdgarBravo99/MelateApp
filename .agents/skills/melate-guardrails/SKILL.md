# melate-guardrails

Use this skill for every MelateApp task that produces user-visible text, reports, CLI output, JSON lessons, HTML reports, or brain analysis.

Permanent language rules:
MelateApp is a review_default system.
It must not present itself as a predictor.

Forbidden visible language:
- predicción
- probabilidad
- seguro
- garantizado
- certeza
- va a salir
- ganador
- más probable
- mejor probabilidad
- win probability
- likely winner
- best pick

Allowed language:
- revisión
- rastro
- huella
- postmortem
- tesis de revisión
- señales
- aprendizaje de auditoría
- soporte estructural
- cobertura
- concentración
- diversidad
- alerta de revisión

Hard rules:
- Do not modify the main fisicapapa repo.
- Do not modify resultados.json.
- Do not modify v4_replay_memory.json.
- Do not touch crunchers, scores, priors, or replay memory.
- Learning memory may write only inside MelateApp local data files.
- Monte Carlo output is structural review only, never probability.
- LLM analyst output is narrative review only, never decision-making.

Validation:
Run guardrail checks on all generated visible strings.
