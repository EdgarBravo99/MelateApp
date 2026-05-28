# melate-llm-analyst

Use this skill when implementing LLM analyst or narrative brain output.

Goal:
Convert structured data into clear Spanish review text.

The LLM analyst must:
- summarize what worked
- summarize what was missed
- identify trace patterns
- identify repeated review errors
- suggest next review actions

The LLM analyst must not:
- invent numbers
- alter scores
- modify memory directly
- claim predictions
- use probability language
- decide tickets

For MVP:
Use LLMAnalystStub only.
No external API calls yet.

Allowed output:
- diagnosis_es
- what_worked_es
- what_was_missed_es
- next_cycle_review_thesis_es
- risk_notes_es
