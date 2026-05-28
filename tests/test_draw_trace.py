from melate_app_lab.draw_trace import trace_draw


def test_trace_draw_returns_required_fixture_trace():
    trace = trace_draw(4218, [2, 18, 22, 38, 51, 52])

    assert trace["draw"] == 4218
    assert trace["numbers"] == [2, 18, 22, 38, 51, 52]
    assert trace["sum"] == 183
    assert trace["sum_band"] == "high_tail"
    assert trace["block_signature"] == "1-1-1-1-2"
    assert trace["block_presence_signature"] == "1-1-1-1-1"
    assert "huella" in trace["trace_es"].lower()
    assert "tesis de revisión" in trace["next_review_thesis_es"].lower()
