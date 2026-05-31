from __future__ import annotations

import json
import pytest
from melate_app_lab.manual_verifier import (
    parse_manual_combinations,
    verify_manual_combinations,
    save_manual_portfolio,
)
from melate_app_lab.memory import DEFAULT_DB_PATH

def test_parse_manual_combinations():
    # Valid input with label and commas/spaces
    text = "A: 1, 2, 3, 4, 5, 6\nB: 7 8 9 10 11 12"
    parsed = parse_manual_combinations(text)
    assert parsed["success"] is True
    assert len(parsed["candidates"]) == 2
    assert parsed["candidates"][0]["label"] == "A"
    assert parsed["candidates"][0]["numbers"] == [1, 2, 3, 4, 5, 6]
    assert parsed["candidates"][1]["label"] == "B"
    assert parsed["candidates"][1]["numbers"] == [7, 8, 9, 10, 11, 12]

    # Invalid input
    text_invalid = "1, 2, 3\nC: 1 2 3 4 5 57\nD: 1 2 3 4 5 5"
    parsed_invalid = parse_manual_combinations(text_invalid)
    assert parsed_invalid["success"] is False
    assert len(parsed_invalid["errors"]) == 3

def test_verify_manual_combinations(tmp_path):
    db_dir = tmp_path / "data"
    db_dir.mkdir()
    db_file = db_dir / "test_memory.sqlite"
    # Set up test database with historical draws
    from melate_app_lab.memory import init_db
    from melate_app_lab.thesis_memory import save_thesis_portfolio
    from melate_app_lab.historical_store import insert_draw_record, _connect
    init_db(db_file)
    
    conn = _connect(db_file)
    try:
        # Insert 35 draws so we satisfy prior history requirement (at least 30)
        for i in range(1, 40):
            insert_draw_record(conn, {
                "game": "revancha",
                "draw": i,
                "date": "2026-05-29",
                "numbers": [1, 2, 3, 4, 5, i % 50 + 6],
                "sum": 15 + (i % 50 + 6),
                "sum_band": "low_band",
                "block_signature": "1-1-1-1-2",
            }, commit=True, ensure_schema=True)
    finally:
        conn.close()

    text = "A: 1, 2, 3, 4, 5, 6\nB: 10, 11, 12, 13, 14, 15"
    res = verify_manual_combinations(
        manual_text=text,
        game="revancha",
        draw=40,
        compare_against_generated=True,
        db_path=db_file,
    )
    
    assert res["success"] is True
    assert len(res["manual_candidates"]) == 2
    assert "manual_portfolio_metrics" in res
    assert "generated_portfolio_comparison" in res
    
    # Test saving
    port_id = save_manual_portfolio(res, notes="Test user notes", db_path=db_file)
    assert port_id > 0
