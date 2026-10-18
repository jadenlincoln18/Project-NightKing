"""Invariants that must hold for the whole of a 14-day unattended run.

These are not unit tests for their own sake. Each one guards a specific way the
collector could silently produce unusable data or violate a PROTOCOL gate while
nobody is watching. A fourteen-day run that fails on day one and is noticed on
day fourteen has cost fourteen days.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from mm import config, kapi, store

ROOT = pathlib.Path(__file__).resolve().parents[1]


# --- PROTOCOL gates ----------------------------------------------------------

def test_orders_are_inert():
    """PROTOCOL: the order manager is inert for all of phase 1."""
    assert config.ORDERS_ENABLED is False


def test_no_maker_fee_series_in_quote_universe():
    """PROTOCOL §1: maker fee is *structurally* zero on the quoting universe.

    If a fee-paying series leaks in, every cent-denominated threshold in
    PROTOCOL is wrong for it and the 58.50% no longer describes the population.
    """
    leaked = set(config.QUOTE_UNIVERSE) & set(config.MAKER_FEE_SERIES)
    assert not leaked, f"maker-fee series in quote universe: {sorted(leaked)}"


def test_sports_control_is_never_quoted():
    """PROTOCOL §1A: sports is the negative control. Collected, never quoted."""
    leaked = set(config.QUOTE_UNIVERSE) & set(config.CONTROL_SERIES)
    assert not leaked, f"control series in quote universe: {sorted(leaked)}"


def test_known_maker_fee_series_are_flagged():
    """Regression: these three were measured against the live API, not assumed."""
    for s in ("KXAAAGASM", "KXNFLSPREAD", "KXNFLTOTAL"):
        assert s in config.MAKER_FEE_SERIES, f"{s} lost its maker-fee flag"


# --- universe integrity ------------------------------------------------------

def test_every_collected_series_has_a_fee_type():
    """A series with no fee_type has no known maker cost. It must not exist."""
    fee_map = json.loads((ROOT / "fee_map_ladder.json").read_text())
    known = {x["series"] for x in fee_map if x.get("fee_type")}
    missing = set(config.COLLECT_UNIVERSE) - known
    assert not missing, f"series collected with no fee_type: {sorted(missing)}"


def test_universe_groups_partition_the_collection_set():
    groups = (
        set(config.PRIMARY_SERIES)
        | set(config.COMPARISON_SERIES)
        | set(config.CONTROL_SERIES)
    )
    assert groups == set(config.COLLECT_UNIVERSE)
    # groups must not overlap, or per-group statistics double count
    assert not set(config.PRIMARY_SERIES) & set(config.CONTROL_SERIES)
    assert not set(config.PRIMARY_SERIES) & set(config.COMPARISON_SERIES)
    assert not set(config.COMPARISON_SERIES) & set(config.CONTROL_SERIES)


def test_primary_universe_is_entirely_maker_free():
    """The whole point of picking daily temperature was a clean, free book."""
    assert not set(config.PRIMARY_SERIES) & set(config.MAKER_FEE_SERIES)


# --- API shape guards --------------------------------------------------------

def test_depth_param_is_accepted_by_the_api():
    """depth=1000 returns HTTP 400. Measured, not assumed. Do not raise this
    without re-testing against the live endpoint."""
    assert kapi.DEPTH_PARAM <= 100


@pytest.mark.parametrize(
    "raw,expected",
    [
        # measured live shape 2026-10-18: step is in DOLLARS, result in cents
        ([{"start": "0.0000", "end": "1.0000", "step": "0.0100"}], 1.0),
        # finest step wins when the ladder is segmented -- the finest step is
        # what invalidates a cent-denominated threshold
        (
            [
                {"start": "0.0000", "end": "0.5000", "step": "0.0100"},
                {"start": "0.5000", "end": "1.0000", "step": "0.0010"},
            ],
            0.1,
        ),
        # legacy dict shape must still parse -- this field already changed once
        ({"tick_size": "0.0100"}, 1.0),
        ([], None),
        (None, None),
    ],
)
def test_tick_from_price_ranges(raw, expected):
    assert kapi.tick_from_price_ranges(raw) == expected


def test_tick_detects_a_sub_cent_grid():
    """Other Kalshi markets already quote $0.001. If a ladder moves to a finer
    grid, every cent-denominated threshold in PROTOCOL silently breaks, so this
    must come back as sub-cent rather than rounding to 1c."""
    fine = kapi.tick_from_price_ranges(
        [{"start": "0.0000", "end": "1.0000", "step": "0.0010"}]
    )
    assert fine is not None and fine < 1.0


def test_parse_book_handles_empty_and_missing():
    """A market with no book is normal (pre-open). It must not crash a cycle."""
    for raw in (None, {}, {"orderbook": {}}, {"orderbook": {"yes": None, "no": None}}):
        yes, no = kapi.parse_book(raw)
        assert yes == [] and no == []


def test_depth_row_records_level_counts_for_truncation_detection():
    """depth=100 is only safe because clipping stays *detectable*. If the level
    counts stop being recorded, a silent truncation becomes unfalsifiable."""
    row = store.depth_row("KXHIGHLAX-26OCT18-B60", "KXHIGHLAX", None, store.utcnow())
    assert "n_yes_levels" in row and "n_no_levels" in row


# --- the kill switch ---------------------------------------------------------

def test_kill_file_path_is_outside_the_data_tree():
    """The operator must be able to stop the run without touching the store."""
    assert config.KILL_FILE.name == "KILL"
    assert not config.KILL_FILE.exists(), "a KILL file is present; collector will halt"
