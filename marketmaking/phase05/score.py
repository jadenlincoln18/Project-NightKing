"""Test A scoring — Brier, log score, and the event-clustered bootstrap (PROTOCOL §1B).

§1B, verbatim on the points that matter:

  "Primary: Brier score, the mean squared error between stated probability and
   the 0/1 settlement outcome. Lower is better."
  "Secondary: log score. Reported always, including when it disagrees with
   Brier."
  "Clustering. Brackets of one event share a single settlement outcome and are
   therefore *not* independent observations. Bootstrap by event, never by
   bracket. Bracket-level resampling would overstate significance by roughly
   the square root of the brackets per event and is forbidden."

  "Pass: the fit's Brier score is strictly lower than the quote's on the
   disagreement set, with the 95% event-clustered bootstrap interval on the
   difference excluding zero."

Sign conventions used throughout, stated once:
  - Brier: lower is better. The reported difference is `brier_fit - brier_quote`,
    so the fit wins when the difference is NEGATIVE.
  - Log score: reported as mean log-likelihood, so HIGHER is better. The reported
    difference is `logscore_fit - logscore_quote`, so the fit wins when the
    difference is POSITIVE. The two primaries therefore pass with opposite signs;
    this is signposted rather than silently normalised.
"""
from __future__ import annotations

import numpy as np

# §1B does not specify a clipping epsilon for the log score, but a stated
# probability of exactly 0 or 1 makes it infinite and a single such row would
# decide the secondary test on its own. We clip, report the epsilon, and the
# caller is expected to report sensitivity to it. This is an ASSUMPTION, not a
# measurement, and is flagged as such in FINDINGS_PHASE05.md.
DEFAULT_LOG_EPS = 1e-6


def brier(p, y) -> float:
    """Mean squared error between stated probability and the 0/1 outcome."""
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    if p.size == 0:
        return float("nan")
    return float(np.mean((p - y) ** 2))


def log_score(p, y, eps: float = DEFAULT_LOG_EPS) -> float:
    """Mean log-likelihood. Higher is better. Clipped at `eps` (see module docstring)."""
    p = np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)
    y = np.asarray(y, dtype=float)
    if p.size == 0:
        return float("nan")
    return float(np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _group_index(event_id):
    """Row indices grouped by event, in stable first-seen event order."""
    event_id = np.asarray(event_id)
    order = {}
    for i, e in enumerate(event_id):
        order.setdefault(e, []).append(i)
    keys = list(order.keys())
    return keys, [np.asarray(order[k], dtype=np.int64) for k in keys]


def event_clustered_bootstrap(p_fit, p_quote, y, event_id, stat="brier",
                              n_boot: int = 10000, seed: int = 0, eps: float = DEFAULT_LOG_EPS):
    """Bootstrap the fit-minus-quote score difference, RESAMPLING EVENTS.

    The resampling unit is the event, never the bracket: whole events are drawn
    with replacement and all of their bracket-minute rows travel together, so
    the shared settlement outcome stays shared. §1B forbids bracket-level
    resampling because it would overstate significance by roughly the square
    root of the brackets per event.

    Returns a dict with the point estimate, the 95% percentile interval, and the
    cluster counts, so the caller can report N at every cut.
    """
    p_fit = np.asarray(p_fit, dtype=float)
    p_quote = np.asarray(p_quote, dtype=float)
    y = np.asarray(y, dtype=float)
    if not (len(p_fit) == len(p_quote) == len(y) == len(event_id)):
        raise ValueError("p_fit, p_quote, y and event_id must be the same length")

    if stat == "brier":
        def _diff(idx):
            return brier(p_fit[idx], y[idx]) - brier(p_quote[idx], y[idx])
    elif stat == "log":
        def _diff(idx):
            return log_score(p_fit[idx], y[idx], eps) - log_score(p_quote[idx], y[idx], eps)
    else:
        raise ValueError("stat must be 'brier' or 'log'")

    keys, groups = _group_index(event_id)
    n_events = len(keys)
    if n_events == 0:
        return dict(point=float("nan"), lo=float("nan"), hi=float("nan"),
                    n_rows=0, n_events=0, n_boot=0, stat=stat)

    all_idx = np.arange(len(y), dtype=np.int64)
    point = _diff(all_idx)

    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        pick = rng.integers(0, n_events, size=n_events)
        idx = np.concatenate([groups[k] for k in pick])
        draws[b] = _diff(idx)

    lo, hi = np.percentile(draws, [2.5, 97.5])
    return dict(point=float(point), lo=float(lo), hi=float(hi),
                n_rows=int(len(y)), n_events=int(n_events), n_boot=int(n_boot),
                stat=stat, brackets_per_event=float(len(y) / n_events))


def test_a_verdict(p_fit, p_quote, y, event_id, n_boot: int = 10000, seed: int = 0,
                   eps: float = DEFAULT_LOG_EPS) -> dict:
    """The full Test A result and its pass/fail against the §1B threshold.

    Pass requires BOTH:
      - brier_fit strictly below brier_quote, and
      - the 95% event-clustered interval on the difference excluding zero
        (i.e. the upper bound is strictly below zero, since lower Brier is
        better and the difference is fit minus quote).

    The log score is computed and returned always, including when it disagrees
    with Brier, because §1B treats that disagreement as itself a finding.
    """
    p_fit = np.asarray(p_fit, dtype=float)
    p_quote = np.asarray(p_quote, dtype=float)
    y = np.asarray(y, dtype=float)

    bf, bq = brier(p_fit, y), brier(p_quote, y)
    lf, lq = log_score(p_fit, y, eps), log_score(p_quote, y, eps)

    bs = event_clustered_bootstrap(p_fit, p_quote, y, event_id, "brier", n_boot, seed, eps)
    ls = event_clustered_bootstrap(p_fit, p_quote, y, event_id, "log", n_boot, seed, eps)

    passed = bool(bf < bq and bs["hi"] < 0.0)
    return dict(
        n_rows=int(len(y)), n_events=int(bs["n_events"]),
        brier_fit=bf, brier_quote=bq, brier_diff=bs["point"],
        brier_ci=(bs["lo"], bs["hi"]),
        log_fit=lf, log_quote=lq, log_diff=ls["point"], log_ci=(ls["lo"], ls["hi"]),
        log_eps=eps,
        agree=bool((bf < bq) == (lf > lq)),
        passed=passed,
        verdict="PASS" if passed else "FAIL",
    )


def share_ci(successes, event_id, n_boot: int = 10000, seed: int = 0, null: float = 0.5):
    """Event-clustered bootstrap CI for a binary share (Test B's laggard share).

    Same clustering argument as Test A: deviations inside one event are not
    independent, so events are the resampling unit.
    """
    s = np.asarray(successes, dtype=float)
    keys, groups = _group_index(event_id)
    n_events = len(keys)
    if n_events == 0 or s.size == 0:
        return dict(point=float("nan"), lo=float("nan"), hi=float("nan"),
                    n_rows=0, n_events=0, excludes_null=False)
    point = float(np.mean(s))
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        pick = rng.integers(0, n_events, size=n_events)
        idx = np.concatenate([groups[k] for k in pick])
        draws[b] = np.mean(s[idx])
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return dict(point=point, lo=float(lo), hi=float(hi),
                n_rows=int(s.size), n_events=int(n_events),
                excludes_null=bool(lo > null or hi < null))
