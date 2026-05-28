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
