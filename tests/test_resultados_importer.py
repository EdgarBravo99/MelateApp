from __future__ import annotations

import sqlite3

from melate_app_lab.resultados_importer import (
    import_resultados_csv_to_memory,
    parse_resultados_csv,
)
from melate_app_lab.historical_store import (
    get_latest_draw,
    load_draw_history,
    suggest_next_draw,
)


def _write_csv(tmp_path, content: str):
    path = tmp_path / "resultados.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_accepts_game_draw_date_n_columns_with_extra_columns(tmp_path):
    path = _write_csv(
        tmp_path,
        "game,draw,date,n1,n2,n3,n4,n5,n6,ignored\n"
        "Revancha,4218,2026-05-27,2,18,22,38,51,52,anything\n",
    )

    records = parse_resultados_csv(path)

    assert records[0]["game"] == "revancha"
    assert records[0]["draw"] == 4218
    assert records[0]["date"] == "2026-05-27"
    assert records[0]["numbers"] == [2, 18, 22, 38, 51, 52]


def test_parse_accepts_draw_date_numbers_columns_with_default_game(tmp_path):
    path = _write_csv(
        tmp_path,
        "draw,date,numbers\n"
        '4218,2026-05-27,"2,18,22,38,51,52"\n',
    )

    records = parse_resultados_csv(path, default_game="melate")

    assert records[0]["game"] == "melate"
    assert records[0]["draw"] == 4218
    assert records[0]["numbers"] == [2, 18, 22, 38, 51, 52]


def test_parse_accepts_sorteo_fecha_r_columns(tmp_path):
    path = _write_csv(
        tmp_path,
        "sorteo,fecha,r1,r2,r3,r4,r5,r6\n"
        "4218,2026-05-27,2,18,22,38,51,52\n",
    )

    records = parse_resultados_csv(path)

    assert records[0]["draw"] == 4218
    assert records[0]["date"] == "2026-05-27"
    assert records[0]["numbers"] == [2, 18, 22, 38, 51, 52]


def test_parse_accepts_concurso_fecha_numero_columns_with_accents(tmp_path):
    path = _write_csv(
        tmp_path,
        "concurso,fecha,número1,número2,número3,número4,número5,número6\n"
        "4218,2026-05-27,2,18,22,38,51,52\n",
    )

    records = parse_resultados_csv(path)

    assert records[0]["draw"] == 4218
    assert records[0]["numbers"] == [2, 18, 22, 38, 51, 52]


def test_parse_reports_invalid_rows_without_aborting_valid_rows(tmp_path):
    path = _write_csv(
        tmp_path,
        "draw,date,n1,n2,n3,n4,n5,n6\n"
        "4218,2026-05-27,2,18,22,38,51,52\n"
        "4219,2026-05-28,2,18,22,38,51,57\n",
    )

    result = import_resultados_csv_to_memory(path, tmp_path / "history.sqlite")

    assert result["imported"] == 1
    assert result["invalid_rows"] == 1
    assert result["duplicates_skipped"] == 0


def test_import_skips_duplicates_and_reports_history_summary(tmp_path):
    path = _write_csv(
        tmp_path,
        "draw,date,n1,n2,n3,n4,n5,n6\n"
        "4218,2026-05-27,2,18,22,38,51,52\n"
        "4218,2026-05-27,2,18,22,38,51,52\n",
    )
    db_path = tmp_path / "history.sqlite"

    result = import_resultados_csv_to_memory(path, db_path)

    assert result == {
        "imported": 1,
        "duplicates_skipped": 1,
        "invalid_rows": 0,
        "history_count": 1,
        "latest_draw": 4218,
        "suggested_next_draw": 4219,
    }


def test_historical_store_latest_next_and_limited_history_by_game(tmp_path):
    db_path = tmp_path / "history.sqlite"
    import_resultados_csv_to_memory(
        _write_csv(
            tmp_path,
            "game,draw,date,n1,n2,n3,n4,n5,n6\n"
            "melate,100,2026-05-26,1,2,3,4,5,6\n"
            "revancha,4217,2026-05-26,1,11,21,31,41,51\n"
            "revancha,4218,2026-05-27,2,18,22,38,51,52\n",
        ),
        db_path,
    )

    assert get_latest_draw(db_path, game="revancha") == 4218
    assert suggest_next_draw(db_path, game="revancha") == 4219
    assert [record["draw"] for record in load_draw_history(db_path, limit=1, game="revancha")] == [4218]
    assert get_latest_draw(db_path) == 4218


def test_historical_store_accepts_existing_connection_with_limit(tmp_path):
    db_path = tmp_path / "history.sqlite"
    import_resultados_csv_to_memory(
        _write_csv(
            tmp_path,
            "draw,date,n1,n2,n3,n4,n5,n6\n"
            "4217,2026-05-26,1,11,21,31,41,51\n"
            "4218,2026-05-27,2,18,22,38,51,52\n",
        ),
        db_path,
    )

    connection = sqlite3.connect(db_path)
    try:
        assert suggest_next_draw(connection, game="revancha") == 4219
        assert [record["draw"] for record in load_draw_history(connection, limit=1)] == [4218]
    finally:
        connection.close()
