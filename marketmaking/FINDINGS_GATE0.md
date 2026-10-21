# FINDINGS — Gate 0 (PROTOCOL §1B "Gate 0", specified in §8)

**Date:** 2026-10-20
**Branch:** `claude/gracious-edison-s2s7t5`
**Pre-registration:** `PROTOCOL.md` §8, committed **`3dcd015`** and pushed
**before a single synthetic ladder existed**. §1B is not modified by this run.

> **The question.** `BRIEF.md` §2 claims the fit beats a bracket's own quote by
> pooling **~25 noisy observations of one distribution**. The §1A universe
> supplies **6**. Gate 0 hands the fitter a truth it already knows the answer to
> and asks whether, at six brackets, it still wins.

---

## 1. What was measured on the real ladders first

Gate 0's synthetic ladders are not invented shapes. Their geometry and their
quote noise are measured from the staged store, and nothing else about the real
data is read — **no settlement outcome enters anything that is scored here.**
§1A explicitly permits microstructure as a design input.

### 1.1 Geometry — all 48 staged temperature series, 15,523 classifiable events

| quantity | measured | source |
|---|---|---|
| Brackets per event | **5.989 mean**; exactly 6 on **15,355 / 15,523 = 98.9%** | `fit/geometry.py` |
| Interior edge spacing | **2.0 °F** on 61,771 of 61,927 gaps (**99.7%**) | " |
| Interior span | **8.0 °F** median | " |
| Ladder kind | `range` on 15,712 events; `cumul` on **zero** | " |

A real ladder is literally `≤29 | 30–31 | 32–33 | 34–35 | 36–37 | ≥38`: four
2 °F interior brackets and two open wings. Measured strike conventions on this
universe: `less` carries an **exclusive** cap, `greater` an **exclusive** floor,
`between` an inclusive `[floor, cap]`; settlement is on integer °F, so the
continuous bracket boundaries fall on the half degree. The synthetic ladders use
exactly this: edges at `{−4, −2, 0, +2, +4}` °F, six brackets, open wings.

### 1.2 Quote noise — two independent measurements that agree

**(a) From the ladder's own arithmetic.** A `range` ladder partitions the
outcome space, so coherent mids sum to 1. With `m_i = p_i + e_i` and independent
`e_i`, `sd(Σm − 1) = σ_q √n_br`. On **6,680 fully-tight ladder-minutes** across
12 series (every bracket two-sided, every spread < 20c):

```
sd(Σ mid − 1) = 0.0445     n_br = 6.0     =>   σ_q = 0.0182   (1.8 cents)
mean(Σ mid − 1) = +0.0356  — the overround, a systematic quantity, not noise
```

This measures the **idiosyncratic** component only; common-mode error cancels in
the sum. That is the right component: a common-mode error is one the fit absorbs
rather than corrects, so counting it would credit the fit with knowledge it does
not have.

**(b) From the spread.** On 45,338 two-sided executable bracket-minutes,
**26.3% are degenerate 1/99-type books** (spread ≥ 20c; 8.1% at ≥ 90c) — quoted
in the data, but not prices. On the remaining 73.7% the median spread by mid
level (cents) is:

| mid (c) | 0–5 | 5–15 | 15–35 | 35–65 | 65–85 | 85–95 | 95–100 |
|---|---|---|---|---|---|---|---|
| median spread | 2 | 5 | 5 | 4 | 6 | 9 | 1 |

Median half-spread **≈ 2c**, independently agreeing with σ_q = 1.8c. The two
numbers come from unrelated features of the data — one from cross-sectional
incoherence, one from the touch — and they land in the same place, so the noise
scale Gate 0 uses is not a guess.

### 1.3 The two conservative choices, both made before any result

1. **Degenerate books excluded from the noise model.** Including 1/99 books
   would hand the quote comparator a 26% subset of mid-50 non-prices and let the
   fit win on arithmetic rather than on knowledge.
2. **No overround in the primary.** Real mids sum to 1.0356; a fitted density
   normalises to 1 by construction and would cancel that bias for free. The
   primary run sets the overround to zero so the quote is **unbiased**. The
   measured +3.56% is run as a declared sensitivity.

Both choices make the gate **harder** to pass. That was the point of fixing them
in advance.

---

## 2. What was built

New code under `marketmaking/fit/`. **`wti_arb/synth/`, `ladder/` and `waves/`
are not modified, not patched and not imported for inference.** `ladder.store`
is read read-only for the geometry and spread measurements above.

| module | what it is |
|---|---|
| `fit/geometry.py` | the §1.1–§1.2 measurements |
| `fit/density.py` | the fitter: **linear °F grid**, **indicator payoff**, spline log-density, posterior band90 |
| `fit/nuts.py` | the sampler, **copied verbatim** from `act3.py` (Whitened, NUTS, split-Rhat, ESS) |
| `fit/synth.py` | truth families, realised settlement, measured quote noise |
| `fit/gate0.py` | the driver, the disagreement sets, the Brier scoring, the verdict |

### 2.1 The one structural change, and why it was unavoidable

The WTI extractor's payoff matrix is `G[i,k] = (s_k − K_i)⁺` on a grid
`s = F₀·exp(x)`, `x ∈ ±extent_sd·σ√T`. A daily temperature has **no forward
`F₀`**, **no implied volatility**, and a support that reaches 0 °F and below,
where `log(s/F₀)` does not exist. And a Kalshi bracket is **not a vanilla**: it
is a digital on an interval, already a probability.

```
WTI :  Chat_i = Σ_k D·(s_k − K_i)⁺ · p_k          s linear in log-moneyness
Gate 0: Chat_i = Σ_k 1{s_k ∈ bracket_i} · p_k      s linear in degrees Fahrenheit
```

Because `p` is normalised by construction, `G@p` **is** the model's predicted
bracket probability, and the columns of `G` sum to 1. Cells straddling an edge
are split in proportion to the overlap, so a boundary between grid points does
not quantise the likelihood.

Everything else is the extractor's, reproduced not retuned: cubic B-spline
log-density with **m = 24** coefficients, sum-zero gauge, second-difference
P-spline prior whose smoothing scale `τ` is integrated out by quadrature,
`N(0, 30²)` on the exponential tilt, Gaussian likelihood with **sd = the
half-spread**, dense Gauss-Newton metric at the MAP, NUTS in whitened
coordinates, and **band90 = the posterior 5th/95th percentile per bracket,
asymmetric as drawn**. No martingale constraint, because there is no forward to
constrain to.

**m = 24 was deliberately not reduced.** Twenty-four coefficients against six
prices is exactly the prior-dominated regime Gate 0 exists to measure. Tuning it
down to make the fit look better is the move the pre-registration forbids.

---

---

# 3. The real gate — the parametric fitter (PROTOCOL §9)

**Pre-registration:** `PROTOCOL.md` §9, committed **`3ecbc62`** and pushed
**before any skew-normal fit existed**. §9.0 states the timeline without
flattery: the operator's parametric ruling pre-dated every Gate 0 result, the
§8 run did not apply it, and a spline **smoke** result (§2's `PASS: false` on
n = 15) **had been seen** before §9 was written. §9's answer to that was to
reproduce §8.7's bar verbatim, add a CI requirement to it, and add two more
bars — tightening only.

## 3.0 VERDICT: **FAIL** — bars 1 and 2 fail, bar 3 passes

| bar | required | achieved | |
|---|---|---|---|
| **1** | `Brier(fit) < Brier(quote)` on the PRIMARY disagreement set, **and** clustered 95% CI excludes zero | **0.067899 vs 0.067657** (fit worse by 0.000241), CI **[−0.00130, +0.00080]** spans zero | **FAIL** |
| **2** | 90% band contains the truth on 85–95% of trusted observations | **81.45%** — too narrow | **FAIL** |
| **3** | GoF fires on ≥ 60% of bimodal truths | **71.0%**, with a **0.17%** false-fire rate on the well-specified families | **PASS** |

**Per §9.13 this stops here. Test A is not run.** It was not licensed by a pass
and is certainly not licensed by this.

**The disagreement set is not underpowered.** `n = 1378` against §8.7's
threshold of 100 — the §8 smoke's `n = 15` was the thing that made its number
meaningless, and that objection is now closed. The gate failed with power.

## 3.1 What was run

1,200 ladders (300 each of unimodal **U**, skewed **K**, bimodal **B**, and the
§9.9-added mix **M**), 7,200 bracket observations, §8.2 geometry, §8.4 noise,
overround zero, `rng(20261020)`. The m = 24 spline was run as the §9.8
comparison arm on the declared paired subset of 100 ladders per family.
Results are per-family checkpointed in `reports/gate0_parametric/`.

### Inference: Laplace was tested and **rejected**, by its own pre-stated rule

§9.6 fixed the licence condition before running it. On the declared 60-ladder
subsample:

| comparison | mean abs Δ mean | mean abs Δ band endpoint | max abs Δ band |
|---|---|---|---|
| **Laplace vs quadrature** | **0.0173** (tol 0.005) | **0.0810** (tol 0.010) | 0.855 |
| MCMC vs quadrature | 0.0019 | 0.0024 | 0.043 |
| quadrature, 81 vs 121 nodes/axis | 0.0032 | 0.0040 | 0.067 |

**Laplace misses both tolerances by an order of magnitude** and is not used.
The posterior in `α` is far heavier-tailed than any Gaussian at the mode — the
skew-normal's shape parameter is weakly identified, which is exactly the
pathology a 3-parameter model was supposed to avoid and does not. §9.6's
pre-registered fallback applies and **the primary run uses the quadrature
posterior**, independently corroborated by an adaptive random-walk Metropolis
to 0.0024 on band endpoints. Two notes against the reference itself, both
reported rather than buried: §9.6's stated grid (±6 Laplace sd) failed its own
boundary-mass criterion, so the grid is sinh-stretched and adaptively widened
until boundary mass < 1e−4 — reached on 57 of 60 ladders, with 3 residual at up
to 3.3e−2 where the posterior is effectively prior-bounded; and MCMC's own
diagnostics were mediocre (worst split-R̂ 1.51), which is why it is the check
and not the primary.

## 3.2 Bar 1 — the fit does not beat the quote, and the loss is not an artefact

| set | n | Brier(fit) | Brier(quote) | diff | clustered 95% CI |
|---|---|---|---|---|---|
| **PRIMARY (trusted)** | **1378** | **0.067899** | **0.067657** | **−0.000241** | **[−0.001304, +0.000799]** |
| union (trusted + untrustworthy) | 2278 | 0.087994 | 0.085902 | −0.002092 | — |
| secondary, Reading B (never decides) | 662 | 0.029110 | 0.029297 | +0.000187 | — |
| all observations | 7200 | 0.124102 | 0.123502 | −0.000601 | — |

The result is a **dead heat landing on the wrong side**. The fit is not beaten
badly; it is not distinguishable from the quote at all, and the strict
inequality §8.7 demands is not met.

**§9.7's required disclosure: the exclusion did not do the work.** Bar 1 fails
on the primary set *and* on the union of trusted and untrustworthy
observations. The 900 excluded observations were not where the loss was hiding;
removing them improved the fit's score and it still lost.

**Reading B is reported and does not decide (§9.10).** On the executable set the
fit is ahead by +0.000187. **This does not rescue anything and is not a pass**
— no escalation clause exists, and §9.10 says so in advance precisely so that
this number could not be used the way it is tempting to use it.

### Per family, on the primary set — where the fit wins and where it does not

| family | n | Brier(fit) | Brier(quote) | diff | |
|---|---|---|---|---|---|
| **U unimodal** | 211 | 0.04519 | 0.04671 | **+0.00152** | fit wins |
| **K skewed** | 555 | 0.02334 | 0.02404 | **+0.00070** | fit wins |
| **B bimodal** | 193 | 0.11911 | 0.11635 | −0.00276 | fit loses |
| **M mix** | 419 | 0.11476 | 0.11355 | −0.00121 | fit loses |

§8.7 is explicit that this cannot be re-cut into a pass: *"A pass on U alone,
with K or B losing, is a fail."* It is reported because it is the whole
explanation. **The fit wins on exactly the two families it is correctly
specified for and loses on the two it is not.**

## 3.3 Bar 2 — the bands are too narrow, and misspecification is why

Coverage of the **true** bracket probability by the 90% band, trusted fits:
**81.45%** against a required 85–95%. Including untrustworthy fits it is
72.61%. The failure direction is **overconfident**, and it is not uniform:

| family | coverage (trusted) | |
|---|---|---|
| **U unimodal** | **0.964** | above the band's upper edge — correctly specified, and the bands are if anything *conservative* |
| **K skewed** | 0.802 | correctly specified, yet already under |
| **M mix** | 0.745 | misspecified, undetected |
| **B bimodal** | 0.567 | misspecified; the 29% the GoF misses are concentrated here |

Read this with 3.2's family table and the mechanism is unambiguous. Where the
truth is in the family, the 90% interval is honest — too wide, even. Where it
is not, the posterior concentrates on the wrong shape and reports a tight
interval around it. **Bar 2 does not fail because the posterior is computed
badly; it fails because a 3-parameter posterior cannot express "this is not my
shape" as width.** That is precisely what bar 2 was written to catch, and it is
the reason bar 2 was written to fail in both directions.

## 3.4 Bar 3 — PASS. The model does know when it is wrong, usually

| family | GoF fire rate | ladders |
|---|---|---|
| **B bimodal** | **0.710** (bar: ≥ 0.60) | 300 |
| M mix | 0.067 | 300 |
| K skewed | 0.003 | 300 |
| U unimodal | 0.000 | 300 |

**234 of 1,200 ladders (19.5%) were marked UNTRUSTWORTHY, excluding 900 bracket
observations from the primary set. That is a reported number, not a silent
drop**, and the §9.7 union check above shows it did not manufacture the
verdict.

The specificity is the better half of this result: a **0.17%** false-fire rate
on the 600 correctly-specified ladders, against the ~1% the χ²₀.₉₉ threshold
budgets for. The check is not trigger-happy.

But bar 3 passing is also where the failure lives. The GoF catches the
*obvious* misspecification — two clean peaks — and misses the subtle kind: on
family M it fires on **6.7%** while M's bands cover only 74.5% and its fit
*loses* to the quote. Undetected misspecification, quantified on the trusted
subset where the fitter claims to be reliable:

| family | trusted obs | Brier(fit vs TRUTH) | Brier(quote vs TRUTH) | ratio |
|---|---|---|---|---|
| U | 1800 | 0.000162 | 0.000318 | **0.51** |
| K | 1794 | 0.000196 | 0.000405 | **0.48** |
| M | 1680 | 0.000465 | 0.000338 | 1.38 |
| B | 522 | 0.001052 | 0.000366 | 2.88 |

On the shapes it fits, the fit **halves the error against the truth** — real
pooling, from six prices. On the shapes it does not fit, *and still certifies
as trustworthy*, it is 1.4× to 2.9× worse than simply reading the quote.

## 3.5 The §9.8 comparison arm, and the question underneath Gate 0

Both arms, **identical 400 ladders**, identical §9.5 noise scale, paired by
generation index:

| | parametric (3 params) | spline (m = 24) |
|---|---|---|
| disagreement rate | 20.8% | 10.4% |
| primary set n | 500 | 250 |
| Brier(fit) − Brier(quote) | **+0.000105** | **−0.000022** |
| clustered 95% CI | [−0.00172, +0.00194] | [−0.00238, +0.00211] |
| band coverage of truth | 0.730 | 0.823 |
| mean band width | 0.0500 | 0.0605 |
| GoF fires | 74 / 400 ladders | **0 / 400** |
| Brier(fit vs TRUTH), all | 0.000979 | 0.000341 |

Brier against the **known truth**, by family, paired — the low-variance
diagnostic, and the one that actually separates the arms:

| family | parametric | spline | quote |
|---|---|---|---|
| U unimodal | **0.000180** | 0.000191 | 0.000324 |
| K skewed | **0.000188** | 0.000376 | 0.000423 |
| B bimodal | 0.003050 | 0.000516 | **0.000351** |
| M mix | 0.000499 | **0.000281** | 0.000349 |

### Was six brackets the binding constraint, or the model's flexibility?

**Six brackets.** The parametric model was built to test the §8.1 suspicion that
24 coefficients against 6 prices is prior-dominated. Cutting 24 to 3 did
measurably what it was supposed to: on in-family shapes the parametric fit
recovers the truth **2× better than the quote** and better than the spline
(K: 0.000188 vs 0.000376 — the spline halves its own error away). Flexibility
*was* costing accuracy. **And it changes the verdict not at all** — both arms'
CIs straddle zero, at margins of 1e−4 against Brier scores of 3e−2 to 7e−2.

The reason is visible in one row of the table above: **the spline's GoF never
fires. Not once in 400 ladders** — median X² = 1.75, maximum 10.10, under a
threshold of 11.3449 the parametric arm exceeds on 19.5% of ladders and clears
128 on its worst. With 24 coefficients the model reproduces any six numbers
almost exactly, so its residuals carry no information about whether it is right,
and it cannot be caught being wrong. With 3 coefficients the residuals are
informative — that is bar 3's pass — but the model is then too rigid to be
right off-family, and six prices are not enough to tell you which case you are
in: the check catches 71% of clean bimodality and 7% of a mild mixture.

So the dilemma is not a tuning problem to be solved between m = 3 and m = 24.
**Six brackets contain enough information to estimate a shape or to verify a
shape, but not both.** A flexible model spends all six degrees of freedom
matching the quotes and learns nothing beyond them; a rigid model genuinely
pools and beats the quote by 2× — but only when its assumption happens to hold,
and the same six numbers cannot reliably tell you whether it does. `BRIEF.md`
§2's claim rests on **~25** observations of one distribution. At six, on this
evidence, the claim does not hold.

## 3.6 What is NOT concluded

- **Not** that the fit has no skill. On correctly specified shapes it has
  measurable skill, twice the quote's accuracy against the truth, at six
  brackets. The gate is about whether that survives contact with shapes chosen
  by the weather rather than by the modeller.
- **Not** that the spline is better. Its apparent advantage on pooled
  truth-error is bought by refusing to commit, and its GoF-never-fires property
  means it would be the more dangerous of the two in production.
- **Not** a licence to retune and re-score. §9.13 forbids it, and the margin is
  so far inside the noise that any retune that produced a pass would be fitting
  the gate rather than the market.

The decision this hands back to the protocol author is §8.7's stated one:
**whether to move the §1A universe toward ladders with more than six brackets.**
That is now a decision with a number attached, taken with power — n = 1378, not
n = 15.
