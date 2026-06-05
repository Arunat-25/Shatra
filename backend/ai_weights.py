"""Tunable evaluation weights for Shatra AI (default = legacy ai.py values)."""
from __future__ import annotations

import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Iterator

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "ai_trained_weights.json"

_active: ContextVar["EvalWeights | None"] = ContextVar("ai_eval_weights", default=None)


@dataclass
class EvalWeights:
    piece_shatra: int = 100
    piece_batyr: int = 350
    piece_biy: int = 10_000
    biy_loss_penalty: int = 800_000
    hanging_penalty: int = 350
    promotion_bonus: int = 2_500
    promotion_progress_weight: int = 12
    position_scale: float = 3.0
    forced_trap_bonus: int = 15_000
    chain_capture_bonus: int = 8_000
    sacrifice_setup_bonus: int = 5_000
    even_trade_bonus: int = 60
    side_file_shatra_bonus: int = 60
    side_file_batyr_bonus: int = 90
    batyr_anchor_bonus: int = 110
    danger_zone_penalty: int = 140
    fortress_entry_shatra_bonus: int = 45
    fortress_entry_batyr_bonus: int = 120
    fortress_entry_biy_bonus: int = 2500
    fortress_deploy_penalty: int = 120_000
    fortress_intrusion_penalty: int = 12_000
    biy_anchor_bonus: int = 280
    crowded_main_field_threshold: int = 20

    def piece_values(self) -> dict[str, int]:
        return {
            "шатра": self.piece_shatra,
            "батыр": self.piece_batyr,
            "бий": self.piece_biy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalWeights":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def mutate(self, rng, rate: float = 0.3, scale: float = 0.15) -> "EvalWeights":
        """Return a slightly mutated copy for evolution."""
        import copy

        out = copy.deepcopy(self)
        for f in fields(type(self)):
            if rng.random() > rate:
                continue
            val = getattr(out, f.name)
            if isinstance(val, float):
                delta = abs(val) * scale * (rng.random() * 2 - 1)
                setattr(out, f.name, max(0.1, val + delta))
            else:
                delta = max(1, int(abs(val) * scale * (rng.random() * 2 - 1)))
                setattr(out, f.name, max(1, val + delta))
        return out


def default_weights() -> EvalWeights:
    return EvalWeights()


def get_active_weights() -> EvalWeights:
    w = _active.get()
    return w if w is not None else default_weights()


def has_context_weights() -> bool:
    return _active.get() is not None


@contextmanager
def use_weights(weights: EvalWeights) -> Iterator[None]:
    token = _active.set(weights)
    try:
        yield
    finally:
        _active.reset(token)


def load_weights(path: Path | str | None = None) -> EvalWeights:
    p = Path(path) if path else _DEFAULT_PATH
    if not p.is_file():
        return default_weights()
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return EvalWeights.from_dict(data)


def save_weights(weights: EvalWeights, path: Path | str | None = None) -> Path:
    p = Path(path) if path else _DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(weights.to_dict(), f, indent=2, ensure_ascii=False)
    return p
