# NightKing Backtesting Code Audit

**Audited:** `worktree-forward-sync-fix` branch, `/Users/patel/.openclaw/workspace/Project-NightKing/`
**Audit date:** 2026-10-04
**Files reviewed:** `synth/backtest.py`, `synth/realchain.py`, `synth/act3.py`, `synth/friction_measure.py`, `synth/densities.py`, `synth/detector.py`, `BACKTEST_PROTOCOL.md`, `FINDINGS_BACKTEST_V2.md`, `FINDINGS_LEGCOUNT.md`, `BACKTEST_NEXT_PASS.md`

---

## 1. Architecture Overview

The backtest is a four-stage pipeline:

```
CME Options TBBO/bbo-1m ──► realchain.run_one() ──► Act III posterior ──► bracket_draws()
                                                                                  │
Kalshi 1-min candles ────────────────────────────────────────────────► compare_bracket()
                                                                                  │
                                                                         P&L / filter / Stage 18
```

**Core modules:**

| File | Role |
|---|---|
| `synth/realchain.py` | Loads option data, synchronises quotes along an intraday path, runs Act III (Bayesian spline density), Gate 4 (split-half + LOO) |
| `synth/act3.py` | The density model: exp-cubic-B-spline with second-difference roughness prior, NUTS sampler, tau integrated by 1-D quadrature |
| `synth/backtest.py` | Main backtest driver: loads Kalshi candles, integrates posterior over bracket edges (Stage 16), computes gaps, friction, Stage 18, Stage 19 filter, P&L |
| `synth/friction_measure.py` | Standalone half-spread measurement from TBBO and bbo-1m, leg availability statistics |
| `synth/densities.py` | Planted risk-neutral densities for synthetic testing |
| `synth/detector.py` | Split-half gate (max|z| over brackets) and LOO predictive residuals |

---

## 2. Friction Model — What's Included and How It's Computed

### Formula (per Kalshi contract, $1 notional)

```python
# backtest.py::friction()
f_k   = KALSHI_FEE_COEF * P * (1 - P)              # Kalshi taker fee
f_spread = sum_hs / SPREAD_WIDTH                     # CME bid-ask, in prob units
f_cme = n_legs * CME_FEE_PER_LEG * (1 + CME_EXIT_FRACTION) / SIZE_APPLICABLE
total = f_k + f_spread + f_cme
```

### Parameter values and sources

| Parameter | Value | Source / assumption |
|---|---|---|
| `KALSHI_FEE_COEF` | 0.07 | Published Kalshi general fee schedule; verify before trading |
| `CME_FEE_PER_LEG` | $2.37 | $1.50 exchange+clearing (NYMEX, non-member, Globex) + $0.02 NFA + $0.85 commission |
| `CME_EXIT_FRACTION` | 0.5 | Expected fraction of legs that finish ITM and incur assignment/exercise fee |
| `SPREAD_WIDTH` | $0.50/bbl | Condor width: matches CME $0.50 strike grid |
| `SIZE_APPLICABLE` | 500 | Kalshi contracts per standard CL structure (1000 bbl × $0.50 = $500 per structure) |
| `n_legs` | 4 (bracket), 2 (tail/threshold) | Determined by `structure_spec()` from market type |

### What is and is not in the friction stack

**Included:**
- Kalshi taker fee (both entry and exit are taker)
- CME bid-ask spread on all legs (measured from bbo-1m after Amendment 8; TBBO before)
- CME exchange, NFA, and commission fees on entry
- Expected CME fees on exit (exit fraction assumption)

**Not included (correctly excluded by construction):**
- Kalshi bid-ask spread: the gap `g` is computed on the *executable* side (bid if selling, ask if buying), so the spread is implicitly inside the gap rather than added to friction. This is correct and documented in protocol §5.
- Market impact: not modeled; at $500 notional per structure, immaterial.

### Friction in practice (as measured)

Per `FINDINGS_LEGCOUNT.md` §B, with bbo-1m quotes:

| Bracket type | Typical friction |
|---|---|
| Four-leg interior bracket | 21–25¢ per Kalshi dollar |
| Two-leg threshold ("Above $X") | ~15¢ per Kalshi dollar |
| Dominant component | CME spread (18–22¢ of the total) |

Against gaps of ~1¢ mean, friction is 15–25× the typical signal. No bracket clears the filter; the nearest miss is 1.6¢ short.

---

## 3. Signal / Edge Measurement

### Gap definition

```python
# compare_bracket()
if b["g_mid"] > 0:
    b["side"], P = "sell_kalshi", bid   # Kalshi rich: sell at bid
else:
    b["side"], P = "buy_kalshi", ask    # Kalshi cheap: buy at ask
b["g"] = P - b["pq_mean"]              # executable gap
```

Side is determined from the *mid-based* gap, then the executable price on that side is used. This avoids the circularity of using the executable price to determine which side to take.

### Model probability (`pq_mean`)

For each of M=1,600 NUTS draws, `bracket_draws()` integrates the grid density over the exact Kalshi bracket edges (from `market_edges()`, verified against the subtitle text). The posterior mean across draws is `pq_mean`.

### Stage 19 filter (a bracket is "traded" iff all hold)

1. Date clears G0a–G0d, G4, and sampler check
2. `|g| > band90 + friction_total` (band90 = 90% posterior width)
3. Executable Kalshi price in [2¢, 98¢]
4. `band90 ≤ 20¢`
5. Bracket doesn't overlap an interior trough of the posterior-mean density
6. All replicating legs have a fresh two-sided quote (≤5 min on TBBO; ≤2 min on bbo-1m)

### Stage 18 — structural characterisation

OLS per posterior draw of logit(Kalshi_mid) on logit(p_Q) + bracket_midpoint, using Kalshi's *mid* (not executable side). The slope `b ≈ 0.69` indicates the favourite-longshot bias is present, but in magnitude it's tiny — Kalshi's 2¢ quote vs the density's 0.6¢ is the 1¢ minimum tick plus a 1¢ spread, not a structural premium.

---

## 4. Comparison vs Kalshi: How It Works

The comparison computes, per bracket per snapshot:

1. **Model probability**: integral of Act III posterior density over bracket edges
2. **Kalshi executable price**: bid or ask of the stored 1-minute candle at the snapshot minute (or nearest within 10 min)
3. **Gap**: executable Kalshi price minus Act III posterior mean
4. **Hedge price**: outer condor on the CME $0.50 strike grid (from bbo-1m quotes after Amendment 8)
5. **Friction**: Kalshi fee + CME spread + CME fees
6. **Filter**: bracket is a "trade" only if |gap| > band + friction, on a valid date with quoted legs

### Key edge convention (verified at runtime)

`market_edges()` translates Kalshi's floor/cap strike fields:
- "Between $84.00 to $84.99" → edges [83.995, 84.995)
- "Above $95.99" → edges (95.995, ∞) — not the same as ≥ $96.00

This is verified against the subtitle text at runtime, with any disagreement resolved in favour of the subtitle and logged.

### Condor construction

```python
# structure_spec(): for a "between" bracket [X-0.005, X+0.995)
# where X = lo + 0.005 = round dollar
legs = [(X - 0.5, +1), (X, -1), (X + 1, -1), (X + 1.5, +1)]  # 4 legs
# for "Above $X": lower-only spread
legs = [(X - 0.5, +1), (X, -1)]  # 2 legs
```

This outer condor pays $0.50/bbl inside the bracket, zero outside [X-0.5, X+1.5], with linear ramps on [X-0.5, X] and [X+1, X+1.5]. The ramps lie *outside* the bracket, which is why the gap inside the bracket is locked (both legs cancel) but there's a ramp residual if settlement is near an edge.

---

## 5. Known Issues and Amendments (History)

### Amendment 4 (contract month mismatch)
**What happened:** Gate 0b was not verified ex-post in the first pass. The only "trade" (2026-04-17 T-1d) was a contract mismatch — the options were on CLM6 at $91.18 but Kalshi settled on CLK6 at $83.85, producing an illusory 24.5¢ gap. Removed by a rule about the data, not the result.

**Status:** Fixed. `contract_check()` now verifies the Kalshi settlement value equals the NYMEX settlement of the option's underlying. Mismatched dates are labelled `g0b_contract_mismatch`.

### Amendment 5 (TBBO leg quotes too stale)
**What happened:** TBBO's "last two-sided quote in the window" was often 20–60 minutes old (TBBO only records a BBO at the instant of a trade). The underlying moves tens of cents in half an hour, so these were not executable prices.

**Resolution:** A leg counts for a *trade* only if its TBBO quote is ≤5 minutes old. With this rule, 44% of brackets were `cme_leg_unquoted`.

**Status:** Superseded by Amendment 8 (bbo-1m).

### Amendment 7 (leg count fee bug)
**What happened:** The CME fee term was `4 × $2.37 × 1.5 / 500` on every structure, even two-leg threshold markets. Two-leg structures were overcharged by 1.42¢ (about 9% of typical friction).

**Code fix:**
```python
# Before (bug):
f_cme = 4 * CME_FEE_PER_LEG * (1.0 + CME_EXIT_FRACTION) / contracts_per_structure

# After (correct):
f_cme = n_legs * CME_FEE_PER_LEG * (1.0 + CME_EXIT_FRACTION) / contracts_per_structure
```

**Status:** Fixed in `cme_fees_per_contract(n_legs)`. All records re-processed. No bracket changed status.

### Amendment 8 (bbo-1m legs)
**What happened:** The TBBO was not just stale — it was structurally incapable of supplying an executable four-leg quote at a given instant. The bbo-1m data provides a book snapshot per instrument per minute.

**Effect:** With bbo-1m, essentially all brackets now have priced legs (vs 44% unquoted on TBBO), and the measured spreads are ~2× wider than trade-sampled TBBO: 4¢/bbl at the money, 2.5–3¢ on the tail legs. Friction per four-leg bracket is 21–25¢ rather than the estimate of ~8¢.

**Status:** Applied by `--reprocess --legs bbo1m`. The live-book legs are now the definitive measurement.

---

## 6. Potential Bugs and Issues

### 6.1 `estimate_leg_hs` uses TBBO spreads, not bbo-1m

**Location:** `backtest.py::estimate_leg_hs()`, called in `compare_bracket()` for brackets without quoted legs.

**Issue:** This function estimates friction for the "signal record" of unquoted brackets by taking the median half-spread of the TBBO-sampled chain within $1 of each leg. The TBBO's trade-sampled spreads are ~1.5–2¢/bbl, while the live bbo-1m book is ~3–4¢/bbl. Estimated friction for unquoted brackets is therefore ~2× too low.

**Consequence:** The `excess_est` and `would_clear_est` flags could falsely indicate a bracket "would clear" on estimated friction when it would not on measured friction. **However**, since no bracket clears even with the low estimate (nearest miss: 1.6 points on measured friction), this bug doesn't affect any trading or verdict decisions.

**Verdict:** No impact on results; worth noting for future passes where gaps might be larger.

### 6.2 `CME_EXIT_FRACTION = 0.5` is a rough assumption

**Location:** `backtest.py::cme_fees_per_contract()`

**Issue:** The fraction of legs finishing in-the-money at expiry (requiring exercise or assignment fees) depends on moneyness at entry. For a bracket where settlement is almost certain to be inside or outside, fewer legs may need exercise. The blanket 50% assumption could overstate exit fees for deep-tail brackets (where the condor almost certainly expires worthless) or understate them for near-ATM brackets.

**Magnitude:** The fee component is `n_legs × $2.37 × 0.5 / 500 = 0.95¢` for a 4-leg bracket — less than 5% of total friction. The spread dominates.

**Verdict:** Immaterial. The protocol documents this as an assumption.

### 6.3 `kalshi_at()` stale limit (10 minutes) may admit non-representative prices

**Location:** `backtest.py::kalshi_at()`

**Issue:** If the exact snapshot candle is absent, the function falls back to the latest candle within 10 minutes. In a volatile session, Kalshi's price 10 minutes before the snapshot could differ materially from the snapshot price.

**Consequence:** The gap `g` could reflect a price not contemporaneous with the option chain snapshot. The protocol accepts this risk and logs the candle age.

**Verdict:** Minor. The T-1d snapshot is at 14:30 ET; Kalshi markets should be active then. The `age_min` field is logged and visible in the bracket CSV.

### 6.4 Pooled Stage 18 assumes cross-date homogeneity

**Location:** `backtest.py::stage18_pooled()`

**Issue:** The pooled regression fits per-date intercepts but a common slope `b` and tilt `c`. If the favourite-longshot bias is regime-dependent (e.g., stronger when vol is elevated), the common-slope assumption is wrong and the pooled `b` is a weighted average.

**Consequence:** The Stage 18 result (`b ≈ 0.69`) is an average characterisation. The per-date regressions (also stored) would reveal heterogeneity, but the pooled estimate drives verdict B1.

**Verdict:** This is a known limitation of the pooled OLS at a small sample size (~24 dates). Not a bug — it's the analysis as designed.

### 6.5 `trough_regions()` boundary condition

**Location:** `backtest.py::trough_regions()`

**Issue:** Peaks are defined as `f[i] >= f[i-1] and f[i] > f[i+1]` (non-strict on left). This can return false peaks at the leading boundary of a flat region.

**Consequence:** Could occasionally flag a trough where none exists (false positive → bracket excluded from trading). With zero brackets being traded, this has no impact on results.

**Verdict:** Low risk; harmless given the null result.

### 6.6 `LOO_NEAR_EDGE = 1.00` radius: may miss structurally relevant strikes

**Location:** `backtest.py`, protocol §3

**Issue:** The LOO proximity flag applies to strikes within $1 of either bracket edge (= within $1 of the two condor inner strikes). The outer condor strikes are $0.50 further out, and LOO anomalies at those strikes are not flagged.

**Consequence:** A strike with high LOO residual exactly on an outer condor leg would be silently used in the hedge. Not a trading gate, but the risk factor would be underreported.

**Verdict:** Minor; the LOO is a diagnostic, not a gate. The $1 proximity is pre-stated in the protocol.

### 6.7 `bracket_draws()` grid interpolation precision

**Location:** `backtest.py::bracket_draws()`

**Issue:** CDF values are linearly interpolated from the model's grid midpoints. For brackets near the edge of the price grid (e.g., deep tail markets at ±7 vol-scales), interpolation is extrapolating from the last grid point, which always evaluates to 0 or 1.

**Consequence:** Very deep tail brackets may have `pq_mean ≈ 0` or `1`, triggering the `price_out_of_range` filter (2¢–98¢) before reaching the gap computation anyway.

**Verdict:** Handled correctly by the filter. No hidden issue.

### 6.8 `structure_quotes()` put-call parity conversion in exotic situations

**Location:** `backtest.py::structure_quotes()`

**Issue:** When a leg at strike K is priced from a put (K < F0) and converted to call terms via `conv = D * (F0 - K)`, the conversion uses the stored `F0` (the forward at the snapshot). If the forward has shifted between the option snapshot and the Kalshi candle snapshot (even 1–2 minutes), the parity conversion introduces a small error.

**Consequence:** At T-1d, F0 comes from intraday NYMEX bars (protocol: the 1-minute bar at the snapshot instant). For a $1 move in oil, the parity adjustment on a $5 OTM put vs call is ~$1 — material if the forward moved substantially between the option and Kalshi candle. However, the snapshots are designed to be contemporaneous (both at 14:30 ET), so the risk is small.

**Verdict:** Acceptable given the synchronised snapshot design.

---

## 7. Hardcoded Assumptions and Thresholds (Protocol §3–§5)

All of these are frozen before any Kalshi price was read (per protocol §8):

| Constant | Value | Risk if wrong |
|---|---|---|
| `KALSHI_FEE_COEF = 0.07` | Current Kalshi schedule | Verify before trading; schedule can change |
| `CME_FEE_PER_LEG = 2.37` | $1.50 + $0.02 + $0.85 | Commission varies by broker; IB ~$0.65–0.70 vs assumed $0.85 |
| `CME_EXIT_FRACTION = 0.5` | ~50% of legs expire ITM | Conservative; see §6.2 |
| `SPREAD_WIDTH = 0.50` | $0.50/bbl grid | Fixed by CME strike grid; would change if $1 grid used |
| `SIZE_APPLICABLE = 500` | Kalshi contracts per CL structure | Correct for 1000 bbl × $0.50; verify at execution |
| `KALSHI_STALE_MAX_MIN = 10.0` | Candle age limit | 10 min is generous; tighten for live trading |
| `PRICE_MIN, PRICE_MAX = 0.02, 0.98` | Executable price range | Reasonable; screens missing sides |
| `BAND_MAX = 0.20` | Max 90% posterior width | Uninformative extraction filter |
| `TROUGH_DIP = 0.02` | Min dip for interior minimum | Calibrated to avoid grid ripple |
| `LEG_SHIFT_MAX = 2` | Max 0.25-step outward shifts when a strike is unquoted | Widens ramp; logged |
| `LEG_MAX_AGE_MIN = 5.0` | Max TBBO quote age for executable legs | Effectively not binding with bbo-1m (age ≤2 min) |

---

## 8. The bbo-1m vs TBBO Data Quality Issue

This is the most structurally important finding in the codebase history.

**TBBO (before Amendment 8):**
- Records a BBO at each trade event — biased toward liquid, tightly-spread moments
- Median half-spread 1.5–2¢/bbl (trade-sampled tightest moments)
- 44% of replicating legs "unquoted" at ≤5 min age filter (not a market issue — they have live quotes, just no recent trade to attach them to)

**bbo-1m (after Amendment 8):**
- One book snapshot per instrument per minute — unbiased sample of the resting book
- Median half-spread 4.0¢/bbl at the money, 2.5–3¢/bbl at 2–8$ OTM
- 100% of replicating legs quoted (every bracket has a priced hedge)

**Impact:** Friction for a four-leg bracket goes from ~8¢ (TBBO-estimated) to 21–25¢ (bbo-1m measured). The gaps are ~1¢. The null result was robust to this change — gaps were always far below friction — but the *quality* of the friction measurement changed from an estimate to a measurement.

**Key insight from the data:** The TBBO's 1.5–2¢ figure was the book at its *tightest moments* (when someone crossed the spread). The resting book is 2× wider. Any strategy relying on the TBBO spread estimate would significantly underestimate execution cost.

---

## 9. Overall Assessment

### What the code gets right

1. **Protocol discipline**: the extractor, gates, and thresholds are frozen before any Kalshi price is read. The protocol commit timestamp precedes all price reads.
2. **Gap construction**: the executable-side gap correctly absorbs the Kalshi spread, avoiding double-counting.
3. **Friction stack**: correct arithmetic for Kalshi fee, CME spread (per measured half-spread), and CME fees by leg count (post-Amendment 7).
4. **Contract month verification** (Amendment 4): ex-post checks Kalshi's settlement against NYMEX, catching the one mis-centred trade.
5. **bbo-1m migration** (Amendment 8): provides genuinely executable quotes for all legs; the friction is now a measurement, not an estimate.
6. **Ramp residual accounting**: the P&L correctly separates the locked gap from the ramp residual, and the posterior probability of landing in a ramp is computed per bracket.
7. **Denominator transparency**: every date/snapshot has a row explaining why it did or didn't reach the comparison.

### What's missing or imprecise

1. **`estimate_leg_hs` still uses TBBO spreads** (§6.1): estimated friction for unquoted brackets is ~2× too low. Doesn't affect status of any bracket, but misleading for "would_clear_est."
2. **Commission assumption** ($0.85/leg) may be high for some brokers, low for others; verify broker-specifically.
3. **Exit fraction** (0.5) is conservative for deep-tail brackets; immaterial in magnitude.
4. **Stage 18 pooled homogeneity assumption**: one slope across 24 dates; per-date heterogeneity not quantified.
5. **LOO proximity radius** (§6.6): only covers inner condor strikes, not outer.

### Effect on the verdict

The verdict **STRUCTURE, NOT AN EDGE** is robust:
- The signal (b ≈ 0.69, favourite-longshot bias) is real but tiny in magnitude (~1–2¢)
- Friction is 21–25¢ for a four-leg bracket (measured, not estimated)
- The gap:friction ratio is approximately 1:15–25
- No bracket clears the filter under any realistic friction assumption
- The only filtered trade in the first pass was a contract assignment artifact, correctly identified and removed

The code correctly implements the protocol, and the amendments document the data quality issues honestly. The null result is not an artifact of miscoded friction — if anything, the initial pass *understated* friction (TBBO spreads ~2× too low), and the correction made the null even clearer.

---

## 10. Recommendations for Next Pass

Per `BACKTEST_NEXT_PASS.md` and the above analysis:

1. **Fix `estimate_leg_hs`**: replace TBBO chain spreads with bbo-1m snapshot spreads for consistency with the friction measurement. The `friction_est` field will then give an honest picture of "what estimated friction would be if all legs were quoted."

2. **Test cheaper replication strategies**: hedging adjacent brackets as one wider digital (fewer legs, lower spread friction) is the most promising path to closing the gap:friction ratio.

3. **Quantify Stage 18 heterogeneity**: run the per-date regressions and report the cross-date dispersion of `b`. The b ≈ 0.69 pooled estimate could be driven by a few dates; understanding whether it's regime-stable matters for any trading hypothesis.

4. **Check the exit fraction by moneyness**: for a deep-tail bracket where settlement is almost certain outside the condor, exit cost is approximately zero (all legs expire worthless). The per-bracket exit cost could be computed from the posterior at settlement rather than the blanket 0.5 assumption.

5. **Pre-commit the roll rule cross-check**: Amendment 4's contract matching is retrospective. A pre-snapshot check (compare the ladder's centre brackets to the two candidate delivery months' spot levels) would catch misassignments before entry.
