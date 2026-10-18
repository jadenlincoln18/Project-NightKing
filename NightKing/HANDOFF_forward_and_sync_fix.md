# Fix the forward and quote synchronicity, then re-run the real-chain study

Step 2 ran (`FINDINGS_REALCHAIN.md`, 240 jobs, 0 errors). It found a blocker, and
the blocker is **not** the one the synthetic study predicted.

**Read first, in this order:**

1. `FINDINGS_REALCHAIN.md` — the run you are responding to
2. `FINDINGS_SYNTHETIC.md` §8 (forward sensitivity) and §9 (the verdict)
3. `NightKing/PIPELINE_CHOICES.md` — the Stage 6 section, which this work
   deliberately overturns; read the original argument before changing it

---

## 1. What the real-chain run found

Three problems, ranked by how much they bite.

### 1.1 The parity forward is off by 20–38¢ (the blocker)

`FINDINGS_REALCHAIN.md` §7: parity forward vs the NYMEX settlement of the
option's own underlying contract.

| snapshot | usable strike pairs (median) | RMSE vs NYMEX | within 10¢ |
|---|---|---|---|
| T-2d, 60min | 2 | 23.3¢ | 64% |
| T-1d, 60min | 6 | 37.7¢ | 32% |
| T-0, 60min | 6 | 37.6¢ | 25% |

Synthetic RMSE was **1.17¢**. Real is 20–30× worse.

Corroborating symptom: the same regression estimates a discount factor, which
should be ≈1.000 at T ≤ 2 days. It returned **0.947 at expiry** — the run
already hard-codes `D = e^{-0.04T}` as a workaround. A slope that wrong means
the line is fitted through noise.

**Why this is the blocker, not a nuisance.** `FINDINGS_SYNTHETIC.md` §8
measured bracket sensitivity to forward error: mean 0.036 ¢/¢, up to **0.18
¢/¢** on the steepest bracket. So 30¢ of forward error moves that bracket 5.4¢
— larger than its 90% band (~2¢) and larger than the whole ~5¢ friction budget.

And the failure is the dangerous kind: a mis-centred density slides sideways, so
**every bracket shifts the same direction**. That is indistinguishable from a
persistent market mispricing. It is the fedarb artifact.

### 1.2 Quotes are smeared across the window

Gate 0 defines the chain from a 60-minute quote window. WTI moves $1+ in an hour
in this regime, so a "snapshot" is assembled from quotes describing materially
different underlying levels.

Same dates, same code, only the window changes:

| window | χ²/strike (median) | runs >50% multimodal draws | detector fires |
|---|---|---|---|
| 60 min | 8.1 | 43% | 68% |
| 10 min | **2.0** | **0%** | 44% |

Multimodality that disappears when you tighten the window is not in the market.

But the tighter window is not a free fix: **T-1d/10min clears Gate 0 on only 9
of 30 dates, and T-2d/10min on 0 of 30.** Hence §2.2.

### 1.3 Act III cannot fit the quotes

χ²/strike is 4–8 on real chains against **1.1** synthetic. Act III's prices miss
the market's by several half-spreads. Only 7–44% of chains reach χ² < 2.

This is Act III's own diagnostic — no Act II involved — and it is the alarm that
matters most. But it drops to 2.0 at the tight window, which points at §1.1 and
§1.2 as cause rather than the model itself.

Also failing on real data: the Stage 14 unconstrained mean-equals-forward check
passes only **36–56%** of the time (|z| median 2.5–3.9). On synthetic it was
|z| 0.74. Consistent with a bad forward.

---

## 2. What to build

### 2.1 Forward from the futures, parity demoted to a check

**This deliberately overturns `PIPELINE_CHOICES.md` §"Stage 6".** That section
argues the forward must come from the chain, because an externally sourced
forward that disagrees produces a silent mis-centring artifact. The argument is
sound but assumed the parity regression was *reliable*. On real chains it is
not.

**The resolution: keep the protection, change the source.**

Put-call parity is an arbitrage identity, not a model — the synthetic long
call / short put at strike K pays exactly $F_T − K$ in every state. So the
parity forward and the futures price are **two measurements of the same
number**, not two competing numbers. Take the less noisy one.

- **Backtest:** the NYMEX settlement of the option's own underlying, from the
  `CL.FUT statistics` pull already in `data_cme/`. Published at 14:30 ET, which
  is the same instant as the T-1d and T-2d snapshots. `FINDINGS_REALCHAIN.md`
  §7 verified `underlying = Kalshi contract` on **100%** of dates.
- **Live (note for later, do not build now):** the CL futures quote at decision
  time. Settlements are published after the fact and do not exist at 14:25.

**Parity still runs, as a gate.** Compute it, compare to the futures forward,
flag when they disagree by more than the option spreads justify. A large
disagreement means the option quotes are stale relative to the futures — exactly
when not to trade. Report the distribution of that disagreement.

**One more reason parity is worse than merely noisy here:** CME's standard WTI
weeklies are American-style, so parity is an inequality rather than an equality,
and the distortion is *systematically signed*. Stage 8's OTM-only selection
keeps it small, but it is a bias, not scatter.

### 2.2 Delta-adjust the chain to a common underlying level

The 10-minute window is clean but drops 70% of dates. The 60-minute window keeps
the dates but smears the quotes. Recover both.

For each option quote, you know its timestamp. You have CL futures prices
timestamped through the session in `data_cme/`. So: shift each quote to a common
reference underlying level before fitting, using the futures move between that
quote's timestamp and the reference instant.

Judgement on the method is yours — adjusting moneyness, adjusting the strike, or
adjusting the price by the option's delta are all defensible and they differ in
second-order ways. Pick one, justify it, and **report the before/after** on the
same dates so the effect is visible.

**Success criterion, stated in advance:** 60-minute windows with adjustment
should approach 10-minute χ² (≈2.0) while retaining 60-minute date coverage
(28–30 of 30). If χ² does not improve, the adjustment is not the fix and that is
worth knowing.

### 2.3 Replace the Act II/Act III detector

The current Gate 4 compares Act II to Act III. **Act II differentiates (second
difference of the fitted call curve); Act III integrates.** On a chain whose
quotes are mutually inconsistent, Act II amplifies that inconsistency while Act
III averages it — so disagreement grows faster than either method's true error.
The detector measures Act II's fragility as much as Act III's trouble. That is
why it fires 64–77% of the time on real chains.

Act II also went butterfly-negative in **41%** of synthetic fits, so the
comparison arm is itself partly broken.

**Build split-half consistency instead.** Fit Act III to odd-indexed strikes,
fit again to even-indexed strikes, compare the two posteriors over the bracket
edges.

Why it is better:

- Same machinery both sides, so disagreement indicates inconsistency **in the
  data**, not in one method's numerics
- Both halves carry posteriors, so "do they disagree more than their own
  uncertainty allows" is a well-posed question, not a hand-picked threshold
- It is directly diagnostic of the actual problem: asynchronous quotes are
  precisely what splits a chain against itself

Costs one extra pair of fits per date. Acceptable.

**Also add leave-one-out predictive**, which needs no second method: drop a
strike, refit, predict the dropped price, compare to the market quote,
standardised by its half-spread. Standard Bayesian model check and it localises
which strike is the problem.

**Keep Act II** — as one signal among several, reported but not gating. Two
independent implementations agreeing is still evidence; it is just not a gate.

### 2.4 Re-run the study

Same 30 dates, same snapshots, same sampler settings as
`FINDINGS_REALCHAIN.md`. Only the forward, the delta adjustment, and the
detector change. **Before/after on every table** so the effect of each change is
attributable.

---

## 3. Foundational — do not deviate without raising it

- **Still descriptive.** No Kalshi price is read, no gap is computed, no trade is
  evaluated, and none of that code gets written. The pipeline is not yet
  trustworthy enough to inform a decision.
- **χ²/strike is the headline metric.** It is Act III's own goodness-of-fit
  against the market's own spreads, independent of any cross-check. Report it
  first.
- **Report before/after on the same dates**, not just after. A number with no
  baseline cannot be attributed to a change.
- **Do not tune the prior in this pass.** Tuning against chains with a known
  data-quality problem teaches the model to absorb artifacts, and the diagnostic
  that would reveal it is the one being tuned away. The prior's form is the next
  question, not this one.
- **State it plainly if a fix does not work.** "χ² went 8.1 → 7.6, the
  adjustment is not the fix" is a more useful result than a tuned number.

## 4. Your judgement

- The delta-adjustment method (moneyness vs strike vs price; which delta;
  reference instant)
- The split-half construction (odd/even, random halves, repeated splits) and the
  disagreement statistic
- The parity-vs-futures disagreement threshold, and whether it should gate or
  merely report
- Whether to fix `D` analytically from the risk-free rate now that the forward
  no longer depends on the regression slope
- Whether T-2d is worth keeping at all (14 of 30 extracted, median 2 pairs)
- Sampler settings if real posteriors are worse-conditioned than synthetic
  (real: bracket R̂ median 1.038, min ESS 135, vs synthetic 1.014 / 303)

**If you think something foundational is wrong, say so rather than working
around it.** §2.1 exists because that is how the Stage 6 decision got revisited.

## 5. Deliverables

1. Updated `synth/realchain.py` (or successor) with the three changes
2. `synth/detector.py` replaced or supplemented by split-half + LOO
3. `FINDINGS_REALCHAIN_V2.md` — before/after on every table from V1, with a
   clear verdict on each of the three fixes: worked / partially / did not
4. Corrections to `NightKing/PIPELINE_CHOICES.md` and
   `nightking-strategy-writeup.md`:
   - **Stage 6** — forward now sourced from futures, parity demoted to a check.
     Preserve the original mis-centring argument and explain why the source
     changed; do not delete the reasoning.
   - **Stage 9/10 SVI bound** — both documents state $b(1+|\rho|) \le 4/\sqrt T$
     and claim it excludes butterfly arbitrage. Lee's moment bound is
     $b(1+|\rho|) \le 2$, and per Gatheral–Jacquier the slope bound alone does
     not exclude butterfly arbitrage; $g(k)$ must be verified. This was flagged
     in `FINDINGS_SYNTHETIC.md` §10 and is still uncorrected in the docs.
   - **Gate 4** in `PIPELINE_MAP.md` and `Pipeline.canvas` if the detector
     changes.

## 6. Context worth having

**The 2–6 strike pairs is partly a data artifact, not a market fact.** The
backtest uses Databento `tbbo`, which samples in *trade* space — a strike gets a
recorded quote only when it trades. Live, the full book shows every listed
strike's two-sided market continuously. So parity would have materially more to
work with in production than it does here. The backtest is harder than reality
on this specific axis. Worth stating in the findings so nobody later concludes
parity is hopeless.

**T-0 is unusable and that is fine.** 75–82% of quotes are 1¢ bids on settlement
day; zero extractions succeeded. The trade is decided before then.

## 7. Environment

macOS, Python 3.9-compatible. Data in `data/` (Kalshi) and `data_cme/` (CME),
read-only. No network, no spend. `python3 -m unittest test_synthetic` must stay
green.
