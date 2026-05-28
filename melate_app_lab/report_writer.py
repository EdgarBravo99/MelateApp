from __future__ import annotations

import csv
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


def _metric(label: str, value: Any) -> str:
    return f"<div class=\"metric\"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>"


def write_html_report(report: dict[str, Any], output_path: str | Path) -> Path:
    validate_output_json(report)
    postmortem = report["components"]["postmortem"]
    trace = report["components"]["trace"]
    stress = report["components"]["stress_review"]
    graph = report["components"].get("graph", {})
    graph_stats = graph.get("graph_stats", {}) if isinstance(graph, dict) else {}
    played_items = [
        f"{chr(65 + index)}: {' '.join(map(str, ticket))}"
        for index, ticket in enumerate(report["played_tickets"])
    ]
    lessons = postmortem.get("lessons_es", [])
    alerts = stress.get("review_alerts_es", [])
    anchors = stress.get("anchor_concentration", {}).get("repeated_numbers", [])
    coverage = stress.get("played_coverage", {})
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
      --paper: #eef2f0;
      --panel: #ffffff;
      --line: #ccd6d2;
      --accent: #0f766e;
      --warn: #9a3412;
      --soft: #e0f2f1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      border-bottom: 2px solid var(--accent);
      padding-bottom: 18px;
      margin-bottom: 18px;
    }}
    h1, h2 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: clamp(2rem, 4vw, 3rem); }}
    h2 {{ font-size: 1rem; margin-bottom: 10px; }}
    .subtitle {{ color: var(--muted); max-width: 820px; }}
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
      margin-bottom: 14px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }}
    .metric {{
      background: var(--soft);
      border: 1px solid #b2dfdb;
      border-radius: 8px;
      padding: 12px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: .82rem;
    }}
    .metric strong {{
      display: block;
      margin-top: 6px;
      overflow-wrap: anywhere;
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
  <section>
    <h2>Resumen ejecutivo</h2>
    <div class="metrics">
      {_metric("Capturados", postmortem["captured_numbers"])}
      {_metric("No capturados", postmortem["missed_numbers"])}
      {_metric("Suma", trace["sum"])}
      {_metric("Banda", trace["sum_band"])}
      {_metric("Firma de bloques", trace["block_signature"])}
      {_metric("Aristas", graph_stats.get("edge_count", "-"))}
    </div>
  </section>
  <div class="grid">
    <section>
      <h2>Lectura del brain</h2>
      <p>{html.escape(report["what_worked_es"])}</p>
      <p>{html.escape(report["what_was_missed_es"])}</p>
      <p>{html.escape(report.get("structural_reading_es", ""))}</p>
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
      <h2>Concentración de anclas</h2>
      <ul>{_list(anchors)}</ul>
    </section>
    <section>
      <h2>Cobertura estructural</h2>
      <p>Firmas: {html.escape(str(coverage.get("block_signatures", {})))}</p>
      <p>Bandas: {html.escape(str(coverage.get("sum_bands", {})))}</p>
    </section>
    <section>
      <h2>Grafo resumido</h2>
      <p>Nodos: {html.escape(str(graph_stats.get("node_count", "-")))}</p>
      <p>Aristas: {html.escape(str(graph_stats.get("edge_count", "-")))}</p>
      <p>Tipos: {html.escape(str(graph_stats.get("edge_type_counts", {})))}</p>
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


def write_csv_summary(report: dict[str, Any], output_path: str | Path) -> Path:
    validate_output_json(report)
    postmortem = report["components"]["postmortem"]
    trace = report["components"]["trace"]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "draw",
                "sum",
                "sum_band",
                "block_signature",
                "captured_numbers",
                "missed_numbers",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "draw": report["draw"],
                "sum": trace["sum"],
                "sum_band": trace["sum_band"],
                "block_signature": trace["block_signature"],
                "captured_numbers": " ".join(map(str, postmortem["captured_numbers"])),
                "missed_numbers": " ".join(map(str, postmortem["missed_numbers"])),
            }
        )
    return path
