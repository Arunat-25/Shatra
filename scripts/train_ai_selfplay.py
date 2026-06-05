#!/usr/bin/env python3
"""Evolve EvalWeights via self-play: candidate (strong) vs baseline (easy)."""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai_trained import reload_weights
from backend.ai_weights import EvalWeights, default_weights, load_weights, save_weights
from scripts.ai_selfplay_common import (
    MAX_PLIES_DEFAULT,
    candidate_score,
    play_game,
)

DEFAULT_WEIGHTS_PATH = ROOT / "data" / "ai_trained_weights.json"


def _default_workers() -> int:
    n = os.cpu_count() or 2
    return max(1, n - 1)


def _run_one_game(args: tuple) -> float:
    weights_dict, seed, candidate_color, max_plies, easy_depth, strong_depth = args
    rng = random.Random(seed)
    weights = EvalWeights.from_dict(weights_dict)
    result = play_game(
        weights,
        candidate_color=candidate_color,
        max_plies=max_plies,
        easy_depth=easy_depth,
        strong_depth=strong_depth,
        candidate_starts=rng.random() < 0.5,
    )
    return candidate_score(result, candidate_color)


def _evaluate_weights(
    weights: EvalWeights,
    *,
    games: int,
    max_plies: int,
    workers: int,
    easy_depth: int,
    strong_depth: int,
    base_seed: int,
) -> float:
    tasks = []
    for i in range(games):
        color = "белый" if i % 2 == 0 else "черный"
        tasks.append(
            (
                weights.to_dict(),
                base_seed + i,
                color,
                max_plies,
                easy_depth,
                strong_depth,
            )
        )

    total = 0.0
    if workers <= 1:
        for t in tasks:
            total += _run_one_game(t)
        return total / games

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_one_game, t) for t in tasks]
        for fut in as_completed(futures):
            total += fut.result()
    return total / games


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train Shatra AI weights via self-play (candidate vs easy baseline).",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=20,
        help="Games per generation (total = games × generations).",
    )
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--max-plies", type=int, default=MAX_PLIES_DEFAULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_WEIGHTS_PATH)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoke", action="store_true", help="2 games, 1 generation, 1 worker.")
    parser.add_argument("--easy-depth", type=int, default=3)
    parser.add_argument("--strong-depth", type=int, default=5)
    args = parser.parse_args()

    if args.smoke:
        args.games = 2
        args.generations = 1
        args.workers = 1
        _smoke_mode = True
    else:
        _smoke_mode = False

    workers = args.workers if args.workers is not None else _default_workers()
    cpu = os.cpu_count() or 2
    if workers >= cpu:
        print(f"Warning: workers={workers} uses all cores; plan recommends leaving 1 free.", file=sys.stderr)
    workers = max(1, workers)

    total_games = args.games * args.generations
    print(
        f"Training: {args.generations} generations × {args.games} games/gen = {total_games} games, "
        f"workers={workers}, max_plies={args.max_plies}",
        flush=True,
    )

    rng = random.Random(args.seed)
    best = load_weights(args.output) if args.output.is_file() else default_weights()
    best_fitness = _evaluate_weights(
        best,
        games=args.games,
        max_plies=args.max_plies,
        workers=workers,
        easy_depth=args.easy_depth,
        strong_depth=args.strong_depth,
        base_seed=args.seed,
    )
    print(f"Initial fitness: {best_fitness:.3f}", flush=True)

    for gen in range(1, args.generations + 1):
        t0 = time.time()
        candidates = [best] if _smoke_mode else [best] + [best.mutate(rng) for _ in range(3)]
        gen_best = best
        gen_best_fit = best_fitness

        for cand in candidates:
            fit = _evaluate_weights(
                cand,
                games=args.games,
                max_plies=args.max_plies,
                workers=workers,
                easy_depth=args.easy_depth,
                strong_depth=args.strong_depth,
                base_seed=args.seed + gen * 10_000 + hash(tuple(sorted(cand.to_dict().items()))) % 10_000,
            )
            if fit > gen_best_fit:
                gen_best_fit = fit
                gen_best = cand

        if gen_best_fit > best_fitness:
            best = gen_best
            best_fitness = gen_best_fit
            save_weights(best, args.output)

        elapsed = time.time() - t0
        print(
            f"Gen {gen}/{args.generations}: fitness={gen_best_fit:.3f} best={best_fitness:.3f} "
            f"({elapsed:.1f}s)",
            flush=True,
        )

    save_weights(best, args.output)
    reload_weights()
    print(f"Saved weights to {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
