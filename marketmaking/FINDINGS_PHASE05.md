# FINDINGS — Phase 0.5 (PROTOCOL §1B)

**Date:** 2026-10-18
**Branch:** `claude/gracious-edison-s2s7t5`
**Protocol:** `marketmaking/PROTOCOL.md` §1B, committed `132ce8c` before any phase 0.5 data was read. Not modified by this run.

---

## Verdict

> ### Test A: **NOT RUN — BLOCKED on data staging.**
> ### Test B: **not reached** (§1B gates it on Test A passing).

**This is not a FAIL and must not be read as one.** A FAIL is a measurement: the
fit was scored against the quote and lost. Nothing was scored here. The
disagreement set §1B defines cannot be constructed from the data phase 0.5 is
permitted to read, because the required store is not staged. No inference about
the fit — favourable or unfavourable — is licensed by this document.

The honest summary is: **the gate is built, tested, and ready; the data it
scores is not present in this clone.**

---

## 1. Why Test A could not run

§1B fixes the unit of observation:

> "The unit is a **(bracket, minute)** observation on a settled ladder where…
> both a bid and an ask exist… Fair value is scored against the **quote midpoint
> of executable bid/ask**… The fit at time *t* is constructed from quotes
> available at or before *t*."

That requires a **quote time series on a one-minute grid**. Three things must
exist per observation: the bracket's executable bid/ask *at minute t*, the fit's
fair value and credible band *as of ≤ t*, and the realised settlement. The first
two are time-indexed.

Phase 0.5 is restricted (by the run's constraints) to `marketmaking/data/_import/`.
That directory contains, in full:

| File | Size | What it is |
|---|---:|---|
| `waves_data_discovery_markets.parquet` | 92.7 MB | **Snapshot.** 5,232,426 rows, 5,232,426 unique tickers — exactly one row per market. No observation timestamp. |
| `waves_data_discovery_events.parquet` | 22.2 MB | Event-level metadata (ladder flags, market counts). No quotes. |
| `waves_data_summary.csv` | 44 KB | Per-series **aggregates**: candle *counts* and first/last candle timestamps. |
| `ladder_results_summary.parquet` | 336 KB | Per-event **aggregates** (2,194 rows): minute counts, violation histograms. |
| `waves_data_pull_series.txt` | 8 KB | Series list. |

The discovery store carries `yes_bid`/`yes_ask`, but **one row per ticker with no
observation timestamp** — a single snapshot at discovery time. For a settled
market that snapshot is taken at or after close, so it is simultaneously
degenerate (one point, no path) and look-ahead contaminated. It cannot produce a
fit at *t*, a quote midpoint at *t*, or the 5/30/60-minute path Test B needs.

**What is missing** is the one-minute candle tree plus its markets table, in the
shape `ladder/store.py` already reads:

```
<root>/parquet/kalshi_candles/period=1/series=*/event=*/part.parquet
<root>/parquet/kalshi_markets/series=*/part.parquet
```

This is by design, not by accident. `.gitignore` states it plainly:

```
# --- collector data stores: tens of GB, live outside git ---
# Phases 1-2 collect fresh data; historical stores transfer separately.
waves_data/
ladder/data/
```

The transfer into `_import/` brought the summaries and the discovery snapshots.
It did not bring the candle trees. **The staging is incomplete relative to §1B,
not the protocol unsatisfiable.** The data exists; it is one copy away.

`phase05/stores.py::check_staging()` is a hard gate that reproduces this
diagnosis on demand; `python -m phase05.run --band-rule …` exits 2 with it.

---

## 2. What a staged run would have to work with (measured, from `_import/`)

These numbers come from the staged metadata and are real, so the staging
decision can be made on evidence rather than hope.

**§1A primary universe — the 51 `KXHIGH*`/`KXLOW*` daily city temperature ladders:**

| Cut | N |
|---|---:|
| Series in the fixed universe (`universe_groups.json`) | 51 |
| …with candle data in the waves pull | **48** |
| …**absent** from the candle store | 3 — `KXHIGHINFLATION`, `KXLOW`, `KXLOWA` |
| Candles across those 48 series | **67,875,049** |
| Events in the candle-store metadata | 16,528 |
| Markets in the candle-store metadata | 96,018 |
| Candle window | 2024-12-30 → 2026-10-09 |

**Settlement availability (discovery snapshot, primary universe):**

| Cut | N |
|---|---:|
| Markets | 18,937 |
| Events | 3,153 |
| Finalized markets | 18,332 |
| **Settled events** | **3,054** |
| Results | `no` 15,277 / `yes` 3,055 — no non-binary values |

So the settled-event population is in the **thousands**, comfortably past the
"a result on 40 events is not a result" bar — *before* the two-sided and
disagreement cuts, which will reduce it by an unknown factor. The disagreement
set's N is the number that will decide whether phase 0.5 is informative, and it
is not knowable until the store is staged.

**Measured clustering penalty.** Brackets per settled event: **mean 6.00**,
median 6, range 6–11. √6.00 = **2.45**. This confirms §1B's stated reason for
banning bracket-level resampling with a real number: a bracket-level bootstrap
would overstate significance by roughly 2.45× on this universe. The test suite
demonstrates the same effect directly on fixtures.

**Note on the settlement source.** The candle-store metadata reports 16,528
events for these series while the discovery snapshot holds 3,153. The discovery
snapshot is the *narrower* source. A staged run should therefore join settlement
from the store's own `kalshi_markets` table, not from the discovery parquet, or
it will silently discard ~80% of the available events.

---

## 3. The one definitional ambiguity — a ruling is needed before Test A runs

§1B's second disagreement bullet:

> "the fit's fair value lies **outside the fit's own credible band** relative to
> the quote midpoint. The band is the fitter's existing interval; phase 0.5 does
> not invent a new one."

**Taken literally this is never true.** The fitter's fair value (`pq_mean`) lies
inside its own 5th–95th interval by construction. The clause "relative to the
quote midpoint" must be doing the work, and it can do it two ways:

| Reading | Rule | Comment |
|---|---|---|
| **A** `mid_outside_fit_band` | `mid < fit_lo` or `mid > fit_hi` | Band stays where the fitter put it; asks whether the market's price is inside it. Consistent with "the band is the fitter's existing interval; phase 0.5 does not invent a new one." |
| **B** `fit_outside_mid_band` | `\|fit_mean − mid\| > (fit_hi − fit_lo)/2` | Matches the sentence's word order more literally, but re-centres the interval on the quote — arguably "inventing a new one". |

**These select different observations, and the difference is not pedantic.** On a
right-skewed density — the normal shape near a tail strike — band `[0.48, 0.90]`
around a fair value of `0.50`: a midpoint of `0.45` is *outside* the fitter's
interval (A: disagreement) while sitting far closer to fair value than the
half-width of 0.21 (B: not a disagreement). This case is pinned in
`tests/test_phase05.py::test_the_two_band_readings_select_different_sets`.

Because the choice is capable of moving Test A's result, **phase 0.5 has not
resolved it.** `disagree.build_disagreement_set` requires `band_rule` explicitly
and has **no default**; `run.py` requires `--band-rule`. Per the instruction to
stop on genuine ambiguity rather than pick the reading that happens to help,
this needs the protocol author's ruling. Reading A is the conventional one and
the one the sentence's second half supports, but that is an argument, not a
decision.

**Secondary, smaller assumptions, all flagged in code:**

- **Log-score clipping.** §1B does not specify an epsilon. A stated probability
  of exactly 0 or 1 makes the log score infinite and one such row would decide
  the secondary test alone. `score.py` clips at `1e-6` and exposes it. Sensitivity
  to this must be reported in any real run. *Assumed, not measured.*
- **Test B window endpoints.** §1B says "a preceding window of W = 15 minutes"
  without fixing endpoints. `firstmove.py` uses the inclusive `[t−W, t]`. The
  alternative differs by one minute. *Assumed.*
- **Test B residual beta.** §1B requires the laggard share "residual to the
  underlying". The bracket's sensitivity to CL is an estimate;
  `classify_residual` defaults to `beta=1.0` in probability-per-underlying-unit,
  which is a placeholder, not a measurement. A real run must estimate beta per
  bracket or report the control as indicative only.

---

## 4. Substitutes considered and declined

Two datasets in the repo could have produced *a* number. Running either and
calling it Test A would have been wrong, and I did not.

**`wti_arb/synth/results_backtest/brackets_KXWTI.csv` and `…KXWTIW.csv`.** These
genuinely contain fit fair value (`pq_mean`), the fitter's own credible band
(`pq_q05`, `pq_q95`, `band90`), the Kalshi quote (`kalshi_bid`, `kalshi_ask`) and
settlement (`settled_yes`) — 2,202 two-sided bracket rows over 105 settle-dates.
It is tempting. It is also not Test A, for four independent reasons:

1. **Wrong unit.** Two snapshots per event (`T-1d`, `T-4h`), not the
   (bracket, minute) grid §1B specifies. Test B's 5/30/60-minute paths are
   impossible outright.
2. **Wrong universe.** KXWTI and KXWTIW only. §1A fixes the primary universe as
   the 51 temperature ladders; §1B's Test B refers to "the two WTI series" as a
   *subset* needing a special control, not as the population.
3. **Already-seen data.** These rows are cached output of a prior study that has
   been read, reported on, and whose thesis was killed in
   `_audit/NIGHTKING_AUTOPSY.md`. §1B's entire value comes from being committed
   before its data was read. Scoring it against already-examined data destroys
   exactly the property the `132ce8c` commit ordering was created to preserve.
4. **N.** 105 event-days before any disagreement cut, against a stated bar that
   40 events is not a result.

**The discovery snapshot's `yes_bid`/`yes_ask` against `result`.** One snapshot
per settled market, taken at or after close. This is a look-ahead-contaminated
single point, and §1B calls any use of *t+* data run-invalidating.

Declining both is the protocol working, not the protocol being obstructed.

---

## 5. What was built

All new code in `marketmaking/phase05/`. Nothing under `ladder/`, `waves/`,
`wti_arb/synth/` or `PROTOCOL.md` was modified; `ladder.store` is imported
read-only. The live collector (`com.nightking.mm.collector`, pid 45417 at time
of writing) was not touched, and no file under `data/depth|touch|price_ranges|
incentive|live*` was read or written.

| Module | Role |
|---|---|
| `stores.py` | Staging gate; `assert_not_live()` refuses live-collector paths. |
| `disagree.py` | §1B disagreement set; `BandRule` with **no default**; `assert_no_lookahead` is a hard error; `lag_fit` negative control. |
| `score.py` | Brier, log score, **event-clustered** bootstrap, `test_a_verdict` with §1B's pass rule. |
| `firstmove.py` | §1B "first to move": per-bracket p95, pooled fallback <50 changes, ladder skip, W=15, **ties → not first**. Conventions transcribed from `waves/census.py`. |
| `testb.py` | Laggard/leader, residual-to-underlying control, laggard share. |
| `run.py` | Driver. Exits 2 at the staging gate; refuses to run without `--band-rule`. |

**Test suite: 47 passed** (`../.venv/bin/python -m pytest tests/ -q` from
`marketmaking/`; 17 pre-existing invariants + 30 new). The new tests are the
pipeline sanity checks §1B's rigor requirements demand, on fixtures with known
ground truth:

- **The bootstrap clusters on event, verified two ways.** Duplicating every row
  within an event 8× leaves the interval *exactly* unchanged (an event repeated
  carries no new information); and the forbidden bracket-level bootstrap is
  shown to be strictly narrower on the same data — the overstatement §1B bans.
  A third test scrambles the event labels and confirms the interval moves, so
  the function demonstrably reads the field it claims to.
- **The gate can fail.** Test A returns PASS on a fixture where the fit is the
  true probability and FAIL where the fit is noise. A gate that cannot fail is
  not a gate.
- **Look-ahead.** `fit_asof > ts` raises, and a deliberately staled fit is shown
  to score worse than the honest one — so a spurious "edge" from a bad join
  would be visible.
- **First to move.** Ties resolve to *not* first; the W boundary is enforced;
  the p95 realised share is confirmed to exceed 5% on the discrete half-cent
  grid, per §1B's instruction to label by percentile cleared rather than assumed
  share; thin ladders raise and thin brackets are flagged as pooled fallbacks.

---

## 6. Limitations

1. **The headline limitation: Test A was not run.** Everything in §2 is
   *available* data, not *scored* data. The disagreement set's N — the number
   that decides whether phase 0.5 can conclude anything — is unknown.
2. **The fit side has not been exercised at all.** This run never constructed a
   fair value or a credible band from `wti_arb/synth/`. Whether that extractor
   can even be driven across the 48 temperature ladders at one-minute cadence is
   **untested and should not be assumed** — it was built for WTI against CME
   option chains. If it cannot produce a band for a temperature ladder, §1B's
   disagreement set has no fit side and phase 0.5 needs a prior step nobody has
   scoped. *This is the largest unknown in the plan and it is unaddressed.*
3. **"Credible band" may not mean what §1B assumes.** §1B says "the band is the
   fitter's existing interval". In the WTI backtest that interval is `pq_q05`/
   `pq_q95` — a **90% interval**, labelled `band90`. §1B never states a coverage
   level, so the disagreement threshold inherits whatever the fitter emits. A
   90% band and a 95% band give materially different disagreement sets and
   therefore different Test A results. **Flagging loudly:** the coverage level
   should be fixed explicitly before the run, or the pass/fail is partly an
   artefact of an unstated choice.
4. **Settlement join caveat, measured.** Of 3,054 settled primary-universe
   events, 3,052 have exactly one YES bracket. The two exceptions
   (`KXLOW-26AUGCOMP`, 3 YES; `KXLOW-26AUGTXN`, 0 YES) are **not errors** — they
   are *cumulative* threshold ladders, where a monotone YES→NO staircase (or an
   all-NO outcome below the lowest threshold) is correct. `ladder/store.py`
   already distinguishes `cumul` from `range`. Any settlement validation must
   respect ladder kind; a naive "exactly one YES" check will wrongly reject
   cumulative ladders. Both affected events are in `KXLOW`, one of the three
   series absent from the candle store anyway.
5. **Three universe series have no candle data** (`KXHIGHINFLATION`, `KXLOW`,
   `KXLOWA`), so a staged run covers 48 of the 51 §1A series. That exclusion is
   a property of the pull, not a choice made here, and should be stated in any
   result.
6. **The CL futures control for Test B is unverified.** §1B relies on "the CME
   intraday bars already bought". `wti_arb/data_cme/` contains findings and a
   manifest, but `data_cme/parquet/` and `data_cme/raw/` are gitignored and not
   present. The underlying control is therefore also unstaged — though since
   Test B applies it only to the two WTI series, and the §1A primary universe is
   temperature, its scope in a staged run is unclear and worth a ruling too.
7. **Bootstrap draws default to 10,000** with a fixed seed; intervals are
   percentile, not BCa. For a difference near zero the percentile interval is
   the weaker choice, and a borderline Test A result should be re-checked with
   BCa before being believed.

---

## 7. What is needed to run phase 0.5

1. **A ruling on the band sentence** (§3 above) — reading A or B. Blocking.
2. **Stage the candle + markets trees** for the 48 covered §1A series into
   `marketmaking/data/_import/`, in the layout of §1. ~68M candles; the full
   waves store is tens of GB, so a universe-filtered subset is preferable.
3. **Confirm the extractor can produce a fair value and credible band for
   temperature ladders** at one-minute cadence (limitation 2). If it cannot,
   phase 0.5 as written does not apply to the §1A primary universe and the
   protocol needs amending before, not after, any number is produced.
4. **Fix the band's coverage level explicitly** (limitation 3).

Then `python -m phase05.run --band-rule <ruling>` from `marketmaking/`, after
wiring `load_observations` to the staged tree.

---

## 8. One line

**The fit was never asked the question.** The gate that would ask it is written,
tested and refuses to guess; the data it needs is one staged copy and one
definitional ruling away.
