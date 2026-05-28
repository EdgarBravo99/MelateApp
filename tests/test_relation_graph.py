import json

from melate_app_lab.relation_graph import build_relation_graph, export_relation_graph
from tests.conftest import DRAW, PLAYED, RESULT


def test_build_relation_graph_contains_fixture_nodes_and_edges(tmp_path):
    graph = build_relation_graph(DRAW, RESULT, PLAYED)
    node_numbers = {node["number"] for node in graph["nodes"]}
    edge_types = {edge["type"] for edge in graph["edges"]}

    assert {2, 18, 22, 38, 51, 52} <= node_numbers
    assert "same_draw" in edge_types
    assert any(
        edge["type"] == "high_block_pair" and set(edge["numbers"]) == {51, 52}
        for edge in graph["edges"]
    )
    assert any(
        edge["type"] == "adjacent_high_pair" and set(edge["numbers"]) == {51, 52}
        for edge in graph["edges"]
    )
    assert any(
        edge["type"] == "captured_together" and set(edge["numbers"]) == {18, 52}
        for edge in graph["edges"]
    )
    assert "edge_summary" in graph
    assert "graph_stats" in graph

    output_path = tmp_path / "graph.json"
    export_relation_graph(graph, output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["metadata"]["draw"] == DRAW
    assert saved["metadata"]["review_mode"] == "review_default"


def test_relation_graph_stats_and_summary_for_fixture():
    graph = build_relation_graph(DRAW, RESULT, PLAYED)

    assert graph["graph_stats"] == {
        "node_count": 22,
        "edge_count": 58,
        "result_count": 6,
        "played_unique_count": 18,
        "captured_count": 2,
        "missed_count": 4,
        "missed_from_played_set_count": 33,
    }
    assert graph["edge_summary"]["total_edges"] == len(graph["edges"])
    assert graph["edge_summary"]["by_type"]["missed_from_played_set"] == 33
    assert graph["edge_summary"]["by_severity"]["concentration"] == 35


def test_missed_edges_do_not_expand_to_full_played_cross_product():
    graph = build_relation_graph(DRAW, RESULT, PLAYED)
    missed_edges = [edge for edge in graph["edges"] if edge["type"] == "missed_from_played_set"]
    full_cross_product = graph["graph_stats"]["missed_count"] * graph["graph_stats"]["played_unique_count"]

    assert len(missed_edges) == 33
    assert len(missed_edges) < full_cross_product
    assert len(graph["edges"]) < 80
    assert {edge["severity"] for edge in graph["edges"]} == {"info", "review", "concentration"}
