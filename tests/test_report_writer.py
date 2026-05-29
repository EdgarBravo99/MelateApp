import json

from melate_app_lab.evaluator_brain import brain_review
from melate_app_lab.guardrails import validate_text
from melate_app_lab.report_writer import write_csv_summary, write_html_report, write_json_report, write_graph_html_report, write_history_dashboard_html
from melate_app_lab.relation_graph import build_relation_graph


RESULT = [2, 18, 22, 38, 51, 52]
PLAYED = [
    [7, 15, 29, 41, 42, 48],
    [7, 16, 18, 23, 29, 39],
    [9, 13, 18, 30, 45, 52],
    [7, 15, 20, 30, 36, 53],
]


def test_write_reports(tmp_path):
    report = brain_review(4218, RESULT, PLAYED)
    json_path = tmp_path / "postmortem_4218.json"
    html_path = tmp_path / "postmortem_4218.html"
    csv_path = tmp_path / "postmortem_4218.csv"

    write_json_report(report, json_path)
    write_html_report(report, html_path)
    write_csv_summary(report, csv_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["draw"] == 4218
    html = html_path.read_text(encoding="utf-8")
    assert "Sorteo 4218" in html
    assert "Resumen ejecutivo" in html
    assert "Concentración de anclas" in html
    assert "Cobertura estructural" in html
    assert "Grafo resumido" in html
    assert "18" in html
    assert "52" in html
    assert validate_text(html) == html
    assert csv_path.read_text(encoding="utf-8").startswith("draw,sum,sum_band")


def test_write_visual_reports(tmp_path):
    # Test graph visualization
    graph = build_relation_graph(4218, RESULT, PLAYED)
    graph_html_path = tmp_path / "relation_graph_4218.html"
    write_graph_html_report(graph, graph_html_path)
    graph_html = graph_html_path.read_text(encoding="utf-8")
    assert "Grafo de Relaciones" in graph_html
    assert "cytoscape" in graph_html
    assert "n2" in graph_html  # element ID check

    # Test dashboard visualization
    history_data = [
        {
            "draw": 4218,
            "numbers": RESULT,
            "sum": sum(RESULT),
            "sum_band": "high_tail",
            "block_signature": "1-1-1-1-2"
        }
    ]
    dashboard_html_path = tmp_path / "history_dashboard.html"
    write_history_dashboard_html(history_data, dashboard_html_path)
    dashboard_html = dashboard_html_path.read_text(encoding="utf-8")
    assert "Dashboard de Analisis Historico" in dashboard_html
    assert "chart.js" in dashboard_html

