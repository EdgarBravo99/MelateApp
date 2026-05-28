import json

from melate_app_lab.relation_graph import build_relation_graph, export_relation_graph


def test_build_relation_graph_contains_fixture_nodes_and_edges(tmp_path):
    graph = build_relation_graph(4218, [2, 18, 22, 38, 51, 52])
    node_numbers = {node["number"] for node in graph["nodes"]}
    edge_types = {edge["type"] for edge in graph["edges"]}

    assert {2, 18, 22, 38, 51, 52} <= node_numbers
    assert "same_draw" in edge_types
    assert any(
        edge["type"] == "high_block_pair" and set(edge["numbers"]) == {51, 52}
        for edge in graph["edges"]
    )

    output_path = tmp_path / "graph.json"
    export_relation_graph(graph, output_path)
    assert json.loads(output_path.read_text(encoding="utf-8"))["metadata"]["draw"] == 4218
