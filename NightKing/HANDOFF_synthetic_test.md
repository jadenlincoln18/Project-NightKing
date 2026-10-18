# Synthetic validation of the density extractor — handoff brief

You are building the test that decides whether the extraction pipeline works at
all. Nothing downstream is trustworthy until this passes.

**Read these first, in this order:**

1. `PIPELINE_MAP.md` and `Pipeline.canvas` — which stages are in the build,
   which are validation-only, and how they connect
2. `PIPELINE_CHOICES.md` — why each stage was chosen and what was rejected
3. `nightking-strategy-writeup.md` Parts 2–4 — the derivations. Part 3 in
   particular explains why the naive estimator fails, which is the thing this
   test must confirm the pipeline avoids.

Everything below assumes those. Where this brief and those documents disagree,
raise it rather than silently picking one.

---

## 1. Why this exists

The pipeline extracts a risk-neutral density from an options chain and compares
it to Kalshi's bracket ladder. On real data **there is no answer key.** If the
extractor outputs a density that disagrees with Kalshi, there is no way to tell
whether that is an edge or a bug.

Worse, the bugs in this domain look exactly like edges. A mis-centred density
is smooth, convex, integrates to 1, fits every observed price inside its
bid-ask — and disagrees with every Kalshi bracket **in the same direction**.
That is indistinguishable from a persistent, sign-consistent mispricing. A prior
project (fedarb) spent months on a −8pt "finding" that turned out to be exactly
this class of artifact.

Synthetic data is the only place an answer key exists. **This test is where
"my code is broken" and "the market is interesting" are separable.** After this,
they are not.

### What this gates

Step 1 of the build order in `Decision-Flow.canvas`. Steps 2–6 (real chain,
backtest, live trade) are all downstream. Nothing else blocks it — the open
items (June 15 basis anomaly, session-long depth, MCO expiry) affect sizing and
backtest design, not this.

---

## 2. Foundational — do not deviate without raising it

These are not style preferences. Each one exists because of a specific failure
that has already happened or a specific property the strategy depends on.

### 2.1 Coverage is the primary test, not point recovery

A pipeline that recovers the right density with bands that are **too narrow**
will produce confident false signals forever, and that failure is completely
invisible on real data.

So the headline result is not "the posterior mean was close to the truth." It
is: **across many independent synthetic runs, does a 90% credible interval
contain the true value approximately 90% of the time?**

Report coverage at several nominal levels (50/80/90/95) for:

- the density at a grid of points
- **bracket probabilities** (see 2.4)
- the implied forward

Under-coverage is a failure. Substantial over-coverage is also a finding — it
means the bands are too wide and the trade filter will reject real signals.

### 2.2 Use the real strike geometry and the real noise

Testing on evenly-spaced strikes with uniform tight spreads is testing an
easier problem than the one you have.

- **Strike spacing** must come from the actual CME chain in `data_cme/`. WTI
  weeklies list at $0.25 increments near the money and widen in the wings.
  Part 3 of the writeup shows the estimator's behaviour is driven by spacing,
  so this is not a detail.
- **Noise** must be calibrated to the **observed half-spreads** in the stored
  TBBO data, per strike, including the way spreads widen away from the money.
  A single global noise level would understate the wing problem.
- **Strike count** should span what actually occurs: the gate threshold is 8
  strikes with 3+ per wing; the median observed date has 23 with wings at
  12/11. Test across that range, not just the median.

### 2.3 Run the Stage 14 diagnostic

Before the martingale constraint is enabled, run the sampler **without** it and
check whether the posterior mean lands on the planted forward unaided.

- If yes: Stages 6–13 are internally consistent end to end.
- If no: there is a bug upstream, and enabling the constraint would **mask** it
  while leaving the density subtly wrong elsewhere.

This is a one-time development check, but it is the cheapest end-to-end
validation available and it must happen before the constraint goes in.

### 2.4 Bracket probabilities are the quantity that matters

The strategy never trades a point density. It trades
$\mathbb{Q}(a < F_T < b)$ over Kalshi's bracket edges.

So the decisive accuracy and coverage numbers are on **bracket probabilities
integrated over realistic bracket edges** — $1-wide, spanning the range Kalshi
actually lists. Point-density accuracy is diagnostic; bracket accuracy is the
product.

### 2.5 Test both routes

`PIPELINE_CHOICES.md` puts Act III (Bayesian) on the trading path and Act II
(SVI smile) as an independent cross-check. Validate both. Two independent
implementations agreeing is stronger evidence than either alone, and a
disagreement on synthetic data localizes the bug immediately.

### 2.6 Injected failure modes

The test must demonstrate that known failure modes are **caught**, not just
that the happy path works. At minimum:

- **Mis-specified forward.** Feed the extractor an $F_0$ offset by 5¢, 15¢,
  50¢ from truth. Confirm the mean-equals-forward check fires, and quantify how
  far bracket probabilities shift per cent of forward error. *This is the
  fedarb artifact; we need to know the sensitivity.*
- **Truncated integration grid.** Confirm the normalization check catches mass
  leaking past the grid edges.
- **Convexity violation.** Inject a crossed or stale quote that makes the price
  curve locally concave. Confirm it is detected.
- **Unconverged chain.** Run deliberately too short. Confirm the diagnostics
  flag it, and show what the (wrongly narrow) bands would have looked like.
- **Truth outside the prior's comfort zone.** See 2.7.

### 2.7 The bimodal test — the one I most want to see

The Stage 12 prior penalizes roughness, which encodes "be smooth, roughly
lognormal-ish unless the data insists otherwise." That is a sensible default
and it is also an assumption.

**Plant a bimodal density** — two separated humps, of the kind a market pricing
a binary supply event might actually produce — and ask:

- Does the posterior recover the bimodality, or does it report a confident
  unimodal density?
- **If it fails to recover it, do the error bars widen to admit the
  possibility, or do they stay tight?**

That second question is the important one. A pipeline that quietly imposes
unimodality *and reports tight bands* is the worst possible outcome, because it
would be confidently wrong exactly when the market is doing something
interesting.

Prior work established that a single-humped and a bimodal density can produce
option prices differing by **less than the bid-ask spread** at most strikes. So
the honest result may well be "cannot distinguish" — and that is fine, provided
the bands say so.

### 2.8 Report honestly

If coverage is 70% at the nominal 90% level, say so plainly. Do not tune the
prior until coverage looks good and then report the tuned number — that is
fitting the test. If something needs tuning to achieve coverage, report both the
before and after, and what was changed.

---

## 3. Your judgement — where you likely know better

These are genuinely open. Where you have a better approach than what the
pipeline docs sketch, take it and explain the reasoning in the write-up.

**Sampler and framework.** `PIPELINE_CHOICES.md` says "NUTS preferred." Whether
that means NumPyro, Stan, PyMC, or a hand-rolled implementation is your call.
Gradient availability through the forward map is the constraint; if a
reparameterization makes that easier, do it.

**Spline basis and knots.** The spec says "20–30 coefficients, knots dense where
strikes are dense." B-spline vs natural cubic vs something else, exact knot
count and placement, boundary behaviour — yours. If a different basis behaves
better in the tails, use it.

**Hyperprior form on λ.** Gamma was a suggestion, not a requirement. Whatever
gives sensible behaviour when the data is uninformative.

**Quadrature for the forward map.** This runs inside every likelihood
evaluation, so it matters for speed. Grid extent, resolution, and scheme are
yours — subject to the normalization check passing.

**Number of synthetic runs.** Enough for a meaningful coverage estimate.
Several hundred is the right order; you judge the tradeoff against runtime.

**Which densities to plant.** A crude-like skewed density with a fat upper tail
and the bimodal case are required. Beyond that, plant whatever you think
stresses the pipeline — near-lognormal, heavy both tails, sharp peak, whatever
exposes weakness.

**Test harness structure, parallelism, caching, reporting format.** Entirely
yours.

**If you think a foundational item is wrong**, say so rather than working
around it. Several decisions in `PIPELINE_CHOICES.md` were changed by exactly
this kind of pushback.

---

## 4. Suggested shape

Not prescriptive — adapt if you see better.

```
plant density f_true (several shapes)
  ↓
compute exact prices  C(K) = e^-rT ∫(s-K) f_true(s) ds
  on the REAL strike grid from data_cme/
  ↓
add noise calibrated to observed per-strike half-spreads
  ↓
run pipeline: Stage 6 → 8 → 7 → [Act II | Act III]
  ↓
compare recovered vs planted:
  - forward, discount factor
  - density pointwise
  - BRACKET PROBABILITIES over realistic edges
  - band widths
  ↓
repeat N times with fresh noise → coverage at 50/80/90/95
  ↓
repeat across: strike counts, noise levels, planted shapes
```

Worth measuring while you are in here, since it is impossible on real data:

- **How does coverage degrade as strikes thin toward the 8-strike gate?** This
  may justify raising or lowering that threshold.
- **How does bracket-probability error scale with noise?** Tells you what
  spread environment makes the strategy unusable.
- **Where in the distribution is accuracy worst?** Expect the wings. Quantify
  it — the strategy wants to trade the 5–20¢ tails, and if extraction is
  unreliable there the whole thesis needs revisiting.

---

## 5. Deliverables

1. **`synth/`** — the generator, the harness, the runner
2. **`test_synthetic.py`** — assertions that fail loudly on regression, runnable
   in CI without a long sampler run (use a fast fallback sampler if needed)
3. **`FINDINGS_SYNTHETIC.md`** — the verdict, containing at minimum:
   - coverage tables at 50/80/90/95 for density, brackets, forward
   - bias and RMSE by region (wings vs body)
   - the Stage 14 diagnostic result (mean lands on $F_0$ unaided: yes/no)
   - Act II vs Act III agreement
   - each injected failure mode: caught / not caught
   - **the bimodal result, stated plainly**
   - sensitivity of bracket probabilities to forward error, in ¢ per ¢
   - a clear **PASS / PASS WITH CAVEATS / FAIL**
4. **Plots** — planted vs recovered with bands, coverage curves, error by
   region. These will go in the strategy document.

---

## 6. Environment

macOS. Python 3.9-compatible (3.12 conda laptop, 3.9 system Python on a Mac
Mini). Existing deps: pandas, pyarrow, databento, python-dotenv. Add what you
need, pin it in `requirements.txt`.

Data in `data/` (Kalshi, 58.9M candles) and `data_cme/` (CME TBBO, definitions,
statistics). Read-only for this task.

No network required. No spend.

---

## 7. Out of scope

The real-chain run (step 2), the backtest (step 3), the June 15 basis anomaly,
the MCO expiry problem, and the hedge ratio — that last one is operator-owned.
