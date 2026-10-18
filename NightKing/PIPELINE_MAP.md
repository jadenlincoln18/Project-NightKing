---
tags: [nightking, pipeline, architecture]
---

# NightKing — Pipeline Selection Map

The 20-stage specification in [[nightking-strategy-writeup]] is the **menu**.
This is the **order**: which stages are in the build, which are validation only,
which are deliberately skipped, and why.

Written after data collection completed and every precondition cleared.
Reasoning and rejected alternatives live in [[PIPELINE_CHOICES]].

---

## The pipeline

![[Pipeline.canvas]]

> Open the canvas directly for panning and zooming: [[Pipeline.canvas]]

**Reading the colours.** Green is in the build. Yellow is validation only — the
SVI smile route runs as an independent cross-check but never produces the
density that gets traded. Violet are the gates that drop a date before any
computation. Orange are diagnostics that run alongside, including Gate 4 (chain
consistency), which skips a date whose own strikes disagree with each other.
Red are exits and open problems.

---

## Per-date decision flow and build order

![[Decision-Flow.canvas]]

> [[Decision-Flow.canvas]]

The left board is what happens to a single Kalshi settlement date. The right
board is the build sequence, and the distinction drawn on it is the one that
matters most:

**Step 1 failing is a bug. Step 3 failing is a result.**

The synthetic test is the only stage with an answer key, so a failure there is
debuggable. The backtest has no answer key — so if the gap does not beat band
plus friction, that is the finding, and re-tuning the pipeline afterward is how
you fit noise. With ~34 effective observations, post-hoc adjustment is
indistinguishable from overfitting.

---

## Selection summary

| stage | status | one-line reason |
|---|---|---|
| 1–4 | **foundation** | the identity and its three checks; not code, but everything rests on them |
| 5 | **rejected as estimator** | noise 25× signal at $0.25 strike spacing |
| 6 | **IN, revised** | forward = the futures level at the snapshot instant (1-minute CL bars in the backtest, live CL quote in production); parity regression demoted to a check; quotes synchronised along the real intraday path before fitting (Stage 6a, `synth/sync.py`; the options-implied reconstruction is the fallback) |
| 7 | **IN** | Black-76 as coordinate change, not model |
| 8 | **IN** | OTM only; kills vega collapse and American contamination |
| 9 | **validation only** | SVI smile, run as an independent cross-check |
| 10 | **folded into 9** | constraints in the optimizer, not a post-hoc check |
| 11 | **IN, revised** | `exp(spline)` makes illegal densities unrepresentable; **48 uniform knots** (was 24 — too coarse to represent a bimodal trough; `FINDINGS_PRIOR.md`) |
| 12 | **IN + hyperprior** | tails are prior-dominated; τ integrated out by quadrature; heavy-tailed / local-scale forms tested and rejected (no gain, worse mixing) |
| 13 | **IN, revised** | integrate forward — the whole reason Act III exists; tolerance = max(half-spread, 1¢) on real chains (`FINDINGS_TICKFLOOR.md`) |
| 14 | **IN** | free constraint, catches the most dangerous artifact |
| 15 | **IN** | NUTS preferred; convergence diagnostics are load-bearing |
| 16 | **IN, corrected** | ranges *and thresholds*, not points: a bracket is $D(a)-D(b)$ (four legs), a threshold "Above $X" is $D(a)$ (two legs); KXWTI's daily ladder is an ICE-settled threshold ladder and is in the study (`FINDINGS_LEGCOUNT.md`) |
| 17 | **IN** | exact bracket edges |
| 18 | **IN** | required because the hedge is never perfect |
| 19 | **IN** | the trade filter |
| 20 | **IN** | 4-leg replication, Micro WTI where available |
| Gate 4 | **IN** (replaced) | split-half Act III consistency over the ladder + leave-one-out residuals; Act II vs Act III reported, not gating |

---

## What is deliberately not in the pipeline

| excluded | why |
|---|---|
| **raw finite-difference density** | measured: 25× noise at real strike spacing |
| **`bbo-1s` / `bbo-1m` data** | TBBO measured sufficient; saves ~$1,835 |
| **ICE options chain** | licence required, and the basis is zero — no reason to want it |
| **Pyth-settled series** (Brent, gold, natgas) | no specific contract to hedge against; pending a `rules_primary` read |
| **intraday Kalshi series** | no CME option expires hourly; Case 1 unavailable by construction |
| **KXWTI Tue/Thu dates** | 53 dates with no same-day CME weekly |
| **pre-2026 history** | median bracket volume 0 through the dead zone |
| **Case 2 (directional)** | requires knowing P vs Q; the trap |
| **intraday exit** | thin book means exit is not guaranteed |
| **Polymarket** | no bracket ladders exist |

---

## The backtest (October 2026)

`BACKTEST_PROTOCOL.md` was committed before any Kalshi price was read; `FINDINGS_BACKTEST.md` is the result and
`BACKTEST_NEXT_PASS.md` the questions it leaves. Mechanical verdict on the pre-stated bar: **STRUCTURE, NOT AN EDGE.**
Kalshi's executable bracket prices agree with the Act III density to within a cent on 535 brackets across 24 cleared
KXWTIW weeks (mean gap +0.2¢, mean |gap| 1.1¢); Stage 18's favourite–longshot b ≈ 0.63 is real in logit space and worth
one tick in cents; no bracket clears band + friction because the CL replication, priced leg by leg from the live book
(`bbo-1m` at the snapshot minute, `FINDINGS_LEGCOUNT.md`), costs 21–25¢ per Kalshi dollar for a four-leg bracket and
15¢ for a two-leg threshold, not the ~5¢ the writeup assumed; the nearest miss is 1.6 points. Two data rules were added
before the verdict: Gate 0b verified ex post against the settlement value (three weeks had Kalshi settling on a
different delivery month than the calendar rule assigned), and legs priced from the sampled book rather than the
TBBO's trade-attached quotes, which had marked 44% of brackets unquoted when every leg was live. Stage 19 and 20 are
therefore **IN, tested, nothing passed**: the filter ran on executable quotes on both sides.

## Open problems

**The replication costs more than the gap.** 7–30¢ per Kalshi dollar against gaps of a cent (`FINDINGS_BACKTEST.md`
§1). First item of `BACKTEST_NEXT_PASS.md`; nothing downstream matters until it moves.

**Executable CME prices.** TBBO carries a BBO only at trade instants; `bbo-1m` or `mbp-1` on the ~30 settlement windows
would price the hedge. Declined once to save ~$1,835; now the binding data gap.

**MCO expires monthly only.** Micro WTI is what makes the depth work — 50
contracts clears every moderate-tail bracket on both sides, while 500 fails on
the ask side in 6 of 9. But weekly Kalshi dates need a weekly option expiry, and
only standard CL lists one. The two requirements collide: **Micro has the right
size and the wrong expiry; the weeklies have the right expiry and too large a
size.** Resolve before the backtest, since it determines what position sizes the
backtest should simulate.

**June 15, −$4.70.** One unexplained ICE/NYMEX divergence, one day before
Kalshi's roll date. Blocks sizing, not the backtest.

**Session-long depth.** All depth evidence is one snapshot plus lifetime volume.
Needed before sizing.

---

## Related

- [[PIPELINE_CHOICES]] — reasoning and rejected alternatives per stage
- [[nightking-strategy-writeup]] — full theory, 20 stages in detail
- `data_cme/FINDINGS_BASIS.md` — the zero-basis result
- `data_cme/FINDINGS_CHAIN.md` — root selection, TBBO density
- `FINDINGS_REALCHAIN.md`, `FINDINGS_REALCHAIN_V2.md`, `FINDINGS_REALCHAIN_V3.md` — the extractor on real chains: V1, the Stage 6 / Gate 4 revision, the real intraday path
- `FINDINGS_ACTII_V2.md` — Act II's firing rate on synchronised chains and its overlap with the split-half gate
- `FINDINGS_PRIOR.md`, `FINDINGS_REALCHAIN_V4.md` — the prior-form candidates, the knot-count finding, and the 48-knot model on the real chains
- `FINDINGS_TICKFLOOR.md`, `FINDINGS_SYNTHETIC_V2.md` — the tick floor vs the exclusion rule, and the definitive synthetic study at 48 knots (24 vs 48 side by side)
- `BACKTEST_PROTOCOL.md`, `FINDINGS_BACKTEST.md`, `BACKTEST_NEXT_PASS.md` — the pre-registered bar, the first Kalshi-vs-density comparison, and what it leaves open
