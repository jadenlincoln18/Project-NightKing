# Fix the roughness prior's form, then quote-level exclusion at T-1d

V3 closed the data side (`FINDINGS_REALCHAIN_V3.md`). The real intraday path took
T-4h multimodality 23% → 7% and T-2d's χ² p90 6.3 → 2.3, while leaving T-1d
unchanged — and the report's own reading is that **the residual at T-1d is not
the path.** What is left is the model.

This brief is that work, in two parts. **Part A is the hard one and comes first.**

**Read first:**

1. `FINDINGS_REALCHAIN_V3.md` §8 — the verdicts and the "Reading" section
2. `FINDINGS_SYNTHETIC.md` §9 — the FAIL verdict and the three named routes to PASS
3. `FINDINGS_ACTII_V2.md` — the detector split, and which chains Act II flags alone
4. `synth/act3.py` — the model docstring, which records what was already tried
   and why it was abandoned

---

## Part A — the roughness prior

### A.1 What is wrong, stated precisely

Current prior (`synth/act3.py`): the log-density is a cubic B-spline with m=24
coefficients, and second differences carry a Gaussian penalty with a single
shared scale,

    D2 theta ~ N(0, tau^2 I),   tau ~ lognormal(0.5, 1)

with tau integrated out analytically over a 1-D quadrature grid.

**Two structural properties cause the blind spot, and neither is tau's value.**

**One scale for the whole curve.** The prior cannot express "smooth in the body,
sharp at one point." Raising tau licenses bending *everywhere*, which the
likelihood then rejects because a globally wiggly density stops fitting the
quotes. A locally sharp feature is not in the family at any tau.

**Gaussian tails.** The penalty is quadratic in the bend, so cost grows as the
square. A sharp local feature is not merely disfavoured but astronomically
improbable, at any tau.

This explains the result that otherwise looks inexplicable:
`FINDINGS_SYNTHETIC.md` §9 reports that **three different tau hyperpriors gave
essentially identical answers** (z = -9.3, -9.5, -9.6 on the bimodal trough).
The strength was never the issue. **The form is.**

Consequence, measured: on a planted bimodal truth the posterior recovers both
humps but overstates the trough by z ~ +7.8 with a **0.6c band that contains the
truth 3% of the time**, and chi2/strike stays ~1.2 so **no diagnostic fires**.
Halving the noise makes it *worse* (z +10.9) — the signature of a misspecified
model rather than an underpowered one.

### A.2 What to build

**Locally adaptive smoothing.** Two routes, related (a Student-t is a Gaussian
with a random per-coordinate scale, so route 2 is often how route 1 is
implemented):

1. **Heavy-tailed increments** — Laplace, Student-t with low nu, or horseshoe on
   the second differences. Most bends stay near zero; an occasional large one is
   cheap.
2. **Local scales** — a tau_j per increment with its own hyperprior, so
   smoothness varies along the curve.

**Which one is your judgement.** Evaluate at least two and report both.

### A.3 The engineering constraint — read this before choosing

**Do not reintroduce the sampling problem that was already solved.** The
`act3.py` docstring records the history: half-Cauchy on tau left NUTS at ESS ~ 40,
and both centred and non-centred parameterisations with tau sampled left it at
ESS ~ 20, because the likelihood pins some directions to 1e-4 while leaving
others to the prior (condition number 1e8).

The current design escapes that by **integrating tau out exactly**: one shared
scale means the marginal prior depends only on the scalar S = sum_j e_j u_j^2,
collapsing to a 1-D quadrature with no funnel.

**Local scales break that.** With m-2 separate tau_j you cannot integrate them
out the same way, and the funnel returns once per scale.

There is a second complication. The model works in the **eigenbasis** of
Q'D2'D2 Q, where coordinates are a priori independent. Per-coordinate local
scales live naturally in *coefficient* space, and that rotation mixes them — so
the independence the current implementation relies on may not survive. Handle it
explicitly; do not assume it carries over.

**Scale-mixture representations are the obvious lever** (Laplace = Gaussian x
exponential; Student-t = Gaussian x inverse-gamma), since they may preserve
enough conditional-Gaussian structure to keep some of the analytic integration.
Whether that survives the eigenbasis rotation is for you to work out.

**Sampler health is a gate, not a footnote.** Current real-chain numbers:
bracket Rhat median 1.016-1.021, min ESS 202-246, divergences 0. A prior that
fixes the blind spot but returns ESS 40 has not fixed anything —
`FINDINGS_SYNTHETIC.md` already established that a poorly-mixed chain produces
bands ~13% too narrow, which is a false trading signal rather than a bad plot.
**Report Rhat, ESS and divergences for every candidate. A candidate that
degrades them materially is rejected regardless of its coverage.**

### A.4 How to judge it — the synthetic harness is the arbiter

Every candidate goes through `synth/runner.py` on the same configurations as
`FINDINGS_SYNTHETIC.md`, before and after, on the same planted densities.

**Must not regress** (the current prior's results):

| | current |
|---|---|
| crude-skew bracket coverage @90% | 93% (body 94%, 1-10c tail 95%) |
| bracket RMSE | 0.59c body / 0.20c tail, ~zero bias |
| coverage at the 8-strike gate | 97% |
| Stage 14 unconstrained bias | -0.16c, abs(z) 0.74 |
| all injected faults caught | 98-100% |

**Must improve** — this is the point of the exercise:

| | current | target |
|---|---|---|
| bimodal trough coverage | **3%** | honest, i.e. near nominal |
| bimodal trough z | +7.8 | small, or bands wide enough to contain the truth |
| bimodal overall coverage | 39% | near 90% |
| spiked truth coverage | 48% | near 90% |
| kinked-peak body coverage | 49% | near 90% |

**The standard is honesty, not recovery.** `FINDINGS_SYNTHETIC.md` established
that a single-humped and a bimodal density can produce prices differing by less
than the bid-ask spread — so "cannot distinguish" is a legitimate answer. What
is *not* legitimate is a 0.6c band that is wrong by 8 standard deviations.
**A candidate that widens the bands to admit the truth has succeeded even if the
posterior mean does not move.**

Note the useful contrast already in hand: `F_bimodal_close` (humps 1.6
vol-scales apart) is **already honest** at 90% trough coverage, while
`C_bimodal_full` (2.6 apart) fails at 3%. The prior is honest about ignorance
and dishonest about disagreement. A fix should make the second behave like the
first.

### A.5 Then the real chains

Best candidate goes through `synth/realchain.py` on the same 30 dates, `real`
arm, before/after on every V3 table. Report chi2/strike, Stage 14, Gate 4
firing, Act II firing, band widths, sampler health.

**Two specific chains to watch.** V3 §8 names **2026-05-01** and **2026-03-06**
as the T-4h posteriors that stayed multimodal under the real path, both from
Task 1's "genuinely multimodal" group. Report them individually before and
after. If a locally adaptive prior sharpens rather than flattens them, that is
the project's first real evidence that WTI densities are genuinely bimodal —
worth its own subsection.

Watch for the opposite too: if the new prior turns *many* chains multimodal,
suspect it is fitting quote noise, and say so.

---

## Part B — quote-level exclusion at T-1d (only after Part A)

V3 §8 says this is now **warranted rather than tuning**, because the path has
been ruled out as the cause: at T-1d/60 half the chains still have max residual
> 3 and LOO flags strikes on 80% of them.

Constraints:

- **Exclusion must be by a stated rule, not by inspection.** A LOO standardised
  residual threshold, or a rule keyed to quote age or spread width. Fix the rule
  in advance, apply it uniformly, report how many quotes it removes per chain.
- **Report what gets excluded**, by strike position, quote age, spread width,
  and whether it is a call or a put. If exclusions cluster on stale quotes, the
  fix belongs upstream in the window definition rather than here.
- **A rule that removes more than ~10% of quotes is suspect.** Say so if that
  happens rather than proceeding.
- Run it through both harnesses. If synthetic coverage degrades, the rule is
  removing signal, not noise.

---

## On a learned prior — evaluate, do not assume

The operator raised training a model on historical data to produce an empirical
prior per market and horizon. Worth assessing, with two risks stated:

**Circularity.** Historical densities were extracted *by this pipeline, using
the prior under replacement*. Training on them would encode the assumption being
escaped, undetectably. Any learned prior needs ground truth that is not pipeline
output — and the only such data is 30 realized settlements, nowhere near enough
to learn a density family.

**It deepens the blind spot it aims to fix.** 28 of 30 extracted densities are
unimodal. A prior fitted to them would make bimodality *less* probable than the
current one does — most confident exactly when the market is least normal.

**Where it is clearly sound:** calibrating **tau's hyperprior** (or a local
smoothness profile) from the 90 real extractions already in hand, conditioned on
horizon and ATM vol. That calibrates a scale rather than imposing a shape, and
tau stays sampled so data can override. Currently lognormal(0.5, 1) is a
reasoned guess — the docstring says 0.5 is "the order of the second difference a
lognormal body produces at this knot spacing."

**Sequencing:** the structural fix first, calibration second. A well-calibrated
dial on a mechanism that cannot express sharp features does not help. If Part A
lands and there is signal worth calibrating, say so and propose it as its own
piece of work.

---

## Foundational

- **Still descriptive.** No Kalshi price read, no gap computed, no trade
  evaluated, and that code stays unwritten. The backtest is next, not now.
- **Synthetic first, real chains second.** The synthetic harness is the only
  place with an answer key. A prior that improves real chi2 but degrades
  synthetic coverage is worse, not better.
- **Before/after on the same configurations**, every table.
- **Sampler health gates acceptance** (A.3).
- **Report a candidate that does not work, plainly.** "Horseshoe fixed the
  trough but ESS fell to 60, rejected" is a useful result.
- **Do not touch the data pipeline.** Forward, synchronisation and the real path
  are settled; changing them would confound the comparison.

## Your judgement

- Which heavy-tail or local-scale form, and how many to try
- Whether to preserve any analytic integration, and how
- Whether the eigenbasis rotation survives local scales, or whether to work in
  coefficient space
- Non-centred parameterisation, metric adaptation, target_accept
- Whether m=24 knots and their uniform spacing still suit a locally adaptive
  prior — the V2 docs note uniform knots were a deviation from the writeup's
  "dense where strikes are dense"
- The LOO exclusion rule in Part B

**If something foundational looks wrong, say so rather than working around it.**
The Stage 6 forward decision was overturned exactly that way, and V3 vindicated
it.

## Deliverables

1. Prior implementation(s) in `synth/act3.py` or a sibling, switchable so the
   current prior stays runnable as the baseline
2. `FINDINGS_PRIOR.md` — every candidate, synthetic before/after, sampler
   health, a clear recommendation, and a plain verdict on whether the bimodal
   blind spot is closed
3. `FINDINGS_REALCHAIN_V4.md` — best candidate on the 30 dates, V3 vs V4, with
   2026-05-01 and 2026-03-06 called out individually
4. Part B results, if reached
5. Doc updates where conclusions change `NightKing/PIPELINE_CHOICES.md`,
   `PIPELINE_MAP.md`, `Pipeline.canvas`, or the root writeup — including
   `FINDINGS_SYNTHETIC.md`'s FAIL verdict if it is now superseded

## Long runs

The operator will start this and walk away. Retry with backoff, **pause and
resume rather than exit** on connection loss, checkpoint per completed job (not
at the end), resume as the default, and distinguish "failed" from "not
attempted" in the checkpoint. Timestamped logs including pauses. Nothing here
needs the network — no new data, no spend.

## Environment

macOS, Python 3.9-compatible, numpy/scipy only (no JAX/Stan — `act3.py` is
hand-rolled with analytic gradients; keep it that way unless you make the case
otherwise). `data/` and `data_cme/` read-only. Both test suites stay green.
