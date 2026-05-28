from __future__ import annotations

from collections import Counter
from typing import Iterable


BLOCKS = (
    ("1_10", 1, 10),
    ("11_20", 11, 20),
    ("21_30", 21, 30),
    ("31_40", 31, 40),
    ("41_56", 41, 56),
)


def parse_numbers(input_value: str | Iterable[int]) -> list[int]:
    if isinstance(input_value, str):
        separators_normalized = input_value.replace(",", " ")
        numbers = [int(part) for part in separators_normalized.split()]
    else:
        numbers = [int(number) for number in input_value]
    return validate_numbers(numbers)


def validate_numbers(numbers: Iterable[int]) -> list[int]:
    parsed = [int(number) for number in numbers]
    if len(parsed) != 6:
        raise ValueError("Se requieren exactamente 6 números.")
    if len(set(parsed)) != 6:
        raise ValueError("Los 6 números deben ser únicos.")
    invalid = [number for number in parsed if number < 1 or number > 56]
    if invalid:
        raise ValueError("Todos los números deben estar entre 1 y 56.")
    return sorted(parsed)


def number_block(number: int) -> str:
    for label, start, end in BLOCKS:
        if start <= number <= end:
            return label
    raise ValueError("Número fuera de rango.")


def block_counts(numbers: Iterable[int]) -> dict[str, int]:
    counts = Counter(number_block(number) for number in numbers)
    return {label: counts.get(label, 0) for label, _, _ in BLOCKS}


def block_signature(numbers: Iterable[int]) -> str:
    counts = block_counts(numbers)
    return "-".join(str(counts[label]) for label, _, _ in BLOCKS)


def block_presence_signature(numbers: Iterable[int]) -> str:
    counts = block_counts(numbers)
    return "-".join("1" if counts[label] else "0" for label, _, _ in BLOCKS)


def sum_band(total: int) -> str:
    if total <= 120:
        return "low_band"
    if total <= 160:
        return "mid_band"
    if total <= 180:
        return "high_band"
    return "high_tail"


def parity_signature(numbers: Iterable[int]) -> str:
    even = sum(1 for number in numbers if number % 2 == 0)
    odd = 6 - even
    return f"{odd} odd / {even} even"
