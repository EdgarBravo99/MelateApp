from melate_app_lab.graph_optimizer import (
    build_graph_stats,
    select_missed_played_relations,
    severity_for_edge,
    summarize_edges,
)


def test_select_missed_played_relations_uses_limited_candidate_sets():
    relations = select_missed_played_relations(
        missed=[2, 22],
        played_numbers=[7, 9, 18, 23, 29, 30, 52],
        captured=[18, 52],
        repeated_anchors=[7, 29, 30],
    )

    assert relations == [
        (2, 7, ["repeated_anchor", "same_block"]),
        (2, 9, ["same_block"]),
        (2, 18, ["captured"]),
        (2, 29, ["repeated_anchor"]),
        (2, 30, ["repeated_anchor"]),
        (2, 52, ["captured"]),
        (22, 7, ["repeated_anchor"]),
        (22, 18, ["captured"]),
        (22, 23, ["same_block"]),
        (22, 29, ["repeated_anchor", "same_block"]),
        (22, 30, ["repeated_anchor", "same_block"]),
        (22, 52, ["captured"]),
    ]


def test_edge_summary_counts_type_and_severity():
    edges = [
        {"type": "same_draw", "severity": severity_for_edge("same_draw")},
        {"type": "missed_from_played_set", "severity": severity_for_edge("missed_from_played_set")},
        {"type": "captured_together", "severity": severity_for_edge("captured_together")},
    ]

    assert summarize_edges(edges) == {
        "total_edges": 3,
        "by_type": {"captured_together": 1, "missed_from_played_set": 1, "same_draw": 1},
        "by_severity": {"concentration": 1, "info": 1, "review": 1},
    }


def test_graph_stats_counts_current_output_shape():
    nodes = [{"id": "n2"}, {"id": "n7"}]
    edges = [{"type": "same_draw"}, {"type": "missed_from_played_set"}]
    missed_relations = [(2, 7, ["same_block"])]

    assert build_graph_stats(nodes, edges, [2, 18], [7, 18], [18], [2], missed_relations) == {
        "node_count": 2,
        "edge_count": 2,
        "result_count": 2,
        "played_unique_count": 2,
        "captured_count": 1,
        "missed_count": 1,
        "missed_from_played_set_count": 1,
    }
