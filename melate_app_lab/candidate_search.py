from __future__ import annotations

import random
from typing import Any

from .number_utils import block_signature, sum_band


def search_candidates(
    analysis: dict[str, Any],
    pool_size: int = 1000,
    seed: int = 42,
) -> list[list[int]]:
    """Generate a pool of unique candidate combinations using multiple strategies.

    Strategies include block balance, historical pair relations, and contrast (hot/warm/cold).
    Filter candidates to exclude exact matches in the historical sets and apply basic stress filters.
    """
    rng = random.Random(seed)
    pool: list[list[int]] = []

    frequencies = analysis.get("frequencies", {})
    co_occurrences = analysis.get("co_occurrences", {})
    common_sigs = analysis.get("common_signatures", []) or [
        "1-1-1-1-2",
        "1-1-1-2-1",
        "1-1-2-1-1",
        "1-2-1-1-1",
        "2-1-1-1-1",
    ]
    common_bands = analysis.get("common_bands", []) or ["mid_band", "high_band"]
    historical_sets = analysis.get("historical_sets", set())

    # Sort numbers by frequency
    sorted_nums = sorted(frequencies.keys(), key=lambda n: frequencies[n], reverse=True)
    hot_numbers = sorted_nums[:18] if len(sorted_nums) >= 18 else sorted_nums
    cold_numbers = sorted_nums[-18:] if len(sorted_nums) >= 18 else sorted_nums
    warm_numbers = [n for n in sorted_nums if n not in hot_numbers and n not in cold_numbers]

    if not hot_numbers:
        hot_numbers = list(range(1, 19))
    if not cold_numbers:
        cold_numbers = list(range(39, 57))
    if not warm_numbers:
        warm_numbers = list(range(19, 39))

    attempts = 0
    max_attempts = pool_size * 20

    while len(pool) < pool_size and attempts < max_attempts:
        attempts += 1
        strat = rng.choice(["balance", "relation", "contrast"])
        ticket: list[int] = []

        if strat == "balance":
            # 1 from each block, plus 1 extra
            blocks_ranges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 56)]
            for r in blocks_ranges:
                ticket.append(rng.randint(r[0], r[1]))
            while len(ticket) < 6:
                val = rng.randint(1, 56)
                if val not in ticket:
                    ticket.append(val)
        elif strat == "relation":
            # 1 top co-occurring pair, then hot/warm numbers
            if co_occurrences:
                top_pairs = sorted(co_occurrences.keys(), key=lambda p: co_occurrences[p], reverse=True)
                pair = rng.choice(top_pairs[:min(10, len(top_pairs))])
                ticket.extend(pair)
            else:
                ticket.extend(rng.sample(range(1, 57), 2))
            while len(ticket) < 6:
                val = rng.choice(hot_numbers + warm_numbers)
                if val not in ticket:
                    ticket.append(val)
        else:  # contrast
            # 2 hot, 2 warm, 2 cold
            ticket.extend(rng.sample(hot_numbers, min(2, len(hot_numbers))))
            ticket.extend(rng.sample(warm_numbers, min(2, len(warm_numbers))))
            ticket.extend(rng.sample(cold_numbers, min(2, len(cold_numbers))))
            while len(ticket) < 6:
                val = rng.randint(1, 56)
                if val not in ticket:
                    ticket.append(val)

        ticket = sorted(ticket)

        if len(set(ticket)) != 6:
            continue
        if frozenset(ticket) in historical_sets:
            continue

        tot = sum(ticket)
        band = sum_band(tot)
        sig = block_signature(ticket)

        # Basic stress filters (common bands / signatures) with random bypass to keep diversity
        if band not in common_bands and rng.random() > 0.3:
            continue
        if sig not in common_sigs and rng.random() > 0.3:
            continue

        if ticket not in pool:
            pool.append(ticket)

    return pool
