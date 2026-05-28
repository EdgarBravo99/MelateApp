from melate_app_lab.historical_analysis import (
    build_history_review_thesis,
    compare_trace_to_history,
    detect_recurrent_structures,
    summarize_history,
)
from melate_app_lab.importers import parse_draw_csv


def test_summarize_history_counts_high_tail_and_signature():
    history = parse_draw_csv("data/samples/revancha_4218.csv")

    summary = summarize_history(history)

    assert summary["draw_count"] == 1
    assert summary["sum_bands"]["high_tail"] == 1
    assert summary["block_signatures"]["1-1-1-1-2"] == 1
    assert summary["block_presence_signatures"]["1-1-1-1-1"] == 1
    assert summary["review_default"]["mode"] == "review_default"


def test_compare_trace_to_history_counts_matching_structures():
    history = parse_draw_csv("data/samples/revancha_4218.csv")

    comparison = compare_trace_to_history(history[0], history)

    assert comparison["matches"] == {
        "same_sum_band": 1,
        "same_block_signature": 1,
        "same_block_presence_signature": 1,
    }


def test_detect_recurrent_structures_returns_guardrailed_notes():
    history = parse_draw_csv("data/samples/revancha_4218.csv")

    structures = detect_recurrent_structures(history)

    assert structures["top_sum_bands"][0] == {"value": "high_tail", "count": 1}
    assert structures["review_default"]["mode"] == "review_default"


def test_build_history_review_thesis_returns_review_default_notes():
    history = parse_draw_csv("data/samples/revancha_4218.csv")

    thesis = build_history_review_thesis(history[0], history)

    assert thesis["review_default"]["mode"] == "review_default"
    assert "huella" in thesis["review_default"]["notes_es"]

