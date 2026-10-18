# Project NightKing — Backtest Findings Audit Summary

*Compiled from: `FINDINGS_BACKTEST.md`, `FINDINGS_BACKTEST_V2.md`, `FINDINGS_LEGCOUNT.md`, `FINDINGS_ACTII_V2.md`*
*All four files read in full. All numerical citations are direct from source.*

---

## 1. FINDINGS_BACKTEST.md

### Purpose
The **first-pass backtest** of the NightKing strategy: comparing the Act III density extractor's implied bracket
probabilities against executable Kalshi bid/ask prices on WTI oil event markets (KXWTIW weekly and KXWTI daily),
with CME crude oil options as the replication vehicle. Covers 37 KXWTIW events from Jan–Sep 2026; 37 T-1d
snapshots and 37 T-4h snapshots.

### Key Numerical Results

**Denominator (KXWTIW):**
- 37 total events; 24 cleared all gates at T-1d, 22 at T-4h
- Exclusions: 3 no same-day CME weekly, 3 contract mismatch (Gate 0b), 2 too few strikes, 1/2 split-half failures,
  4/5 sampler failures

**Gap statistics (KXWTIW, T-1d, 296 two-sided brackets across 24 cleared dates):**
- Mean gap: +0.2¢ (Kalshi vs. Act III density)
- Mean |gap|: 1.1¢
- Median |gap|: 0.5¢
- 23% of brackets outside the 90% posterior band
- 0% outside band + friction

**Stage 18 (logistic structure test, KXWTIW):**
- T-1d: b = 0.69 [90% CI: 0.68–0.71], c = +0.023 [0.020, 0.027] — favourite–longshot bias confirmed, state tilt
  changes sign across snapshots
- T-4h: b = 0.68 [0.66–0.70], c = −0.009 [−0.015, −0.003]
- b < 1 indicates longshots are systematically overpriced on Kalshi vs. the density — but only by ~one tick

**Friction (first pass, from TBBO/estimated):**
- Measured CME half-spreads: 4–5¢/bbl (from one removed trade — later shown to be misleading; see V2)
- Chain-estimated friction: median 12¢ per Kalshi dollar at T-1d, 10¢ at T-4h
- Range: 7–30¢ per Kalshi dollar
- Only **2 brackets** at T-1d and **1 at T-4h** had every leg quoted within 5 minutes of the snapshot (TBBO data)

**KXWTI (daily arm, 46 cleared T-4h dates):**
- Mean gap: +0.4¢, mean |gap|: 1.0¢
- Stage 18: b = 0.88 [0.85–0.91], c = +0.066 [0.042–0.092] — less pronounced bias, one snapshot only
- 57 brackets below threshold, 0 trades

**Stage 19 (filter pass):** 0 brackets cleared the filter at any snapshot, either series.

**One spurious trade identified:** 2026-04-17 T-1d — Kalshi settled CLK6, options priced on CLM6. Removed by contract-
mismatch rule (Gate 0b) plus leg-staleness amendment (amendment 5). Loss would have been −29¢/contract.

### Verdict
**STRUCTURE, NOT AN EDGE**
- B1 (structure exists): ✅ — favourite–longshot bias confirmed, b ≈ 0.69
- B2 (tradeable edge): ❌ — 0 brackets cleared the filter
- B3 (survives friction at size): ❌ — 0 trades executed

**Plain English:** Kalshi and the CME options market agree on WTI bracket prices to within ~1¢. The theoretical edge
(longshot bias) exists in logit space but is worth one tick in dollar terms. CME replication costs 10× the gap.

### Caveats / Methodological Concerns
1. **TBBO data limitation:** Only 2–3 brackets per snapshot had all legs quoted within 5 minutes. The hedge was
   effectively "not priceable from the stored data" — friction was chain-estimated, not measured.
2. **The 4–5¢ half-spread figure** was extrapolated from the one spurious trade on a crash day (oil −$11), not from
   the general book. (Corrected in V2.)
3. **c (state tilt) sign-flip:** +0.023 at T-1d, −0.009 at T-4h — not a stable risk premium. B1 is carried solely by b.
4. **KXWTI one-snapshot limitation:** Only T-4h available; the two-snapshot agreement B1 requires cannot be tested.
5. **Depth unknown:** 50 or 500 Kalshi contracts per structure — depth not verifiable from stored data.
6. **Sampler and split-half failures** excluded 4–5 potentially valid dates per snapshot.

### Potential Sources of False Negatives
- The TBBO was discarding 44% of bracketable structures as "unquoted" when in fact those legs were live on the book
  (confirmed in V2 with the `bbo-1m` data). The first pass thus understated how many brackets could theoretically be
  compared, though this helped friction rather than hurting it.
- Estimated friction (chain-based, ~12¢ median) was **lower** than the real book friction (~21–25¢). This means the
  first pass actually *overestimated* the chance of finding a clear — i.e., the methodology had a false-positive bias,
  not a false-negative one.
- If Kalshi's actual taker fee schedule differs from `KALSHI_FEE_COEF=0.07` used in the model, results could shift
  slightly (but not enough to change the verdict, given 25¢ gaps).

---

## 2. FINDINGS_BACKTEST_V2.md

### Purpose
A **corrected re-render** of the first backtest after two protocol amendments:
- **Amendment 7:** Fee overcharge on two-leg structures corrected (4-leg fee was applied to all structures)
- **Amendment 8:** CME legs now priced from the live `bbo-1m` order book at the snapshot minute, replacing the
  TBBO/chain-estimated approach

Extractor, gates, and thresholds unchanged. This is the definitive version.

### Key Numerical Results

**Gap statistics (unchanged from V1):**
- KXWTIW T-1d: mean gap +0.2¢, mean |gap| 1.1¢, median 0.5¢
- 23% outside the 90% band; 0% outside band + friction
- Stage 18 b: identical to V1 (0.69 at T-1d, 0.68 at T-4h)

**Friction (corrected, from live book `bbo-1m`, 58 snapshot windows):**
- **Four-leg bracket:** median 21–25¢ per Kalshi dollar (vs. ~12¢ estimated in V1)
  - T-1d deep tail: 20.8¢ (p25–p75: 14.0–49.1¢), spread component 18.0¢
  - T-1d moderate tail: 24.8¢ (18.7–35.8¢), spread 21.0¢
  - T-4h deep tail: 24.8¢ (22.5–40.4¢), spread 22.0¢
- **Two-leg threshold:** median ~15¢ per Kalshi dollar
- Per-leg half-spread medians: 2.38–3.63¢/bbl depending on moneyness
- Closest miss: 1.6 probability points from clearing (nearest any bracket came to breaking even after friction + band)
- Median shortfall: 25¢ at T-1d

**Bracket status redistribution:**
- V1 had 201 "cme_leg_unquoted" at T-1d → V2 has **1** (one leg beyond the listed strikes)
- V1 had 2 "below_threshold" at T-1d → V2 has **202** (all those previously unquoted brackets now have live legs
  and are properly evaluated, and all fail the threshold)

**KXWTI friction (corrected):**
- Deep tail: 7.4¢ (was 8.8¢ in V1 — 1.4¢ fee overcharge corrected)
- Body: 14.1¢ (was 15.5¢)

**Top 15 worst-case brackets (in probability space), both KXWTIW and KXWTI:** None pass. Best net after friction:
- KXWTI 2026-04-20 T-4h "$91 or above": +0.1 pts after friction, but still fails band (need +1.1 pts more)
- KXWTIW 2026-01-30 T-4h "$64 or above": −0.1 pts after friction, fails band by 2.6 pts

### Verdict
**STRUCTURE, NOT AN EDGE** — unchanged.

Key upgrade: the hedge is now **measured**, not estimated. Friction is larger than V1 estimated, making the null
stronger. Zero brackets cleared; nearest miss 1.6 points; median shortfall 25¢.

### Caveats / Methodological Concerns
1. **Friction direction of surprise:** V2 found friction was roughly **double** V1's estimates (21–25¢ vs. 12¢).
   The first pass understated the barrier significantly — the live book is ~2× wider than the TBBO (which only
   samples at trade events, i.e., at the tightest moments).
2. **`bbo-1m` data cost $4.23** and covered 181,675 two-sided samples — this wasn't "free" to confirm.
3. **Fee assumptions still unverified:** `CME_FEE_PER_LEG=$2.37`, `KALSHI_FEE_COEF=0.07` — secondary vs. spread
   but should be verified against live schedules.
4. **Size assumption unverified:** 500 Kalshi contracts per structure. Depth at this size not confirmed.
5. **KXWTI two-snapshot constraint** persists — B1 can only be called STRUCTURE conditionally.
6. **Contract roll ambiguity:** 6 dates excluded for contract mismatch (01-16, 04-17, 05-15) — Kalshi's naming
   convention inconsistent with stated rules. See FINDINGS_LEGCOUNT.md §C.

### Potential Sources of False Negatives
- **Same as V1**, with the key one now closed: the TBBO data gap is no longer a concern. All 304 previously
  "unquoted" brackets had live two-sided legs on the `bbo-1m` book. The edit makes the test *more* conservative
  (higher friction), so there's less risk of false negatives now.
- **Remaining risk:** If Kalshi's actual executable spread at size differs materially from the mid-market `bbo-1m`,
  the friction could be even higher. The test assumed the book is fillable at the quoted spread.
- **Out-of-sample:** 24 KXWTIW events is a relatively thin sample. Edges requiring 30+ comparators for reliable
  detection might not be visible yet — though with median shortfalls of 25¢, the effect size would need to be
  implausibly large.

---

## 3. FINDINGS_LEGCOUNT.md

### Purpose
An **error-correction and methodological audit** document covering three issues discovered after the first pass:
(A) Fee overcharge on two-leg structures; (B) Friction measurement from TBBO vs. live book; (C) Roll rule
documentation error. Also catalogs all exchange-settled threshold ladders in the data store.

### Key Numerical Results

**A. Leg-count audit:**
- KXWTIW: 728 two-sided brackets — 648 four-leg ("between"), 80 two-leg (tails/thresholds)
- KXWTI: 1,474 two-sided brackets — 1,469 two-leg thresholds, 5 four-leg
- Fee overcharge per two-leg structure: **1.42¢** (was charging `4 × $2.37 × 1.5/500 = 2.84¢` regardless of leg
  count; corrected to `n_legs × $2.37 × 1.5/500`)
- After fix: no bracket changes status; nothing clears. Verdict unchanged.

**B. Friction measurement — TBBO vs. live book:**

*TBBO (6,450 quotes, trade-sampled):* median 1.5–2.0¢/bbl by distance from forward — biased toward tight because
a trade crosses only when someone hits a tight market.

*Live `bbo-1m` book (3,038 instruments at snapshot minute, 181,675 total samples):*

| Distance from forward | Half-spread median |
|---|---|
| < $0.50 (ATM) | 4.00¢/bbl |
| $0.50–1.00 | 3.00¢ |
| $1–2 | 3.00¢ |
| $2–6 | 2.50¢ |
| $6–12 | 2.50–3.00¢ |
| > $12 | 4.00¢ |

By premium level: 1.5¢ under $0.05 premium, 3¢ at $0.10–0.25, 4–5¢ at $0.25–1.00, 8.5¢ at $1–2.

Leg availability by TBBO vs. live book: at <$0.50 from forward, TBBO had 55% of legs quoted within 5 min;
live book had 100% at the snapshot minute. At >$12 from forward: TBBO 0%, live book 69%.
→ TBBO was silently discarding 44% of comparable brackets. The live book finds them all live.

**Friction per bracket (live book, by leg count):**
- Four-leg brackets: median 23.1¢ (T-1d), 25.8¢ (T-4h)
- Two-leg thresholds: median 15.5¢ (T-1d), 15.6¢ (T-4h)
- Closest miss: 1.6¢ short (four-leg, T-4h), 2.7¢ short (two-leg, T-4h)

**Closest call (daily arm):** 2026-03-20 "$92.99 or below" — Kalshi 0.150 vs. density 0.289 = 13.9-point
disagreement, but friction is 12.3 points (two puts at 6.5¢ and 7.0¢ wide), net +1.5 before band, −0.2 after.
Settled "no" (price was 98.23). Not a missed trade.

**C. Roll rule:**
- "The 16th" and "2 business days before LTD" are both wrong as general rules.
- Observed switches: 1–4 business days before NYMEX last trading day, varying by month.
- From June 2026, Kalshi's `rules_primary` field names the contract directly → 99% reliable.
- Pre-June: calendar fallback is unreliable. Gate 0b + settlement verification is the correct approach.
- The backtest's ex-post check caught every misassignment. The 6 excluded dates were all correct exclusions.

**D. Other exchange-settled ladders in the store:**
- KXWTIW: 201 events, ICE WTI, RANGE ladder — in the study
- KXWTI: 838 events, ICE WTI, threshold ladder — in the study (as two-leg)
- KXGOLD: 19 events, ICE gold, RANGE ladder — candidate for future study (COMEX GC options, not examined)
- KXWTIMAX/KXWTIMIN: path-dependent, not hedgeable with vanilla digitals
- Others (KXWTIVSBRENT, Pyth-settled series): not hedgeable

### Verdict / Conclusion
**Null confirmed and strengthened.** The leg-count fix was small (1.42¢ per structure); the friction remeasurement
was large (doubled). Both changes make the null more robust, not less.

### Caveats / Limitations
1. **Only the snapshot minute was sampled** for the live book. Intraday tightening could mean a patient trader
   entering earlier gets better fills — but the protocol is snapshot-time pricing.
2. **TBBO's selection bias** now fully quantified and documented. The first pass was working with a fundamentally
   misleading data source for hedge pricing.
3. **Roll rule ambiguity pre-June 2026** is a permanent limitation on those historical dates. The settlement
   verification is the only reliable check.

### Potential Sources of False Negatives
- **Timing of entry:** The live book at the snapshot minute might not reflect what a trader could achieve with a
  limit order placed 30 minutes earlier. Earlier entry might catch tighter spreads — but the test framework is
  not designed for this.
- **KXGOLD not examined.** If a similar density extractor works on gold and the friction is lower (COMEX GC
  options have a different liquidity profile), this could be a missed opportunity.

---

## 4. FINDINGS_ACTII_V2.md

### Purpose
An independent analysis of Act II (the SVI-based extractor, the "second pass" extraction method) vs. Act III
(the main spline/Gaussian posterior extractor used throughout the backtest). Tests whether Act II fires on the
same chains where split-half fires, and whether Act II's anomaly detection reveals real density structure vs.
extractor artifacts. Uses `synth/results_real/runs_v2.pkl` — no Kalshi prices involved.

**Context:** Act II = alternative SVI-based fit; Act III = primary extractor; "fires" = flags a chain as
anomalous. Split-half = the V2 stability gate (max |z| > 2.65). Both gates were studied to understand if they
catch the same problems.

### Key Numerical Results

**Act II firing rates (raw V1 vs. synchronized V2):**

| Snapshot | Window | V1 raw fire rate | V2 sync fire rate |
|---|---|---|---|
| T-2d | 60-min | 64% | 31% |
| T-1d | 60-min | 68% | **7%** |
| T-4h | 60-min | 77% | **53%** |
| Pooled | all | 67% (n=90) | **27%** (n=124) |

Calibrated false-positive rate on well-specified synthetic chains: **0%**. Rate on bimodal calibration chains: **100%**.

**V1 raw → V2 synchronized reduction:** Synchronization (fixing intraday path asynchrony) explains most of the
high V1 firing rate. The main confound was Act II differentiating asynchronous chains, not genuinely bimodal ones.

**Act II vs. split-half agreement (V2 synchronized, pooled over 124 chains):**
- Both fire: 11 chains
- Act II only: 22 chains
- Split-half only: 9 chains
- Neither: 82 chains
- φ = 0.28, Fisher p = 0.004, Jaccard = 0.26
- **T-1d/60: fully disjoint** — 0 chains fire both, 2 Act II only, 5 split-half only

**The four chain classes (V2 synchronized):**

| Class | n | Act II Δ median (¢) | χ²/strike median | Multimodal posterior | LOO flags |
|---|---|---|---|---|---|
| Both fire | 11 | 9.03 | 5.2 | 45% | 5.8 |
| Act II only | 22 | 3.41 | 1.5 | 14% | 2.0 |
| Split-half only | 9 | 2.14 | 3.3 | 0% | 4.7 |
| Neither | 82 | 0.83 | 1.4 | 0% | 1.0 |

**The 22 Act-II-only fires decompose into 4 groups:**
1. **3 genuinely multimodal T-4h chains** (2026-05-01, 2026-05-29, 2026-03-06): τ = 6.7–17.0 (vs. normal ≈0.7–1.0),
   96–100% of draws multimodal, 2–4 posterior modes, 6–7 LOO flags, Act II disagreement 5–21¢. These are the
   ones split-half cannot see because both halves share the same pathology.
2. **Act II is broken, not the chain** — SVI wings run to $16–24 above forward, or |ρ| pinned at 0.99 constraint.
   Chains pass split-half easily; Act II's error is the signal.
3. **Thin chains (9–11 strikes)** — already flagged as "untrusted" by Act II's own output.
4. **Marginal fires at clean chains** — 6 of 82 clean chains at/just above the 2.5¢ p95 cutoff. Expected false
   positives.

**T-4h/60 summary:** Act II fires on 53% of T-4h chains; split-half fires on 17%; overlap φ = 0.42. The 5 "both"
chains at T-4h are the worst in the study (χ²/strike 5.2 median).

**Act II fit health issues:**
- Density mean within 15¢ of the forward: only 52–73% of chains
- p90 of |mean − F₀|: $1.8 to $20 depending on snapshot
- Act II probabilities inside Act III's 90% band on all brackets: 0–15% of chains
- Root cause: SVI wings extrapolate beyond the last strike unconstrained; the wing slope (Lee's b·(1+|ρ|)) is
  not pinned to the forward

### Verdict / Conclusion
**Act II cannot be used as a gate in its current form.** It successfully identifies 3 genuinely anomalous T-4h
chains that split-half misses — this is valuable — but 19 of 22 Act-II-only fires are either Act II's own fit
errors or expected false positives from a p95 cutoff. The prior does not need adjustment based on this evidence
(the 3 true anomalies are all T-4h, where path reconstruction is weakest). T-4h remains the critical open
question for Task 2.

**For the backtest:** Act II's anomaly detection did not affect any backtest result (FINDINGS_BACKTEST.md/V2 used
only split-half and the standard gates). This is a methodological document about the extractor's diagnostic
capabilities.

### Caveats / Limitations
1. **Act II's SVI wings unconstrained:** Until wing slopes are pinned or the mean is constrained to the forward,
   Act II cannot be used as a filter gate.
2. **T-4h path reconstruction uncertainty:** The three genuinely multimodal chains are all T-4h. The window sits
   furthest from the 14:29 intraday anchor, uses a reconstructed path. If the reconstruction introduces bias,
   the posterior multimodality might be an artifact.
3. **Small n for the "both fire" class:** Only 11 chains. The association statistic (φ = 0.28) is based on small
   counts; the T-4h sub-result (φ = 0.42) has only 30 chains total.
4. **Act II comparison restricted to priced brackets:** Act II vs. Act III probabilities include tail brackets
   where the SVI extrapolation is most unreliable.

### Potential Sources of False Negatives
- **Split-half misses genuine bimodality** when both halves carry the same structure (the "both fail the same way"
  case). The 3 confirmed multimodal T-4h chains are exactly this. If real WTI densities are bimodal around
  EIA release times, the main gate (split-half) cannot see it.
- **T-4h is undertested:** 53% Act II fire rate at T-4h vs. 7% at T-1d. If real edge opportunities concentrate
  near settlement (T-4h), the extraction quality at that snapshot is the binding constraint, and it's currently
  the weakest link.
- **Act II's wing problem masks true anomalies in the tail:** The 0–15% rate of Act II being within Act III's
  band on all brackets means nearly all Act II fires in the tails are fit artifacts. If there are real density
  anomalies in the deep tail, Act II as currently implemented cannot reliably surface them.

---

## Cross-Document Summary

| Document | Core Question | Answer | Confidence |
|---|---|---|---|
| FINDINGS_BACKTEST.md | Is there a tradeable edge? | No (0 trades, friction ~12¢ vs. 1¢ gaps) | High — though friction was underestimated |
| FINDINGS_BACKTEST_V2.md | Same, with correct friction | No (0 trades, friction 21–25¢ vs. 1¢ gaps) | **High** — friction now measured from live book |
| FINDINGS_LEGCOUNT.md | Was the backtest methodology sound? | Mostly yes; one fee bug (1.42¢) fixed; friction remeasured (2× larger than estimated) | High |
| FINDINGS_ACTII_V2.md | Does Act II add signal? | Partially — it catches 3 real bimodal T-4h chains; broken as a gate otherwise | Medium |

### Open Questions / Next Steps (as identified in the documents)
1. **Trade structure, not density:** The extractor is validated (±1¢ agreement with Kalshi across 535 bracket comparisons). The question is whether any replication of a Kalshi bracket can be built for under ~10–15¢. This requires a different instrument (narrower spreads, Micro options, direct Kalshi hedging).
2. **T-4h multimodality:** 3 T-4h chains have genuine multimodal posteriors. Task 2 needs to determine if these survive a real intraday path (vs. reconstruction artifact).
3. **KXGOLD:** Not examined. Exchange-settled, RANGE ladder, with COMEX GC options as the potential hedge. Unknown friction profile.
4. **Roll rule documentation:** Updated in PIPELINE_CHOICES.md, PIPELINE_MAP.md, and root writeup. The reliable approach is: read `rules_primary` when available (post-June 2026), else verify settlement value directly.
5. **Act II repair:** Pin wing slopes or constrain the SVI mean to the forward; restrict comparison to brackets inside the strike range.
6. **Live trading experiment (mentioned in FINDINGS_LEGCOUNT.md §B):** Checking tastytrade chain at ~14:30 ET on Thursdays (3 Thursdays needed) to see if the book at the close is similar to the snapshot-minute book — a free cross-check.
