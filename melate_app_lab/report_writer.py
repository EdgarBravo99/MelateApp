from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from .guardrails import validate_output_json, validate_text
from .paths import resources_dir


def _get_cytoscape_script() -> str:
    local_path = resources_dir() / "cytoscape.min.js"
    if local_path.exists():
        try:
            js_content = local_path.read_text(encoding="utf-8")
            return f"<script>{js_content}</script>"
        except Exception:
            pass
    return '<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.29.2/cytoscape.min.js"></script>'


def _get_chartjs_script() -> str:
    local_path = resources_dir() / "chart.js"
    if local_path.exists():
        try:
            js_content = local_path.read_text(encoding="utf-8")
            return f"<script>{js_content}</script>"
        except Exception:
            pass
    return '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'


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


def write_graph_html_report(graph_data: dict[str, Any], output_path: str | Path) -> Path:
    validate_output_json(graph_data)
    mode = graph_data.get("mode", "postmortem")

    if mode == "historical":
        return _write_historical_graph_html(graph_data, output_path)
    return _write_postmortem_graph_html(graph_data, output_path)


def _write_postmortem_graph_html(graph_data: dict[str, Any], output_path: str | Path) -> Path:
    draw = graph_data["metadata"]["draw"]

    nodes_js = []
    for node in graph_data["nodes"]:
        nodes_js.append({
            "data": {
                "id": node["id"],
                "number": node["number"],
                "block": node["block"],
                "roles": node["roles"],
                "label": str(node["number"])
            }
        })

    edges_js = []
    for edge in graph_data["edges"]:
        edges_js.append({
            "data": {
                "source": edge["source"],
                "target": edge["target"],
                "type": edge["type"],
                "severity": edge["severity"],
                "evidence": edge.get("evidence_es", "")
            }
        })

    html_content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Grafo postmortem | Sorteo {draw}</title>
  {_get_cytoscape_script()}
  <style>
    :root {{
      --bg: #0b0f19;
      --panel: #111827;
      --panel-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #10b981;
      --accent-glow: rgba(16, 185, 129, 0.2);
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    header {{
      background: var(--panel);
      border-bottom: 1px solid var(--panel-border);
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
    }}
    h1 {{ margin: 0; font-size: 1.5rem; font-weight: 600; color: #fff; }}
    h1 span {{ color: var(--accent); }}
    .subtitle {{ font-size: 0.875rem; color: var(--text-muted); margin-top: 4px; }}
    .layout {{
      display: flex;
      flex: 1;
      position: relative;
    }}
    #cy {{
      flex: 1;
      height: 100%;
      background: #0f172a;
    }}
    #sidebar {{
      width: 360px;
      background: var(--panel);
      border-left: 1px solid var(--panel-border);
      padding: 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .panel-section {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 16px;
    }}
    h2 {{ margin: 0 0 12px 0; font-size: 1rem; font-weight: 600; color: #fff; border-bottom: 1px solid var(--panel-border); padding-bottom: 8px; }}
    .detail-item {{ margin-bottom: 12px; }}
    .detail-item:last-child {{ margin-bottom: 0; }}
    .detail-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
    .detail-value {{ font-size: 0.95rem; margin-top: 4px; font-weight: 500; }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      margin-right: 6px;
      margin-top: 6px;
    }}
    .badge-result {{ background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); }}
    .badge-played {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.4); }}
    .badge-captured {{ background: rgba(139, 92, 246, 0.2); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.4); }}
    .badge-missed {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
      font-size: 0.85rem;
    }}
    .legend-color {{
      width: 14px;
      height: 14px;
      border-radius: 50%;
    }}
    .legend-line {{
      width: 24px;
      height: 3px;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Grafo postmortem | Sorteo <span>{draw}</span></h1>
      <div class="subtitle">Visualizacion interactiva de conexiones entre boletos jugados y resultados</div>
    </div>
  </header>
  <div class="layout">
    <div id="cy"></div>
    <div id="sidebar">
      <div class="panel-section">
        <h2>Detalles de Seleccion</h2>
        <div id="details-content">
          <p style="color: var(--text-muted); font-style: italic;">Haz clic en un numero o una conexion para ver sus detalles analiticos.</p>
        </div>
      </div>

      <div class="panel-section">
        <h2>Leyenda de Nodos</h2>
        <div class="legend-item">
          <div class="legend-color" style="background: #10b981; border: 1px solid #059669;"></div>
          <span>Numero del Resultado (Sorteado)</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: #3b82f6; border: 1px solid #2563eb;"></div>
          <span>Numero Jugado (No sorteado)</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: #8b5cf6; border: 1px solid #7c3aed;"></div>
          <span>Numero Capturado (Acierto)</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: #ef4444; border: 1px solid #dc2626;"></div>
          <span>Numero No Capturado (Fallo)</span>
        </div>
      </div>

      <div class="panel-section">
        <h2>Leyenda de Conexiones</h2>
        <div class="legend-item">
          <div class="legend-line" style="background: #10b981;"></div>
          <span>same_draw (Aparece en el sorteo)</span>
        </div>
        <div class="legend-item">
          <div class="legend-line" style="background: #8b5cf6; height: 1px; border-bottom: 2px dashed #8b5cf6;"></div>
          <span>missed_from_played_set (Fallo de cobertura)</span>
        </div>
        <div class="legend-item">
          <div class="legend-line" style="background: #3b82f6;"></div>
          <span>captured_together (Aciertos conectados)</span>
        </div>
        <div class="legend-item">
          <div class="legend-line" style="background: #4b5563; height: 1px; border-bottom: 1px dotted #4b5563;"></div>
          <span>same_block (Mismo bloque)</span>
        </div>
      </div>
    </div>
  </div>

  <script>
    const elements = {{
      nodes: {json.dumps(nodes_js)},
      edges: {json.dumps(edges_js)}
    }};

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: [
        ...elements.nodes,
        ...elements.edges
      ],
      style: [
        {{
          selector: 'node',
          style: {{
            'label': 'data(label)',
            'color': '#fff',
            'font-size': '12px',
            'font-weight': 'bold',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#4b5563',
            'width': '34px',
            'height': '34px',
            'border-width': '2px',
            'border-color': '#1f2937'
          }}
        }},
        {{
          selector: 'node[roles]',
          style: {{
            'background-color': function(node) {{
              const roles = node.data('roles') || [];
              if (roles.includes('captured')) return '#8b5cf6';
              if (roles.includes('missed')) return '#ef4444';
              if (roles.includes('result')) return '#10b981';
              if (roles.includes('played')) return '#3b82f6';
              return '#4b5563';
            }},
            'border-color': function(node) {{
              const roles = node.data('roles') || [];
              if (roles.includes('captured')) return '#7c3aed';
              if (roles.includes('missed')) return '#dc2626';
              if (roles.includes('result')) return '#059669';
              if (roles.includes('played')) return '#2563eb';
              return '#111827';
            }}
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'width': 2,
            'line-color': '#4b5563',
            'target-arrow-shape': 'none',
            'curve-style': 'bezier',
            'opacity': 0.6
          }}
        }},
        {{
          selector: 'edge[type="same_draw"]',
          style: {{
            'line-color': '#10b981',
            'width': 3,
            'opacity': 0.8
          }}
        }},
        {{
          selector: 'edge[type="captured_together"]',
          style: {{
            'line-color': '#3b82f6',
            'width': 3,
            'opacity': 0.8
          }}
        }},
        {{
          selector: 'edge[type="missed_from_played_set"]',
          style: {{
            'line-color': '#ef4444',
            'line-style': 'dashed',
            'width': 2,
            'opacity': 0.9
          }}
        }},
        {{
          selector: 'edge[type="same_block"]',
          style: {{
            'line-color': '#374151',
            'line-style': 'dotted',
            'width': 1.5,
            'opacity': 0.4
          }}
        }},
        {{
          selector: 'node:selected',
          style: {{
            'border-width': '4px',
            'border-color': '#fbbf24',
            'width': '40px',
            'height': '40px'
          }}
        }},
        {{
          selector: 'edge:selected',
          style: {{
            'width': 5,
            'line-color': '#fbbf24',
            'opacity': 1.0
          }}
        }}
      ],
      layout: {{
        name: 'cose',
        nodeRepulsion: function( node ){{ return 2048; }},
        idealEdgeLength: function( edge ){{ return 64; }},
        animate: true,
        fit: true,
        padding: 40
      }}
    }});

    cy.on('tap', function(evt) {{
      const target = evt.target;
      const detailsDiv = document.getElementById('details-content');

      if (target === cy) {{
        detailsDiv.innerHTML = '<p style="color: var(--text-muted); font-style: italic;">Haz clic en un numero o una conexion para ver sus detalles analiticos.</p>';
        return;
      }}

      if (target.isNode()) {{
        const num = target.data('number');
        const block = target.data('block');
        const roles = target.data('roles') || [];

        let badgesHtml = roles.map(r => `<span class="badge badge-${{r}}">${{r}}</span>`).join(' ');

        detailsDiv.innerHTML = `
          <div class="detail-item">
            <div class="detail-label">Elemento</div>
            <div class="detail-value" style="font-size: 1.25rem; font-weight: bold; color: var(--accent);">Numero ${{num}}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Bloque de revision</div>
            <div class="detail-value"><code>${{block}}</code></div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Roles en el Analisis</div>
            <div style="margin-top: 4px;">${{badgesHtml}}</div>
          </div>
        `;
      }} else if (target.isEdge()) {{
        const type = target.data('type');
        const severity = target.data('severity');
        const evidence = target.data('evidence');
        const sourceNum = cy.getElementById(target.data('source')).data('number');
        const targetNum = cy.getElementById(target.data('target')).data('number');

        detailsDiv.innerHTML = `
          <div class="detail-item">
            <div class="detail-label">Conexion</div>
            <div class="detail-value" style="font-weight: bold;">${{sourceNum}} &harr; ${{targetNum}}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Tipo de Conexion</div>
            <div class="detail-value"><code>${{type}}</code></div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Severidad Estructural</div>
            <div class="detail-value" style="color: ${{severity > 2 ? '#ef4444' : '#fbbf24'}};">${{severity}} / 5</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Evidencia del Analisis</div>
            <div class="detail-value" style="font-size: 0.875rem; color: var(--text-muted); line-height: 1.4;">${{evidence}}</div>
          </div>
        `;
      }}
    }});
  </script>
</body>
</html>
"""
    validate_text(html_content)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def _write_historical_graph_html(graph_data: dict[str, Any], output_path: str | Path) -> Path:
    game = html.escape(str(graph_data.get("game", "revancha")))
    window = graph_data.get("window", 30)
    draws_count = graph_data.get("draws_count", 0)

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    candidates = graph_data.get("candidates", [])

    # Build Cytoscape elements
    max_freq = max((n.get("frequency", 1) for n in nodes), default=1)
    nodes_js = []
    for node in nodes:
        freq = node.get("frequency", 1)
        size = 24 + int(20 * freq / max(max_freq, 1))
        nodes_js.append({
            "data": {
                "id": str(node["number"]),
                "number": node["number"],
                "block": node.get("block", ""),
                "frequency": freq,
                "degree": node.get("degree", 0),
                "weighted_degree": node.get("weighted_degree", 0),
                "last_seen_draws": node.get("last_seen_draws", []),
                "label": str(node["number"]),
                "size": size,
            }
        })

    max_count = max((e.get("count", 1) for e in edges), default=1)
    edges_js = []
    for edge in edges:
        cnt = edge.get("count", 1)
        width = 1 + int(5 * cnt / max(max_count, 1))
        edges_js.append({
            "data": {
                "source": str(edge["source"]),
                "target": str(edge["target"]),
                "count": cnt,
                "draws": edge.get("draws", []),
                "last_seen_draw": edge.get("last_seen_draw", 0),
                "width": width,
            }
        })

    # Build fallback tables
    nodes_sorted = sorted(nodes, key=lambda n: n.get("frequency", 0), reverse=True)
    fallback_nodes_rows = "\n".join(
        f"<tr><td>{html.escape(str(n['number']))}</td>"
        f"<td>{html.escape(str(n.get('frequency', 0)))}</td>"
        f"<td>{html.escape(str(n.get('block', '')))}</td>"
        f"<td>{html.escape(str(n.get('degree', 0)))}</td>"
        f"<td>{html.escape(str(n.get('weighted_degree', 0)))}</td></tr>"
        for n in nodes_sorted[:30]
    )
    edges_sorted = sorted(edges, key=lambda e: e.get("count", 0), reverse=True)
    fallback_edges_rows = "\n".join(
        f"<tr><td>{html.escape(str(e['source']))}—{html.escape(str(e['target']))}</td>"
        f"<td>{html.escape(str(e.get('count', 0)))}</td>"
        f"<td>{html.escape(str(e.get('last_seen_draw', '')))}</td>"
        f"<td>{html.escape(str(e.get('draws', [])[:3]))}</td></tr>"
        for e in edges_sorted[:30]
    )

    candidates_json = json.dumps(candidates)

    html_content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Grafo historico de Revancha | MelateApp Lab</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --panel: #111827;
      --panel-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #f59e0b;
      --accent2: #10b981;
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    header {{
      background: var(--panel);
      border-bottom: 1px solid var(--panel-border);
      padding: 16px 24px;
      z-index: 10;
    }}
    h1 {{ margin: 0; font-size: 1.5rem; font-weight: 600; color: #fff; }}
    h1 span {{ color: var(--accent); }}
    .subtitle {{ font-size: 0.875rem; color: var(--text-muted); margin-top: 4px; }}
    .layout {{
      display: flex;
      flex: 1;
      position: relative;
      overflow: hidden;
    }}
    #cy {{
      flex: 1;
      height: 100%;
      background: #0f172a;
    }}
    #sidebar {{
      width: 380px;
      background: var(--panel);
      border-left: 1px solid var(--panel-border);
      padding: 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .panel-section {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 16px;
    }}
    h2 {{ margin: 0 0 12px 0; font-size: 1rem; font-weight: 600; color: #fff; border-bottom: 1px solid var(--panel-border); padding-bottom: 8px; }}
    .detail-item {{ margin-bottom: 12px; }}
    .detail-item:last-child {{ margin-bottom: 0; }}
    .detail-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
    .detail-value {{ font-size: 0.95rem; margin-top: 4px; font-weight: 500; }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      margin-right: 6px;
      margin-top: 6px;
      background: rgba(245, 158, 11, 0.2);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }}
    #fallback {{ display: none; padding: 24px; overflow-y: auto; }}
    #fallback table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
    #fallback th, #fallback td {{ padding: 8px 12px; border: 1px solid var(--panel-border); text-align: left; font-size: 0.85rem; }}
    #fallback th {{ background: var(--panel); color: var(--accent); }}
  </style>
</head>
<body>
  <header>
    <h1>Grafo historico de Revancha | <span>ultimos {window} sorteos</span></h1>
    <div class="subtitle">Coapariciones historicas entre numeros — {draws_count} sorteos analizados del juego {game}</div>
  </header>
  <div class="layout">
    <div id="cy"></div>
    <div id="sidebar">
      <div class="panel-section">
        <h2>Controles del Grafo</h2>
        <div class="control-group" style="margin-bottom: 12px;">
          <label for="min-cooccurrence" class="detail-label" style="display: block; margin-bottom: 4px;">Mostrar conexiones con mínimo coapariciones</label>
          <select id="min-cooccurrence" style="width: 100%; background: #1f2937; border: 1px solid var(--panel-border); color: #fff; padding: 6px; border-radius: 4px; font-family: var(--font);" onchange="updateGraph()">
            <option value="1">1+</option>
            <option value="2" selected>2+</option>
            <option value="3">3+</option>
            <option value="4">4+</option>
          </select>
        </div>
        <div class="control-group" style="margin-bottom: 12px;">
          <label style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; cursor: pointer; color: var(--text-muted);">
            <input type="checkbox" id="hide-isolated" onchange="updateGraph()" checked>
            <span>Ocultar números sin conexiones</span>
          </label>
        </div>
        <div class="control-group">
          <label for="resaltar-set" class="detail-label" style="display: block; margin-bottom: 4px;">Resaltar Set de Tesis</label>
          <select id="resaltar-set" style="width: 100%; background: #1f2937; border: 1px solid var(--panel-border); color: #fff; padding: 6px; border-radius: 4px; font-family: var(--font);" onchange="updateGraph()">
            <option value="none" selected>Ninguno</option>
          </select>
        </div>
      </div>

      <div class="panel-section">
        <h2>Detalle de Seleccion</h2>
        <div id="details-content">
          <p style="color: var(--text-muted); font-style: italic;">Haz clic en un numero o una conexion para ver detalles de coaparicion historica.</p>
        </div>
      </div>
      
      <div class="panel-section">
        <h2>Leyenda</h2>
        <div style="font-size:0.85rem; margin-bottom:8px;">
          <strong style="color:var(--accent);">Nodo grande</strong> = alta frecuencia en ventana
        </div>
        <div style="font-size:0.85rem; margin-bottom:8px;">
          <strong style="color:var(--accent2);">Arista gruesa</strong> = coaparicion frecuente
        </div>
        <div style="font-size:0.85rem; margin-bottom:8px;">
          <strong style="color:#a855f7;">Color Morado</strong> = Elementos del Set resaltado
        </div>
        <div style="font-size:0.85rem;">
          Ventana: ultimos <strong>{window}</strong> sorteos
        </div>
      </div>
    </div>
    <div id="fallback">
      <h2>Fallback: Tabla de Nodos (top 30 por frecuencia)</h2>
      <table>
        <tr><th>Numero</th><th>Frecuencia</th><th>Bloque</th><th>Degree</th><th>W. Degree</th></tr>
        {fallback_nodes_rows}
      </table>
      <h2>Fallback: Tabla de Aristas (top 30 por coapariciones)</h2>
      <table>
        <tr><th>Par</th><th>Coapariciones</th><th>Ultima vez</th><th>Sorteos</th></tr>
        {fallback_edges_rows}
      </table>
      <p style="color:var(--text-muted);">Ventana historica: ultimos {window} sorteos — {draws_count} sorteos de {game}</p>
    </div>
  </div>

  {_get_cytoscape_script()}
  <script>
    if (typeof cytoscape === 'undefined') {{
      document.getElementById('cy').style.display = 'none';
      document.getElementById('sidebar').style.display = 'none';
      document.getElementById('fallback').style.display = 'block';
    }} else {{
      const elements = {{
        nodes: {json.dumps(nodes_js)},
        edges: {json.dumps(edges_js)}
      }};

      const candidates = {candidates_json};

      // Populate sets dropdown dynamically
      const setSelect = document.getElementById('resaltar-set');
      candidates.forEach((cand, idx) => {{
        const option = document.createElement('option');
        option.value = String(idx);
        option.textContent = `Set ${{cand.letter || String.fromCharCode(65 + idx)}} (${{cand.classification}})`;
        setSelect.appendChild(option);
      }});

      const cy = cytoscape({{
        container: document.getElementById('cy'),
        elements: [
          ...elements.nodes,
          ...elements.edges
        ],
        style: [
          {{
            selector: 'node',
            style: {{
              'label': 'data(label)',
              'color': '#fff',
              'font-size': '11px',
              'font-weight': 'bold',
              'text-valign': 'center',
              'text-halign': 'center',
              'background-color': '#f59e0b',
              'width': 'data(size)',
              'height': 'data(size)',
              'border-width': '2px',
              'border-color': '#92400e',
              'transition-property': 'background-color, border-color, border-width, opacity',
              'transition-duration': '0.2s'
            }}
          }},
          {{
            selector: 'edge',
            style: {{
              'width': 'data(width)',
              'line-color': '#10b981',
              'target-arrow-shape': 'none',
              'curve-style': 'bezier',
              'opacity': 0.5,
              'transition-property': 'line-color, width, opacity',
              'transition-duration': '0.2s'
            }}
          }},
          {{
            selector: 'node:selected',
            style: {{
              'border-width': '4px',
              'border-color': '#fbbf24'
            }}
          }},
          {{
            selector: 'edge:selected',
            style: {{
              'line-color': '#fbbf24',
              'opacity': 1.0
            }}
          }},
          {{
            selector: '.dimmed',
            style: {{
              'opacity': 0.12
            }}
          }},
          {{
            selector: '.highlighted-node',
            style: {{
              'background-color': '#a855f7',
              'border-color': '#c084fc',
              'border-width': '4px',
              'opacity': 1.0
            }}
          }},
          {{
            selector: '.highlighted-edge',
            style: {{
              'line-color': '#a855f7',
              'opacity': 1.0,
              'width': function(edge) {{ return edge.data('width') + 2; }}
            }}
          }}
        ],
        layout: {{
          name: 'cose',
          nodeRepulsion: function( node ){{ return 4096; }},
          idealEdgeLength: function( edge ){{ return 80; }},
          animate: true,
          fit: true,
          padding: 40
        }}
      }});

      function showSetDetails(index) {{
        const cand = candidates[index];
        const letter = cand.letter || String.fromCharCode(65 + index);
        const detailsDiv = document.getElementById('details-content');

        let connectionsHtml = '';
        if (cand.pair_edges && cand.pair_edges.length > 0) {{
          connectionsHtml = cand.pair_edges.map(pe => 
            `<li><strong>${{pe.pair}}</strong>: coaparece ${{pe.count}} veces</li>`
          ).join('');
        }} else {{
          connectionsHtml = '<li>Ninguna conexión interna en la ventana</li>';
        }}

        let evidenceHtml = '';
        if (cand.evidence_draws && cand.evidence_draws.length > 0) {{
          evidenceHtml = cand.evidence_draws.map(d => `<code>${{d}}</code>`).join(', ');
        }} else {{
          evidenceHtml = 'Ninguna';
        }}

        detailsDiv.innerHTML = `
          <div class="detail-item" style="border-bottom: 1px solid var(--panel-border); padding-bottom: 8px; margin-bottom: 8px;">
            <div class="detail-label" style="color: #c084fc;">Detalles del Set</div>
            <div class="detail-value" style="font-size: 1.3rem; font-weight: bold; color: #fff;">Set ${{letter}}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Perfil</div>
            <div class="detail-value" style="color: var(--accent2); font-weight: 600;">${{cand.classification}}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Números del Set</div>
            <div class="detail-value" style="font-size: 1.1rem; font-weight: bold; letter-spacing: 1px; margin-top: 4px;">
              ${{cand.numbers.join(' ')}}
            </div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Soporte de Grafo Score</div>
            <div class="detail-value" style="font-size: 1.2rem; color: #f59e0b; font-weight: bold;">${{cand.graph_support_score}}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Conexiones Internas</div>
            <ul style="margin: 4px 0; padding-left: 16px; font-size: 0.85rem; line-height: 1.4;">
              ${{connectionsHtml}}
            </ul>
          </div>
          <div class="detail-item">
            <div class="detail-label">Evidencia Histórica (Sorteos)</div>
            <div class="detail-value" style="font-size: 0.85rem;">
              ${{evidenceHtml}}
            </div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Suma / Banda</div>
            <div class="detail-value">Suma: ${{cand.sum}} (${{cand.sum_band}})</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Firma de Bloques</div>
            <div class="detail-value"><code>${{cand.block_signature}}</code></div>
          </div>
        `;
      }}

      window.updateGraph = function() {{
        const minCount = parseInt(document.getElementById('min-cooccurrence').value);
        const hideIsolated = document.getElementById('hide-isolated').checked;
        const selectedSetIndex = document.getElementById('resaltar-set').value;

        let setNumbers = null;
        if (selectedSetIndex !== 'none') {{
          const setObj = candidates[parseInt(selectedSetIndex)];
          setNumbers = new Set(setObj.numbers);
        }}

        cy.batch(() => {{
          // Remove custom classes
          cy.elements().removeClass('dimmed highlighted-node highlighted-edge');

          // Apply minimum co-occurrence filter on edges
          cy.edges().forEach(e => {{
            const cnt = e.data('count');
            if (cnt < minCount) {{
              e.style('display', 'none');
            }} else {{
              e.style('display', 'element');
            }}
          }});

          // Handle isolated nodes hiding
          cy.nodes().forEach(n => {{
            if (hideIsolated) {{
              // Count how many visible edges connect to this node
              const connectedVisibleEdges = n.connectedEdges().filter(e => e.data('count') >= minCount);
              if (connectedVisibleEdges.length === 0) {{
                n.style('display', 'none');
              }} else {{
                n.style('display', 'element');
              }}
            }} else {{
              n.style('display', 'element');
            }}
          }});

          // Apply thesis set highlighting overlay
          if (selectedSetIndex !== 'none') {{
            // Dim everything
            cy.elements().addClass('dimmed');

            // Highlight nodes in the Set
            cy.nodes().forEach(n => {{
              const num = n.data('number');
              if (setNumbers.has(num)) {{
                n.removeClass('dimmed');
                n.addClass('highlighted-node');
              }}
            }});

            // Highlight internal edges in the Set
            cy.edges().forEach(e => {{
              const src = parseInt(e.data('source'));
              const tgt = parseInt(e.data('target'));
              const cnt = e.data('count');
              if (cnt >= minCount && setNumbers.has(src) && setNumbers.has(tgt)) {{
                e.removeClass('dimmed');
                e.addClass('highlighted-edge');
              }}
            }});
          }}
        }});

        if (selectedSetIndex !== 'none') {{
          showSetDetails(parseInt(selectedSetIndex));
        }} else {{
          const detailsDiv = document.getElementById('details-content');
          if (detailsDiv.innerHTML.includes('Detalles del Set')) {{
            detailsDiv.innerHTML = '<p style="color: var(--text-muted); font-style: italic;">Haz clic en un numero o una conexion para ver detalles de coaparicion historica.</p>';
          }}
        }}
      }};

      // Initial filter apply
      updateGraph();

      cy.on('tap', function(evt) {{
        const target = evt.target;
        const detailsDiv = document.getElementById('details-content');

        if (target === cy) {{
          detailsDiv.innerHTML = '<p style="color: var(--text-muted); font-style: italic;">Haz clic en un numero o una conexion para ver detalles de coaparicion historica.</p>';
          return;
        }}

        if (target.isNode()) {{
          const num = target.data('number');
          const block = target.data('block');
          const freq = target.data('frequency');
          const deg = target.data('degree');
          const wdeg = target.data('weighted_degree');
          const lastSeen = target.data('last_seen_draws') || [];

          // Find appearing sets
          const appearingSets = [];
          candidates.forEach((cand, idx) => {{
            if (cand.numbers.includes(num)) {{
              appearingSets.push(`Set ${{cand.letter || String.fromCharCode(65 + idx)}}`);
            }}
          }});
          const setsText = appearingSets.length > 0 ? appearingSets.join(', ') : 'Ninguno';

          // Find top connections in JS
          const nodeIdStr = String(num);
          const nodeEdges = elements.edges.filter(e => e.data.source === nodeIdStr || e.data.target === nodeIdStr);
          nodeEdges.sort((a, b) => b.data.count - a.data.count);
          const topEdges = nodeEdges.slice(0, 3);
          let topConnHtml = '';
          if (topEdges.length > 0) {{
            topConnHtml = topEdges.map(e => {{
              const peer = e.data.source === nodeIdStr ? e.data.target : e.data.source;
              const drawsSlice = (e.data.draws || []).slice(-3).reverse();
              return `<div style="font-size: 0.85rem; margin-bottom: 4px;">
                &bull; Con <strong>${{peer}}</strong>: coaparece ${{e.data.count}} veces 
                <span style="color: var(--text-muted); font-size: 0.75rem;">(Sorteos: ${{drawsSlice.join(', ')}})</span>
              </div>`;
            }}).join('');
          }} else {{
            topConnHtml = '<div style="font-size: 0.85rem; color: var(--text-muted); font-style: italic;">Ninguna conexión histórica registrada</div>';
          }}

          detailsDiv.innerHTML = `
            <div class="detail-item">
              <div class="detail-label">Numero</div>
              <div class="detail-value" style="font-size: 1.25rem; font-weight: bold; color: var(--accent);">${{num}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Frecuencia en ventana</div>
              <div class="detail-value">${{freq}} apariciones</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Bloque</div>
              <div class="detail-value"><code>${{block}}</code></div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Degree (conexiones unicas)</div>
              <div class="detail-value">${{deg}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Weighted Degree (coapariciones totales)</div>
              <div class="detail-value">${{wdeg}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Ultimas apariciones</div>
              <div class="detail-value">${{lastSeen.join(', ') || '-'}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Top Conexiones Historicas</div>
              <div style="margin-top: 4px;">${{topConnHtml}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Aparece en Tesis</div>
              <div class="detail-value" style="color: #c084fc; font-weight: bold;">${{setsText}}</div>
            </div>
          `;
        }} else if (target.isEdge()) {{
          const src = parseInt(target.data('source'));
          const tgt = parseInt(target.data('target'));
          const cnt = target.data('count');
          const draws = target.data('draws') || [];
          const lastSeen = target.data('last_seen_draw');

          // Find sets containing both numbers of this pair
          const appearingSets = [];
          candidates.forEach((cand, idx) => {{
            if (cand.numbers.includes(src) && cand.numbers.includes(tgt)) {{
              appearingSets.push(`Set ${{cand.letter || String.fromCharCode(65 + idx)}}`);
            }}
          }});
          const setsText = appearingSets.length > 0 ? appearingSets.join(', ') : 'Ninguno';

          detailsDiv.innerHTML = `
            <div class="detail-item">
              <div class="detail-label">Par</div>
              <div class="detail-value" style="font-weight: bold; font-size: 1.1rem; color: var(--accent2);">${{src}} &harr; ${{tgt}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Coapariciones historicas</div>
              <div class="detail-value" style="color: var(--accent); font-weight: bold;">${{cnt}} veces</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Ultimo sorteo con el par</div>
              <div class="detail-value">${{lastSeen}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Sorteos donde apareció el par</div>
              <div class="detail-value" style="font-size: 0.85rem; max-height: 80px; overflow-y: auto; line-height: 1.4;">${{draws.join(', ')}}</div>
            </div>
            <div class="detail-item">
              <div class="detail-label">Aparece en Tesis</div>
              <div class="detail-value" style="color: #c084fc; font-weight: bold;">${{setsText}}</div>
            </div>
          `;
        }}
      }});
    }}
  </script>
</body>
</html>
"""
    validate_text(html_content)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def write_history_dashboard_html(history_data: list[dict[str, Any]], output_path: str | Path) -> Path:
    from collections import Counter
    draws = [d["draw"] for d in history_data]
    sums = [d["sum"] for d in history_data]
    
    signatures_counts = Counter(d.get("block_signature", "unknown") for d in history_data)
    sig_labels = list(signatures_counts.keys())
    sig_values = list(signatures_counts.values())
    
    num_freqs = Counter()
    for d in history_data:
        num_freqs.update(d.get("numbers", []))
    
    num_labels = list(range(1, 57))
    num_values = [num_freqs.get(n, 0) for n in num_labels]
    
    html_content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard Historico Melate/Revancha | MelateApp Lab</title>
  {_get_chartjs_script()}
  <style>
    :root {{
      --bg: #0b0f19;
      --panel: #111827;
      --panel-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #10b981;
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
      min-height: 100vh;
    }}
    header {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 12px;
      padding: 20px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    h1 {{ margin: 0; font-size: 1.75rem; font-weight: 600; color: #fff; }}
    h1 span {{ color: var(--accent); }}
    .subtitle {{ font-size: 0.9rem; color: var(--text-muted); margin-top: 4px; }}
    .stats-summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }}
    .stat-card {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 10px;
      padding: 16px;
      text-align: center;
    }}
    .stat-label {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
    .stat-val {{ font-size: 1.75rem; font-weight: bold; color: #fff; margin-top: 8px; }}
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
    }}
    @media (min-width: 900px) {{
      .dashboard-grid {{
        grid-template-columns: 1fr 1fr;
      }}
      .full-width {{
        grid-column: span 2;
      }}
    }}
    .chart-card {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      height: 400px;
    }}
    .chart-card.tall {{
      height: 450px;
    }}
    .chart-title {{ font-size: 1.1rem; font-weight: 600; color: #fff; }}
    .chart-wrapper {{
      position: relative;
      flex: 1;
      width: 100%;
      height: 100%;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Dashboard de Analisis Historico</h1>
      <div class="subtitle">Exploracion interactiva de tendencias de sorteos acumulados</div>
    </div>
  </header>
  
  <div class="stats-summary">
    <div class="stat-card">
      <div class="stat-label">Sorteos Analizados</div>
      <div class="stat-val">{len(history_data)}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Banda de Suma Promedio</div>
      <div class="stat-val">{int(sum(sums)/len(sums)) if draws else 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Numeros Unicos Vistos</div>
      <div class="stat-val">{sum(1 for v in num_values if v > 0)} / 56</div>
    </div>
  </div>

  <div class="dashboard-grid">
    <div class="chart-card tall full-width">
      <div class="chart-title">Histograma y Frecuencia de Numeros (1 al 56)</div>
      <div class="chart-wrapper">
        <canvas id="freqChart"></canvas>
      </div>
    </div>

    <div class="chart-card">
      <div class="chart-title">Tendencia de Sumas por Sorteo</div>
      <div class="chart-wrapper">
        <canvas id="sumsChart"></canvas>
      </div>
    </div>

    <div class="chart-card">
      <div class="chart-title">Frecuencia de Firmas de Bloque</div>
      <div class="chart-wrapper">
        <canvas id="sigChart"></canvas>
      </div>
    </div>
  </div>

  <script>
    Chart.defaults.color = '#9ca3af';
    Chart.defaults.borderColor = '#1f2937';

    new Chart(document.getElementById('freqChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(num_labels)},
        datasets: [{{
          label: 'Apariciones',
          data: {json.dumps(num_values)},
          backgroundColor: '#10b981',
          hoverBackgroundColor: '#34d399',
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }}
        }},
        scales: {{
          y: {{ beginAtZero: true, grid: {{ color: '#1f2937' }} }},
          x: {{ grid: {{ display: false }} }}
        }}
      }}
    }});

    new Chart(document.getElementById('sumsChart'), {{
      type: 'line',
      data: {{
        labels: {json.dumps(draws)},
        datasets: [{{
          label: 'Suma de numeros',
          data: {json.dumps(sums)},
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.3,
          borderWidth: 2
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          y: {{ 
            grid: {{ color: '#1f2937' }},
            suggestedMin: 80,
            suggestedMax: 240
          }},
          x: {{ grid: {{ display: false }} }}
        }}
      }}
    }});

    new Chart(document.getElementById('sigChart'), {{
      type: 'doughnut',
      data: {{
        labels: {json.dumps(sig_labels)},
        datasets: [{{
          data: {json.dumps(sig_values)},
          backgroundColor: [
            '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#6b7280'
          ],
          borderWidth: 1,
          borderColor: '#111827'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'right' }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
    validate_text(html_content)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def write_consolidated_portfolio_report_html(
    portfolio: dict[str, Any],
    candidates: list[dict[str, Any]],
    redundancy_analysis: dict[str, Any],
    output_path: str | Path,
) -> Path:
    validate_output_json(portfolio)
    for c in candidates:
        validate_output_json(c)
    validate_output_json(redundancy_analysis)

    draw = portfolio["draw"]
    game = portfolio["game"]
    notes = portfolio.get("notes", "") or "Sin notas adicionales."
    created_at = portfolio.get("created_at", "")

    # Group candidates by classification
    by_class: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        cls = c["classification"]
        by_class.setdefault(cls, []).append(c)

    # Build candidates HTML cards
    candidates_cards_html = []
    for cls, cands in by_class.items():
        candidates_cards_html.append(f"""
        <div class="profile-group">
            <h3>{html.escape(cls)}</h3>
            <div class="cards-grid">
        """)
        for c in cands:
            letter = c.get("letter", "?")
            nums_str = " ".join(map(str, c["numbers"]))
            score = c.get("graph_support_score", 0)
            sig = c.get("block_signature", "")
            band = c.get("sum_band", "")
            sum_val = c.get("sum", 0)
            state = c.get("state", "Pendiente")

            bullets_html = "".join(f"<li>{html.escape(b)}</li>" for b in c.get("reason_bullets", []))

            # Connections details
            conn_html = ""
            if c.get("pair_edges"):
                conn_html = "<h4>Conexiones internas:</h4><ul>" + "".join(
                    f"<li>{html.escape(pe['pair'])} ({pe['count']} coapariciones)</li>" for pe in c["pair_edges"]
                ) + "</ul>"

            candidates_cards_html.append(f"""
                <div class="card state-{state.lower()}">
                    <div class="card-header">
                        <span class="card-letter">Set {html.escape(letter)}</span>
                        <span class="badge badge-{state.lower()}">{html.escape(state)}</span>
                    </div>
                    <div class="card-numbers">{html.escape(nums_str)}</div>
                    <div class="card-metrics">
                        <div class="card-metric">Soporte: <strong>{score}</strong></div>
                        <div class="card-metric">Firma: <code>{html.escape(sig)}</code></div>
                        <div class="card-metric">Suma: <strong>{sum_val}</strong> ({html.escape(band)})</div>
                    </div>
                    <div class="card-reasons">
                        <ul>{bullets_html}</ul>
                    </div>
                    {conn_html}
                </div>
            """)
        candidates_cards_html.append("</div></div>")

    candidates_html_section = "\n".join(candidates_cards_html)

    # Build redundancy alerts HTML
    alerts_html = []
    if redundancy_analysis["has_alerts"]:
        alerts_html.append("""
        <div class="alert-box alert-danger">
            <h3>⚠️ Alertas de Concentración y Redundancia Estructural</h3>
            <p>Se han identificado los siguientes riesgos de sobredimensión o redundancia en la cartera:</p>
            <ul>
        """)

        # Redundancies (shared numbers)
        for r in redundancy_analysis["redundancies"]:
            lvl = "danger" if r["level"] == "alta" else "warning"
            alerts_html.append(f"""
                <li class="alert-item alert-item-{lvl}">
                    <strong>Set {html.escape(r['set_a'])} vs Set {html.escape(r['set_b'])}</strong>:
                    Comparten {r['shared_count']} números ({html.escape(str(r['shared_numbers']))}).
                    Nivel: <span class="text-{lvl}">{html.escape(r['level'].upper())}</span>
                </li>
            """)

        # Number concentration
        for nc in redundancy_analysis["number_concentration"]:
            alerts_html.append(f"""
                <li class="alert-item alert-item-danger">
                    <strong>Concentración de número ({nc['number']})</strong>:
                    Aparece en el {nc['percentage']}% de los sets (límite 40%).
                </li>
            """)

        # Signature concentration
        for sc in redundancy_analysis["signature_concentration"]:
            alerts_html.append(f"""
                <li class="alert-item alert-item-danger">
                    <strong>Concentración de firma ({html.escape(sc['signature'])})</strong>:
                    Presente en el {sc['percentage']}% de los sets (límite 60%).
                </li>
            """)

        # Profile concentration
        for pc in redundancy_analysis["profile_concentration"]:
            alerts_html.append(f"""
                <li class="alert-item alert-item-danger">
                    <strong>Concentración de perfil ({html.escape(pc['profile'])})</strong>:
                    Presente en el {pc['percentage']}% de los sets (límite 60%).
                </li>
            """)

        # Block concentration
        for bc in redundancy_analysis["block_concentration"]:
            alerts_html.append(f"""
                <li class="alert-item alert-item-danger">
                    <strong>Concentración de bloque ({html.escape(bc['block'])})</strong>:
                    Acumula el {bc['percentage']}% de todas las apariciones de números (límite 35%).
                </li>
            """)

        alerts_html.append("</ul></div>")
    else:
        alerts_html.append("""
        <div class="alert-box alert-success">
            <h3>✅ Cartera Diversificada</h3>
            <p>La cartera cumple con todos los límites estructurales de redundancia y concentración (intersección, números, firmas, perfiles y bloques).</p>
        </div>
        """)

    alerts_html_section = "\n".join(alerts_html)

    html_content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reporte de Cartera de Tesis | MelateApp Lab</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --panel: #111827;
      --panel-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #f59e0b;
      --accent-success: #10b981;
      --accent-danger: #ef4444;
      --accent-warning: #f59e0b;
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      line-height: 1.6;
      padding: 32px 20px;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0; font-size: 1.8rem; color: #fff; }}
    h1 span {{ color: var(--accent); }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-top: 16px;
      border-top: 1px solid var(--panel-border);
      padding-top: 16px;
    }}
    .meta-item {{ font-size: 0.9rem; }}
    .meta-label {{ color: var(--text-muted); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
    .meta-value {{ font-weight: bold; margin-top: 4px; }}

    .alert-box {{
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;
    }}
    .alert-danger {{
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
    }}
    .alert-success {{
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #a7f3d0;
    }}
    .alert-box h3 {{ margin: 0 0 10px 0; font-size: 1.1rem; }}
    .alert-item {{ margin-bottom: 8px; font-size: 0.9rem; list-style-type: none; position: relative; padding-left: 20px; }}
    .alert-item::before {{
      content: "•";
      position: absolute;
      left: 0;
      font-size: 1.2rem;
    }}
    .alert-item-danger::before {{ color: var(--accent-danger); }}
    .alert-item-warning::before {{ color: var(--accent-warning); }}
    .text-danger {{ color: var(--accent-danger); font-weight: bold; }}
    .text-warning {{ color: var(--accent-warning); font-weight: bold; }}

    .profile-group {{
      margin-bottom: 32px;
    }}
    .profile-group h3 {{
      border-bottom: 2px solid var(--panel-border);
      padding-bottom: 8px;
      color: #fff;
      font-size: 1.2rem;
      margin-bottom: 16px;
    }}
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 20px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      transition: transform 0.2s, border-color 0.2s;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: #3b82f6;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .card-letter {{ font-weight: bold; color: #fff; font-size: 1.1rem; }}
    .badge {{
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: bold;
      text-transform: uppercase;
    }}
    .badge-pendiente {{ background: rgba(156, 163, 175, 0.2); color: #9ca3af; border: 1px solid rgba(156, 163, 175, 0.4); }}
    .badge-favorito {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); }}
    .badge-jugado {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.4); }}
    .badge-descartado {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }}
    .badge-revisado {{ background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); }}

    .card-numbers {{
      font-size: 1.5rem;
      font-weight: bold;
      letter-spacing: 2px;
      color: #fff;
      text-align: center;
      background: rgba(255,255,255,0.02);
      padding: 10px;
      border-radius: 6px;
      border: 1px solid rgba(255,255,255,0.05);
    }}
    .card-numbers:hover {{
      color: var(--accent);
    }}
    .card-metrics {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      font-size: 0.8rem;
      text-align: center;
    }}
    .card-metric {{
      background: rgba(255,255,255,0.03);
      padding: 6px;
      border-radius: 4px;
      color: var(--text-muted);
    }}
    .card-metric strong {{ color: #fff; }}
    .card-metric code {{ color: var(--accent); }}

    .card-reasons ul {{ margin: 0; padding-left: 16px; font-size: 0.85rem; color: var(--text-muted); }}
    .card h4 {{ margin: 8px 0 4px 0; font-size: 0.85rem; color: #fff; }}
    .card ul {{ margin: 0; padding-left: 16px; font-size: 0.8rem; color: var(--text-muted); }}

    footer {{
      margin-top: 48px;
      border-top: 1px solid var(--panel-border);
      padding-top: 20px;
      font-size: 0.8rem;
      color: var(--text-muted);
      text-align: center;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Reporte de Cartera de Tesis | <span>MelateApp Lab v1.0</span></h1>
      <div class="meta-grid">
        <div class="meta-item">
          <div class="meta-label">Juego / Tipo</div>
          <div class="meta-value">{html.escape(game.upper())}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Sorteo Objetivo</div>
          <div class="meta-value">{draw}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Fecha de Generación</div>
          <div class="meta-value">{html.escape(created_at)}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Notas de Cartera</div>
          <div class="meta-value">{html.escape(notes)}</div>
        </div>
      </div>
    </header>

    {alerts_html_section}

    {candidates_html_section}

    <footer>
      <p><strong>Nota Descriptiva del Laboratorio:</strong> Este reporte de candidatos y tesis tiene un propósito puramente analítico y descriptivo de relaciones observadas en la ventana histórica. La aplicación no realiza predicciones ni promete resultados de sorteos de la Lotería Nacional.</p>
    </footer>
  </main>
</body>
</html>
"""
    validate_text(html_content)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def write_backtest_report_html(backtest_results: dict[str, Any], output_path: str | Path) -> Path:
    validate_output_json(backtest_results)
    
    metrics = backtest_results.get("metrics", {})
    draws_data = backtest_results.get("results", [])
    game = backtest_results.get("game", "revancha")
    
    draws_labels = [str(r["draw"]) for r in draws_data]
    ranker_max_hits = [r["ranker_top_k_max_hits"] for r in draws_data]
    baseline_max_hits = [r["baseline_top_k_max_hits"] for r in draws_data]
    
    chart_js = f"""
    document.addEventListener("DOMContentLoaded", function() {{
      const ctx = document.getElementById("backtestChart").getContext("2d");
      new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: {json.dumps(draws_labels)},
          datasets: [
            {{
              label: 'Ranker Estructural (Top K Máx Aciertos)',
              data: {json.dumps(ranker_max_hits)},
              borderColor: '#f59e0b',
              backgroundColor: 'rgba(245, 158, 11, 0.1)',
              tension: 0.1,
              fill: true
            }},
            {{
              label: 'Baseline Aleatorio (Top K Máx Aciertos)',
              data: {json.dumps(baseline_max_hits)},
              borderColor: '#6b7280',
              backgroundColor: 'rgba(107, 114, 128, 0.1)',
              tension: 0.1,
              fill: true
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ labels: {{ color: '#f3f4f6' }} }}
          }},
          scales: {{
            x: {{ grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }} }},
            y: {{ grid: {{ color: '#1f2937' }}, ticks: {{ color: '#9ca3af' }}, min: 0, max: 6 }}
          }}
        }}
      }});
    }});
    """

    rows_html = []
    for r in draws_data:
        draw_id = r["draw"]
        nums_str = " ".join(map(str, r["numbers"]))
        r_max = r["ranker_top_k_max_hits"]
        b_max = r["baseline_top_k_max_hits"]
        
        r_class = "text-success" if r_max >= 3 else ("text-warning" if r_max > 0 else "")
        b_class = "text-success" if b_max >= 3 else ("text-warning" if b_max > 0 else "")
        
        rows_html.append(f"""
        <tr>
          <td>{draw_id}</td>
          <td><code>{nums_str}</code></td>
          <td class="{r_class}"><strong>{r_max}</strong></td>
          <td>{r["ranker_top_k_mean_hits"]:.2f}</td>
          <td class="{b_class}"><strong>{b_max}</strong></td>
          <td>{r["baseline_top_k_mean_hits"]:.2f}</td>
        </tr>
        """)
        
    table_body = "\n".join(rows_html)
    chart_script_tag = _get_chartjs_script()
    
    html_content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Laboratorio de Evaluación Retrospectiva | MelateApp</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --panel: #111827;
      --panel-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #f59e0b;
      --accent-success: #10b981;
      --accent-danger: #ef4444;
      --accent-warning: #f59e0b;
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      padding: 32px 20px;
      margin: 0;
      line-height: 1.6;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}
    header {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 24px;
    }}
    h1 {{ margin: 0; font-size: 1.8rem; }}
    h1 span {{ color: var(--accent); }}
    
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 16px;
      border-top: 1px solid var(--panel-border);
      padding-top: 16px;
    }}
    .meta-item {{
      background: rgba(255,255,255,0.01);
      padding: 12px;
      border-radius: 6px;
      border: 1px solid var(--panel-border);
    }}
    .meta-label {{ color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .meta-value {{ font-size: 1.2rem; font-weight: bold; margin-top: 4px; }}
    
    .chart-container {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 24px;
      position: relative;
      height: 400px;
      width: 100%;
    }}
    
    .table-container {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 24px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}
    th, td {{
      padding: 12px;
      border-bottom: 1px solid var(--panel-border);
    }}
    th {{
      color: var(--text-muted);
      font-size: 0.85rem;
      text-transform: uppercase;
    }}
    tr:hover td {{
      background: rgba(255,255,255,0.02);
    }}
    
    .text-success {{ color: var(--accent-success); }}
    .text-warning {{ color: var(--accent-warning); }}
    
    footer {{
      border-top: 1px solid var(--panel-border);
      padding-top: 20px;
      font-size: 0.8rem;
      color: var(--text-muted);
      text-align: center;
    }}
  </style>
  {chart_script_tag}
</head>
<body>
  <main>
    <header>
      <h1>Evaluación Retrospectiva | <span>ML Lab & Backtesting</span></h1>
      <p style="margin: 4px 0 0 0; color: var(--text-muted);">Análisis de desempeño de candidatos estructurales en sorteos históricos del juego {html.escape(game.upper())}</p>
      
      <div class="meta-grid">
        <div class="meta-item">
          <div class="meta-label">Sorteos Evaluados</div>
          <div class="meta-value">{metrics.get("draws_evaluated", 0)}</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Tasa Acumulada ≥ 3 Aciertos (Ranker)</div>
          <div class="meta-value text-success">{metrics.get("ranker_3plus_rate", 0)}%</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Tasa Acumulada ≥ 3 Aciertos (Baseline)</div>
          <div class="meta-value">{metrics.get("baseline_3plus_rate", 0)}%</div>
        </div>
        <div class="meta-item">
          <div class="meta-label">Promedio Máx Aciertos (Ranker vs Base)</div>
          <div class="meta-value" style="color: var(--accent);">{metrics.get("avg_ranker_top_k_max_hits", 0)} vs {metrics.get("avg_baseline_top_k_max_hits", 0)}</div>
        </div>
      </div>
    </header>

    <div class="chart-container">
      <canvas id="backtestChart" style="height:100%; width:100%;"></canvas>
    </div>

    <div class="table-container">
      <h3>Detalle de Simulaciones Walk-Forward</h3>
      <table>
        <thead>
          <tr>
            <th>Sorteo</th>
            <th>Resultado Real</th>
            <th>Máx Aciertos (Ranker)</th>
            <th>Media Aciertos (Ranker)</th>
            <th>Máx Aciertos (Baseline)</th>
            <th>Media Aciertos (Baseline)</th>
          </tr>
        </thead>
        <tbody>
          {table_body}
        </tbody>
      </table>
    </div>

    <footer>
      <p><strong>Nota Descriptiva del Laboratorio:</strong> Este reporte de backtesting y evaluación retrospectiva tiene un propósito puramente analítico y descriptivo de relaciones estructurales en la ventana histórica. La aplicación no realiza predicciones ni promete resultados de sorteos de la Lotería Nacional.</p>
    </footer>
  </main>
  <script>
    {chart_js}
  </script>
</body>
</html>
"""
    validate_text(html_content)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def write_candidates_catalog_html(
    candidates_features: list[dict[str, Any]],
    output_path: str | Path,
    game: str = "revancha",
) -> Path:
    validate_output_json(candidates_features)
    
    rows_html = []
    for cand in candidates_features:
        rank = cand.get("rank", 0)
        nums_str = " ".join(map(str, cand["numbers"]))
        score = cand.get("rank_score", 0.0)
        sig = cand.get("block_signature", "")
        sum_val = cand.get("sum", 0)
        band = cand.get("sum_band", "")
        freq_m = cand.get("frequency_mean", 0.0)
        w_deg_m = cand.get("weighted_degree_mean", 0.0)
        div = cand.get("diversity_score", 0)
        exact = "Sí" if cand.get("historical_exact_match") else "No"
        
        exact_class = "text-danger" if cand.get("historical_exact_match") else ""
        
        rows_html.append(f"""
        <tr>
          <td><strong>#{rank}</strong></td>
          <td><code style="font-size: 1.1rem; color: #fff;">{nums_str}</code></td>
          <td><strong>{score:.2f}</strong></td>
          <td><code>{sig}</code></td>
          <td>{sum_val} ({band})</td>
          <td>{freq_m:.2f}</td>
          <td>{w_deg_m:.2f}</td>
          <td>{div}</td>
          <td class="{exact_class}">{exact}</td>
        </tr>
        """)
        
    table_body = "\n".join(rows_html)
    
    html_content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Catálogo de Candidatos Estructurales | MelateApp</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --panel: #111827;
      --panel-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #f59e0b;
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      padding: 32px 20px;
      margin: 0;
      line-height: 1.6;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}
    header {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 24px;
    }}
    h1 {{ margin: 0; font-size: 1.8rem; }}
    h1 span {{ color: var(--accent); }}
    
    .table-container {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 8px;
      padding: 24px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}
    th, td {{
      padding: 12px;
      border-bottom: 1px solid var(--panel-border);
    }}
    th {{
      color: var(--text-muted);
      font-size: 0.85rem;
      text-transform: uppercase;
    }}
    tr:hover td {{
      background: rgba(255,255,255,0.02);
    }}
    .text-danger {{ color: #ef4444; font-weight: bold; }}
    
    footer {{
      border-top: 1px solid var(--panel-border);
      padding-top: 20px;
      font-size: 0.8rem;
      color: var(--text-muted);
      text-align: center;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Catálogo de Candidatos Estructurales | <span>MelateApp Lab</span></h1>
      <p style="margin: 4px 0 0 0; color: var(--text-muted);">Candidatos descriptivos ordenados por puntuación estructural para el juego {html.escape(game.upper())}</p>
    </header>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Rango</th>
            <th>Combinación</th>
            <th>Puntuación</th>
            <th>Firma</th>
            <th>Suma</th>
            <th>Frec. Media</th>
            <th>Grado Ponderado Medio</th>
            <th>Bloques Ocupados</th>
            <th>Exact Match Histórico</th>
          </tr>
        </thead>
        <tbody>
          {table_body}
        </tbody>
      </table>
    </div>

    <footer>
      <p><strong>Nota Descriptiva del Laboratorio:</strong> Este catálogo tiene un propósito puramente analítico y descriptivo de relaciones estructurales en la ventana histórica. La aplicación no realiza predicciones ni promete resultados de sorteos de la Lotería Nacional.</p>
    </footer>
  </main>
</body>
</html>
"""
    validate_text(html_content)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path

