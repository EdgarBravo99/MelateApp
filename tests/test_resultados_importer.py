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

    assert result["imported"] == 1
    assert result["duplicates_skipped"] == 1
    assert result["invalid_rows"] == 0
    assert result["history_count"] == 1
    assert result["latest_draw"] == 4218
    assert result["suggested_next_draw"] == 4219
    assert result["encoding_used"] in ("utf-8-sig", "utf-8")
    assert result["invalid_row_samples"] == []


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


def test_import_utf8_sig_csv(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes(
        b"\xef\xbb\xbfdraw,date,n1,n2,n3,n4,n5,n6\n"
        b"4218,2026-05-27,2,18,22,38,51,52\n"
    )
    result = import_resultados_csv_to_memory(path, tmp_path / "h.sqlite")
    assert result["imported"] == 1
    assert result["encoding_used"] == "utf-8-sig"


def test_import_latin1_csv(tmp_path):
    path = tmp_path / "latin.csv"
    header = "concurso,fecha,número1,número2,número3,número4,número5,número6\n"
    row = "4218,2026-05-27,2,18,22,38,51,52\n"
    path.write_bytes((header + row).encode("latin-1"))
    result = import_resultados_csv_to_memory(path, tmp_path / "h.sqlite")
    assert result["imported"] == 1
    assert result["encoding_used"] == "latin-1"


def test_import_skips_empty_rows(tmp_path):
    path = tmp_path / "blanks.csv"
    path.write_text(
        "draw,date,n1,n2,n3,n4,n5,n6\n"
        "4218,2026-05-27,2,18,22,38,51,52\n"
        ",,,,,,,\n"
        "\n"
        "4219,2026-05-28,1,11,21,31,41,51\n",
        encoding="utf-8",
    )
    result = import_resultados_csv_to_memory(path, tmp_path / "h.sqlite")
    assert result["imported"] == 2
    assert result["invalid_rows"] == 0


def test_import_captures_invalid_row_samples(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "draw,date,n1,n2,n3,n4,n5,n6\n"
        "4218,2026-05-27,2,18,22,38,51,52\n"
        "bad_draw,no-date,x,y,z,w,a,b\n",
        encoding="utf-8",
    )
    result = import_resultados_csv_to_memory(path, tmp_path / "h.sqlite")
    assert result["imported"] == 1
    assert result["invalid_rows"] == 1
    assert len(result["invalid_row_samples"]) == 1


def test_import_pakin_revancha_style_csv_with_extras(tmp_path):
    """Simulates a Pakin/Revancha CSV with extra columns, accents, and duplicates."""
    path = tmp_path / "revancha_pakin.csv"
    path.write_text(
        "Concurso,Fecha,Número1,Número2,Número3,Número4,Número5,Número6,Acumulado,Ganadores\n"
        "4215,2026-05-24,1,11,21,31,41,51,$50000,0\n"
        "4216,2026-05-25,5,15,25,35,45,55,$60000,1\n"
        "4217,2026-05-26,3,13,23,33,43,53,$70000,0\n"
        "4218,2026-05-27,2,18,22,38,51,52,$80000,2\n"
        "4218,2026-05-27,2,18,22,38,51,52,$80000,2\n",
        encoding="utf-8",
    )
    result = import_resultados_csv_to_memory(path, tmp_path / "h.sqlite")
    assert result["imported"] == 4
    assert result["duplicates_skipped"] == 1
    assert result["invalid_rows"] == 0
    assert result["history_count"] == 4
    assert result["latest_draw"] == 4218
    assert result["suggested_next_draw"] == 4219


def test_bulk_import_many_rows(tmp_path):
    """Ensure bulk import with >500 rows works and commits in chunks."""
    lines = ["draw,date,n1,n2,n3,n4,n5,n6"]
    for i in range(600):
        draw = 1000 + i
        lines.append(f"{draw},2026-01-01,1,11,21,31,41,51")
    path = tmp_path / "bulk.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = import_resultados_csv_to_memory(path, tmp_path / "h.sqlite")
    assert result["imported"] == 600
    assert result["duplicates_skipped"] == 0
    assert result["invalid_rows"] == 0
    assert result["history_count"] == 600


def test_ensure_historical_schema_exists():
    from melate_app_lab import historical_store
    assert hasattr(historical_store, "ensure_historical_schema")
    assert historical_store.ensure_schema == historical_store.ensure_historical_schema


def test_load_draw_history_closes_local_connection():
    from unittest.mock import patch, MagicMock
    from melate_app_lab import historical_store
    mock_conn = MagicMock()
    with patch("melate_app_lab.historical_store._connect", return_value=mock_conn) as mock_connect:
        historical_store.load_draw_history("dummy_path")
        mock_connect.assert_called_once_with("dummy_path")
        mock_conn.close.assert_called_once()


def test_get_latest_draw_closes_local_connection():
    from unittest.mock import patch, MagicMock
    from melate_app_lab import historical_store
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = [None]
    with patch("melate_app_lab.historical_store._connect", return_value=mock_conn) as mock_connect:
        historical_store.get_latest_draw("dummy_path")
        mock_connect.assert_called_once_with("dummy_path")
        mock_conn.close.assert_called_once()


def test_load_draw_history_does_not_close_passed_connection():
    from melate_app_lab import historical_store
    import sqlite3
    conn = sqlite3.connect(":memory:")
    historical_store.ensure_schema(conn)
    try:
        historical_store.load_draw_history(conn)
        # Verify connection is still open
        conn.execute("SELECT 1")
    finally:
        conn.close()


def test_get_latest_draw_does_not_close_passed_connection():
    from melate_app_lab import historical_store
    import sqlite3
    conn = sqlite3.connect(":memory:")
    historical_store.ensure_schema(conn)
    try:
        historical_store.get_latest_draw(conn)
        # Verify connection is still open
        conn.execute("SELECT 1")
    finally:
        conn.close()



