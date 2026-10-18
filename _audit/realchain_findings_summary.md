# NightKing — REALCHAIN Findings Summary
> Audit compiled by Alfred (subagent: nightking-audit-realchain), 2026-10-04.
> Source files: FINDINGS_REALCHAIN.md (V1), V2, V3, V4.
> **Nothing in any of these documents is a trade signal.** No Kalshi price was read; no gap was computed.

---

## Overview: The Four-Document Arc

| Version | Core question | Key verdict |
|---|---|---|
| V1 | What do real KXWTIW chains look like to the extractor at all? | Extractor runs; fit is bad (~8× worse than synthetic). Asynchronous quotes identified as likely culprit. |
| V2 | Fix the forward (use NYMEX settlement) and synchronise the quotes. | Quote synchronisation is the fix. χ²/strike drops from 8.1 → 1.6 at T-1d/60. Old Gate 4 replaced. |
| V3 | Replace V2's path reconstruction with real 1-minute CL futures bars. | Partial improvement. T-4h and T-2d benefit; T-1d unchanged (path was already good there). |
| V4 | Test prior variants (Student-t, more knots) and LOO-based quote exclusion. | Prior form doesn't matter much. LOO exclusion does: χ² drops to ~1.1–1.3 across all snapshots. This is the current best configuration. |

All runs: 30 KXWTIW settlement dates (2026-01-09 to 2026-09-04), roots LO1–LO5. Snapshots: T-2d, T-1d, T-4h, T-0 (T-0 unusable throughout — 75–100% one-cent bids). Two quote windows: 60 min and 10 min. NUTS sampler: 4×(400+400).

Baseline comparison: synthetic well-specified chains sit at χ²/strike ≈ 1.1.

---

## FINDINGS_REALCHAIN.md (V1)

### Purpose
Step 2 of the build order: descriptive characterisation of real WTI weekly chains as the extractor sees them. No forward computed, no Kalshi price read, no gap — purely a pipeline diagnostic.

### What was run
- 30 dates × 4 snapshots × 2 windows = 240 jobs. 0 errors.
- Stage 6 parity regression → OTM density extraction → Act II → Act III with/without martingale constraint → Gate 4 (max |Act II − Act III| > 2.5¢).
- Forward: Stage 6 parity regression on the raw quote window (unstable at 2 days).

### Key numerical results

**Coverage by snapshot (60-min window, the critical one):**

| Snapshot | Extracted of 30 | Median OTM strikes | Median quoted strikes | Median quote age (min) |
|---|---|---|---|---|
| T-2d / 60 | 14 | 24 | 20 | 20.3 |
| T-1d / 60 | 28 | 29 | 31 | 14.9 |
| T-4h / 60 | 30 | 26 | 28 | 17.7 |
| T-0 / 60 | 0 | 20 | 18 | 18.4 |

T-2d extracted only 14 of 30 (parity needed ≥2 two-sided pairs; most had only 2 median two-sided strikes). T-0 extracted 0 — dead on arrival from penny bids (75% 1¢ bids).

**Fit quality (Act III χ²/strike):**

| Snapshot | Window | Median χ² | % chains χ² < 2 | % max resid < 3 |
|---|---|---|---|---|
| T-2d | 60 | 4.2 | 21% | 21% |
| T-1d | 60 | **8.1** | 14% | 11% |
| T-1d | 10 | 2.0 | 44% | 44% |
| T-4h | 60 | 5.7 | 7% | 0% |
| T-4h | 10 | 2.2 | 44% | 44% |

The 60-minute windows are 4–8× worse than synthetic well-specified chains (1.1). The 10-minute windows are near the target — which pointed to quote asynchrony within the 60-minute window as the dominant problem.

**Parity forward vs NYMEX settlement:**
- T-1d/60: parity − NYMEX median −6.9¢, RMSE 37.7¢, within 10¢ on only 32% of dates.
- T-0/60: parity − NYMEX median −21.3¢, RMSE 37.6¢, within 10¢ on 25%.

The parity-derived forward is badly wrong — a direct consequence of options striking at many different underlying levels across a volatile 60-minute window.

**Density shape:**
- 43% of T-1d/60 posterior draws are multimodal-majority. This drops to 0% at 10 minutes → artifact of asynchrony, not real market structure.
- Consistent positive skew (86–93% of chains).
- ATM σ: ~65–70% vol at T-2d/T-1d, ~80% at T-4h, >100% at T-4h/10.

**Gate 4 (old detector, max |Act II − Act III| > 2.5¢):**
- Fires on 64–77% of T-1d and T-4h chains. Correctly identifies these chains as problematic, but provides no diagnosis.

**Sampler health:**
- Real chains worse than synthetic: bracket R̂ p90 up to 1.741 at T-1d/60 vs 1.051 on synthetic. ESS much lower. Posterior was badly conditioned because the data themselves were inconsistent.

### Verdict
The extractor runs cleanly on real data, but the fit is grossly poor at 60-minute windows due to quote asynchrony (options struck at different underlying levels across the hour). The 10-minute window is a useful existence proof that the extractor works when quotes are near-synchronous. The parity forward is too noisy to trust. T-0 is unusable.

### Caveats / Open Questions
- Gate 4 fires but doesn't tell you *why*. A better diagnostic was needed.
- T-2d extraction too sparse (only 14 of 30 dates) due to parity pair requirement.
- Sampler degradation on real chains was a symptom, not a cause.
- Section 8 ("Where real chains differ from synthetic") was listed but deferred to after the numbers.

---

## FINDINGS_REALCHAIN_V2.md

### Purpose
Response to `HANDOFF_forward_and_sync_fix.md`. Tests three attributable fixes: (1) using the NYMEX futures settlement as the forward instead of parity; (2) synchronising all option quotes to the snapshot instant via sticky-strike Black-76 reprice along an intraday path; (3) replacing the Act II detector with a split-half / LOO-based Gate 4.

Four arms run in parallel against V1 baseline (re-run to confirm exact reproduction): `base` (V1), `fwd` (futures forward only), `sync` (futures forward + synchronised quotes), `sync_m` (sticky-moneyness sensitivity).

### What was run
- 30 dates × all snapshots × both windows × 5 arms = 750 jobs. 0 errors.
- V1 `base` arm reproduced to the last decimal (max Δχ² = 0.000).
- Synchronisation engine: `synth/sync.py`. Option trade stream used to estimate intraday path on 1-minute knots; anchored to NYMEX settlement at 14:29. No intraday futures prices in the data store at this stage (only session-level stats).

### Key numerical results

**The headline — χ²/strike on T-1d/60 (the most important snapshot):**

| Arm | Extracted | χ² med | % < 2 | % multimodal majority |
|---|---|---|---|---|
| V1 (parity fwd, raw) | 28 | 8.1 | 14% | 43% |
| futures fwd, raw | 30 | 6.4 | 13% | 33% |
| **futures fwd + sync** | **30** | **1.6** | **57%** | **0%** |
| sync (sticky-moneyness) | 30 | 1.6 | 60% | 3% |

Synchronisation alone drops χ² from 8.1 to 1.6 — matching V1's near-synchronous 10-minute window (χ² = 2.0) while keeping all 30 dates (V1's 10-minute window kept only 9).

**The forward fix alone (arm `fwd`):**
- At T-1d/60: χ² 8.1 → 6.4. Marginal improvement.
- Sampler *worsened* (bracket R̂ 1.038→1.065, ESS 135→88). The correct forward with asynchronous quotes is a harder problem.
- Fix 1 only pays off with Fix 2.

**Synchronisation fix (arm `sync`) across all snapshots:**

| Snapshot | Window | V1 χ² | sync χ² | % multimodal: V1 → sync |
|---|---|---|---|---|
| T-2d | 60 | 4.4 | 1.9 | 46% → 8% |
| T-1d | 60 | 8.1 | 1.8 | 43% → 0% |
| T-1d | 10 | 2.0 | 1.0 | 0% → 0% |
| T-4h | 60 | 5.7 | 1.9 | 43% → 23% |
| T-4h | 10 | 2.2 | 1.5 | 11% → 0% |

T-4h/60 still shows 23% multimodal-majority runs after sync — flagged as "next to investigate."

**Coverage gains from the futures forward (no parity pairs needed):**
- T-2d/60: 14 → 26 extracted dates
- T-1d/10: 9 → 21 extracted dates
- T-2d/10: 0 → 8 extracted dates

**Parity vs futures, after synchronisation:**
- T-1d/60: synchronised parity vs settlement: RMSE 10.8¢ (was 37.7¢), within 10¢ on 68% of dates.
- T-1d/60: synchronised parity vs path forward: RMSE 7.6¢, 82% within 10¢. Residual is the honest measurement error of parity on 6 pairs.

**New Gate 4 (split-half + LOO), calibration on synthetic:**
- Null p95 = 2.65 (cutoff set before scoring real chains).
- Stale-quote injection: LOO catches 88% of chains, localises to the injected strike on 88%.
- Bimodal-truth injection: split-half catches 0% (LOO 12%) — a known blind spot. Act II stays in the report as the bimodal detector.

**New Gate 4 on real data:**
- V1 raw chains: gate fires 79% at T-1d/60 (correctly flagging bad data).
- Synchronised chains: gate fires 17% at T-1d/60.
- Every synchronised 10-minute chain passes.

**Stage 14 (unconstrained mean = forward):**
- T-1d/60: pass rate 36% → 70% after synchronisation. |z| median 3.9 → 1.8 (synthetic: 0.74).

**Sampler health after synchronisation:**
- T-1d/60: bracket R̂ median 1.038 → 1.016, ESS 135 → 246, runs with R̂ < 1.05: 64% → 83%. The posterior was ill-conditioned because the data were inconsistent.

### Verdict
**Fix 2 (quote synchronisation) is the fix.** Fix 1 (futures forward) unlocks more dates but barely improves fit on its own and briefly makes the sampler worse. Fix 3 (new Gate 4) works: it correctly diagnoses 79% of raw chains as bad, then goes quiet (17%) once data are consistent.

Remaining issues:
- T-4h/60 multimodality (23%) and fatter χ² tail. Window spans 20% of option life, 21% 1¢ bids, parity-anchored forward.
- Residual at T-1d: half the chains still have max |resid| > 3; LOO flags 70% (2.2 flags/chain avg). This is quote-level inconsistency, not path error — calls for LOO exclusion rather than path fixes.
- T-0 still unusable.
- The reconstruction path uses option trade events — V2 noted that live deployment would have a real futures feed.
- Bimodal-truth blind spot of Act II and the roughness prior unchanged.

### Methodological concerns / false negative sources
- The synchronisation path is in-sample: it absorbs some inconsistency into the estimated path, flattering the chain. Gate 4 fires ~30% with the exogenous real path (V3 finding).
- LOO 12% false-positive rate on clean synthetic chains means a single LOO flag is a pointer, not a verdict.
- The sticky-strike assumption may understate residuals when the smile slope is large.

---

## FINDINGS_REALCHAIN_V3.md

### Purpose
Response to `HANDOFF_actii_and_intraday.md` Task 3. Replaces V2's options-trade-based path reconstruction with real 1-minute CL futures OHLCV bars (`ohlcv-1m`). All V1/V2 arms re-run; full V1→V2→V3 comparison on the same dates.

New arm: `real` = V2's `sync` arm but path comes from actual futures bars; reconstruction fills holes > 5 min only.

### What was run
- 30 dates × all snapshots × both windows × multiple arms = 990 jobs. 0 errors.
- Bar coverage: 100% on every window (no fallback needed).
- Cost: $0.70 (ohlcv-1m) + $0.26 (bbo-1m for completeness).

### Key numerical results

**V1 → V2 → V3 χ²/strike progression (paired on same dates, 60-min windows):**

| Snapshot | n | V1 χ² | V2 χ² | V3 χ² | V3 % < 2 | multimodal: V1→V2→V3 |
|---|---|---|---|---|---|---|
| T-2d | 13 | 4.4 | 1.9 | **1.6** | 85% | 46%→8%→**0%** |
| T-1d | 28 | 8.1 | 1.8 | **1.8** | 54% | 43%→0%→4% |
| T-4h | 30 | 5.7 | 1.9 | **1.5** | 70% | 43%→23%→**7%** |

V3 helps significantly at T-2d and T-4h. At T-1d it's essentially flat (χ² 1.8→1.8).

**The real vs reconstructed path (shape error):**

| Snapshot | Window | Shape RMSE at anchor (0–5 min) | Shape RMSE 45–60 min out | Level RMSE at anchor |
|---|---|---|---|---|
| T-2d | 60 | 24.0¢ | **88.6¢** | 4.0¢ |
| T-1d | 60 | 11.4¢ | 16.5¢ | 6.0¢ |
| T-4h | 60 | 17.0¢ | 26.9¢ | **24.4¢** |

T-2d: reconstruction catastrophically wrong far from the anchor (88¢ RMSE at 45–60 min) — only 38 informative events per window vs 98 at T-1d. Real path fixes this.

T-4h: reconstruction's level error at the anchor is 24¢ RMSE — because V2 had to anchor to a parity forward at 10:30 (no 10:30 futures print in the store). Real path has the actual 10:30 price.

T-1d: reconstruction already close (shape RMSE flat at ~16.5¢ across the window; real level matches anchor to 0¢ median / 6¢ RMSE). Real path changes almost nothing here.

**T-4h improvement:**
- Multimodal-majority runs: 23% (V2) → **7%** (V3). Two remaining multimodal chains (2026-05-01, 2026-03-06) are genuine structural candidates, not artifacts. 2026-05-29 lost its modes with the real path.
- χ²/strike: 1.9 → 1.5, % < 2: 53% → 70%.
- Stage 14: 80% → 90% pass rate.

**T-2d improvement:**
- χ² p90: 6.3 → 2.3. % < 2: 65% → 77% (paired: 54% → 85%).
- Stage 14: 50% → 92%.
- Gate 4: 35% → 19%.
- Multimodal residue: 4% → 0%.

**The honest cost of the real path at T-1d:**
- Gate 4 fires more (17% → 30%). The in-sample reconstruction absorbed some inconsistency. The 30% is the more honest number.
- Sampler slightly worse (bracket R̂ 1.016 → 1.021, ESS 246 → 202).

**Verdict on reconstruction vs real:**
- T-4h: reconstruction artifact of the parity-anchored level, not the shape. Real path fixes it.
- T-2d: reconstruction artifact of sparse option trades (only 38 events/window). Real path fixes it.
- T-1d: reconstruction was already adequate. Real path neither helps nor hurts on χ².

### Verdict
**Partial.** Pre-specified criteria: χ²/strike median drop ≥ 0.20 at T-1d/60 AND T-4h/60 multimodal majority ≤ 12%. Result: T-1d criterion not met (1.8→1.8); T-4h criterion met (23%→7%). The real path becomes the default; reconstruction stays as fallback. T-4h forward is now the real 10:30 futures level everywhere.

**What is not fixed by V3:**
- T-1d residual inconsistency: quote-level (LOO flags 80% of chains, 2.3 flags/chain). The path was not the problem; it's the model and individual stale quotes.
- The prior was untouched per brief.
- T-0 unchanged.

### Caveats
- Two T-4h chains (2026-05-01, 2026-03-06) remain multimodal; these may be genuinely bimodal — Act II would flag them (prior misspecification blind spot of split-half/LOO).
- 100% bar coverage in backtest is optimistic; live would need fallback planning.
- The 30% Gate 4 rate at T-1d/60 with the real path is the correct number to carry forward.

---

## FINDINGS_REALCHAIN_V4.md

### Purpose
Response to `HANDOFF_prior_fix.md` §A.5. Tests whether changing the Act III prior (Gaussian second-differences → Student-t ν=3 or ν=1 / horseshoe) and/or increasing knot count (24 → 36 → 48) improves fit. Also introduces Part B: LOO-based quote exclusion (drop LOO |z| > 3 strikes, one pass, Gate 0 preserved). Everything built on top of V3's `real` arm.

Arms: `real_t3` (Student-t ν=3), `real_t1` (ν=1), `real_hs` (horseshoe), `real_m36` (36 knots), `real_m48` (48 knots), `real_m48_x` (48 knots + LOO exclusion), `real_m48_f1` (48 knots + 1¢ tick floor), `real_m48_f1x` (48 knots + 1¢ tick floor + LOO exclusion). 2430 total jobs. 0 errors.

### Key numerical results

**Prior shape (Student-t ν=3) vs Gaussian (V3), 60-min windows:**

| Snapshot | V3 χ² | V4(t3) χ² | Change |
|---|---|---|---|
| T-2d | 1.6 | 1.6 | none |
| T-1d | 1.8 | 1.9 | slightly worse |
| T-4h | 1.5 | 1.5 | none |

Student-t prior makes essentially no difference to fit. Sampler is worse (R̂ up, ESS down). **Prior shape is not the bottleneck.**

**Increasing knots (24 → 36 → 48), 60-min windows:**

| Snapshot | V3(24) χ² (p90) | V4(36) χ² (p90) | V4(48) χ² (p90) | % < 2: 24→48 |
|---|---|---|---|---|
| T-2d | 1.6 (2.3) | 1.6 (2.2) | 1.5 (2.1) | 77%→85% |
| T-1d | 1.8 (3.4) | 1.8 (3.3) | 1.8 (3.2) | 53%→53% |
| T-4h | 1.5 (3.1) | 1.5 (3.1) | 1.5 (3.1) | 70%→70% |

More knots deliver incremental improvement but not breakthrough. The p90 (the fat tail) barely moves. The bulk of remaining error is not prior resolution.

**LOO-based quote exclusion (48 knots + LOO exclusion), the headline result:**

| Snapshot | 48-knots χ² | + LOO excl χ² | % < 2 | % max resid < 3 | Gate 4 fired | multimodal |
|---|---|---|---|---|---|---|
| T-2d / 60 | 1.5 | **1.3** | 85% → **100%** | 65% → 92% | 23% → **0%** | 8% → 0% |
| T-1d / 60 | 1.8 | **1.3** | 53% → **97%** | 53% → **100%** | 27% → **0%** | 10% → 0% |
| T-4h / 60 | 1.5 | **1.2** | 70% → **97%** | 53% → 77% | 13% → 3% | 10% → 3% |

Adding a 1¢ tick floor (treating penny bids as 1¢ half-spread) combined with LOO exclusion pushes further:

| Snapshot | Best arm χ² med (p90) | % < 2 | % max resid < 3 | Gate 4 | Stage 14 pass |
|---|---|---|---|---|---|
| T-2d / 60 | **0.9** (1.4) | 100% | 100% | **0%** | 96% |
| T-1d / 60 | **1.1** (1.6) | 97% | 100% | 0% | 100% |
| T-4h / 60 | **0.9** (1.4) | 100% | 100% | 3% | 100% |
| T-2d / 10 | 1.1 | 100% | 100% | 0% | 100% |
| T-1d / 10 | 1.0 | 100% | 100% | 0% | 95% |
| T-4h / 10 | 1.2 | 100% | 100% | 0% | 100% |

These are now at or below the synthetic well-specified benchmark of 1.1.

**Quote exclusion stats (48-knots, all 60-min chains):**
- 124 chains, 2734 quotes; 211 removed (7.7%).
- 29% of chains lost > 10% of quotes (marked suspect).
- Removed quotes: 48% calls / 52% puts; age median 14.7 min (all: 13.9 min) — slightly older; half-spread median 0.5¢ (all: 1.0¢) — actually tighter spreads, so the exclusion is driven by cross-strike inconsistency, not wide spreads.
- LOO |z| of removed quotes: median 3.7.

**The two persistent T-4h chains:**
- 2026-05-01 (T-4h/60): χ² 4.25 with V3, 4.11 with V4(48 knots). Posterior multimodal on 100% of draws. 8 LOO flags. Act II Δ = 25.19¢. Stage 14 z = 4.9. With 48-knot LOO exclusion: χ² drops to **1.35**, multimodal-majority to **10%**, LOO flags to **0**, Stage 14 z = **1.3**. Eight quotes removed.
- 2026-03-06 (T-4h/60): χ² 4.41, unimodal, Gate 4 fires. LOO exclusion → χ² **1.94**, Gate 4 quiet. Six quotes removed.
- Both chains' pathology is quote-level inconsistency, not genuine bimodality.

**V1→V4 evolution (full progression, T-1d/60, paired dates):**

χ²: 8.1 → 6.9 (fwd) → 1.8 (V2 sync) → 1.8 (V3 real) → 1.8 (t3) → 1.8 (m48) → **1.3 (m48+LOO excl)** → **1.2 (m48+f1+LOO)**

### Verdict
**Prior form is not the bottleneck.** LOO-based quote exclusion is the lever that brings real chains to synthetic benchmark levels. With 48 knots + LOO exclusion (± 1¢ tick floor), all six primary snapshot/window combinations reach χ²/strike ≤ 1.3. The tick floor helps further by correctly re-weighting penny-bid quotes that had underestimated their own uncertainty.

The 29% of chains losing >10% of their quotes is a caution flag — these chains should be treated as lower-quality. For production, a suspect flag at > 10% quote removal is warranted.

The two T-4h persistent chains (2026-05-01, 2026-03-06) are explained by quote inconsistency, not genuine bimodality, once exclusion is applied. This closes the concern raised in V3.

T-0 is unchanged and remains unusable.

### Caveats / Open Questions
1. **LOO exclusion was not cross-validated against the detector calibration.** The split-half/LOO cutoffs were calibrated on synthetic null chains. Applying LOO as an exclusion rule rather than just a flag is a methodological step not validated against held-out real chains.
2. **Exclusion is run on the backtest data itself.** In live use, LOO exclusion would operate at decision time on real-time quotes — appropriate and lower risk of leakage, but the 7.7% removal rate needs to be confirmed as stable across different market regimes.
3. **29% of chains lose > 10% of quotes.** These should be downweighted or gated in production.
4. **The bimodal blind spot persists.** Split-half and LOO detect inconsistency; neither reliably detects genuine bimodality. Act II (reports 100% on bimodal-truth in synthetic calibration) remains the necessary second look. V4's Act II rates are still high on some snapshots (37–53% at T-4h/60 depending on arm), though most are quote-inconsistency artifacts.
5. **The Student-t ν=3 prior introduced sampler degradation** (R̂ up to 1.062, ESS drops) without benefit. It is not the path forward.
6. **T-1d/60 Gate 4 rate with real path** is 30% — higher than V2's 17%. As noted in V3, the honest number is the exogenous-path figure. The 17% with the in-sample reconstruction was flattering.
7. **Parity normalisation** fails on 30–40% of chains across all versions. The extractor cannot integrate to 1 exactly on real data with limited strikes — not a blocking issue but inflates normalization-check failure rates.
8. **Potential false negatives in the bimodal channel**: Act II fires on genuine bimodality but split-half/LOO do not. Any genuinely bimodal market density would pass the new Gate 4 cleanly, be captured by Act II, but Act II is a report line, not a gate in V2–V4. If the bimodal signal matters for a trade, the flag path needs to be hardened.

---

## Cross-Document Summary: The Improvement Arc

```
                V1       V2       V3       V4(m48+f1x)
T-1d/60 χ²:   8.1  →   1.6  →   1.8  →   1.1
T-4h/60 χ²:   5.7  →   1.9  →   1.5  →   0.9
T-2d/60 χ²:   4.4  →   1.9  →   1.6  →   0.9
Multimodal%:  43%  →   0%   →   0-7%  →   0%
Gate 4 fired: 79%  →   17%  →   30%  →   0%
Dates (T-1d): 28   →   30   →   30   →   30
```

Each fix was cleanly attributed. The dominant gains came from:
1. **Quote synchronisation** (V2): 8.1 → 1.6 at T-1d/60
2. **Real intraday path** (V3): multimodality at T-4h 23%→7%
3. **LOO quote exclusion** (V4): χ² to synthetic-benchmark levels everywhere

The prior shape was a red herring. Data quality (asynchrony and inconsistent individual quotes) explained nearly all the deviation from synthetic.

---

## What Is Still Unresolved

1. **T-0 is unusable** — 75–100% one-cent bids, no viable extraction regardless of fixes applied.
2. **The bimodal detection gap** — Act II sees genuine bimodality; the new Gate 4 does not. No chain in this study was confirmed genuinely bimodal after LOO exclusion, but the gap remains a structural risk.
3. **Quote exclusion validation** — 7.7% removal rate and 29% of chains >10% removal need regime-robustness testing.
4. **No Kalshi price was read, no gap computed, no trade signal evaluated in any version.** The entire document series is a descriptive/diagnostic characterisation of the density extractor on real chains. The bridge to a live trade signal has not been built.
