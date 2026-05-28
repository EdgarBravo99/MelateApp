import pytest

from melate_app_lab.number_utils import (
    block_presence_signature,
    block_signature,
    parse_numbers,
    sum_band,
    validate_numbers,
)


def test_parse_numbers_from_string():
    assert parse_numbers("2 18 22 38 51 52") == [2, 18, 22, 38, 51, 52]


def test_validate_numbers_rejects_duplicates():
    with pytest.raises(ValueError):
        validate_numbers([2, 18, 18, 38, 51, 52])


def test_validate_numbers_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_numbers([0, 18, 22, 38, 51, 52])


def test_validate_numbers_requires_six_numbers():
    with pytest.raises(ValueError):
        validate_numbers([2, 18, 22, 38, 51])


def test_fixture_sum_band_and_signatures():
    numbers = [2, 18, 22, 38, 51, 52]
    assert sum(numbers) == 183
    assert sum_band(sum(numbers)) == "high_tail"
    assert block_signature(numbers) == "1-1-1-1-2"
    assert block_presence_signature(numbers) == "1-1-1-1-1"
