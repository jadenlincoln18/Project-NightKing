# FINDINGS_LEGCOUNT — what the backtest priced per series, the roll rule, and the friction measurement

`NightKing/HANDOFF_legcount_and_friction.md`. Error-correction on `FINDINGS_BACKTEST.md`, under the unchanged
`BACKTEST_PROTOCOL.md` (amendment 7 documents the one fix). Nothing in the extractor, the gates or the thresholds moved.

**Summary.** (A) The daily series was replicated with **two legs from the first run** — the spread term summed the two
legs actually used — but the **fee term was charged for four legs on every structure**, 1.42¢ too much on a threshold.
Corrected and re-processed: no bracket changes status, no bracket clears. (B) The first findings' "4–5¢/bbl
half-spread" sentence was a mis-generalisation from one trade, and the chain's trade-sampled half-spreads it was
contrasted with (1.5–2¢ median) turn out to be the book at its tightest: on the live `bbo-1m` book, approved and
bought for the 58 snapshot windows, the half-spread is **4.0¢ at the money, 2.5–3¢ two to eight dollars out, 1.5¢
only below $0.05 of premium** — the 4–5¢ figure holds near the money, and every leg of every bracket was live when the
TBBO said 44% of them were unquoted. Friction per bracket from each leg's own quote is **21–25¢ for a four-leg bracket
and 15¢ for a two-leg threshold**, against gaps of a cent; nothing clears, the nearest miss is 1.6 points. (C) The roll
rule in the docs ("the 16th") was wrong and so is the rules page's "2 business days before the last trading day" as a
predictor; the settlements show the switch one to four business days before the NYMEX last trading day, and the
backtest's ex-post check caught every misassignment. (D) KXWTI is an ICE-settled threshold ladder and was in the
study; KXGOLD is the only other exchange-settled ladder in the store. **Both checks come back clean in the brief's
sense — the daily arm was tested as a two-leg strategy and the spreads really are 4¢ near the money — and the null
stands, with the hedge now priced on executable quotes.**

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
the backtest priced, OTM side, 6,450 quotes over 58 windows (`synth/friction_measure.py`): median 1.5–2.0¢/bbl by
distance from the forward, 0.5¢ below $0.10 of premium, 4¢ at $1–2. That is the trade-sampled number, and it is the
one that was wrong in the useful direction: **a trade happens when someone crosses a tight market, so the TBBO shows
the book at its tightest.**

**Measured on the live book** — `bbo-1m` for the whole parent chain in the 60 minutes before each of the 58 snapshots
(approved, $4.23, 181,675 two-sided samples of the backtest's expiry; one sample per instrument per minute, with
`ts_recv` the sample time and `ts_event` the last book update). At the snapshot minute, 3,038 instruments, OTM side,
half-spread in ¢/bbl:

By distance from the forward, $:

| band | n | windows | p25 | median | p75 | mean | ≤ 1¢ | ≤ 2¢ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <0.5 | 225 | 58 | 2.50 | **4.00** | 5.00 | 4.60 | 0% | 16% |
| 0.5–1 | 227 | 58 | 2.00 | 3.00 | 5.50 | 4.47 | 5% | 29% |
| 1–2 | 441 | 58 | 1.50 | 3.00 | 6.00 | 4.32 | 11% | 41% |
| 2–3 | 381 | 55 | 1.50 | 2.50 | 6.00 | 4.10 | 18% | 47% |
| 3–4 | 315 | 49 | 1.50 | 2.50 | 6.00 | 4.23 | 17% | 44% |
| 4–6 | 500 | 43 | 1.50 | 2.50 | 5.00 | 3.78 | 20% | 48% |
| 6–8 | 322 | 36 | 1.50 | 3.00 | 5.50 | 3.67 | 23% | 43% |
| 8–12 | 373 | 26 | 1.50 | 2.50 | 5.50 | 3.81 | 14% | 39% |
| >12 | 254 | 19 | 2.00 | 4.00 | 6.00 | 4.33 | 9% | 30% |

By distance in vol-scales, $|K-F_0| / (F_0\,\sigma_{\text{ATM}}\sqrt{T})$:

| band | n | windows | p25 | median | p75 | mean | ≤ 1¢ | ≤ 2¢ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <0.25 | 259 | 58 | 3.50 | **4.50** | 7.25 | 5.97 | 0% | 7% |
| 0.25–0.5 | 266 | 57 | 3.00 | **5.00** | 9.50 | 6.37 | 0% | 12% |
| 0.5–1 | 523 | 58 | 2.50 | 4.00 | 8.00 | 5.33 | 2% | 22% |
| 1–1.5 | 520 | 58 | 2.00 | 3.00 | 6.50 | 4.40 | 5% | 36% |
| 1.5–2 | 503 | 58 | 1.50 | 2.50 | 5.00 | 3.35 | 16% | 49% |
| 2–3 | 649 | 57 | 1.00 | 2.00 | 4.00 | 2.72 | 28% | 59% |
| 3–4 | 225 | 42 | 1.00 | 1.50 | 3.50 | 2.33 | 38% | 67% |
| >4 | 93 | 22 | 1.00 | 1.50 | 1.50 | 1.59 | 47% | 82% |

By the option's own premium, $/bbl:

| premium | n | windows | p25 | median | p75 | mean | ≤ 1¢ | ≤ 2¢ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| < 0.05 | 732 | 58 | 1.00 | 1.50 | 2.00 | 1.55 | 46% | 84% |
| 0.05–0.10 | 564 | 58 | 1.50 | 2.00 | 4.50 | 2.96 | 15% | 51% |
| 0.10–0.25 | 674 | 58 | 2.00 | 3.00 | 5.50 | 4.05 | 2% | 34% |
| 0.25–0.50 | 469 | 56 | 2.50 | 4.00 | 7.50 | 5.08 | 0% | 15% |
| 0.50–1 | 386 | 39 | 4.00 | 6.00 | 9.00 | 6.56 | 0% | 3% |
| 1–2 | 190 | 17 | 5.63 | 8.50 | 12.00 | 8.94 | 0% | 0% |
| > 2 | 23 | 3 | 13.50 | 14.00 | 14.50 | 12.67 | 0% | 0% |

(The 60-minute distributions, every minute's sample, are within 0.5¢ of these in every bin; `friction_measure.json`.)

**Reading.** On the live book the "4–5¢" figure holds **near the money** — 4.0¢ median within $0.50 of the forward,
4.5–5.0¢ within half a vol-scale — and the book is 2.5–3¢ wide two to eight dollars out, 4¢ beyond twelve. The "1–2
ticks" the brief expected is true only of options under $0.10 of premium. The TBBO's 1.5–2¢ was the book at its
tightest moments; the live book is about twice as wide at every distance. Spread scales with premium (1.5¢ under $0.05,
6¢ at $0.50–1, 8.5¢ at $1–2), which is why the legs of a near-the-money bracket at T-1d — $0.50–2 options — are the
expensive ones, and why the operator's choice of the whole chain over the ±$8 scoping mattered: the far legs the tail
brackets need are not tighter than the near ones.

**Leg availability — what the TBBO was discarding.** Every replicating leg of every bracket of every window (3,984
legs), by the leg's distance from the forward:

| band | legs | two-sided on TBBO ≤ 5 min | TBBO ≤ 60 min | **bbo-1m at the minute** | bbo-1m half-spread median |
|---|---:|---:|---:|---:|---:|
| <0.5 | 174 | 55% | 97% | 100% | 3.00¢ |
| 0.5–1 | 174 | 42% | 90% | 100% | 2.50¢ |
| 1–2 | 348 | 27% | 88% | 100% | 2.50¢ |
| 2–3 | 348 | 16% | 73% | 100% | 2.00¢ |
| 3–4 | 324 | 9% | 56% | 99% | 2.50¢ |
| 4–6 | 601 | 8% | 35% | 96% | 2.50¢ |
| 6–8 | 505 | 2% | 19% | 90% | 3.00¢ |
| 8–12 | 762 | 2% | 17% | 78% | 3.00¢ |
| >12 | 748 | 0% | 6% | 69% | 4.50¢ |

All 304 brackets the TBBO version had marked `cme_leg_unquoted` had every leg live and two-sided on the book at the
snapshot minute; so did all 694 brackets with a two-sided Kalshi quote (only 4 of those had every leg on the TBBO
within 5 minutes, 161 within 60). **The TBBO was silently discarding 44% of the comparable sample on data, not on
markets** — amendment 5's "the hedge is not priceable" was a statement about the TBBO, not about the options.

**Friction per bracket from each leg's own quote** (amendment 8; `--reprocess --legs bbo1m`, 311 of 351 two-sided
brackets at T-1d and 340 of 343 at T-4h now carry a measured structure; the one remaining `cme_leg_unquoted` is a leg
beyond the listed strikes):

| snapshot | Act III band | n | friction median (p25–p75) | of which spread | per-leg half-spread median | legs | \|gap\| median | shortfall to band + friction, median |
|---|---|---:|---|---:|---:|---:|---:|---:|
| T-1d | deep tail (< 5¢) | 164 | 20.8¢ (14.0–49.1) | 18.0¢ | 2.38¢/bbl | 3.8 | 0.4¢ | 20.9¢ |
| | moderate tail (5–20¢) | 120 | 24.8¢ (18.7–35.8) | 21.0¢ | 2.63¢ | 4.0 | 0.9¢ | 26.5¢ |
| | body (20–80¢) | 22 | 19.9¢ (16.4–23.6) | 16.0¢ | 2.12¢ | 3.2 | 1.7¢ | 21.8¢ |
| | favourite (> 80¢) | 5 | 36.1¢ | 34.0¢ | 8.50¢ | 2.0 | 0.7¢ | 37.1¢ |
| T-4h | deep tail | 231 | 24.8¢ (22.5–40.4) | 22.0¢ | 2.88¢ | 3.8 | 0.1¢ | 25.2¢ |
| | moderate tail | 64 | 30.7¢ (20.6–49.3) | 27.0¢ | 3.63¢ | 3.9 | 1.5¢ | 32.4¢ |
| | body | 38 | 21.8¢ (19.0–29.2) | 17.5¢ | 2.19¢ | 3.9 | 2.9¢ | 27.1¢ |
| | favourite | 7 | 11.8¢ (6.7–18.5) | 10.0¢ | 2.50¢ | 2.0 | 1.3¢ | 12.9¢ |

By leg count: four-leg brackets median 23.1¢ at T-1d and 25.8¢ at T-4h; two-leg thresholds and tails 15.5¢ and 15.6¢.
The closest any bracket comes to clearing band + friction is 1.6¢ short (T-4h, four legs) and 2.7¢ short (T-4h, two
legs); the medians are 25¢ and 14¢ short. The two "closest calls" of the TBBO pass (§A) move away: 2026-03-20
"$92.99 or below" has its two puts quoted 6.5¢ and 7¢ wide on the book, friction 29.3 points against a 13.9-point
disagreement.

**Operator option, free (still useful as a cross-check of the book at a different hour).** On the tastytrade chain for
the CL weekly expiring on the next Kalshi Friday, at ~14:30 ET on the Thursday: for each strike from $4 below to $4
above the front future in $0.50 steps, record bid, ask and size on the OTM side, plus the future's bid/ask. Three
Thursdays would say whether the book at the close is like the book at 14:30 the day before.

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
- **Friction:** the 4–5¢ sentence was wrong as written and right in substance: on the live book the half-spread is
  4.0¢ at the money and 2.5–3¢ on the tail legs, roughly double the trade-sampled TBBO figure, and it scales with
  premium. The two-bracket basis is replaced by 3,038 live quotes at the snapshot minute (181,675 in the windows) and
  every bracket now carries a hedge priced from its own legs: 21–25¢ per Kalshi dollar for a bracket, 15¢ for a
  threshold. Amendment 5's "not priceable from the stored data" was true of the TBBO and is now moot.

**The null stands.** `FINDINGS_BACKTEST_V2.md` is the re-render on the corrected fees and the live-book legs; the
mechanical verdict is unchanged (STRUCTURE, NOT AN EDGE), B2 and B3 fail with zero brackets clearing, and the
structure (b ≈ 0.69) is the same tick-sized longshot premium. What changed is the quality of the hedge side: it is now
a measurement, not an estimate, and it is larger than the estimate.
