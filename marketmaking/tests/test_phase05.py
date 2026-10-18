"""Tests for phase 0.5 (PROTOCOL §1B).

These are the sanity checks §1B's rigor requirements demand, run on fixtures
with known ground truth so the pipeline can be trusted independently of whether
the real store is staged:

  - the bootstrap clusters on EVENT and not on bracket (the forbidden one is
    shown to be narrower, which is exactly why it is forbidden);
  - look-ahead is caught as a hard error, and a deliberately staled fit scores
    worse than the honest one;
  - the Test A gate can FAIL as well as pass — a gate that cannot fail is not a
    gate;
  - "first to move" resolves ties to NOT first, per §1B;
  - the per-bracket p95 threshold carries the pooled fallback and the ladder
    skip, and its realised share exceeds 5% because of the half-cent grid.

Run from `marketmaking/`:  ../.venv/bin/python -m pytest tests/ -q
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from phase05 import disagree, firstmove, score, stores, testb


# --- fixtures ----------------------------------------------------------------

def make_frame(n_events=200, n_brackets=5, fit_is_good=True, seed=0):
    """A settled ladder population with a known answer.

    Each event draws one settlement value; every bracket's outcome is determined
    by that single draw, which is exactly the dependence §1B's clustering rule
    exists to respect. When `fit_is_good` the fit is the true probability and
    the quote is a noisy version of it; otherwise the roles are reversed.
    """
    rng = np.random.default_rng(seed)
    rows = []
    edges = np.linspace(0.0, 1.0, n_brackets + 1)
    for e in range(n_events):
        value = rng.uniform()
        for b in range(n_brackets):
            p_true = 0.5 + 0.4 * np.sin(3 * (edges[b] + e * 0.01))
            p_true = float(np.clip(p_true, 0.05, 0.95))
            y = int(value < p_true)
            noisy = float(np.clip(p_true + rng.normal(0, 0.18), 0.02, 0.98))
            fit = p_true if fit_is_good else noisy
            quote = noisy if fit_is_good else p_true
            rows.append(dict(
                event_id="EV%03d" % e, ticker="EV%03d-B%d" % (e, b),
                ts=1_700_000_000 + 60 * b, bid=100 * quote - 1, ask=100 * quote + 1,
                fit_mean=fit, fit_lo=fit - 0.05, fit_hi=fit + 0.05,
                fit_asof=1_700_000_000 + 60 * b, settled_yes=y,
            ))
    return pd.DataFrame(rows)


# --- scoring -----------------------------------------------------------------

def test_brier_and_log_score_known_values():
    assert score.brier([1.0, 0.0], [1, 0]) == 0.0
    assert score.brier([0.5, 0.5], [1, 0]) == pytest.approx(0.25)
    assert score.log_score([0.5, 0.5], [1, 0]) == pytest.approx(np.log(0.5))


def test_log_score_is_finite_at_the_boundary():
    """A stated probability of exactly 0 or 1 must not decide the test alone."""
    assert np.isfinite(score.log_score([0.0, 1.0], [1, 0]))


# --- the clustering rule, which is the whole point ---------------------------

def test_bootstrap_resamples_events_not_brackets():
    """Duplicating every row within an event must not narrow the interval.

    An event repeated B times carries no more information than once. The
    event-clustered interval is therefore EXACTLY the one-row-per-event
    interval under the same seed, because the within-event mean is unchanged
    and the same events are drawn.
    """
    rng = np.random.default_rng(7)
    n_events = 60
    pf = rng.uniform(0.2, 0.8, n_events)
    pq = rng.uniform(0.2, 0.8, n_events)
    y = rng.integers(0, 2, n_events).astype(float)
    ev = np.array(["E%02d" % i for i in range(n_events)])

    single = score.event_clustered_bootstrap(pf, pq, y, ev, n_boot=400, seed=3)
    rep = 8
    dup = score.event_clustered_bootstrap(
        np.repeat(pf, rep), np.repeat(pq, rep), np.repeat(y, rep), np.repeat(ev, rep),
        n_boot=400, seed=3)

    assert dup["n_rows"] == n_events * rep
    assert dup["n_events"] == n_events
    assert dup["lo"] == pytest.approx(single["lo"], abs=1e-12)
    assert dup["hi"] == pytest.approx(single["hi"], abs=1e-12)


def test_bracket_level_bootstrap_would_be_narrower_and_is_not_used():
    """Demonstrates the overstatement §1B forbids, so the guard has teeth."""
    df = make_frame(n_events=80, n_brackets=6, seed=11)
    mid = disagree.quote_mid_prob(df).values
    clustered = score.event_clustered_bootstrap(
        df.fit_mean.values, mid, df.settled_yes.values, df.event_id.values,
        n_boot=400, seed=5)

    # the forbidden alternative: every bracket-minute its own cluster
    naive = score.event_clustered_bootstrap(
        df.fit_mean.values, mid, df.settled_yes.values, np.arange(len(df)),
        n_boot=400, seed=5)

    assert (naive["hi"] - naive["lo"]) < (clustered["hi"] - clustered["lo"])
    assert clustered["n_events"] == 80
    assert naive["n_events"] == len(df)


def test_bootstrap_actually_reads_the_event_field():
    """Scrambling the cluster labels must change the interval."""
    df = make_frame(n_events=60, n_brackets=5, seed=2)
    mid = disagree.quote_mid_prob(df).values
    real = score.event_clustered_bootstrap(
        df.fit_mean.values, mid, df.settled_yes.values, df.event_id.values,
        n_boot=300, seed=1)
    rng = np.random.default_rng(0)
    scrambled = score.event_clustered_bootstrap(
        df.fit_mean.values, mid, df.settled_yes.values,
        rng.permutation(df.event_id.values), n_boot=300, seed=1)
    assert (real["hi"] - real["lo"]) != pytest.approx(scrambled["hi"] - scrambled["lo"], abs=1e-9)


# --- the gate must be able to fail -------------------------------------------

def test_gate_passes_when_the_fit_is_genuinely_better():
    df = make_frame(n_events=250, fit_is_good=True, seed=4)
    mid = disagree.quote_mid_prob(df).values
    a = score.test_a_verdict(df.fit_mean.values, mid, df.settled_yes.values,
                             df.event_id.values, n_boot=400, seed=0)
    assert a["brier_fit"] < a["brier_quote"]
    assert a["brier_ci"][1] < 0
    assert a["passed"] and a["verdict"] == "PASS"


def test_gate_fails_when_the_fit_is_noise():
    df = make_frame(n_events=250, fit_is_good=False, seed=4)
    mid = disagree.quote_mid_prob(df).values
    a = score.test_a_verdict(df.fit_mean.values, mid, df.settled_yes.values,
                             df.event_id.values, n_boot=400, seed=0)
    assert a["brier_fit"] > a["brier_quote"]
    assert not a["passed"] and a["verdict"] == "FAIL"


# --- look-ahead ---------------------------------------------------------------

def test_lookahead_is_a_hard_error():
    df = make_frame(n_events=5, seed=0)
    df.loc[df.index[0], "fit_asof"] = df.loc[df.index[0], "ts"] + 60
    with pytest.raises(disagree.LookAheadError):
        disagree.assert_no_lookahead(df)
    with pytest.raises(disagree.LookAheadError):
        disagree.build_disagreement_set(df, disagree.BandRule.MID_OUTSIDE_FIT_BAND)


def test_a_staled_fit_scores_worse_than_the_honest_one():
    """Negative control: if staling the fit does not hurt, the edge is a join artefact."""
    rng = np.random.default_rng(3)
    n_t, n_ev = 40, 30
    rows = []
    for e in range(n_ev):
        path = np.clip(0.5 + np.cumsum(rng.normal(0, 0.03, n_t)), 0.05, 0.95)
        value = rng.uniform()
        for t in range(n_t):
            rows.append(dict(event_id="E%02d" % e, ticker="E%02d-B0" % e,
                             ts=1_700_000_000 + 60 * t, bid=100 * path[t] - 1,
                             ask=100 * path[t] + 1, fit_mean=path[t],
                             fit_lo=path[t] - 0.02, fit_hi=path[t] + 0.02,
                             fit_asof=1_700_000_000 + 60 * t,
                             settled_yes=int(value < path[-1])))
    df = pd.DataFrame(rows)
    honest = score.brier(df.fit_mean.values, df.settled_yes.values)
    staled = disagree.lag_fit(df, 10)
    lagged = score.brier(staled.fit_mean.values, staled.settled_yes.values)
    assert honest < lagged


# --- the disagreement set -----------------------------------------------------

def test_one_sided_brackets_are_excluded():
    df = make_frame(n_events=10, seed=0)
    df.loc[df.index[:5], "bid"] = np.nan
    out, cuts = disagree.build_disagreement_set(df, disagree.BandRule.MID_OUTSIDE_FIT_BAND)
    assert cuts["rows_two_sided"] == len(df) - 5
    assert out.bid.notna().all() and out.ask.notna().all()


def test_mid_inside_the_band_is_not_a_disagreement():
    df = pd.DataFrame([dict(event_id="E0", ticker="T0", ts=1, bid=49.0, ask=51.0,
                            fit_mean=0.50, fit_lo=0.45, fit_hi=0.55, fit_asof=1,
                            settled_yes=1)])
    out, cuts = disagree.build_disagreement_set(df, disagree.BandRule.MID_OUTSIDE_FIT_BAND)
    assert cuts["rows_disagreement"] == 0 and len(out) == 0


def test_the_two_band_readings_select_different_sets():
    """The §1B ambiguity is real, not pedantic: a skewed band splits the readings.

    Band [0.48, 0.90] around a fair value of 0.50 — a right-skewed density, which
    is the normal shape near a tail strike. A midpoint of 0.45 sits just OUTSIDE
    the fitter's interval (so reading A calls it a disagreement) while being far
    closer to the fair value than the band's half-width of 0.21 (so reading B
    does not). The two readings therefore select different observations, and the
    choice between them is capable of moving Test A.
    """
    df = pd.DataFrame([dict(event_id="E0", ticker="T0", ts=1, bid=44.0, ask=46.0,
                            fit_mean=0.50, fit_lo=0.48, fit_hi=0.90, fit_asof=1,
                            settled_yes=1)])
    a = disagree.disagreement_mask(df, disagree.BandRule.MID_OUTSIDE_FIT_BAND).iloc[0]
    b = disagree.disagreement_mask(df, disagree.BandRule.FIT_OUTSIDE_MID_BAND).iloc[0]
    assert bool(a) is True and bool(b) is False, \
        "the two readings must be shown to differ, or the flag is noise"


def test_band_rule_has_no_default():
    with pytest.raises(TypeError):
        disagree.build_disagreement_set(make_frame(n_events=2))  # type: ignore[call-arg]


def test_cuts_report_n_at_every_stage():
    df = make_frame(n_events=20, seed=1)
    _, cuts = disagree.build_disagreement_set(df, disagree.BandRule.MID_OUTSIDE_FIT_BAND)
    for k in ("rows_in", "events_in", "rows_settled", "rows_two_sided",
              "rows_with_fit", "rows_disagreement", "events_disagreement"):
        assert k in cuts


# --- first to move ------------------------------------------------------------

def _mask(rows):
    return np.array(rows, dtype=bool)


def test_first_to_move_basic_cases():
    # bracket 0 moves at minute 2, bracket 1 at minute 4 -> 0 is first at t=5
    m = _mask([[0, 0], [0, 0], [1, 0], [0, 0], [0, 1], [0, 0]])
    assert firstmove.first_to_move(m, 5, 0)[0] == "first"
    assert firstmove.first_to_move(m, 5, 1)[0] == "not_first"


def test_ties_resolve_to_not_first():
    """§1B: simultaneous repricing is a batch update — precisely nothing to catch."""
    m = _mask([[0, 0], [1, 1], [0, 0]])
    assert firstmove.first_to_move(m, 2, 0)[0] == "not_first"
    assert firstmove.first_to_move(m, 2, 1)[0] == "not_first"


def test_no_event_in_window_is_not_a_verdict():
    m = _mask([[0, 1], [0, 0], [0, 0]])
    assert firstmove.first_to_move(m, 2, 0)[0] == "no_event"


def test_window_w_is_respected():
    """An event older than W minutes is outside the preceding window."""
    n = 40
    m = np.zeros((n, 2), dtype=bool)
    m[1, 0] = True          # bracket 0 moved long ago
    m[38, 1] = True         # bracket 1 moved just now
    assert firstmove.first_to_move(m, 39, 0, W=15)[0] == "no_event"
    assert firstmove.first_to_move(m, 39, 1, W=15)[0] == "first"
    assert firstmove.first_to_move(m, 39, 0, W=39)[0] == "first"


# --- the p95 event threshold --------------------------------------------------

def _ladder(n=400, m=4, seed=0):
    rng = np.random.default_rng(seed)
    steps = rng.choice([-1.0, -0.5, 0.0, 0.0, 0.5, 1.0], size=(n, m))
    mid = 50.0 + np.cumsum(steps, axis=0)
    spread = np.full((n, m), 2.0)
    return mid, spread


def test_thin_ladder_is_skipped():
    mid, spread = _ladder(n=20, m=2)
    with pytest.raises(firstmove.LadderSkipped):
        firstmove.event_mask(mid, spread)


def test_thin_bracket_borrows_pooled_distribution_and_is_flagged():
    mid, spread = _ladder(n=400, m=4, seed=1)
    mid[1:, 3] = mid[0, 3]  # bracket 3 barely moves
    _, info = firstmove.event_mask(mid, spread)
    assert info["fallback"][3]
    assert info["n_fallback_brackets"] >= 1


def test_realised_share_exceeds_five_percent_because_of_ties():
    """§1B: label by the percentile cleared, not by an assumed share."""
    mid, spread = _ladder(n=600, m=4, seed=2)
    _, info = firstmove.event_mask(mid, spread)
    assert info["realised_share"] > 0.05


def test_wide_spreads_are_not_moves():
    mid, spread = _ladder(n=400, m=4, seed=3)
    wide = np.full_like(spread, 50.0)
    with pytest.raises(firstmove.LadderSkipped):
        firstmove.event_mask(mid, wide)  # nothing is tight -> no changes at all


# --- Test B classification ----------------------------------------------------

def test_laggard_and_leader_classification():
    assert testb.classify(0.40, 0.45, 0.50) == "laggard"   # moved toward the fit
    assert testb.classify(0.40, 0.35, 0.50) == "leader"    # moved away
    assert testb.classify(0.40, 0.40, 0.50) == "flat"


def test_residual_control_removes_the_underlying():
    """A move fully explained by the underlying is a trend, not a convergence."""
    raw = testb.classify(0.40, 0.45, 0.50)
    res = testb.classify_residual(0.40, 0.45, 0.50, und_t=0.0, und_th=0.05, beta=1.0)
    assert raw == "laggard" and res == "flat"


def test_laggard_share_excludes_flat_and_missing():
    s = testb.laggard_share(["laggard"] * 6 + ["leader"] * 4 + ["flat", "missing"])
    assert s["decided"] == 10 and s["share"] == pytest.approx(0.6)
    assert s["flat"] == 1 and s["missing"] == 1


def test_share_ci_clusters_on_event():
    ev = np.repeat([f"E{i}" for i in range(40)], 5)
    succ = np.repeat(np.random.default_rng(0).integers(0, 2, 40), 5)
    out = score.share_ci(succ, ev, n_boot=300, seed=0)
    assert out["n_events"] == 40 and out["n_rows"] == 200


# --- the staging gate ---------------------------------------------------------

def test_staging_gate_blocks_when_the_minute_store_is_absent(tmp_path):
    with pytest.raises(stores.StagingGap) as e:
        stores.check_staging(tmp_path)
    assert "one-minute candle store is not staged" in str(e.value)


def test_staging_gate_accepts_a_well_formed_store(tmp_path):
    (tmp_path / stores.CANDLES_SUBPATH).mkdir(parents=True)
    (tmp_path / stores.MARKETS_SUBPATH).mkdir(parents=True)
    assert stores.check_staging(tmp_path) == tmp_path


def test_live_collector_store_is_off_limits():
    """A collector is running under launchd; phase 0.5 must never touch its output."""
    for name in ("depth", "touch", "price_ranges", "incentive", "live_books"):
        with pytest.raises(PermissionError):
            stores.assert_not_live(stores.MM_ROOT / "data" / name / "x.parquet")


def test_phase05_does_not_write_outside_its_own_directory():
    """Guard against the protocol's 'may not modify ladder/, waves/, wti_arb/synth' rule."""
    src = (stores.MM_ROOT / "phase05").rglob("*.py")
    for f in src:
        text = f.read_text()
        for forbidden in ("ladder/", "waves/", "wti_arb/synth/"):
            assert "open(%r" % forbidden not in text
            assert ".to_parquet('../%s" % forbidden not in text
