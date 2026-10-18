"""Locating the staged historical store, and the staging gate.

Phase 0.5 is restricted to historical settled ladders in the staged stores under
`marketmaking/data/_import/`. It must not read the live collector's output under
`marketmaking/data/live*`, `depth/`, `touch/`, `price_ranges/` or `incentive/`,
and must not touch the running launchd job.

§1B's unit of observation is a (bracket, MINUTE) pair on a one-minute grid. That
requires the Kalshi one-minute candle store plus the markets table — the inputs
`ladder.store` reads. As of this run those are NOT staged: `_import/` holds the
discovery snapshots and the per-series aggregates only. `check_staging()` is the
hard gate that says so precisely rather than letting a run silently proceed on a
substitute dataset.
"""
from __future__ import annotations

import sys
from pathlib import Path

MM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MM_ROOT.parent
IMPORT_DIR = MM_ROOT / "data" / "_import"

# Live collector output. Phase 0.5 must never read or write these.
FORBIDDEN = ("live", "depth", "touch", "price_ranges", "incentive")

# What §1B needs, in the shape `ladder.store.paths()` expects.
CANDLES_SUBPATH = Path("parquet") / "kalshi_candles" / "period=1"
MARKETS_SUBPATH = Path("parquet") / "kalshi_markets"


def add_repo_to_path() -> None:
    """Make `ladder.store` importable. Read-only reuse; `ladder/` is never modified."""
    p = str(REPO_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)


class StagingGap(RuntimeError):
    """The historical minute store §1B needs is not staged where phase 0.5 may read it."""


def staged_files() -> list[Path]:
    return sorted(p for p in IMPORT_DIR.glob("*") if p.is_file()) if IMPORT_DIR.exists() else []


def candle_root(root: Path | None = None) -> Path | None:
    """The staged store root that contains a one-minute candle tree, or None."""
    roots = [root] if root is not None else [IMPORT_DIR, IMPORT_DIR / "waves_data", IMPORT_DIR / "ladder_data"]
    for r in roots:
        if r is None:
            continue
        if (r / CANDLES_SUBPATH).is_dir() and (r / MARKETS_SUBPATH).is_dir():
            return r
    return None


def check_staging(root: Path | None = None) -> Path:
    """Return the usable store root, or raise StagingGap with what is missing.

    This is deliberately a hard failure. §1B is a pre-registered gate; running it
    against a different dataset than the one it specifies — a coarser snapshot,
    a narrower universe, or data that has already been looked at — would not be
    the pre-registered test, whatever number came out.
    """
    found = candle_root(root)
    if found is not None:
        return found

    have = "\n".join("    %s  (%.1f MB)" % (p.name, p.stat().st_size / 1e6)
                     for p in staged_files()) or "    (nothing)"
    raise StagingGap(
        "PHASE 0.5 CANNOT RUN: the one-minute candle store is not staged.\n\n"
        "§1B scores (bracket, MINUTE) observations on a one-minute grid. That needs:\n"
        "    <root>/%s/series=*/event=*/part.parquet\n"
        "    <root>/%s/series=*/part.parquet\n"
        "searched under %s\n\n"
        "What IS staged there:\n%s\n\n"
        "Those are discovery snapshots (one row per ticker, no observation\n"
        "timestamp) and per-series aggregates. They carry settlement outcomes\n"
        "and candle COUNTS, but no quote time series, so no fit at time t, no\n"
        "quote midpoint at time t, and no 5/30/60-minute path for Test B.\n\n"
        "The store exists outside git by design (.gitignore: 'historical stores\n"
        "transfer separately'). Stage the candle + markets trees for the §1A\n"
        "universe into %s and re-run.\n\n"
        "Phase 0.5 will not substitute a different dataset for the one §1B names."
        % (CANDLES_SUBPATH, MARKETS_SUBPATH, IMPORT_DIR, have, IMPORT_DIR)
    )


def assert_not_live(path) -> None:
    """Guard: refuse any path inside the live collector's stores."""
    p = Path(path).resolve()
    try:
        rel = p.relative_to(MM_ROOT / "data")
    except ValueError:
        return
    head = rel.parts[0] if rel.parts else ""
    if head.startswith("live") or head in FORBIDDEN:
        raise PermissionError(
            "phase 0.5 may not read or write the live collector store: %s "
            "(a collector is running under launchd)" % p
        )
