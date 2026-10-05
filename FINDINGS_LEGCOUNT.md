# FINDINGS_LEGCOUNT — what the backtest priced per series, the roll rule, and the friction measurement

`NightKing/HANDOFF_legcount_and_friction.md`. Error-correction on `FINDINGS_BACKTEST.md`, under the unchanged
`BACKTEST_PROTOCOL.md` (amendment 7 documents the one fix). Nothing in the extractor, the gates or the thresholds moved.

**Summary.** (A) The daily series was replicated with **two legs from the first run** — the spread term summed the two
legs actually used — but the **fee term was charged for four legs on every structure**, 1.42¢ too much on a threshold.
Corrected and re-processed: every friction number on a two-leg structure falls by 1.4¢, no bracket changes status, no
bracket clears, the verdict stands. (B) The "4–5¢/bbl half-spread" sentence in the first findings was a
mis-generalisation from one trade; the half-spreads the arithmetic actually used are the chain's, and measured on
6,450 TBBO quotes in the snapshot windows they are **median 1.5–2¢/bbl near the money, 0.5¢ below $0.10 of premium
and 4¢ above $1 of premium** — the spread scales with the option's price, and the legs of a near-the-money $1
bracket are $1–2 options at T-1d. A scoped `bbo-1m` pull to replace the trade-sampled number is quoted below and
waits for approval. (C) The roll rule in the docs ("the 16th") was wrong and so is the rules page's "2 business days
before the last trading day" as a predictor; the settlements show the switch one to four business days before the
NYMEX last trading day, and the backtest's ex-post check caught every misassignment. (D) KXWTI is an ICE-settled
threshold ladder and was in the study; KXGOLD is the only other exchange-settled ladder in the store.

---

## A. Leg-count audit

**What the code does.** `synth/backtest.py::structure_spec(lo, hi)` builds the replication from the market's edges:
a "between" bracket $[X, X+1)$ gets the outer condor $C(X-0.5) - C(X) - C(X+1) + C(X+1.5)$ (four legs); a one-sided
market gets the single spread at its edge — "Above $X" is $C(X-0.5) - C(X)$, "$Y or below" is
$0.5 - [C(Y) - C(Y+0.5)]$ — two legs. `structure_quotes` sums the half-spreads of the legs it actually used
(`sum_hs`), and `estimate_leg_hs` estimates them for the spec's strikes. So the **spread term** was right for both
market types. The **fee term** was `4 × $2.37 × 1.5 / 500 = 2.84¢` regardless of leg count.

**What the stored records show** (every two-sided bracket, both snapshots, before the fix):

| series | two-sided brackets | 4 legs | 2 legs | market types | est. friction median (2-leg) | spread / fees / Kalshi fee | implied half-spread per leg |
|---|---:|---:|---:|---|---:|---|---:|
| KXWTIW | 728 | 648 | 80 | between 648, greater 42, less 38 | 8.4¢ | 5.3 / 2.84 / 0.36 | 1.31¢/bbl |
| KXWTI | 1,474 | 5 | 1,469 | greater 1,469, between 5 | 7.8¢ | 4.0 / 2.84 / 0.20 | 1.00¢/bbl |

KXWTI's 1,469 thresholds were priced as two legs of spread (4.0¢ = 2 × 1.0¢ / 0.5) and four legs of fees. The weekly
ladder's 80 tail markets were the same.

**The fix** (amendment 7): `cme_fees_per_contract(n_legs)`, `n_legs × $2.37 × 1.5 / 500` — 1.42¢ on a two-leg
structure. Applied by re-processing the stored extractions (`python3 -m synth.backtest --reprocess`), which touches
nothing upstream of the friction arithmetic. `FINDINGS_BACKTEST.md` is left as the record of the first pass;
`FINDINGS_BACKTEST_V2.md` is the re-render.

**Before / after** (the only rows that moved; every other table is identical):

| table | row | before | after |
|---|---|---|---|
| KXWTI T-4h gap by moneyness, mean friction | deep tail | 8.8¢ | 7.4¢ |
| | moderate tail | 11.4¢ | 10.0¢ |
| | body | 15.5¢ | 14.1¢ |
| | favourite | 9.6¢ | 8.2¢ |
| KXWTIW T-1d, mean friction | body (tails in the body band) | 13.8¢ | 13.0¢ |
| KXWTIW T-4h, mean friction | body | 16.0¢ | 15.3¢ |
| KXWTI T-4h signal record | legs quoted, below threshold: shortfall median | 11.4¢ | 10.0¢ |
| | legs unquoted: estimated friction median | 9.4¢ | 8.0¢ |
| KXWTIW signal record (tails are two-leg) | T-1d quoted shortfall / unquoted est. friction medians | 16.5¢ / 13.6¢ | 15.8¢ / 13.5¢ |
| | T-4h quoted shortfall / unquoted est. friction medians | 18.4¢ / 11.6¢ | 17.0¢ / 11.4¢ |
| bracket statuses, both series | traded / below_threshold / cme_leg_unquoted | unchanged | unchanged |
| brackets that would clear band + (estimated) friction | | 0 | 0 |
| mechanical verdict | | STRUCTURE, NOT AN EDGE | STRUCTURE, NOT AN EDGE |

So the daily arm *was* tested as a two-leg threshold strategy; the fee overcharge was a cent and a half and does not
change what clears. The brief's scenario — four legs charged where two were due — did not happen.

**The closest calls, in probability space** (`FINDINGS_BACKTEST_V2.md`, "In probability space"): the largest net
after friction on the daily ladder is 2026-03-20 T-1d "$92.99 or below", Kalshi 0.150 at the ask against the density's
0.289 [0.280, 0.297] — a 13.9-point disagreement, estimated friction 12.3 points (10.0 of it the two legs' spread at
~2.5¢/bbl each), net +1.5 before the band, −0.2 after it; it settled *no* (98.23). The next is 2026-01-30 T-4h
"$64.0 or above", 5.0 points against 4.1 of friction, −1.7 after the band. Those two are where the friction
measurement decides; everything else is further away.

---

## B. The friction measurement

**What the 4–5¢ was.** The one trade of the first pass (2026-04-17 T-1d, since removed as a contract-assignment
artifact) had legs at 90.0 and 90.5 puts quoted 4.5¢ wide on a day oil fell $11, and the verdict sentence generalised
that to "legs quoted at 4–5¢/bbl". The friction medians in the tables were never built from it: they came from the
chain's own half-spreads (median 1.0–1.3¢/bbl per leg, the "implied" column above).

**Measured on the TBBO** — every quote attached to a trade in the 60 minutes before each KXWTIW snapshot on the expiry
the backtest priced, OTM side, 6,450 quotes over 58 windows (`synth/friction_measure.py`):

By distance from the forward, $:

| band | n | p25 | median | p75 | mean | ≤ 1¢ | ≤ 2¢ |
|---|---:|---:|---:|---:|---:|---:|---:|
| <0.5 | 968 | 1.00 | 2.00 | 3.50 | 2.92 | 29% | 58% |
| 0.5–1 | 970 | 1.00 | 1.50 | 3.00 | 2.97 | 39% | 65% |
| 1–2 | 1,266 | 1.00 | 1.50 | 3.00 | 2.55 | 45% | 66% |
| 2–4 | 1,434 | 0.50 | 1.50 | 3.00 | 2.60 | 48% | 65% |
| 4–8 | 1,260 | 0.50 | 1.50 | 3.00 | 2.23 | 40% | 62% |

By the option's own price, $/bbl:

| premium | n | p25 | median | p75 | mean | ≤ 1¢ | ≤ 2¢ |
|---|---:|---:|---:|---:|---:|---:|---:|
| < 0.10 | 1,694 | 0.50 | 0.50 | 1.00 | 0.98 | 78% | 92% |
| 0.10–0.25 | 1,538 | 1.00 | 1.50 | 2.00 | 1.76 | 50% | 78% |
| 0.25–0.50 | 1,373 | 1.00 | 2.00 | 3.00 | 2.57 | 31% | 63% |
| 0.50–1 | 1,124 | 1.50 | 2.50 | 4.00 | 3.44 | 15% | 40% |
| 1–2 | 621 | 2.50 | 4.00 | 6.00 | 5.46 | 7% | 17% |
| > 2 | 100 | 3.00 | 4.75 | 7.00 | 11.93 | 3% | 11% |

(half-spreads in ¢/bbl; the leg region 0.5–4 from the forward: median 1.5¢, p75 3.0¢, mean 2.7¢, n 3,670)

**Reading.** The "1–2 ticks" the brief expects is what a sub-$0.25 option shows. The spread scales with premium, and
at T-1d the options at a near-the-money bracket's edges are $0.50–2 options, where the median half-spread is
2.5–4¢/bbl. That is why the four-leg stack near the money comes out at 20–32 points and the two-leg stack at 10–16,
while deep-tail thresholds — cheap options, 0.5¢ half-spread — cost 2 points of spread. The trade-sampled number is
if anything biased *tight*: a quote is recorded when someone crosses it.

**What a proper measurement costs.** `db_preflight_bbo.py` quoted `bbo-1m` for the strikes within $8 of the forward
on the backtest's expiry, for the 60 minutes before each of the 58 KXWTIW snapshots (118–128 instruments per window):
**about $0.01 per window scoped, $0.04–0.14 for the whole parent chain per window; totals in
`db_preflight_bbo.json`** (PREFLIGHT_TOTAL). The pull is written (`db_pull_bbo.py`, dry-run by default, cap $50,
manifest and resume via `db_common.DBClient`) and `synth/friction_measure.py` reads its output into the same tables
next to the TBBO ones. **It has not been executed; it waits for approval.** If approved it also answers the
executable-legs question (amendment 5) with one quote per instrument per minute, and the backtest's `structure_quotes`
can be pointed at it for a re-processing.

**Operator option, free.** On the tastytrade chain for the CL weekly expiring on the next Kalshi Friday, at ~14:30 ET
on the Thursday: for each strike from $4 below to $4 above the front future in $0.50 steps, record bid, ask and size on
the OTM side (puts below, calls above), plus the future's bid/ask. Twenty minutes, one page. Repeated on three
Thursdays it would settle whether the live book is tighter than the trade-sampled one.

---

## C. The roll rule

**What the backtest used.** `db_common.kalshi_settlements`: the contract named in `rules_primary` when present
(every event from June 2026, 95 events, 99% correct against the settlement value), else `custom_strike`, else the
calendar fallback "delivery month M+2 from the 16th" (71 events, 90% correct). Gate 0b then required the option's
underlying to equal that contract, and amendment 4 verified the assignment ex post against the realised settlement.

**What the settlements show.** First date on which Kalshi's settlement value equalled the next month's NYMEX
settlement, against the two stated rules:

| switch | first settle on new month | previous event (old month) | NYMEX last trading day of old | "2 bd before LTD" | "the 16th" |
|---|---|---|---|---|---|
| CLG6 → CLH6 | 2026-01-23 | 01-16 | 01-20 | 01-16 ✗ (01-16 was still CLG6) | 01-16 ✗ |
| CLH6 → CLJ6 | 02-20 | 02-13 | 02-20 | 02-18 (consistent) | 02-16 (consistent) |
| CLJ6 → CLK6 | 03-17 | 03-16 | 03-20 | 03-18 ✗ | 03-16 ✗ |
| CLK6 → CLM6 | 04-20 | 04-17 | 04-21 | 04-17 ✗ | 04-16 ✗ |
| CLM6 → CLN6 | 05-18 | 05-15 | 05-19 | 05-15 ✗ | 05-16 (consistent) |
| CLN6 → CLQ6 | 06-16 | 06-12 | 06-22 | 06-18 ✗ | 06-16 ✓ |
| CLQ6 → CLU6 | 07-16 | 07-15 | 07-21 | 07-17 ✗ | 07-16 ✓ |
| CLU6 → CLV6 | 08-17 | 08-14 | 08-20 | 08-18 ✗ | 08-16 ✓ |

Neither rule predicts the observed switches. In the rules era the month is simply what the rules say — and Kalshi
named the next month from the 16th in June, July and August. Before June the switch came one to four business days
before the NYMEX last trading day (03-17, 04-20, 05-18), later than the 16th. The practical rule for the backtest is
the one it already applies: **read the rules; verify against the settlement value; never infer from a date.** Docs
corrected: `NightKing/PIPELINE_CHOICES.md` (Gate 0), `PIPELINE_MAP.md`, the root writeup (Stage 16).

---

## D. Threshold ladders in the store

`settlement_sources` × ladder type across every series collected:

| series | events | settles on | ladder | hedgeable? |
|---|---:|---|---|---|
| KXWTIW | 201 | ICE WTI | RANGE (585 "between", 74 tails since Jan 2026) | yes — in the study |
| KXWTI | 838 | ICE WTI | **threshold** ("Above $X": 3,082 markets; 13 ranges) | yes — in the study, two legs; the events table's `ladder_kind` says RANGE on 702 of them, which is how the "all RANGE" error could arise |
| KXGOLD | 19 | ICE (gold) | RANGE | candidate: COMEX GC options, not examined |
| KXWTIMAX / KXWTIMIN (+M) | 7 / 7 (+1 / +3) | ICE WTI | threshold on the period's max / min | no — path-dependent, not a vanilla digital |
| KXWTIWHEN, KXWTIDIRY, KXWTIE/EU | 2, 1, 1, 1 | ICE WTI | threshold | one or two events each |
| KXWTIVSBRENT | 1 | ICE / Pyth | custom | no |
| KXBRENTD, KXGOLDD, KXNATGASD | — | Pyth | threshold | no specific contract |

The earlier brief's claim that threshold markets are hourly or Pyth-settled conflated the hourly series and the
Pyth-settled daily commodity series with KXWTI. KXWTI is neither, and it was never excluded from the backtest.

---

## E. Verdict on the two checks

- **Leg count:** handled correctly for the spread, overcharged 1.42¢ on fees; corrected; nothing changes status.
- **Friction:** the 4–5¢ sentence was wrong; the arithmetic used ~1–1.3¢/bbl per leg; the measured TBBO distribution
  is 1.5–2¢ median near the money and rises with premium to 4¢ on $1–2 options; the trade-sampled basis is replaced by
  6,450 quotes with the bias direction stated, and a $-scale `bbo-1m` pull is quoted and ready.

**The null stands**, with the daily arm properly tested as a two-leg strategy, until a `bbo-1m` measurement says the
live book is materially tighter than the trade-sampled one. The two closest calls (§A) are the brackets that would
move first if it is.
