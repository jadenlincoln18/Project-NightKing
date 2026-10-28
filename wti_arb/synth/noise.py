"""Quote generation: true prices -> bid/ask with half-spreads calibrated to the stored TBBO.

Two half-spread sources
  "model"     hs = max(floor, exp(alpha + beta*log(price) + tau*eps)), parameters from
              synth/geometry.json (fitted on every OTM quote in the real snapshots);
              widens with price level the way the data does, with the observed scatter
  "observed"  the real snapshot's own per-strike half-spread at that strike

Two error models for where the mid sits relative to truth
  "gaussian"  mid = C + N(0, hs^2)        (what the Stage 13 likelihood assumes)
  "uniform"   mid = C + U(-hs, hs)        (truth inside the quoted spread; sd = hs/sqrt(3))

Bid/ask are rounded to the $0.01 tick with a 1-cent floor on the bid, as in the data.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

TICK = 0.01


def round_tick(x, tick=TICK):
    return np.round(np.asarray(x, float) / tick) * tick


def half_spreads(rng: np.random.Generator, true_price: np.ndarray, model: Dict[str, float], scale: float = 1.0,
                 observed: Optional[np.ndarray] = None) -> np.ndarray:
    if observed is not None:
        hs = np.asarray(observed, float) * scale
    else:
        p = np.maximum(np.asarray(true_price, float), model["floor"])
        eps = rng.standard_normal(p.shape)
        hs = np.exp(model["alpha"] + model["beta"] * np.log(p) + model["tau"] * eps) * scale
    hs = np.maximum(hs, model.get("floor", TICK / 2))
    # quotes live on the tick grid: half-spreads are multiples of a half-tick
    return np.maximum(np.round(hs / (TICK / 2)) * (TICK / 2), TICK / 2)


def quotes(rng: np.random.Generator, true_price: np.ndarray, hs: np.ndarray, error: str = "gaussian"):
    """Returns (bid, ask, mid, hs) after tick rounding and the 1-cent bid floor."""
    C = np.asarray(true_price, float)
    if error == "gaussian":
        mid = C + hs * rng.standard_normal(C.shape)
    elif error == "uniform":
        mid = C + hs * rng.uniform(-1.0, 1.0, C.shape)
    elif error == "none":
        mid = C.copy()
    else:
        raise ValueError(error)
    bid = np.maximum(round_tick(mid - hs), TICK)
    ask = np.maximum(round_tick(mid + hs), bid + TICK)
    mid_q = 0.5 * (bid + ask)
    hs_q = 0.5 * (ask - bid)
    return bid, ask, mid_q, hs_q
