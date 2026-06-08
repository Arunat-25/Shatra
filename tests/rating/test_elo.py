"""Comprehensive unit tests for backend.rating.elo."""

from __future__ import annotations

import math

import pytest

from backend.rating.elo import (
    DEFAULT_RATING,
    ELO_SCALE,
    K_MASTER,
    K_NOVICE,
    K_STANDARD,
    MASTER_RATING_THRESHOLD,
    NOVICE_GAMES_THRESHOLD,
    expected_score,
    k_factor,
    rating_deltas,
)


# ---------------------------------------------------------------------------
# K-factor
# ---------------------------------------------------------------------------


class TestKFactor:
    @pytest.mark.parametrize(
        ("rating", "games", "expected_k"),
        [
            (1500, 0, K_NOVICE),
            (1500, 29, K_NOVICE),
            (800, 29, K_NOVICE),
            (3000, 29, K_NOVICE),
            (1500, 30, K_STANDARD),
            (2399, 30, K_STANDARD),
            (2399, 999, K_STANDARD),
            (2400, 30, K_MASTER),
            (2400, 0, K_NOVICE),  # novice rule first
            (2600, 100, K_MASTER),
            (2500, 10, K_NOVICE),  # novice beats master threshold
        ],
    )
    def test_k_factor_table(self, rating, games, expected_k):
        assert k_factor(rating, games) == expected_k

    def test_threshold_constants(self):
        assert NOVICE_GAMES_THRESHOLD == 30
        assert MASTER_RATING_THRESHOLD == 2400
        assert K_NOVICE == 40
        assert K_STANDARD == 20
        assert K_MASTER == 10


# ---------------------------------------------------------------------------
# Expected score (classic formula, scale 400)
# ---------------------------------------------------------------------------


class TestExpectedScore:
    def test_equal_ratings(self):
        assert expected_score(1500, 1500) == pytest.approx(0.5)

    def test_complement_sums_to_one(self):
        pairs = [(1500, 1500), (1400, 1600), (1200, 1800), (1000, 2000), (800, 2400)]
        for ra, rb in pairs:
            assert expected_score(ra, rb) + expected_score(rb, ra) == pytest.approx(1.0)

    @pytest.mark.parametrize(
        ("rating_a", "rating_b", "expected_e_a"),
        [
            (1500, 1500, 0.5),
            (1600, 1400, 1 / (1 + 10 ** (-0.5))),   # 200-pt gap
            (1400, 1600, 1 / (1 + 10 ** 0.5)),
            (1900, 1500, 1 / (1 + 10 ** (-1.0))),   # 400-pt gap ≈ 90.9%
            (1500, 1900, 1 / (1 + 10 ** 1.0)),
            (2000, 1500, 1 / (1 + 10 ** (-1.25))),  # 500-pt gap
            (1500, 2000, 1 / (1 + 10 ** 1.25)),
            (2200, 1500, 1 / (1 + 10 ** (-1.75))),  # 700-pt gap
            (1500, 2200, 1 / (1 + 10 ** 1.75)),
        ],
    )
    def test_known_expected_values(self, rating_a, rating_b, expected_e_a):
        assert expected_score(rating_a, rating_b) == pytest.approx(expected_e_a, abs=1e-9)

    def test_extreme_rating_gap_underdog_near_zero(self):
        e = expected_score(1000, 2500)
        assert e < 0.01
        assert expected_score(2500, 1000) > 0.99

    def test_symmetry_around_midpoint(self):
        # Swapping ratings flips expected score around 0.5.
        base = 1500
        for diff in (50, 100, 200, 400):
            high = base + diff // 2
            low = base - diff // 2
            e_high = expected_score(high, low)
            e_low = expected_score(low, high)
            assert e_high + e_low == pytest.approx(1.0)
            assert e_high - 0.5 == pytest.approx(0.5 - e_low)

    def test_uses_scale_400_not_200(self):
        # 200-pt advantage with scale 400: exponent ±0.5
        e = expected_score(1600, 1400)
        assert e == pytest.approx(1 / (1 + 10 ** (-0.5)), abs=1e-9)
        assert 0.75 < e < 0.77


# ---------------------------------------------------------------------------
# Rating deltas — hand-verified golden cases
# ---------------------------------------------------------------------------


class TestRatingDeltasGolden:
    """Each case: compute delta manually from formula, assert exact integers."""

    def test_equal_standard_win_loss_draw(self):
        # E=0.5, K=20 → ±10
        assert rating_deltas(1500, 1500, 50, 50, 1.0) == (10, -10)
        assert rating_deltas(1500, 1500, 50, 50, 0.0) == (-10, 10)
        assert rating_deltas(1500, 1500, 50, 50, 0.5) == (0, 0)

    def test_equal_novice_win_doubles_swing(self):
        # K=40 → ±20
        assert rating_deltas(1500, 1500, 0, 0, 1.0) == (20, -20)
        assert rating_deltas(1500, 1500, 10, 10, 0.0) == (-20, 20)

    def test_equal_master_win_halves_swing(self):
        # K=10 → ±5
        assert rating_deltas(2450, 2450, 50, 50, 1.0) == (5, -5)
        assert rating_deltas(2450, 2450, 50, 50, 0.0) == (-5, 5)

    def test_upset_400_points_underdog_wins(self):
        # 1400 beats 1800, K=20 both, E_A=1/11
        e_a = 1 / 11
        delta_a = round(20 * (1.0 - e_a))
        delta_b = round(20 * (0.0 - (1 - e_a)))
        assert rating_deltas(1400, 1800, 50, 50, 1.0) == (delta_a, delta_b)
        assert delta_a == 18
        assert delta_b == -18

    def test_favorite_wins_small_gain(self):
        # 1800 beats 1400, E_A=10/11
        e_a = 10 / 11
        assert rating_deltas(1800, 1400, 50, 50, 1.0) == (
            round(20 * (1.0 - e_a)),
            round(20 * (0.0 - (1 - e_a))),
        )
        assert rating_deltas(1800, 1400, 50, 50, 1.0) == (2, -2)

    def test_heavy_favorite_draw_underdog_gains(self):
        # 1400 draws 1800: underdog exceeds expectation
        e_a = 1 / 11
        assert rating_deltas(1400, 1800, 50, 50, 0.5) == (
            round(20 * (0.5 - e_a)),
            round(20 * (0.5 - (1 - e_a))),
        )
        assert rating_deltas(1400, 1800, 50, 50, 0.5) == (8, -8)

    def test_heavy_favorite_draw_favorite_loses_points(self):
        e_a = 10 / 11
        assert rating_deltas(1800, 1400, 50, 50, 0.5) == (
            round(20 * (0.5 - e_a)),
            round(20 * (0.5 - (1 - e_a))),
        )
        assert rating_deltas(1800, 1400, 50, 50, 0.5) == (-8, 8)

    def test_novice_vs_standard_asymmetric_deltas(self):
        # A novice K=40, B standard K=20, equal rating, A wins
        assert rating_deltas(1500, 1500, 10, 50, 1.0) == (20, -10)
        assert rating_deltas(1500, 1500, 10, 50, 0.0) == (-20, 10)
        assert rating_deltas(1500, 1500, 10, 50, 0.5) == (0, 0)

    def test_novice_vs_master_massive_upset(self):
        # Novice 1500 beats master 2500
        e_novice = expected_score(1500, 2500)
        e_master = expected_score(2500, 1500)
        assert rating_deltas(1500, 2500, 5, 100, 1.0) == (
            round(K_NOVICE * (1.0 - e_novice)),
            round(K_MASTER * (0.0 - e_master)),
        )
        da, db = rating_deltas(1500, 2500, 5, 100, 1.0)
        assert da == 40
        assert db == -10

    def test_master_beats_novice_expected_result(self):
        e_master = expected_score(2500, 1500)
        e_novice = expected_score(1500, 2500)
        da, db = rating_deltas(2500, 1500, 100, 5, 1.0)
        assert da == round(K_MASTER * (1.0 - e_master))
        assert db == round(K_NOVICE * (0.0 - e_novice))
        assert da == 0  # crushing favorite gains almost nothing
        assert db == 0  # novice expected to lose; loss matches expectation

    def test_both_novices_equal_draw(self):
        assert rating_deltas(1500, 1500, 0, 15, 0.5) == (0, 0)

    def test_both_masters_equal_draw(self):
        assert rating_deltas(2500, 2500, 40, 40, 0.5) == (0, 0)


# ---------------------------------------------------------------------------
# K-factor transition at game-count boundary
# ---------------------------------------------------------------------------


class TestKFactorTransition:
    def test_last_novice_game_vs_first_standard_same_match(self):
        # Same ratings/outcome, but A at 29 games (K=40) vs 30 games (K=20)
        win_novice, _ = rating_deltas(1500, 1500, 29, 50, 1.0)
        win_standard, _ = rating_deltas(1500, 1500, 30, 50, 1.0)
        assert win_novice == 20
        assert win_standard == 10

    def test_rating_at_2399_vs_2400_same_games(self):
        # 30 games: 2399→K=20, 2400→K=10
        _, loss_b_2399 = rating_deltas(2399, 2399, 30, 30, 0.0)
        _, loss_b_2400 = rating_deltas(2400, 2400, 30, 30, 0.0)
        assert loss_b_2399 == 10  # K=20, lose as equal
        assert loss_b_2400 == 5   # K=10, lose as equal


# ---------------------------------------------------------------------------
# Rounding behaviour
# ---------------------------------------------------------------------------


class TestRounding:
    def test_uses_python_round_not_floor(self):
        rating_a, rating_b = 1500, 1520
        e_a = expected_score(rating_a, rating_b)
        raw = K_STANDARD * (1.0 - e_a)
        assert raw > 9.5
        delta_a, _ = rating_deltas(rating_a, rating_b, 50, 50, 1.0)
        assert delta_a == round(raw)

    @pytest.mark.parametrize(
        ("rating_a", "rating_b", "games_a", "games_b", "score_a"),
        [
            (1517, 1500, 50, 50, 1.0),
            (1533, 1500, 50, 50, 0.0),
            (1620, 1500, 50, 50, 0.5),
        ],
    )
    def test_delta_matches_formula_round(self, rating_a, rating_b, games_a, games_b, score_a):
        k_a = k_factor(rating_a, games_a)
        k_b = k_factor(rating_b, games_b)
        e_a = expected_score(rating_a, rating_b)
        e_b = expected_score(rating_b, rating_a)
        score_b = 1.0 - score_a
        expected = (
            round(k_a * (score_a - e_a)),
            round(k_b * (score_b - e_b)),
        )
        assert rating_deltas(rating_a, rating_b, games_a, games_b, score_a) == expected


# ---------------------------------------------------------------------------
# Score validation & invariants
# ---------------------------------------------------------------------------


class TestScoreValidation:
    @pytest.mark.parametrize("bad_score", [0.75, 1.5, -0.5, 2.0, 0.25])
    def test_invalid_score_raises(self, bad_score):
        with pytest.raises(ValueError, match="score_a must be"):
            rating_deltas(1500, 1500, 0, 0, bad_score)

    @pytest.mark.parametrize("valid_score", [0.0, 0.5, 1.0])
    def test_valid_scores_accepted(self, valid_score):
        rating_deltas(1500, 1500, 50, 50, valid_score)


class TestInvariants:
    def test_deltas_asymmetric_when_k_differs(self):
        da, db = rating_deltas(1500, 1500, 5, 100, 1.0)
        assert da != -db

    def test_winner_non_negative_when_equal_or_lower_rating(self):
        """Underdog or equal who wins should not lose rating points."""
        cases = [
            (1500, 1500, 50, 50),
            (1400, 1800, 50, 50),
            (1200, 2000, 10, 50),
        ]
        for ra, rb, ga, gb in cases:
            da, _ = rating_deltas(ra, rb, ga, gb, 1.0)
            assert da >= 0

    def test_loser_non_positive_when_equal_or_higher_rating(self):
        cases = [
            (1500, 1500, 50, 50),
            (1800, 1400, 50, 50),
            (2000, 1200, 50, 10),
        ]
        for ra, rb, ga, gb in cases:
            da, _ = rating_deltas(ra, rb, ga, gb, 0.0)
            assert da <= 0

    def test_draw_zero_when_equal_rating_same_k(self):
        for r, g in [(1500, 5), (1500, 30), (2450, 100)]:
            da, db = rating_deltas(r, r, g, g, 0.5)
            assert da == 0
            assert db == 0

    def test_only_match_outcome_matters_not_implied_bonuses(self):
        """Same ratings/games: only score_a changes delta, not arbitrary factors."""
        base = (1500, 1600, 40, 40)
        win = rating_deltas(*base, 1.0)
        loss = rating_deltas(*base, 0.0)
        draw = rating_deltas(*base, 0.5)
        assert win[0] > draw[0] > loss[0]
        assert win[1] < draw[1] < loss[1]


# ---------------------------------------------------------------------------
# Parametric sweep — formula consistency
# ---------------------------------------------------------------------------


class TestFormulaConsistency:
    @pytest.mark.parametrize("rating_a", range(1200, 2601, 100))
    @pytest.mark.parametrize("rating_b", range(1200, 2601, 200))
    @pytest.mark.parametrize("games_a", [0, 15, 30, 80])
    @pytest.mark.parametrize("games_b", [0, 15, 30, 80])
    @pytest.mark.parametrize("score_a", [0.0, 0.5, 1.0])
    def test_always_matches_closed_form(self, rating_a, rating_b, games_a, games_b, score_a):
        k_a = k_factor(rating_a, games_a)
        k_b = k_factor(rating_b, games_b)
        e_a = expected_score(rating_a, rating_b)
        e_b = expected_score(rating_b, rating_a)
        score_b = 1.0 - score_a
        expected = (
            round(k_a * (score_a - e_a)),
            round(k_b * (score_b - e_b)),
        )
        assert rating_deltas(rating_a, rating_b, games_a, games_b, score_a) == expected

    def test_default_rating_constant(self):
        assert DEFAULT_RATING == 1200
        assert ELO_SCALE == 400
        assert math.isclose(expected_score(DEFAULT_RATING, DEFAULT_RATING), 0.5)


# ---------------------------------------------------------------------------
# Realistic match scenarios (named fixtures)
# ---------------------------------------------------------------------------


class TestRealisticScenarios:
    def test_calibration_first_game_win(self):
        """Brand-new player beats another new player."""
        assert rating_deltas(1500, 1500, 0, 0, 1.0) == (20, -20)

    def test_calibration_draw(self):
        assert rating_deltas(1500, 1500, 0, 0, 0.5) == (0, 0)

    def test_grandmaster_draws_even_match(self):
        assert rating_deltas(2600, 2580, 200, 150, 0.5) == (
            round(K_MASTER * (0.5 - expected_score(2600, 2580))),
            round(K_MASTER * (0.5 - expected_score(2580, 2600))),
        )

    def test_29th_game_still_high_volatility(self):
        da, _ = rating_deltas(1500, 1700, 29, 50, 1.0)
        db, _ = rating_deltas(1500, 1700, 30, 50, 1.0)
        assert da > db  # novice K still higher

    def test_public_pvp_typical_resign(self):
        # Two 1500 players, 50 rated games each, white (A) wins
        assert rating_deltas(1500, 1500, 50, 50, 1.0) == (10, -10)

    def test_public_pvp_draw_agreed(self):
        assert rating_deltas(1520, 1480, 50, 50, 0.5) == (
            round(20 * (0.5 - expected_score(1520, 1480))),
            round(20 * (0.5 - expected_score(1480, 1520))),
        )

    def test_mixed_k_draw_slight_favorite(self):
        # Novice 1600 vs veteran 1550, draw
        da, db = rating_deltas(1600, 1550, 10, 60, 0.5)
        e_a = expected_score(1600, 1550)
        assert da == round(K_NOVICE * (0.5 - e_a))
        assert db == round(K_STANDARD * (0.5 - (1 - e_a)))
