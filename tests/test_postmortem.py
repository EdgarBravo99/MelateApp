from melate_app_lab.postmortem import compare_ticket_to_draw, postmortem_review


RESULT = [2, 18, 22, 38, 51, 52]
PLAYED = [
    [7, 15, 29, 41, 42, 48],
    [7, 16, 18, 23, 29, 39],
    [9, 13, 18, 30, 45, 52],
    [7, 15, 20, 30, 36, 53],
]


def test_compare_ticket_to_draw_counts_hits():
    assert compare_ticket_to_draw(PLAYED[0], RESULT, label="A")["hits"] == 0
    assert compare_ticket_to_draw(PLAYED[1], RESULT, label="B")["hit_numbers"] == [18]
    assert compare_ticket_to_draw(PLAYED[2], RESULT, label="C")["hit_numbers"] == [18, 52]
    assert compare_ticket_to_draw(PLAYED[3], RESULT, label="D")["hits"] == 0


def test_postmortem_review_fixture_outputs():
    review = postmortem_review(4218, RESULT, PLAYED)

    assert review["captured_numbers"] == [18, 52]
    assert review["missed_numbers"] == [2, 22, 38, 51]
    assert 7 in review["overused_played_numbers"]
    assert 15 in review["overused_played_numbers"]
    assert review["best_matches"][0]["label"] == "C"
