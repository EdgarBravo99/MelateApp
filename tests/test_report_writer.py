import json

from melate_app_lab.evaluator_brain import brain_review
from melate_app_lab.guardrails import validate_text
from melate_app_lab.report_writer import write_csv_summary, write_html_report, write_json_report, write_graph_html_report, write_history_dashboard_html
from melate_app_lab.relation_graph import build_relation_graph, build_historical_relation_graph


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
    assert "Grafo postmortem" in graph_html
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


def _make_history(count=30, game="revancha"):
    """Generate a synthetic history list."""
    import random
    rng = random.Random(42)
    records = []
    for i in range(count):
        nums = sorted(rng.sample(range(1, 57), 6))
        records.append({
            "game": game,
            "draw": 4200 + i,
            "date": f"2025-01-{(i % 28) + 1:02d}",
            "numbers": nums,
            "sum": sum(nums),
            "sum_band": "mid_band",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1",
        })
    return records


def test_build_historical_relation_graph_basic():
    history = _make_history(10)
    graph = build_historical_relation_graph(history, window=10, game="revancha")
    assert graph["mode"] == "historical"
    assert graph["game"] == "revancha"
    assert graph["window"] == 10
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
    assert graph["draws_count"] == 10
    for node in graph["nodes"]:
        assert "frequency" in node
        assert "degree" in node
        assert "weighted_degree" in node
        assert "block" in node
    for edge in graph["edges"]:
        assert edge["type"] == "historical_cooccurrence"
        assert "count" in edge
        assert "draws" in edge


def test_historical_graph_window_limits():
    history = _make_history(50)
    graph_30 = build_historical_relation_graph(history, window=30, game="revancha")
    graph_10 = build_historical_relation_graph(history, window=10, game="revancha")
    assert graph_30["draws_count"] == 30
    assert graph_10["draws_count"] == 10
    # More draws should generally mean more or equal nodes/edges
    assert len(graph_30["nodes"]) >= len(graph_10["nodes"])


def test_historical_graph_edge_count_accumulates():
    # Two draws share the same pair -> edge count should be 2
    history = [
        {"game": "revancha", "draw": 1, "numbers": [1, 2, 3, 4, 5, 6]},
        {"game": "revancha", "draw": 2, "numbers": [1, 2, 10, 20, 30, 40]},
    ]
    graph = build_historical_relation_graph(history, window=10, game="revancha")
    pair_12 = [e for e in graph["edges"] if {int(e["source"]), int(e["target"])} == {1, 2}]
    assert len(pair_12) == 1
    assert pair_12[0]["count"] == 2
    assert sorted(pair_12[0]["draws"]) == [1, 2]


def test_historical_graph_node_frequency():
    history = [
        {"game": "revancha", "draw": 1, "numbers": [5, 10, 15, 20, 25, 30]},
        {"game": "revancha", "draw": 2, "numbers": [5, 11, 16, 21, 26, 31]},
        {"game": "revancha", "draw": 3, "numbers": [5, 12, 17, 22, 27, 32]},
    ]
    graph = build_historical_relation_graph(history, window=10, game="revancha")
    node_5 = [n for n in graph["nodes"] if n["number"] == 5]
    assert len(node_5) == 1
    assert node_5[0]["frequency"] == 3


def test_historical_graph_filters_by_game():
    history = [
        {"game": "revancha", "draw": 1, "numbers": [1, 2, 3, 4, 5, 6]},
        {"game": "melate", "draw": 2, "numbers": [10, 20, 30, 40, 50, 56]},
    ]
    graph = build_historical_relation_graph(history, window=10, game="revancha")
    assert graph["draws_count"] == 1
    numbers_in_graph = {n["number"] for n in graph["nodes"]}
    assert 10 not in numbers_in_graph


def test_write_historical_graph_html(tmp_path):
    history = _make_history(30)
    graph = build_historical_relation_graph(history, window=30, game="revancha")
    
    # Attach candidates to test JSON embedding
    graph["candidates"] = [
        {
            "numbers": [1, 2, 3, 4, 5, 6],
            "classification": "Balance por bloques",
            "reason_bullets": ["test"],
            "pair_edges": [{"pair": "1—2", "count": 2, "draws": [1, 2]}],
            "graph_support_score": 2,
            "relation_count": 1,
            "strongest_pairs": ["1—2"],
            "evidence_draws": [2, 1],
            "relation_window": 30,
        }
    ]

    html_path = tmp_path / "historical_graph.html"
    write_graph_html_report(graph, html_path)
    content = html_path.read_text(encoding="utf-8")
    assert "Grafo historico de Revancha" in content
    assert "ultimos 30 sorteos" in content
    assert "cytoscape" in content
    assert "fallback" in content.lower()
    
    # Assert new UX improvements exist in HTML
    assert "min-cooccurrence" in content
    assert "resaltar-set" in content
    assert "hide-isolated" in content
    assert "candidates = [" in content
    
    validate_text(content)


def test_write_consolidated_portfolio_report_html(tmp_path):
    from melate_app_lab.report_writer import write_consolidated_portfolio_report_html
    from melate_app_lab.number_utils import analyze_portfolio_redundancy

    portfolio = {
        "id": 1,
        "draw": 4220,
        "game": "revancha",
        "notes": "Test notes",
        "created_at": "2026-05-29",
    }
    candidates = [
        {
            "letter": "A",
            "numbers": [1, 2, 3, 4, 5, 16],
            "classification": "Balance por bloques",
            "sum": 31,
            "sum_band": "low_band",
            "block_signature": "5-1-0-0-0",
            "graph_support_score": 10,
            "reason_bullets": ["cubre bloques", "suma adecuada"],
            "pair_edges": [{"pair": "1—2", "count": 2}],
            "state": "Pendiente",
        }
    ]
    redundancy = analyze_portfolio_redundancy(candidates)

    html_path = tmp_path / "portfolio_report.html"
    write_consolidated_portfolio_report_html(portfolio, candidates, redundancy, html_path)

    content = html_path.read_text(encoding="utf-8")
    assert "Reporte de Cartera de Tesis" in content
    assert "MelateApp Lab v1.0" in content
    assert "REVANCHA" in content
    assert "4220" in content
    assert "Balance por bloques" in content
    assert "Set A" in content
