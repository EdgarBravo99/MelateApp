from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .guardrails import validate_output_json, validate_text


def write_json_report(report: dict[str, Any], output_path: str | Path) -> Path:
    validate_output_json(report)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _list(items: list[Any]) -> str:
    return "".join(f"<li>{html.escape(str(item))}</li>" for item in items)


def write_html_report(report: dict[str, Any], output_path: str | Path) -> Path:
    validate_output_json(report)
    postmortem = report["components"]["postmortem"]
    trace = report["components"]["trace"]
    stress = report["components"]["stress_review"]
    played_items = [
        f"{chr(65 + index)}: {' '.join(map(str, ticket))}"
        for index, ticket in enumerate(report["played_tickets"])
    ]
    lessons = postmortem.get("lessons_es", [])
    alerts = stress.get("review_alerts_es", [])
    document = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sorteo {html.escape(str(report["draw"]))} | MelateApp Lab</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17202a;
      --muted: #5c6670;
      --paper: #f7f4ee;
      --panel: #ffffff;
      --line: #d7d0c6;
      --accent: #0f766e;
      --warn: #9a3412;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Georgia, Cambria, "Times New Roman", serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      border-bottom: 2px solid var(--ink);
      padding-bottom: 18px;
      margin-bottom: 24px;
    }}
    h1, h2 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: clamp(2rem, 4vw, 3.5rem); }}
    h2 {{ font-size: 1.1rem; margin-bottom: 10px; }}
    .subtitle {{ color: var(--muted); max-width: 760px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .numbers {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 0;
      list-style: none;
    }}
    .numbers li {{
      min-width: 42px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      text-align: center;
      font-weight: 700;
    }}
    .captured li {{ border-color: var(--accent); color: var(--accent); }}
    .missed li {{ border-color: var(--warn); color: var(--warn); }}
    ul {{ padding-left: 20px; }}
    code {{ font-family: Consolas, monospace; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Sorteo {html.escape(str(report["draw"]))}</h1>
    <p class="subtitle">{html.escape(report["diagnosis_es"])}</p>
  </header>
  <div class="grid">
    <section>
      <h2>Resumen</h2>
      <p>{html.escape(report["what_worked_es"])}</p>
      <p>{html.escape(report["what_was_missed_es"])}</p>
    </section>
    <section>
      <h2>Huella del sorteo</h2>
      <p><code>{html.escape(trace["block_signature"])}</code></p>
      <p>{html.escape(trace["trace_es"])}</p>
    </section>
    <section>
      <h2>Boletos jugados</h2>
      <ul>{_list(played_items)}</ul>
    </section>
    <section>
      <h2>Capturados</h2>
      <ul class="numbers captured">{_list(postmortem["captured_numbers"])}</ul>
    </section>
    <section>
      <h2>No capturados</h2>
      <ul class="numbers missed">{_list(postmortem["missed_numbers"])}</ul>
    </section>
    <section>
      <h2>Lecciones</h2>
      <ul>{_list(lessons)}</ul>
    </section>
    <section>
      <h2>Tesis de revisión siguiente ciclo</h2>
      <p>{html.escape(report["next_cycle_review_thesis_es"])}</p>
    </section>
    <section>
      <h2>Alertas de revisión</h2>
      <ul>{_list(alerts)}</ul>
    </section>
  </div>
</main>
</body>
</html>
"""
    validate_text(document)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
