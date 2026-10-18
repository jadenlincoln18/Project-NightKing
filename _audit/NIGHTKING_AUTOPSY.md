# Project NightKing — Independent Audit & Post-Mortem

**Auditor:** Alfred (AI)  
**Date:** 2026-10-04  
**Requested by:** Jaden Patel  
**Question:** Is the backtesting verdict a true negative, or could mistakes have produced a false negative?

---

## Executive Summary

**The verdict is correct. NightKing is dead.**

After auditing every FINDINGS document (16 files), the full codebase (`synth/backtest.py`, `synth/act3.py`, `synth/realchain.py`, `synth/friction_measure.py`, `synth/detector.py`, and all supporting modules), the BACKTEST_PROTOCOL, 8 protocol amendments, the synthetic validation harness, the real-chain studies (V1–V4), the data collection infrastructure, and the master strategy writeup — I find no bug, no methodological error, and no data quality issue that would flip the result.

The backtesting was conducted with exceptional rigor. The protocol was committed before any Kalshi price was read. The extractor was frozen. Thresholds were pre-stated. Every amendment is documented and justified. The work is honest.

**The gap between what exists and what would be needed is not close.** The typical signal is ~1¢. The typical friction is ~22¢. That's a 20:1 ratio in the wrong direction. No plausible correction — fixing every known issue, using optimistic assumptions, switching to cheaper hedge structures — comes within an order of magnitude of viability.

---

## Part 1: What the Backtest Found

### The Signal
Across 24 KXWTIW weekly settlement dates (Jan–Sep 2026), 535 bracket comparisons:

| Metric | Value |
|---|---|
| Mean gap (Kalshi vs density) | **+0.2¢** |
| Mean |gap| | **1.1¢** |
| Median |gap| | **0.5¢** |
| Brackets outside 90% posterior band | 23% |
| Brackets outside band + friction | **0%** |

The two venues agree to within a cent. The density extractor works — Kalshi independently confirms it — but there is nothing to trade.

### The Structure (B1 — holds)
Stage 18 finds the favourite-longshot bias:

| Snapshot | b [90% CI] | Interpretation |
|---|---|---|
| T-1d | 0.69 [0.68, 0.71] | Longshots are rich on Kalshi |
| T-4h | 0.68 [0.66, 0.70] | Consistent across snapshots |

In logit space this looks meaningful. In dollar terms, it's Kalshi asking 2¢ for brackets the density prices at 0.6¢ — which is the 1¢ minimum tick plus a 1¢ spread. The "bias" is the tick grid, not a mispricing.

### The Friction
Measured from the live order book (`bbo-1m`, 181,675 quote snapshots across 58 windows):

| Structure | Friction (per Kalshi $1) |
|---|---|
| Four-leg bracket (outer condor) | **21–25¢** |
| Two-leg threshold ("Above $X") | **~15¢** |
| Dominant component | CME bid-ask spread (18–22¢ of the total) |

### The Verdict
- **B1 (structure exists):** YES — favourite-longshot bias present at both snapshots
- **B2 (tradeable edge):** NO — zero brackets clear the filter at any date
- **B3 (survives friction):** NO — zero trades
- **Mechanical verdict:** STRUCTURE, NOT AN EDGE

The nearest miss was 1.6 probability points short of clearing band + friction. The median shortfall was 25¢.

---

## Part 2: Could This Be a False Negative?

I examined every plausible mechanism by which the test could have missed a real signal. None holds.

### 2.1 Could friction be overstated?

**No.** The friction *increased* during the audit process, not decreased.

- **V1 (TBBO-based estimate):** ~8¢ median. This used trade-sampled quotes — the book at its tightest moments, because trades happen when someone crosses a tight spread. The TBBO also silently discarded 44% of replicating legs as "unquoted" (no recent trade attached a quote, even though the live book had two-sided markets on 100% of them).
- **V2 (bbo-1m measurement):** 21–25¢ median. This is the actual resting book, sampled every minute. It's ~2× wider than trade-sampled TBBO at every moneyness level.
- **The corrections all went one direction:** the leg-count fee bug (Amendment 7) overstated fees by 1.42¢ on two-leg structures. Fixing it made friction *slightly lower*, but 1.42¢ against a 22¢ total is noise.

**Could a different broker reduce friction?** The commission assumption is $0.85/leg. Even at zero commission, CME fees are $1.52/leg (exchange + NFA), and the fee component is only ~2¢ of 22¢ total. The spread dominates. You'd need spreads to be 10× tighter to matter, which contradicts 181,675 independent book snapshots.

**Could crossing be avoided by resting on the CME side?** In theory, yes — a resting order at mid saves the half-spread. In practice: (a) you need all 4 legs filled simultaneously before the Kalshi side moves, (b) the Kalshi leg is taker by necessity (you're hitting the executable price), (c) the fill-time risk on a 4-leg resting strategy in weekly WTI options is enormous, and (d) the signal itself (~1¢) is smaller than the half-spread on a single leg (2.5–4¢), so even saving the spread on 3 of 4 legs doesn't close the gap.

### 2.2 Could the signal be understated?

**No.** The gap is computed on the executable side of the Kalshi book. There's no systematic direction to the measurement. Mean gap is +0.2¢, median is essentially zero. Across 24 independent weekly dates with 10–25 brackets each, the variance is low (sd ~0.5–2¢ depending on moneyness band). This is not a noisy signal being averaged to zero — it's a genuinely small signal.

**Could a different snapshot time reveal larger gaps?** The backtest tested T-1d (14:30 ET the day before settlement) and T-4h (10:30 ET on settlement day). The gaps are equally small at both. The gap signs at the two snapshots agree at chance (49%), which means the gaps are noise around zero, not a persistent signal that decays. This is qualitatively different from fedarb, where the gap was 4¢ with 92% sign consistency and a measurable 20-minute half-life.

**Could the density extractor be systematically wrong?** The synthetic validation proves it works on smooth densities (90% coverage ≥93% in body, every injected fault caught at 100%). It has a known blind spot on bimodal densities (trough coverage 57% at 48 knots, down from 3% at 24 knots). But the bimodal blind spot would *create* phantom edges (overconfident in smooth when truth is bimodal), not *hide* real ones. If anything, the extractor's overconfidence on bimodal truth should bias toward *more* apparent signal, not less.

### 2.3 Could the data be wrong?

**No.** The data pipeline is the most audited part of the project.

- **Kalshi data:** 58.9M candles across 130+ series. Four separate collection failures were found and turned into tests (5000-candle cap, `close_dollars` vs `close`, 40-page cursor cap, network-vs-never-traded conflation). The data is verified.
- **CME data:** Databento pull complete at $16.14 + $4.23 for bbo-1m. TBBO and bbo-1m cross-validated. Definitions filtered to the requested root. Stray roots and spread futures excluded. Partial downloads detected and re-bought.
- **Settlement basis:** KXWTIW ICE vs NYMEX: zero to the cent on 33 of 34 dates. KXWTI: tight in body (98%), with 2 unexplained events in 162 (worst: $4.70). The basis is not a confound on KXWTIW.
- **Contract month assignment:** The one "trade" in V1 was a contract-month mismatch (Kalshi on CLK6, options on CLM6). Caught by Amendment 4's ex-post check. Neither the "16th rule" nor the "2 business days before LTD" rule correctly predicts Kalshi's roll dates. The backtest's verification-based approach is the only reliable one.

### 2.4 Could the hedge structure be suboptimal?

**Partly, but it doesn't matter.** The outer condor is the simplest faithful replication of a $1 bracket on a $0.50 strike grid. Alternatives considered:

| Alternative | Legs | Issue |
|---|---|---|
| Two-leg threshold ("Above $X") | 2 | Already tested: friction ~15¢, gaps ~1¢. Still 15:1 wrong direction. |
| Adjacent-bracket run (one wider digital) | 2 | Fewer legs, but wider ramp residual. Listed in BACKTEST_NEXT_PASS item 1(a). Even if friction halved: 11¢ vs 1¢ gap. |
| Delta hedge in futures | 1 | Accepts gamma risk. The residual variance over a 1-day hold is much larger than the ~1¢ gap. |
| Inner condor | 4 | Ramp *inside* the bracket, mismatch up to $1 at the lower edge. Worse, not better. |

The cheapest possible hedge (a single two-leg threshold) still costs 15¢ against a 1¢ signal.

### 2.5 Could the sample be unrepresentative?

**Unlikely.** 24 weekly settlement dates spanning January–September 2026, across different oil price regimes ($64–$98 range in the per-date table), different volatility environments, and different market structures. The Stage 18 parameters are stable across dates (b individually < 1 on 14 of 24 dates). This isn't one regime — it's 9 months of data.

The sample is smaller than ideal (effective n ~ 24–30 dates, not 535 brackets, because brackets within a date share a density). But the conclusion is robust at this sample: the gap:friction ratio is 1:20, not 1:1.5 where sample size might matter.

### 2.6 Could the extractor's known weaknesses (bimodal blind spot, sampler diagnostics) matter?

**No — they work in the wrong direction for a false negative.**

- **Bimodal blind spot:** The P-spline roughness prior produces overconfident posteriors when truth is bimodal (trough coverage 3–57% depending on knot count). This means the extractor reports *narrow* bands when it should report *wide* ones. Narrow bands make it *easier* for |gap| to exceed band + friction, not harder. If the bimodal blind spot were causing problems, we'd see more apparent edges, not fewer.
- **Sampler diagnostics:** 4 of 29 dates at T-1d fail sampler checks (R̂ > 1.05 or ESS < 100). These dates are excluded from trading but *kept in the gap tables*. Their gaps are the same size as the cleared dates (mean |gap| 0.3–1.3¢). Including them wouldn't change the verdict.
- **Stage 6 se underestimate:** The forward standard error is ~25% too small (RMSE 1.17¢ vs se 0.89¢). This affects the martingale constraint precision but not the bracket probabilities directly. The forward sensitivity is 0.036 ¢/¢ — a 1¢ forward error changes a bracket by 0.04¢. Not material.

---

## Part 3: Why NightKing Failed — The Real Reasons

### Reason 1: The markets agree.

This is the fundamental finding that no methodology change can overcome. Kalshi's bracket prices and the CME options-implied density *agree to within a cent*. There is no mispricing to exploit. The two venues are looking at the same underlying (ICE WTI vs NYMEX CL, which agree to the cent 96% of the time), at the same settlement time, and reaching the same probabilities.

The favourite-longshot bias (b ≈ 0.69) exists in logit space but is tiny in cent space — it's the 1¢ minimum tick on Kalshi. Longshot brackets that the density prices at 0.3–0.6¢ can't trade below 1¢ on Kalshi. The "bias" is mechanical, not informational.

### Reason 2: The hedge is too expensive.

Even if a 5–10¢ gap existed, the CME options to replicate a $1 Kalshi bracket cost 21–25¢ of the bracket's value in bid-ask spread alone. The fundamental problem is unit economics:

- A $1 Kalshi bracket maps to a $0.50/bbl option condor
- The half-spread on a CL weekly option is 2.5–4¢/bbl
- Four legs × 3¢ average half-spread = 12¢/bbl of round-trip spread
- 12¢ / 0.50 = **24¢ per Kalshi dollar** just in spread

This is structural. CL weekly options are liquid by commodity standards but not liquid enough to replicate penny-scale digital claims. The "distribution vs ladder" thesis assumed the hedge would cost a few cents. It costs a quarter of the bet.

### Reason 3: Fedarb's lesson repeated at larger scale.

Fedarb died on capacity (hedge ratio 1,042:1, thin book). NightKing improved the hedge ratio dramatically (500:1 for CL, 50:1 for MCO) but hit the same wall in a different form: the friction of the hedge exceeds the gap. The common cause is that **prediction markets and derivatives markets price the same events from the same information, and the cross-venue friction exceeds the cross-venue disagreement.**

This is not an accident. The people making markets on Kalshi's WTI ladder are the same firms — or firms with the same models — as the ones making markets on CME WTI options. The information flows faster than the hedge can be assembled.

### Reason 4: The thesis's key assumption was wrong.

The writeup's thesis was: "Where they disagree by more than posterior spread + friction, trade the gap." The assumption was that the gap would be larger than the friction. The backtesting reveals:

- The gap is ~1¢ (smaller than hypothesized)
- The posterior band is ~1–5¢ (as expected)
- The friction is ~22¢ (10× larger than the ~2¢ assumed in early planning)

The thesis was falsified on the friction term, not the signal term. The density extractor works. The comparison methodology works. The gap decomposition (Stage 18) works. The infrastructure is production-grade. But the cost of locking the gap — crossing 4 option spreads on the CME — is an order of magnitude larger than the gap itself.

---

## Part 4: What Went Right

This project did not fail in the way most trading strategies fail. Most fail because the signal was data-mined, the backtest was overfit, or the friction was ignored. NightKing did the opposite:

1. **The protocol was committed before any price was read.** Extractor frozen, thresholds pre-stated, verdict vocabulary defined. No post-hoc tuning.
2. **Every data quality issue was found and fixed.** The four Kalshi collection bugs, the TBBO's structural bias, the contract-month mismatch, the roll-date rule error — all discovered and corrected honestly.
3. **The synthetic validation was honest about what failed.** The bimodal blind spot was reported as a FAIL verdict, not swept under the rug.
4. **The friction measurement improved during the project** (TBBO estimate → bbo-1m measurement), and the result got *worse*, not better. This is the hallmark of honest research.
5. **The single spurious "trade" was removed by a data rule, not a results rule.** The protocol amendment explicitly separates "a rule about the data" from "a rule about the result."

The intellectual architecture — distributions vs scalars, two independent density pipelines (Act II and Act III), gap decomposition into favourite-longshot and risk premium, pre-stated evidentiary bar — is sound. The infrastructure (hand-rolled NUTS, synthetic harness, real-chain validation, live book measurement) is exceptional for an undergraduate project.

The strategy failed because the opportunity doesn't exist at this venue pair, not because the methodology was wrong.

---

## Part 5: Could Anything Save It?

I considered every lifeline systematically:

| Lifeline | Assessment |
|---|---|
| Different underlying (gold, natgas, Brent) | KXGOLD is the only other exchange-settled ladder. Untested but faces the same friction structure on GC options. Natgas/Brent settle on Pyth — basis risk is unquantified. |
| Different snapshot time | T-1d and T-4h show the same thing. Gap signs agree at chance. |
| Maker on Kalshi (avoid taker fee) | Saves 0.63–1.75¢ per contract. The taker fee is <10% of total friction. |
| Resting on CME (avoid crossing) | Saves ~12¢ if all legs fill. But fill risk on 4 resting legs in weekly CL options is enormous, and the 1¢ signal has a sub-day half-life (if it exists at all). |
| MCO (Micro) for smaller hedge ratio | MCO consistently fails quote density thresholds. The book is thinner, not tighter. |
| Wait for Kalshi to add tighter brackets | Sub-$1 brackets would face worse favourite-longshot (tick grid effect stronger). |
| Wait for CME options spreads to tighten | Structural: weekly commodity options trade at 2.5–4¢ half-spread because that's the tick. No reason to expect change. |
| Different extractor (mixture model, non-uniform splines) | Would fix the bimodal blind spot. But the blind spot *inflates* apparent edges; fixing it would make the signal *smaller*, not larger. |
| Case 2 (use options as truth, trade Kalshi directional) | The writeup explicitly prohibited this. The gap decomposition (Stage 18) shows you can't distinguish mispricing from selling insurance. Case 2 is the trap. |

**None of these are viable.**

---

## Part 6: Final Verdict

**NightKing is a true negative.** The methodology is sound, the implementation is correct, the data is clean, and the result is unambiguous: the two venues agree, and the hedge costs 20× the gap. There is no false negative here.

This is the same death as fedarb — cross-venue friction exceeds cross-venue disagreement — but arrived at through a far more rigorous process. The lesson is structural: **prediction markets and options markets price the same events from the same information, through overlapping market-maker populations, and the arbitrage channel between them is too expensive to traverse at retail scale.**

The project should be closed. The infrastructure, methodology, and intellectual capital are genuinely valuable — they just need a different venue pair where the friction is small relative to the gap, or where information asymmetry between venues is structural rather than momentary.

---

## Appendix: Audit Trail

### Documents Reviewed
- `FINDINGS_BACKTEST.md` (V1, first pass)
- `FINDINGS_BACKTEST_V2.md` (re-render with corrected fees and bbo-1m legs)
- `FINDINGS_LEGCOUNT.md` (leg-count audit, friction measurement, roll rule)
- `FINDINGS_ACTII_V2.md` (Act II diagnostic firing rates)
- `FINDINGS_REALCHAIN.md` through `FINDINGS_REALCHAIN_V4.md` (extractor calibration on real data)
- `FINDINGS_SYNTHETIC.md`, `FINDINGS_SYNTHETIC_48.md`, `FINDINGS_SYNTHETIC_V2.md` (synthetic validation)
- `FINDINGS_TICKFLOOR.md` (likelihood tolerance study)
- `FINDINGS_PRIOR.md` (prior sensitivity study)
- `data/FINDINGS.md` (Kalshi series census)
- `data_cme/FINDINGS_CHAIN.md` (CME option chain audit)
- `data_cme/FINDINGS_BASIS.md` (settlement basis study)
- `BACKTEST_PROTOCOL.md` (pre-committed protocol)
- `BACKTEST_NEXT_PASS.md` (open questions)
- `synth/backtest.py`, `synth/act3.py`, `synth/realchain.py`, `synth/friction_measure.py`, `synth/detector.py` (code)

### Bugs Found (all previously identified and fixed)
1. Amendment 4: Contract-month mismatch on one date
2. Amendment 5: TBBO leg quotes structurally too stale
3. Amendment 7: 4-leg fees charged on 2-leg structures (1.42¢ overcharge)
4. Amendment 8: TBBO trade-sampled spreads ~2× too tight vs live book

### Remaining Minor Issues (none affect verdict)
1. `estimate_leg_hs` still uses TBBO spreads for unquoted brackets (~2× too low estimate)
2. `CME_EXIT_FRACTION = 0.5` is a rough assumption (immaterial: ~1¢ of 22¢ total)
3. Pooled Stage 18 assumes cross-date homogeneity in b and c

### No New Bugs Found
The code correctly implements the protocol. The friction is measured, not estimated. The verdict is robust to every plausible perturbation.
