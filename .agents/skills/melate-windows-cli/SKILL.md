# melate-windows-cli

Use this skill when implementing or testing the local Windows CLI.

Goal:
Provide clear PowerShell-friendly commands.

Required commands:
python -m melate_app_lab trace
python -m melate_app_lab postmortem
python -m melate_app_lab remember
python -m melate_app_lab graph
python -m melate_app_lab montecarlo-stress
python -m melate_app_lab brain
python -m melate_app_lab report

Rules:
- Commands must work in Windows PowerShell.
- Avoid shell syntax that only works on bash.
- Use quoted strings for number lists.
- Write outputs into outputs/.
- Write memory into data/melate_app_memory.sqlite.
- Keep CLI messages concise and in Spanish where user-facing.
