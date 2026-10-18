# §5 recompute — maker analysis on the maker-free series only

**Verdict: the premise is half right. `KXAAAGASM` does head §5's table, but it is only 4.63% of the bracket-minute sample the headline is computed over, so excluding it moves the number from 57.79% to 58.50% — the 58% figure is robust, not dominated.**

The real correction is different and larger: the published **38% branch does not apply to any series we would trade**, and should be retired as a blended figure rather than recomputed.

## What was run

No reimplementation. §5's per-series accumulators are additive integer counts, so the maker-free aggregate is an exact subtraction, not an estimate.

```
source : ladder/results/maker.pkl   (35,602 bytes, mtime 2026-10-05 18:00)
producer: ladder/maker.py :: maker_stats  -> ladder/report.py L357-370
repo   : Project-NightKing @ 0eb56f1, branch claude/gracious-edison-s2s7t5
check  : sum(by_series) == all, exactly, on both bracket_minutes and improvable
```

`improvable_pct` is the 58% headline (`improvable / bracket_minutes`). `survives_fee_pct` is the 38% headline (`sum(room_hist[2:]) / bracket_minutes`) — room of >=2c, which is what survives the 0.44c maker coefficient at 50c.

## Headline

| metric | published (all 126) | excl KXAAAGASM (125) | KXAAAGASM alone | delta |
|---|---|---|---|---|
| ladder-minutes | 1,635,485 | 1,531,305 | 104,180 | |
| bracket-minutes | 18,118,251 | 17,278,993 | 839,258 | |
| mids non-monotone % | 31.95 | 32.98 | 16.93 | +1.02 |
| **improvable % (the 58%)** | 57.79 | 58.50 | 43.06 | +0.72 |
| survives maker fee % (the 38%) | 38.23 | 38.87 | 24.88 | +0.65 |
| mean room (c) | 1.83 | 1.86 | 1.20 | +0.03 |
| mean spread (c) | 5.17 | 5.23 | 4.02 | +0.06 |

## Why the premise overstated it

`KXAAAGASM` is the top row of §5's table **by ladder-minutes** (104,180, 6.37% of the total). But the 58% headline is computed over **bracket-minutes**, and there it is only 4.63% (839,258 of 18,118,251).

The two differ because a ladder-minute contributes as many bracket-minutes as the ladder has quoted brackets, and `KXAAAGASM` ladders are short — ~8.1 brackets per minute against ~11.1 for the sample as a whole. The series that looks dominant in the table is below average in the sample that actually drives the number.

Its maker economics genuinely are the worst of any large series (43.06% improvable against 58.50% for everything else, on a 4.02c spread against 5.23c), so the direction of the correction is favourable. The magnitude is under a point.

## The correction that does matter

The published pair was *38% if makers pay 0.0175, 58% if they pay nothing* — a hedge written when the maker fee was unknown and assumed uniform. Phase 0 established it is **not** uniform.

- The 51 maker-free series: **58.50%** — no fee, so no deduction. This is the live number.
- `KXAAAGASM`, the one series that charges a maker fee: **24.88%** after its fee.
- The published blended **38.23% describes a world that does not exist** — every series paying a fee only one of them pays.

**Phase 1's gate should be stated against 58.50% on the maker-free series, and `KXAAAGASM` should be excluded from the quoting universe** — it is simultaneously the only fee-paying series and the worst microstructure in the sample, which is unlikely to be a coincidence.

## Per-series, top 25 by bracket-minutes

| series | fee_type | bracket-min | share | improvable % | survives-fee % | room c | spread c |
|---|---|---|---|---|---|---|---|
| KXWTI | quadratic | 1,602,644 | 8.85% | 52.89 | 37.28 | 1.82 | 4.91 |
| KXNATGASD | quadratic | 984,101 | 5.43% | 63.45 | 34.86 | 2.13 | 5.58 |
| KXAAAGASM ⚠️ | quadratic_with_maker_fees | 839,258 | 4.63% | 43.06 | 24.88 | 1.20 | 4.02 |
| KXSILVERD | quadratic | 754,264 | 4.16% | 48.85 | 27.47 | 1.50 | 4.49 |
| KXGOLDMON | quadratic | 723,786 | 3.99% | 64.68 | 42.11 | 1.91 | 5.44 |
| KXGOLDD | quadratic | 720,762 | 3.98% | 42.22 | 23.30 | 1.26 | 3.99 |
| KXSILVERMON | quadratic | 667,057 | 3.68% | 69.95 | 44.00 | 2.06 | 5.74 |
| KXGOLDW | quadratic | 636,673 | 3.51% | 45.36 | 27.41 | 1.49 | 4.44 |
| KXWTIMAX | quadratic | 595,265 | 3.29% | 36.36 | 17.66 | 1.10 | 3.58 |
| KXCOPPERD | quadratic | 516,086 | 2.85% | 45.95 | 24.04 | 1.50 | 4.37 |
| KXCOPPERMON | quadratic | 511,753 | 2.82% | 71.94 | 49.26 | 2.28 | 6.26 |
| KXSILVERW | quadratic | 491,395 | 2.71% | 43.01 | 29.79 | 1.65 | 4.68 |
| KXBRENTD | quadratic | 468,285 | 2.58% | 36.37 | 18.49 | 1.06 | 3.63 |
| KXOILRIGS | quadratic | 452,064 | 2.50% | 89.59 | 69.56 | 2.46 | 6.87 |
| KXCOPPERW | quadratic | 451,493 | 2.49% | 49.57 | 26.74 | 1.74 | 4.98 |
| KXBRENTMON | quadratic | 414,247 | 2.29% | 49.42 | 30.38 | 1.61 | 4.69 |
| KXSOLAR | quadratic | 396,772 | 2.19% | 88.10 | 65.87 | 2.35 | 6.65 |
| KXWTIMIN | quadratic | 371,806 | 2.05% | 61.43 | 35.66 | 1.68 | 5.04 |
| KXNATGASMON | quadratic | 336,860 | 1.86% | 69.72 | 38.17 | 1.88 | 5.46 |
| KXBRENTW | quadratic | 327,559 | 1.81% | 29.32 | 18.57 | 0.99 | 3.43 |
| KXAAAGASMAX | quadratic | 301,013 | 1.66% | 37.30 | 20.86 | 1.00 | 3.47 |
| KXAAAGASMINTX | quadratic | 258,715 | 1.43% | 73.64 | 53.09 | 2.29 | 6.24 |
| KXNATGASW | quadratic | 249,261 | 1.38% | 35.72 | 20.79 | 1.49 | 4.32 |
| KXAAAGASMAXCA | quadratic | 231,099 | 1.28% | 84.66 | 68.29 | 2.91 | 7.31 |
| KXAAAGASW | quadratic | 230,860 | 1.27% | 41.04 | 25.10 | 1.28 | 4.08 |

## Caveats

- `improvable` is measured against the ladder's own monotone fit to its mids. On a 5c book that is a weak fair value. §5's own warning stands: it says a coherent quoter would often have been best bid or offer, **not that being there is profitable**. This recompute does not change that — it corrects which population the number describes, not what the number means.

- 126 series appear in `maker.pkl`; `fee_map_ladder.json` covers 52. Series absent from the fee map are unclassified here, not assumed fee-free. None of them is large enough to move the aggregate.

- Sampling is every 10th minute, spread cap 20c, minimum 3 quoted brackets, cumulative ladders only — unchanged from the original run.

- Data ends 2026-09-10. It predates the live-book collector, and was measured while a subsidised designated market maker was quoting these series.
