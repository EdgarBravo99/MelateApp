import pytest

from melate_app_lab.thesis_memory import (
    load_cycle_notes,
    load_recent_theses,
    remember_cycle_note,
    remember_review_thesis,
    summarize_audit_patterns,
)


def test_remember_review_thesis_round_trip_for_draw_4218(tmp_path):
    db_path = tmp_path / "data" / "memory.sqlite"

    remember_review_thesis(
        db_path,
        4218,
        "Tesis de revision: la huella 2-18-22-38-51-52 pide auditar bloques altos.",
    )

    theses = load_recent_theses(db_path)
    assert theses == [
        {
            "draw": 4218,
            "thesis": "Tesis de revision: la huella 2-18-22-38-51-52 pide auditar bloques altos.",
            "created_at": theses[0]["created_at"],
        }
    ]


def test_remember_cycle_note_round_trip_for_draw_4218(tmp_path):
    db_path = tmp_path / "data" / "memory.sqlite"

    remember_cycle_note(
        db_path,
        4218,
        "Nota de ciclo: revisar distancia entre pares bajos y cierre alto.",
    )

    notes = load_cycle_notes(db_path)
    assert notes == [
        {
            "draw": 4218,
            "note": "Nota de ciclo: revisar distancia entre pares bajos y cierre alto.",
            "created_at": notes[0]["created_at"],
        }
    ]


def test_summarize_audit_patterns_counts_local_memory(tmp_path):
    db_path = tmp_path / "data" / "memory.sqlite"
    remember_review_thesis(db_path, 4218, "Tesis de revision: auditar bloques altos.")
    remember_cycle_note(db_path, 4218, "Nota de ciclo: revisar pares bajos.")
    remember_cycle_note(db_path, 4219, "Nota de ciclo: revisar pares bajos.")

    summary = summarize_audit_patterns(db_path)

    assert summary["total_theses"] == 1
    assert summary["total_cycle_notes"] == 2
    assert summary["draws"] == [4219, 4218]
    assert summary["patterns"] == [
        {"kind": "cycle_note", "draw": 4219, "text": "Nota de ciclo: revisar pares bajos."},
        {"kind": "cycle_note", "draw": 4218, "text": "Nota de ciclo: revisar pares bajos."},
        {"kind": "review_thesis", "draw": 4218, "text": "Tesis de revision: auditar bloques altos."},
    ]


@pytest.mark.parametrize(
    ("writer", "payload"),
    [
        (remember_review_thesis, "tesis con " + "proba" + "bilidad prohibida"),
        (remember_cycle_note, "nota con " + "gan" + "ador prohibido"),
    ],
)
def test_memory_writers_reject_guardrail_violations(tmp_path, writer, payload):
    db_path = tmp_path / "data" / "memory.sqlite"

    with pytest.raises(ValueError):
        writer(db_path, 4218, payload)


def test_memory_rejects_paths_outside_data(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    with pytest.raises(ValueError):
        remember_review_thesis(db_path, 4218, "Tesis de revision valida.")


def test_portfolio_and_candidates_crud_round_trip(tmp_path):
    from melate_app_lab.thesis_memory import (
        save_thesis_portfolio,
        load_thesis_portfolios,
        load_thesis_candidates,
        update_candidate_state,
        update_candidate_review_result,
    )
    db_path = tmp_path / "data" / "memory.sqlite"

    candidates = [
        {
            "numbers": [1, 2, 3, 4, 5, 6],
            "classification": "Balance por bloques",
            "sum": 21,
            "sum_band": "low_band",
            "block_signature": "6-0-0-0-0",
            "graph_support_score": 5,
            "pair_edges": [{"pair": "1—2", "count": 2, "draws": [123, 124]}],
            "evidence_draws": [123, 124],
        },
        {
            "numbers": [10, 20, 30, 40, 50, 56],
            "classification": "Contraste / cobertura",
            "sum": 206,
            "sum_band": "high_tail",
            "block_signature": "1-1-1-1-2",
            "graph_support_score": 1,
            "pair_edges": [],
            "evidence_draws": [],
        }
    ]

    # Save
    pid = save_thesis_portfolio(
        db_path, draw=4220, game="revancha", candidates=candidates, notes="Test portfolio notes"
    )
    assert pid > 0

    # Load portfolio
    ports = load_thesis_portfolios(db_path)
    assert len(ports) == 1
    assert ports[0]["id"] == pid
    assert ports[0]["draw"] == 4220
    assert ports[0]["game"] == "revancha"
    assert ports[0]["notes"] == "Test portfolio notes"

    # Load candidates
    cands = load_thesis_candidates(db_path, pid)
    assert len(cands) == 2
    # Sorted by graph_support_score desc
    assert cands[0]["numbers"] == [1, 2, 3, 4, 5, 6]
    assert cands[0]["graph_support_score"] == 5
    assert cands[0]["state"] == "Pendiente"
    assert cands[0]["pair_edges"] == [{"pair": "1—2", "count": 2, "draws": [123, 124]}]
    assert cands[0]["evidence_draws"] == [123, 124]

    assert cands[1]["numbers"] == [10, 20, 30, 40, 50, 56]
    assert cands[1]["graph_support_score"] == 1
    assert cands[1]["state"] == "Pendiente"
    assert cands[1]["pair_edges"] == []

    # Update candidate state
    cand_id = cands[0]["id"]
    update_candidate_state(db_path, cand_id, "Favorito")

    # Reload and assert
    cands_updated = load_thesis_candidates(db_path, pid)
    assert cands_updated[0]["state"] == "Favorito"

    # Test invalid state
    with pytest.raises(ValueError):
        update_candidate_state(db_path, cand_id, "InvalidState")

    # Update review result
    update_candidate_review_result(
        db_path, cand_id, result_numbers=[1, 2, 3, 10, 11, 12], hits_count=3
    )
    cands_reviewed = load_thesis_candidates(db_path, pid)
    assert cands_reviewed[0]["state"] == "Revisado"
    assert cands_reviewed[0]["result_numbers"] == [1, 2, 3, 10, 11, 12]
    assert cands_reviewed[0]["hits_count"] == 3

