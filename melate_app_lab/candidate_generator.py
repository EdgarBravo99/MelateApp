from __future__ import annotations

import random
from collections import Counter
from typing import Any, Iterable
from .number_utils import block_signature, block_presence_signature, sum_band, parse_numbers
from .montecarlo_stress import stress_review

def analyze_time_window(history: list[dict[str, Any]], window: int = 30) -> dict[str, Any]:
    # Extract last 'window' draws
    recent = history[-window:] if len(history) >= window else history
    
    # 1. Frequency of each number
    all_numbers = [num for draw in recent for num in draw.get("numbers", [])]
    frequencies = Counter(all_numbers)
    # Ensure all numbers 1-56 are present in the frequency dict
    for i in range(1, 57):
        if i not in frequencies:
            frequencies[i] = 0
            
    # 2. Co-occurrences (pairs)
    co_occurrences: dict[tuple[int, int], int] = {}
    for draw in recent:
        nums = sorted(draw.get("numbers", []))
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                pair = (nums[i], nums[j])
                co_occurrences[pair] = co_occurrences.get(pair, 0) + 1

    # 3. Common block signatures and sum bands
    signatures = Counter(draw.get("block_signature") for draw in recent if draw.get("block_signature"))
    sum_bands = Counter(draw.get("sum_band") for draw in recent if draw.get("sum_band"))
    
    # Historical sets to avoid duplicates
    historical_sets = {frozenset(draw.get("numbers", [])) for draw in history}
    
    return {
        "frequencies": dict(frequencies),
        "co_occurrences": co_occurrences,
        "common_signatures": [sig for sig, _ in signatures.most_common(5)],
        "common_bands": [band for band, _ in sum_bands.most_common(3)],
        "historical_sets": historical_sets,
        "recent_count": len(recent)
    }

def generate_candidates(
    analysis: dict[str, Any],
    count: int = 10,
    seed: int = 4218,
    graph_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    candidates: list[dict[str, Any]] = []
    
    frequencies = analysis["frequencies"]
    co_occurrences = analysis["co_occurrences"]
    common_sigs = analysis["common_signatures"] or ["1-1-1-1-2", "1-1-1-2-1", "1-1-2-1-1", "1-2-1-1-1", "2-1-1-1-1"]
    common_bands = analysis["common_bands"] or ["mid_band", "high_band"]
    historical_sets = analysis["historical_sets"]

    # Build a lookup from graph_data edges for fast pair -> count / draws
    edge_lookup: dict[tuple[int, int], dict[str, Any]] = {}
    graph_window = 0
    if graph_data and graph_data.get("mode") == "historical":
        graph_window = graph_data.get("window", 0)
        for edge in graph_data.get("edges", []):
            src = int(edge["source"])
            tgt = int(edge["target"])
            pair = (min(src, tgt), max(src, tgt))
            edge_lookup[pair] = {
                "count": edge.get("count", 0),
                "draws": edge.get("draws", []),
                "last_seen_draw": edge.get("last_seen_draw", 0),
            }

    # Sort numbers by frequency
    sorted_nums_by_freq = sorted(frequencies.keys(), key=lambda n: frequencies[n], reverse=True)
    hot_numbers = sorted_nums_by_freq[:18]
    cold_numbers = sorted_nums_by_freq[-18:]
    warm_numbers = [n for n in sorted_nums_by_freq if n not in hot_numbers and n not in cold_numbers]
    
    # Generate 1000 candidate pools and filter them
    pool: list[list[int]] = []
    for _ in range(1000):
        # Pick strategy randomly to diversify
        strat = rng.choice(["balance", "relation", "cadence"])
        ticket: list[int] = []
        if strat == "balance":
            # Select 1 number from each block to maximize coverage, then 1 extra
            # blocks definitions: 1_10 (1-10), 11_20 (11-20), 21_30 (21-30), 31_40 (31-40), 41_56 (41-56)
            blocks_ranges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 56)]
            for r in blocks_ranges:
                ticket.append(rng.randint(r[0], r[1]))
            # 6th number from 1-56 not already selected
            while len(ticket) < 6:
                val = rng.randint(1, 56)
                if val not in ticket:
                    ticket.append(val)
        elif strat == "relation":
            # Start with a top co-occurring pair in recent history
            if co_occurrences:
                top_pairs = sorted(co_occurrences.keys(), key=lambda p: co_occurrences[p], reverse=True)
                pair = rng.choice(top_pairs[:min(10, len(top_pairs))])
                ticket.extend(pair)
            else:
                ticket.extend(rng.sample(range(1, 57), 2))
            # Fill remaining with warm and hot numbers
            while len(ticket) < 6:
                val = rng.choice(hot_numbers + warm_numbers)
                if val not in ticket:
                    ticket.append(val)
        else: # cadence
            # Mix hot, cold, and warm numbers
            ticket.extend(rng.sample(hot_numbers, 2))
            ticket.extend(rng.sample(warm_numbers, 2))
            ticket.extend(rng.sample(cold_numbers, 2))
            
        ticket = sorted(ticket)
        
        # Validations
        if len(set(ticket)) != 6:
            continue
        if frozenset(ticket) in historical_sets:
            continue
            
        # Stress-review validation (pre-filtering sums and signatures)
        tot = sum(ticket)
        band = sum_band(tot)
        sig = block_signature(ticket)
        
        # We prefer common sum bands and common signatures
        if band not in common_bands and rng.random() > 0.3:
            continue
        if sig not in common_sigs and rng.random() > 0.3:
            continue
            
        pool.append(ticket)
        
    # Deduplicate pool
    unique_pool = []
    seen = set()
    for ticket in pool:
        tup = tuple(ticket)
        if tup not in seen:
            seen.add(tup)
            unique_pool.append(ticket)
            
    # Now run stress_review on unique pool and select the best ones
    for ticket in unique_pool:
        # Run a mini stress review
        review = stress_review(ticket, [])
        # Score the ticket based on block presence, sum band, and how well it matches the strategies
        sig = block_signature(ticket)
        presence = block_presence_signature(ticket)
        band = sum_band(sum(ticket))
        
        # Determine the best strategy classification
        presence_count = presence.count("1")
        
        # Calculate how many co-occurrences it matches
        match_pairs = 0
        for i in range(6):
            for j in range(i + 1, 6):
                if (ticket[i], ticket[j]) in co_occurrences:
                    match_pairs += co_occurrences[(ticket[i], ticket[j])]
                    
        # Check hot/cold mix
        hot_count = sum(1 for n in ticket if n in hot_numbers)
        cold_count = sum(1 for n in ticket if n in cold_numbers)
        
        classification = ""
        reason_bullets = []
        
        if presence_count >= 5:
            classification = "Balance por bloques"
            reason_bullets = [
                f"cubre {presence_count} bloques de {len(presence.split('-'))} definidos",
                f"suma dentro de banda {band} ({sum(ticket)})",
                "evita concentracion excesiva de anclas",
                f"mantiene diversidad de firma ({sig})"
            ]
        elif match_pairs >= 2:
            classification = "Relacion historica moderada"
            reason_bullets = [
                f"conserva {match_pairs} coapariciones internas observadas en la ventana histórica",
                f"mezcla numeros de alta ({hot_count}) y baja ({cold_count}) recurrencia",
                f"firma observada en la ventana histórica ({sig})"
            ]
        else:
            classification = "Contraste / cobertura"
            reason_bullets = [
                f"balance temporal optimo: {hot_count} calientes, {cold_count} frios",
                f"suma total de {sum(ticket)} en rango {band}",
                f"estructura de bloques {sig} no repetida recientemente"
            ]

        # --- Graph support evidence ---
        pair_edges: list[dict[str, Any]] = []
        graph_support_score = 0
        evidence_draws: list[int] = []
        strongest_pairs: list[str] = []

        for i in range(6):
            for j in range(i + 1, 6):
                pair_key = (ticket[i], ticket[j])
                if pair_key in edge_lookup:
                    edge_info = edge_lookup[pair_key]
                    pair_edges.append({
                        "pair": f"{ticket[i]}—{ticket[j]}",
                        "count": edge_info["count"],
                        "draws": edge_info["draws"],
                    })
                    graph_support_score += edge_info["count"]
                    evidence_draws.extend(edge_info["draws"])

        # Deduplicate and sort evidence draws
        evidence_draws = sorted(set(evidence_draws), reverse=True)[:5]
        # Top 3 strongest pairs
        pair_edges_sorted = sorted(pair_edges, key=lambda p: p["count"], reverse=True)
        strongest_pairs = [p["pair"] for p in pair_edges_sorted[:3]]

        candidates.append({
            "numbers": ticket,
            "classification": classification,
            "reason_bullets": reason_bullets,
            "sum": sum(ticket),
            "sum_band": band,
            "block_signature": sig,
            "block_presence_signature": presence,
            "review": review,
            "pair_edges": pair_edges,
            "graph_support_score": graph_support_score,
            "relation_count": len(pair_edges),
            "strongest_pairs": strongest_pairs,
            "evidence_draws": evidence_draws,
            "relation_window": graph_window,
        })
            
    # Sort candidates by graph support score descending, and take the requested count
    candidates = sorted(candidates, key=lambda c: c.get("graph_support_score", 0), reverse=True)
    return candidates[:count]

def format_candidates_report(candidates: list[dict[str, Any]]) -> str:
    # First, sort candidates by graph support score descending to establish ranking letters
    candidates = sorted(candidates, key=lambda c: c.get("graph_support_score", 0), reverse=True)
    # Then make sure they have letters
    for idx, cand in enumerate(candidates):
        cand["letter"] = chr(ord('A') + idx)

    lines = []
    lines.append("Tesis de revision para siguiente ciclo")
    lines.append("======================================\n")

    # Resumen de candidatos arriba
    lines.append("Resumen de Candidatos:")
    
    # Sort for ranking text (sets with score > 0)
    ranked = [c for c in candidates if c.get("graph_support_score", 0) > 0]
    if ranked:
        ranked_str = ", ".join(f"Set {c['letter']} (soporte: {c['graph_support_score']})" for c in ranked)
    else:
        ranked_str = "Ninguno"
    lines.append(f"- Sets con mayor soporte de grafo: {ranked_str}")

    # Categorize sets
    balance_sets = [f"Set {c['letter']}" for c in candidates if c.get("classification") == "Balance por bloques"]
    relation_sets = [f"Set {c['letter']}" for c in candidates if c.get("classification") == "Relacion historica moderada"]
    contrast_sets = [f"Set {c['letter']}" for c in candidates if c.get("classification") == "Contraste / cobertura"]

    lines.append(f"- Sets de balance por bloques: {', '.join(balance_sets) if balance_sets else 'Ninguno'}")
    lines.append(f"- Sets de relación histórica: {', '.join(relation_sets) if relation_sets else 'Ninguno'}")
    lines.append(f"- Sets de contraste / cobertura: {', '.join(contrast_sets) if contrast_sets else 'Ninguno'}\n")

    lines.append("Nota de lectura: El soporte de grafo indica coapariciones históricas dentro de la ventana; no implica una confirmación definitiva.\n")

    # Group by profile
    profiles = [
        ("Perfil Balance por bloques", "Balance por bloques"),
        ("Perfil Relación histórica moderada", "Relacion historica moderada"),
        ("Perfil Contraste / cobertura", "Contraste / cobertura"),
    ]

    for title, key in profiles:
        sets = [c for c in candidates if c.get("classification") == key]
        if not sets:
            continue
        lines.append(title)
        lines.append("-" * len(title))
        for cand in sets:
            lines.append(f"Set {cand['letter']} — {cand['classification']}")
            lines.append(" ".join(str(n) for n in cand["numbers"]))

            # Graph support section
            pair_edges = cand.get("pair_edges", [])
            score = cand.get("graph_support_score", 0)
            window = cand.get("relation_window", 0)
            if score > 0:
                lines.append("")
                lines.append("Soporte de grafo:")
                lines.append(f"- graph_support_score: {score}")
                if window:
                    lines.append(f"- ventana: ultimos {window} sorteos")
                lines.append("- conexiones internas:")
                for pe in pair_edges:
                    lines.append(f"  - {pe['pair']} observado {pe['count']} veces")
                ev_draws = cand.get("evidence_draws", [])
                if ev_draws:
                    lines.append("- evidencia en sorteos:")
                    for d in ev_draws:
                        lines.append(f"  - {d}")

            lines.append("")
            lines.append("Motivo:")
            for bullet in cand["reason_bullets"]:
                lines.append(f"- {bullet}")
            lines.append("")
        lines.append("")

    return "\n".join(lines)


