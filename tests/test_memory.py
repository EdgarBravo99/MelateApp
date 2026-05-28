import sqlite3

from melate_app_lab.draw_trace import trace_draw
from melate_app_lab.memory import (
    init_db,
    load_recent_lessons,
    remember_draw,
    remember_played_tickets,
    remember_postmortem,
)
from melate_app_lab.postmortem import postmortem_review


RESULT = [2, 18, 22, 38, 51, 52]
PLAYED = [
    [7, 15, 29, 41, 42, 48],
    [7, 16, 18, 23, 29, 39],
    [9, 13, 18, 30, 45, 52],
    [7, 15, 20, 30, 36, 53],
]


def test_init_db_creates_tables(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {"draws", "played_tickets", "postmortems", "lessons", "trace_patterns"} <= tables


def test_remember_draw_and_postmortem_round_trip(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    init_db(db_path)
    draw_trace = trace_draw(4218, RESULT)
    review = postmortem_review(4218, RESULT, PLAYED)

    remember_draw(db_path, draw_trace)
    remember_played_tickets(db_path, 4218, PLAYED)
    remember_postmortem(db_path, review)

    lessons = load_recent_lessons(db_path)
    assert lessons
    assert lessons[0]["draw"] == 4218
    assert lessons[0]["captured_numbers"] == [18, 52]
    assert lessons[0]["missed_numbers"] == [2, 22, 38, 51]
