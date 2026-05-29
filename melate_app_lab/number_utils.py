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


def analyze_portfolio_redundancy(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {
            "has_alerts": False,
            "redundancies": [],
            "number_concentration": [],
            "signature_concentration": [],
            "profile_concentration": [],
            "block_concentration": [],
        }

    m = len(candidates)
    redundancies = []
    number_counts: Counter[int] = Counter()
    signature_counts: Counter[str] = Counter()
    profile_counts: Counter[str] = Counter()
    block_counts_total: Counter[str] = Counter()

    for idx, cand in enumerate(candidates):
        nums = cand["numbers"]
        classification = cand.get("classification", "Desconocido")
        sig = cand.get("block_signature") or block_signature(nums)

        signature_counts[sig] += 1
        profile_counts[classification] += 1

        for num in nums:
            number_counts[num] += 1
            block_counts_total[number_block(num)] += 1

    # Rule 1: Redundancy between sets (pairwise intersection)
    for i in range(m):
        for j in range(i + 1, m):
            set_a = candidates[i]
            set_b = candidates[j]
            label_a = set_a.get("letter", f"Candidato {i+1}")
            label_b = set_b.get("letter", f"Candidato {j+1}")
            shared = sorted(list(set(set_a["numbers"]) & set(set_b["numbers"])))

            if len(shared) == 3:
                redundancies.append({
                    "set_a": label_a,
                    "set_b": label_b,
                    "shared_count": len(shared),
                    "shared_numbers": shared,
                    "level": "media",
                    "message": f"Los sets {label_a} y {label_b} comparten 3 números ({shared}).",
                })
            elif len(shared) >= 4:
                redundancies.append({
                    "set_a": label_a,
                    "set_b": label_b,
                    "shared_count": len(shared),
                    "shared_numbers": shared,
                    "level": "alta",
                    "message": f"Los sets {label_a} y {label_b} comparten {len(shared)} números ({shared}).",
                })

    # Rule 2: Concentration per number (>40% of sets)
    number_concentration = []
    for num, count in number_counts.items():
        pct = (count / m) * 100
        if pct > 40.0:
            number_concentration.append({
                "number": num,
                "percentage": round(pct, 1),
                "count": count,
                "level": "alta",
                "message": f"El número {num} aparece en {count} sets ({round(pct, 1)}%), superando el límite del 40%.",
            })

    # Rule 3: Concentration per signature (>60% of sets)
    signature_concentration = []
    for sig, count in signature_counts.items():
        pct = (count / m) * 100
        if pct > 60.0:
            signature_concentration.append({
                "signature": sig,
                "percentage": round(pct, 1),
                "count": count,
                "level": "alta",
                "message": f"La firma de bloques {sig} aparece en {count} sets ({round(pct, 1)}%), superando el límite del 60%.",
            })

    # Rule 4: Concentration per profile (>60% of sets)
    profile_concentration = []
    for profile, count in profile_counts.items():
        pct = (count / m) * 100
        if pct > 60.0:
            profile_concentration.append({
                "profile": profile,
                "percentage": round(pct, 1),
                "count": count,
                "level": "alta",
                "message": f"El perfil '{profile}' aparece en {count} sets ({round(pct, 1)}%), superando el límite del 60%.",
            })

    # Rule 5: Concentration per block (>35% of total numbers)
    block_concentration = []
    total_nums = m * 6
    for b_label, start, end in BLOCKS:
        count = block_counts_total.get(b_label, 0)
        pct = (count / total_nums) * 100
        if pct > 35.0:
            block_concentration.append({
                "block": b_label,
                "percentage": round(pct, 1),
                "count": count,
                "level": "alta",
                "message": f"El bloque {b_label} acumula {count} apariciones ({round(pct, 1)}%), superando el límite del 35%.",
            })

    has_alerts = bool(
        redundancies
        or number_concentration
        or signature_concentration
        or profile_concentration
        or block_concentration
    )

    return {
        "has_alerts": has_alerts,
        "redundancies": redundancies,
        "number_concentration": number_concentration,
        "signature_concentration": signature_concentration,
        "profile_concentration": profile_concentration,
        "block_concentration": block_concentration,
    }

