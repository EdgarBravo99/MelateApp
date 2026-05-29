from __future__ import annotations

import logging
from typing import Any

from .candidate_ranker import rank_candidates
from .candidate_search import search_candidates
from .candidate_generator import analyze_time_window
from .feature_extractor import extract_features
from .relation_graph import build_historical_relation_graph

logger = logging.getLogger(__name__)

HAS_SKLEARN = False
try:
    from sklearn.linear_model import Ridge
    HAS_SKLEARN = True
except ImportError:
    pass


def is_ml_available() -> bool:
    """Return True if the scikit-learn library is installed and available."""
    return HAS_SKLEARN


# List of numeric features to extract for ML
ML_FEATURE_KEYS = [
    "sum",
    "even_count",
    "odd_count",
    "frequency_mean",
    "frequency_std",
    "degree_mean",
    "degree_std",
    "weighted_degree_mean",
    "weighted_degree_std",
    "graph_support_score",
    "pair_edges_count",
    "diversity_score",
]


def features_to_vector(features: dict[str, Any]) -> list[float]:
    """Convert a candidate's features dictionary to a numeric feature vector."""
    vector = []
    for key in ML_FEATURE_KEYS:
        val = features.get(key, 0.0)
        vector.append(float(val) if val is not None else 0.0)
    return vector


def train_ml_ranker(
    history: list[dict[str, Any]],
    training_draws: list[int],
    window: int = 30,
    game: str = "revancha",
) -> Any | None:
    """Train a Ridge regression model to evaluate candidate hits based on historical data.

    Returns the trained model if scikit-learn is available, otherwise returns None.
    """
    if not HAS_SKLEARN:
        logger.info("scikit-learn no está instalado. ML ranker no disponible.")
        return None

    # Filter and sort history
    filtered = [d for d in history if str(d.get("game", "")).casefold() == game.casefold()]
    filtered.sort(key=lambda d: d.get("draw", 0))

    history_by_draw = {d["draw"]: d for d in filtered}

    X: list[list[float]] = []
    y: list[float] = []

    for draw_id in training_draws:
        if draw_id not in history_by_draw:
            continue

        draw_record = history_by_draw[draw_id]
        actual_numbers = set(draw_record["numbers"])

        # Prior history to build graph & window frequencies
        prior = [d for d in filtered if d["draw"] < draw_id]
        if len(prior) < 10:
            continue

        train_history = prior[-window:] if len(prior) >= window else prior
        analysis = analyze_time_window(prior, window=window)
        graph_data = build_historical_relation_graph(prior, window=window, game=game)

        # Search candidates and extract features
        candidates = search_candidates(analysis, pool_size=50, seed=42 + draw_id)
        for cand in candidates:
            feats = extract_features(cand, train_history, prior, graph_data)
            vector = features_to_vector(feats)
            hits = len(set(cand) & actual_numbers)

            X.append(vector)
            y.append(float(hits))

    if not X:
        logger.warning("No hay datos de entrenamiento para entrenar el ML Ranker.")
        return None

    try:
        model = Ridge(alpha=1.0)
        model.fit(X, y)
        logger.info(f"ML Ranker entrenado con éxito. Muestras: {len(X)}.")
        return model
    except Exception as e:
        logger.error(f"Error al entrenar el modelo ML Ranker: {e}")
        return None


def rank_candidates_ml(
    model: Any,
    candidates_features: list[dict[str, Any]],
    common_signatures: list[str],
    common_bands: list[str],
) -> list[dict[str, Any]]:
    """Rank candidates using evaluations from the trained ML model.

    Falls back to the standard heuristic ranker if the model is not trained.
    """
    if model is None or not HAS_SKLEARN:
        return rank_candidates(candidates_features, common_signatures, common_bands)

    scored = []
    for cand in candidates_features:
        vector = features_to_vector(cand)
        try:
            eval_score = float(model.predict([vector])[0])
        except Exception:
            eval_score = 0.0

        # Apply a penalty for exact match to prevent historical duplicates
        if cand.get("historical_exact_match", False):
            eval_score -= 10.0

        cand_copy = dict(cand)
        cand_copy["rank_score"] = eval_score
        scored.append(cand_copy)

    # Sort descending by evaluation, ascending by sum as secondary
    scored.sort(key=lambda c: (-c["rank_score"], c["sum"]))

    for idx, cand in enumerate(scored):
        cand["rank"] = idx + 1

    return scored
