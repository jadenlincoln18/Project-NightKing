"""The §1B disagreement set.

§1B defines the unit as a (bracket, minute) observation on a settled ladder where:

  - "the bracket is two-sided and executable — both a bid and an ask exist.
     Fair value is scored against the quote midpoint of executable bid/ask,
     never last trade, which is stale and not transactable."
  - "the fit's fair value lies outside the fit's own credible band relative to
     the quote midpoint. The band is the fitter's existing interval; phase 0.5
     does not invent a new one."
  - "No look-ahead. The fit at time t is constructed from quotes available at
     or before t."

=== THE ONE DEFINITIONAL AMBIGUITY, UNRESOLVED ON PURPOSE =====================

The second bullet does not have a single implementable reading, and the two
readings select different observations. Taken literally, "the fit's fair value
lies outside the fit's own credible band" is never true: the fitter's fair value
(`pq_mean`) sits inside its own 5th-95th interval by construction. The clause
"relative to the quote midpoint" has to be doing work, and it can do it two ways:

  BandRule.MID_OUTSIDE_FIT_BAND
      Disagreement iff the QUOTE MIDPOINT falls outside the fit's credible band:
          mid < fit_lo  or  mid > fit_hi
      The band stays centred where the fitter put it and the market's price is
      asked whether it is inside it. This is the reading consistent with "the
      band is the fitter's existing interval; phase 0.5 does not invent a new
      one", and it is the conventional one.

  BandRule.FIT_OUTSIDE_MID_BAND
      Disagreement iff the fit's fair value is further from the midpoint than
      the band's half-width:
          |fit_mean - mid| > (fit_hi - fit_lo) / 2
      The band is translated onto the quote. This matches the sentence's word
      order more literally, but it re-centres the fitter's interval, which is
      arguably "inventing a new one".

On an asymmetric band these select materially different sets, and the choice is
capable of flattering Test A. PROTOCOL §1B is the bar and is not ours to move,
so this module REFUSES TO DEFAULT: `band_rule` is a required argument. Phase 0.5
must not resolve this by fiat; it is reported to the protocol's author for a
ruling, per the instruction to stop on genuine ambiguity rather than pick the
reading that happens to help.
"""
from __future__ import annotations

import enum

import numpy as np
import pandas as pd


class BandRule(str, enum.Enum):
    MID_OUTSIDE_FIT_BAND = "mid_outside_fit_band"
    FIT_OUTSIDE_MID_BAND = "fit_outside_mid_band"


REQUIRED_COLUMNS = (
    "event_id",   # settlement cluster: all brackets of one event share one outcome
    "ticker",     # bracket
    "ts",         # observation minute (epoch seconds), the "t" of §1B
    "bid",        # executable yes bid, cents
    "ask",        # executable yes ask, cents
    "fit_mean",   # fitter's fair value, probability in [0, 1]
    "fit_lo",     # fitter's own credible band, lower, probability
    "fit_hi",     # fitter's own credible band, upper, probability
    "fit_asof",   # the latest quote timestamp the fit at `ts` was allowed to see
    "settled_yes",  # realised binary outcome, 0/1
)


class LookAheadError(AssertionError):
    """Raised when a fit was built from data later than the minute it is scored at.

    §1B: "Any accidental use of t+ data invalidates the run." This is a hard
    error, never a warning, and never silently dropped rows.
    """


def assert_no_lookahead(df: pd.DataFrame) -> None:
    """Hard gate: every fit must be as-of at or before the minute it is scored at."""
    bad = df[df["fit_asof"] > df["ts"]]
    if len(bad):
        raise LookAheadError(
            "%d of %d rows have fit_asof later than the scored minute ts "
            "(max leak %.0fs). §1B: any accidental use of t+ data invalidates the run."
            % (len(bad), len(df), float((bad["fit_asof"] - bad["ts"]).max()))
        )


def executable_two_sided(df: pd.DataFrame) -> pd.Series:
    """Both a bid and an ask exist and are transactable.

    Kalshi encodes an empty side as bid=0 / ask=100; `ladder.store.build_grid`
    already maps those to NaN, but this re-checks so the predicate is correct on
    any input frame. No spread cap: §1B imposes tightness on Test B's move
    definition, not on Test A's disagreement set, and adding one here would be
    moving the bar.
    """
    b, a = df["bid"], df["ask"]
    return (b.notna() & a.notna() & (b > 0) & (a < 100) & (a >= b))


def quote_mid_prob(df: pd.DataFrame) -> pd.Series:
    """Quote midpoint of executable bid/ask, as a probability. Never last trade."""
    return (df["bid"] + df["ask"]) / 200.0


def disagreement_mask(df: pd.DataFrame, band_rule: BandRule) -> pd.Series:
    """The §1B band test under an explicitly chosen reading. No default."""
    rule = BandRule(band_rule)
    mid = quote_mid_prob(df)
    if rule is BandRule.MID_OUTSIDE_FIT_BAND:
        return (mid < df["fit_lo"]) | (mid > df["fit_hi"])
    half = (df["fit_hi"] - df["fit_lo"]) / 2.0
    return (df["fit_mean"] - mid).abs() > half


def build_disagreement_set(df: pd.DataFrame, band_rule: BandRule,
                           check_lookahead: bool = True) -> tuple[pd.DataFrame, dict]:
    """Apply the §1B filters in order and return the set plus the N at every cut.

    The cut counts are returned, not logged, because §1B reporting requires the
    N at every stage and "a result on 40 events is not a result".
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("missing required columns: %s" % ", ".join(missing))

    cuts = {"rows_in": len(df), "events_in": int(df["event_id"].nunique())}

    settled = df[df["settled_yes"].notna()].copy()
    cuts["rows_settled"] = len(settled)
    cuts["events_settled"] = int(settled["event_id"].nunique())

    if check_lookahead:
        assert_no_lookahead(settled)

    two = settled[executable_two_sided(settled)].copy()
    cuts["rows_two_sided"] = len(two)
    cuts["events_two_sided"] = int(two["event_id"].nunique())

    fitted = two[two["fit_mean"].notna() & two["fit_lo"].notna() & two["fit_hi"].notna()].copy()
    cuts["rows_with_fit"] = len(fitted)
    cuts["events_with_fit"] = int(fitted["event_id"].nunique())

    fitted["mid_prob"] = quote_mid_prob(fitted)
    out = fitted[disagreement_mask(fitted, band_rule)].copy()
    cuts["rows_disagreement"] = len(out)
    cuts["events_disagreement"] = int(out["event_id"].nunique()) if len(out) else 0
    cuts["band_rule"] = BandRule(band_rule).value
    cuts["brackets_per_event"] = (
        float(len(out) / cuts["events_disagreement"]) if cuts["events_disagreement"] else float("nan")
    )
    return out, cuts


def lag_fit(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Shift each bracket's fit later by `minutes` — a negative control.

    Used by the pipeline sanity checks: a fit deliberately staled by N minutes
    must not score better than the honest one. If it does, the "edge" is an
    artefact of the join rather than information.
    """
    out = df.sort_values(["ticker", "ts"]).copy()
    cols = ["fit_mean", "fit_lo", "fit_hi"]
    out[cols] = out.groupby("ticker")[cols].shift(minutes)
    return out[out["fit_mean"].notna()].copy()
