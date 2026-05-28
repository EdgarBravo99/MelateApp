from melate_app_lab.guardrails import validate_output_json
from melate_app_lab.montecarlo_stress import generate_random_ticket, stress_review


RESULT = [2, 18, 22, 38, 51, 52]
PLAYED = [
    [7, 15, 29, 41, 42, 48],
    [7, 16, 18, 23, 29, 39],
    [9, 13, 18, 30, 45, 52],
    [7, 15, 20, 30, 36, 53],
]


def test_generate_random_ticket_creates_valid_ticket():
    ticket = generate_random_ticket()
    assert len(ticket) == 6
    assert len(set(ticket)) == 6
    assert all(1 <= number <= 56 for number in ticket)


def test_stress_review_is_deterministic_and_flags_concentration():
    first = stress_review(RESULT, PLAYED, seed=4218)
    second = stress_review(RESULT, PLAYED, seed=4218)

    assert first == second
    assert 7 in first["anchor_concentration"]["repeated_numbers"]
    assert validate_output_json(first) == first
