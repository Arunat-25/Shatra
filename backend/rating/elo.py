"""Classic Elo rating calculations with per-player dynamic K-factor."""

from __future__ import annotations

import math

DEFAULT_RATING = 1200
ELO_SCALE = 400
NOVICE_GAMES_THRESHOLD = 30
MASTER_RATING_THRESHOLD = 2400
K_NOVICE = 40
K_STANDARD = 20
K_MASTER = 10

_VALID_SCORES = frozenset({0.0, 0.5, 1.0})


def k_factor(rating: int, games_played: int) -> int:
    """Return K-factor for a player (novice > master > standard)."""
    if games_played < NOVICE_GAMES_THRESHOLD:
        return K_NOVICE
    if rating >= MASTER_RATING_THRESHOLD:
        return K_MASTER
    return K_STANDARD


def expected_score(rating_a: int, rating_b: int) -> float:
    """Expected result for player A: E_A = 1 / (1 + 10^((R_B - R_A) / 400))."""
    exponent = (rating_b - rating_a) / ELO_SCALE
    return 1.0 / (1.0 + math.pow(10.0, exponent))


def rating_deltas(
    rating_a: int,
    rating_b: int,
    games_a: int,
    games_b: int,
    score_a: float,
) -> tuple[int, int]:
    """
    Compute rounded integer rating deltas for players A and B.

    score_a: 1.0 (A wins), 0.5 (draw), 0.0 (A loses).
    Deltas may differ because each player has their own K-factor.
    """
    if score_a not in _VALID_SCORES:
        raise ValueError(f"score_a must be 0.0, 0.5, or 1.0, got {score_a}")

    score_b = 1.0 - score_a
    e_a = expected_score(rating_a, rating_b)
    e_b = expected_score(rating_b, rating_a)

    k_a = k_factor(rating_a, games_a)
    k_b = k_factor(rating_b, games_b)

    delta_a = round(k_a * (score_a - e_a))
    delta_b = round(k_b * (score_b - e_b))
    return delta_a, delta_b
