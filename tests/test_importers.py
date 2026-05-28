import json

import pytest

from melate_app_lab.historical_store import import_draws_to_memory, load_draw_history
from melate_app_lab.importers import parse_draw_csv, parse_draw_json


def test_parse_draw_csv_imports_4218_fixture():
    records = parse_draw_csv("data/samples/revancha_4218.csv")

    assert records == [
        {
            "game": "revancha",
            "draw": 4218,
            "date": "2026-05-27",
            "numbers": [2, 18, 22, 38, 51, 52],
            "sum": 183,
            "sum_band": "high_tail",
            "block_signature": "1-1-1-1-2",
            "block_presence_signature": "1-1-1-1-1",
        }
    ]


def test_parse_draw_json_imports_4218_fixture(tmp_path):
    json_path = tmp_path / "history.json"
    json_path.write_text(
        json.dumps(
            {
                "draws": [
                    {
                        "game": "revancha",
                        "draw": 4218,
                        "date": "2026-05-27",
                        "numbers": [2, 18, 22, 38, 51, 52],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    records = parse_draw_json(json_path)

    assert records[0]["sum"] == 183
    assert records[0]["sum_band"] == "high_tail"
    assert records[0]["block_signature"] == "1-1-1-1-2"


def test_import_rejects_duplicates():
    records = parse_draw_csv("data/samples/revancha_4218.csv")

    with pytest.raises(ValueError, match="Duplicate draw"):
        import_draws_to_memory([*records, *records])


def test_import_rejects_numbers_out_of_range():
    with pytest.raises(ValueError, match="entre 1 y 56"):
        import_draws_to_memory(
            [
                {
                    "game": "revancha",
                    "draw": 4219,
                    "date": "2026-05-28",
                    "numbers": [2, 18, 22, 38, 51, 57],
                }
            ]
        )


def test_import_saves_and_loads_ordered():
    connection = import_draws_to_memory(
        [
            {
                "game": "revancha",
                "draw": 4219,
                "date": "2026-05-28",
                "numbers": [1, 11, 21, 31, 41, 42],
            },
            {
                "game": "revancha",
                "draw": 4218,
                "date": "2026-05-27",
                "numbers": [2, 18, 22, 38, 51, 52],
            },
        ]
    )

    history = load_draw_history(connection, game="revancha")

    assert [record["draw"] for record in history] == [4218, 4219]

