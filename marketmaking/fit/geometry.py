"""Measured geometry and quote-noise of the real §1A temperature ladders.

Gate 0's synthetic ladders must look like the real ones, and PROTOCOL §1A
permits exactly this kind of input: bracket edges and spreads are microstructure
and market structure, observable to anyone before a model exists. **No
settlement outcome and no fitter output is read here.**

Two things are measured:

1. **Ladder geometry** — brackets per event, interior edge spacing in °F, and
   the span of the quoted support, from the staged `kalshi_markets` table.
2. **Quote noise** — the distribution of the executable spread `ask - bid` on
   two-sided bracket-minutes, stratified by the bracket's own mid, because a
   bracket quoted near 1c and one quoted near 50c are not equally noisy.

Reads only the staged historical store under `data/_import/` via
`phase05.stores`, which refuses any live-collector path.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field

import numpy as np
import pandas as pd

from phase05 import stores, panel as panel_mod

# Mid-level strata, in cents. Spread is strongly level-dependent on a ladder:
# the wings are quoted 1-wide-but-illiquid, the body is where the money is.
MID_BINS = (0.0, 5.0, 15.0, 35.0, 65.0, 85.0, 95.0, 100.0)


@dataclass
class Geometry:
    """What a Gate 0 synthetic ladder must imitate."""
    n_events: int = 0
    n_series: int = 0
    brackets_per_event_mean: float = 0.0
    brackets_per_event_hist: dict = field(default_factory=dict)
    edge_step_median: float = 0.0
    edge_step_hist: dict = field(default_factory=dict)
    interior_span_median: float = 0.0
    kind_counts: dict = field(default_factory=dict)

    def to_json(self, path):
        with open(path, "w") as fh:
            json.dump(asdict(self), fh, indent=2, sort_keys=True)


def measure_geometry(series_list, root=None, max_events_per_series=None) -> Geometry:
    """Brackets per event and the °F spacing of their interior edges."""
    lstore = panel_mod._load_ladder_store()
    root = stores.check_staging(root)
    stores.assert_not_live(root)

    n_br, steps, spans, kinds = [], [], [], {}
    n_events = 0
    for s in series_list:
        markets = lstore.load_markets([s], root=root)
        if markets.empty:
            continue
        ev = lstore.events_table(markets, root=root)
        if max_events_per_series is not None:
            ev = ev.head(max_events_per_series)
        for _, info in ev.iterrows():
            kinds[info["kind"]] = kinds.get(info["kind"], 0) + 1
            if info["kind"] != "range":
                continue
            e = interior_edges(info)
            if e is None or len(e) < 1:
                continue
            n_events += 1
            # One market = one bracket. A `range` ladder's two wings are open,
            # so n_br brackets have n_br - 1 interior edges.
            n_br.append(len(info["tickers"]))
            steps.extend(np.diff(e).tolist())
            spans.append(float(e.max() - e.min()))

    def hist(vals, dec=0):
        v, c = np.unique(np.round(np.asarray(vals, float), dec), return_counts=True)
        return {str(a): int(b) for a, b in zip(v, c)}

    return Geometry(
        n_events=n_events,
        n_series=len(series_list),
        brackets_per_event_mean=float(np.mean(n_br)) if n_br else 0.0,
        brackets_per_event_hist=hist(n_br),
        edge_step_median=float(np.median(steps)) if steps else 0.0,
        edge_step_hist=hist(steps),
        interior_span_median=float(np.median(spans)) if spans else 0.0,
        kind_counts=kinds,
    )


def interior_edges(info) -> np.ndarray | None:
    """The n_br - 1 interior bracket boundaries of a `range` event, in °F.

    `events_table` returns `strikes` as `[cap(first)] + [floor(i) for i>0]`, so
    on a real ladder — `<=29 | 30-31 | 32-33 | 34-35 | 36-37 | >=38` — it reads
    `[30, 30, 32, 34, 36, 37]`.

    Measured strike conventions on the staged temperature series (no other kind
    appears): `less` carries an **exclusive** cap (`cap=30` is `29 or lower`),
    `greater` an **exclusive** floor (`floor=37` is `38 or higher`), `between`
    an inclusive `[floor, cap]`. Settlement is on integer °F, so the continuous
    boundary sits on the half degree: `strike - 0.5` everywhere except the final
    entry, the last bracket's exclusive floor, which is `strike + 0.5`.

    For the example that gives `[29.5, 31.5, 33.5, 35.5, 37.5]` — five interior
    edges for six brackets, evenly spaced 2 °F, with two open wings.
    """
    k = np.asarray(info["strikes"], float)
    k = k[np.isfinite(k)]
    if len(k) < 2:
        return None
    e = np.unique(np.concatenate([k[:-1] - 0.5, [k[-1] + 0.5]]))
    if len(e) != len(info["tickers"]) - 1:
        return None
    return e


def measure_spreads(series_list, root=None, max_events_per_series=6,
                    every=5) -> pd.DataFrame:
    """Executable spread distribution by mid-level stratum.

    `every` subsamples minutes only to keep the measurement cheap; the spread
    distribution is a cross-sectional object and does not depend on cadence.
    Only two-sided, executable bracket-minutes are counted — the same filter
    §1B's disagreement set uses.
    """
    rows = []
    for s in series_list:
        p, _cuts = panel_mod.series_panel(s, root=root, every=every,
                                          max_events=max_events_per_series)
        if p.empty:
            continue
        ok = (p["bid"].notna() & p["ask"].notna() & (p["bid"] > 0) & (p["ask"] < 100)
              & (p["ask"] >= p["bid"]))
        q = p[ok]
        if q.empty:
            continue
        rows.append(pd.DataFrame({
            "series": s,
            "mid": (q["bid"].to_numpy() + q["ask"].to_numpy()) / 2.0,
            "spread": q["ask"].to_numpy() - q["bid"].to_numpy(),
        }))
    if not rows:
        return pd.DataFrame(columns=["series", "mid", "spread"])
    return pd.concat(rows, ignore_index=True)


def spread_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per-stratum spread quantiles — the table reported with the Gate 0 result."""
    if df.empty:
        return pd.DataFrame()
    b = pd.cut(df["mid"], bins=list(MID_BINS), include_lowest=True)
    g = df.groupby(b, observed=True)["spread"]
    out = g.agg(n="size", mean="mean",
                p25=lambda x: np.percentile(x, 25),
                p50=lambda x: np.percentile(x, 50),
                p75=lambda x: np.percentile(x, 75),
                p90=lambda x: np.percentile(x, 90))
    return out.reset_index().rename(columns={"mid": "mid_bin"})


def half_spread_model(df: pd.DataFrame) -> dict:
    """Mid -> median half-spread, in probability units, as a step function.

    This is the noise model Gate 0 uses: it is **measured, not assumed**, and it
    is the same quantity the fitter is told to use as its per-bracket error sd.
    """
    tab = spread_table(df)
    levels, halves = [], []
    for _, r in tab.iterrows():
        iv = r["mid_bin"]
        levels.append((float(iv.left) / 100.0, float(iv.right) / 100.0))
        halves.append(float(r["p50"]) / 200.0)
    return {"bins": levels, "half_spread": halves,
            "overall_median_spread_cents": float(np.median(df["spread"])) if len(df) else 0.0,
            "n": int(len(df))}


def measure_incoherence(series_list, root=None, max_events_per_series=6,
                        every=5, tight_max=20.0) -> dict:
    """How far a real ladder's mids are from summing to 1 — the quote-noise scale.

    A `range` ladder partitions the outcome space, so a coherent set of mids
    sums to exactly 1. Real mids do not. Writing `m_i = p_i + e_i` with the
    `e_i` independent across brackets,

        Var(sum_i m_i - 1) = n_br * sigma^2   =>   sigma = sd(sum m - 1) / sqrt(n_br)

    This is a **measurement of the quote's own displacement** that needs no
    truth and no settlement: it is identified by the ladder's internal
    arithmetic alone. The *mean* of `sum m - 1` is the overround (the market's
    edge, a systematic quantity), so the sd is taken about that mean and the
    overround is reported separately rather than counted as noise.

    Only ladder-minutes where **every** bracket is two-sided with spread
    < `tight_max` are used, so the degenerate 1/99 books cannot contaminate it.
    """
    lstore = panel_mod._load_ladder_store()
    root = stores.check_staging(root)
    stores.assert_not_live(root)

    sums, n_lad, n_br_seen = [], 0, []
    for s in series_list:
        markets = lstore.load_markets([s], root=root)
        if markets.empty:
            continue
        ev = lstore.events_table(markets, root=root)
        ev = ev[(ev["kind"] == "range") & ev["has_candles"]].head(max_events_per_series)
        for _, info in ev.iterrows():
            candles = lstore.load_event_candles(s, info["event"], root=root)
            if candles is None or candles.empty:
                continue
            g = lstore.build_grid(candles, info)
            if g is None:
                continue
            bid, ask = g.bid[::every], g.ask[::every]
            spread = ask - bid
            ok = (np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask < 100)
                  & (spread >= 0) & (spread < tight_max))
            full = ok.all(axis=1)
            if not full.any():
                continue
            mids = (bid[full] + ask[full]) / 200.0
            sums.extend(mids.sum(axis=1).tolist())
            n_lad += int(full.sum())
            n_br_seen.append(bid.shape[1])
    if not sums:
        return {"n_ladder_minutes": 0}
    a = np.asarray(sums, float)
    n_br = float(np.mean(n_br_seen))
    sd_sum = float(a.std(ddof=1))
    return {
        "n_ladder_minutes": n_lad,
        "mean_brackets": n_br,
        "overround_mean": float(a.mean() - 1.0),
        "sd_sum_mids": sd_sum,
        "sigma_per_bracket": sd_sum / np.sqrt(n_br),
        "sum_q05": float(np.percentile(a, 5)),
        "sum_q50": float(np.percentile(a, 50)),
        "sum_q95": float(np.percentile(a, 95)),
    }
