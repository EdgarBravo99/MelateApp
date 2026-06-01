from __future__ import annotations

PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53}


def get_historical_lags(prior_history: list[dict]) -> dict[int, int]:
    lags = {n: len(prior_history) for n in range(1, 57)}
    for steps_back, draw_record in enumerate(reversed(prior_history)):
        nums = draw_record["numbers"]
        for n in nums:
            if lags[n] == len(prior_history):
                lags[n] = steps_back
    return lags


def analyze_candidate_statistical_profile(
    candidate_numbers: list[int],
    prior_history: list[dict],
) -> dict:
    candidate_numbers = sorted(list(candidate_numbers))

    # 1. Primes
    prime_count = sum(1 for n in candidate_numbers if n in PRIMES)

    # 2. Repeated from previous draw
    repeated_count = 0
    if prior_history:
        prev_nums = prior_history[-1]["numbers"]
        repeated_count = len(set(candidate_numbers) & set(prev_nums))

    # 3. Consecutive pairs
    consecutive_pairs = 0
    for i in range(len(candidate_numbers) - 1):
        if candidate_numbers[i+1] - candidate_numbers[i] == 1:
            consecutive_pairs += 1

    # 4. Mean and Sum
    sum_val = sum(candidate_numbers)
    mean_val = sum_val / len(candidate_numbers)

    # Mean band
    from .number_utils import sum_band
    m_band = sum_band(sum_val)  # Reuse sum_band logic to map sum to bands

    # 5. Even / Odd
    even_count = sum(1 for n in candidate_numbers if n % 2 == 0)
    odd_count = len(candidate_numbers) - even_count

    # 6. Low / High balance
    # low: 1..28, high: 29..56
    low_count = sum(1 for n in candidate_numbers if 1 <= n <= 28)
    high_count = len(candidate_numbers) - low_count
    low_high_balance = f"{low_count}L / {high_count}H"

    # 7. Delayed numbers (lag >= 15)
    lags = {}
    if prior_history:
        lags = get_historical_lags(prior_history)
    delayed_nums = [n for n in candidate_numbers if lags.get(n, 0) >= 15]
    delayed_count = len(delayed_nums)

    # 8. Alerts
    alerts = []
    if consecutive_pairs >= 3:
        alerts.append(f"Alta cantidad de números consecutivos ({consecutive_pairs})")
    if even_count in (0, 6):
        alerts.append(f"Distribución par/impar atípica ({odd_count} O / {even_count} E)")
    if prime_count in (0, 5, 6):
        alerts.append(f"Cantidad de números primos atípica ({prime_count} primos)")
    if repeated_count >= 3:
        alerts.append(f"Alta cantidad de números repetidos del sorteo anterior ({repeated_count})")
    if m_band in ("low_band", "high_tail"):
        alerts.append(f"Media de valores en banda extrema ({m_band})")
    if delayed_count >= 3:
        alerts.append(f"Alta concentración de números demorados ({delayed_count})")

    # 9. Notes
    notes = []
    if not alerts:
        notes.append("Combinación balanceada y consistente con el modelo estadístico general.")
    else:
        notes.append(f"Combinación con {len(alerts)} desviaciones estadísticas respecto a la media histórica.")

    return {
        "prime_count": prime_count,
        "repeated_from_previous_draw_count": repeated_count,
        "consecutive_pairs_count": consecutive_pairs,
        "mean_value": round(mean_val, 2),
        "mean_band": m_band,
        "sum_value": sum_val,
        "even_count": even_count,
        "odd_count": odd_count,
        "low_high_balance": low_high_balance,
        "delayed_numbers_count": delayed_count,
        "delayed_numbers": delayed_nums,
        "statistical_alerts": alerts,
        "statistical_notes": notes,
    }


def analyze_portfolio_statistical_profile(
    portfolio: list[dict],
    prior_history: list[dict],
) -> dict:
    if not portfolio:
        return {
            "portfolio_prime_distribution": {},
            "portfolio_mean_band_distribution": {},
            "portfolio_repeated_distribution": {},
            "portfolio_consecutive_distribution": {},
            "average_prime_count": 0.0,
            "average_repeated_from_previous_draw_count": 0.0,
            "average_consecutive_pairs_count": 0.0,
            "average_mean_value": 0.0,
            "portfolio_statistical_alerts": ["Cartera vacía."],
            "portfolio_statistical_summary": "No hay candidatos en la cartera.",
        }

    primes = []
    repeateds = []
    consecutives = []
    means = []
    bands = []

    for cand in portfolio:
        nums = cand["numbers"]
        prof = analyze_candidate_statistical_profile(nums, prior_history)
        primes.append(prof["prime_count"])
        repeateds.append(prof["repeated_from_previous_draw_count"])
        consecutives.append(prof["consecutive_pairs_count"])
        means.append(prof["mean_value"])
        bands.append(prof["mean_band"])

    from collections import Counter
    prime_dist = dict(Counter(primes))
    mean_band_dist = dict(Counter(bands))
    repeated_dist = dict(Counter(repeateds))
    consec_dist = dict(Counter(consecutives))

    n = len(portfolio)
    avg_prime = sum(primes) / n
    avg_rep = sum(repeateds) / n
    avg_consec = sum(consecutives) / n
    avg_mean = sum(means) / n

    alerts = []
    # Check if there is an overall portfolio-level alert
    extreme_bands_count = bands.count("low_band") + bands.count("high_tail")
    if extreme_bands_count / n > 0.4:
        alerts.append("Alta concentración de candidatos con media en bandas extremas (>40%)")

    if avg_consec > 1.5:
        alerts.append(f"Promedio de consecutivos alto en la cartera ({round(avg_consec, 2)})")

    all_nums = set()
    for cand in portfolio:
        all_nums.update(cand["numbers"])
    if len(all_nums) < n * 3:
        alerts.append(f"Baja cobertura de números en la cartera (solo {len(all_nums)} números únicos para {n} candidatos)")

    summary = f"Cartera de {n} candidatos. Media promedio: {round(avg_mean, 2)}. "
    if alerts:
        summary += f"Se detectaron {len(alerts)} alertas a nivel de cartera."
    else:
        summary += "La distribución agregada cumple con los criterios de consistencia estadística."

    return {
        "portfolio_prime_distribution": {str(k): v for k, v in prime_dist.items()},
        "portfolio_mean_band_distribution": mean_band_dist,
        "portfolio_repeated_distribution": {str(k): v for k, v in repeated_dist.items()},
        "portfolio_consecutive_distribution": {str(k): v for k, v in consec_dist.items()},
        "average_prime_count": round(avg_prime, 2),
        "average_repeated_from_previous_draw_count": round(avg_rep, 2),
        "average_consecutive_pairs_count": round(avg_consec, 2),
        "average_mean_value": round(avg_mean, 2),
        "portfolio_statistical_alerts": alerts,
        "portfolio_statistical_summary": summary,
    }
