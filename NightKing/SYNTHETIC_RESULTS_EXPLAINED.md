---
tags: [nightking, synthetic, validation, findings]
---

# Did the extractor actually work? — the synthetic test, explained

**Short answer: mostly yes, with one specific and serious blind spot.**

The pipeline reads market prices correctly, reports honest uncertainty, and
catches every kind of bug we deliberately fed it — *as long as the true
probability distribution is a smooth single hump.* When the truth is a shape
the model doesn't expect, the pipeline gets it badly wrong **and says it is
confident.** Nothing in the output warns you.

That is why the verdict is **FAIL**, and why FAIL here is good news rather than
bad.

Companion to [[PIPELINE_MAP]] and [[PIPELINE_CHOICES]]. Full numbers in
`FINDINGS_SYNTHETIC.md`; plots in `synth/plots/`.

---

## Part 1 — What we were testing and why

### The problem with real data

The strategy works like this: read a bunch of oil option prices, work backwards
to the probability distribution hiding inside them, then compare that
distribution to what Kalshi's prediction market is charging. Where they
disagree by enough, there may be a trade.

The trouble is that **on real data there is no answer key.** If the pipeline
says a Kalshi bracket is worth 8¢ and Kalshi is charging 13¢, you have two
possible explanations and no way to tell them apart:

1. You found a real mispricing.
2. Your code has a bug.

Worse, the bugs in this particular field look *exactly* like opportunities. A
density that's been accidentally shifted sideways by a few cents will be
smooth, will obey every mathematical law, will fit every observed price — and
will disagree with **every single Kalshi bracket in the same direction.** That
reads as a persistent, consistent edge. A previous project spent months on
exactly such a "finding" before discovering it was an artifact.

### The fix: make up the answer first

Plant a probability distribution. You invent it, so you know it exactly.
Compute what option prices that distribution would produce. Add realistic
noise. Feed those fake prices to the pipeline. Compare what comes out to what
you planted.

**This is the only stage of the whole project where an answer key exists.**
After this, you're flying blind again.

### What "realistic" meant here

The test used real market geometry, not convenient approximations:

- **Strike grids** taken from actual CME chains in `data_cme/` — for every
  expiry that matched a Kalshi settlement date, the strikes that actually had a
  live quote in the hour before settlement. Median 31 strikes.
- **Noise** fitted to the actual bid-ask spreads on those quotes, including the
  way spreads widen on cheap options, tick rounding to the penny, and the 1¢
  bid floor the tape really shows.
- **Volatility** from the real at-the-money implied vol of each snapshot.

So the pipeline was solving the problem it will actually face, not an easier
one.

**Scale of the study:** ~1,840 independent runs across 30 configurations, each
run taking ~75 seconds. Roughly 38 hours of compute.

---

## Part 2 — The main result, in one idea

### What a "90% band" is

The pipeline doesn't output a single number. For each Kalshi bracket it outputs
a **range**: *"this bracket is worth somewhere between 11¢ and 14¢, and I'm 90%
confident of that."*

That range is the **90% band**. It is the pipeline's own statement about how
sure it is.

### The test that matters most

Because we planted the truth, we can check the band. For every bracket in every
run, ask one yes/no question: **did the band actually contain the true value?**

If the pipeline's confidence is honest, the answer should be yes about 90% of
the time. Not always — that would mean the bands are uselessly wide. Not 50% —
that would mean the pipeline is lying about how sure it is.

**This is called coverage**, and it is the single most important number in the
study.

### Why it matters more than accuracy

A pipeline that is slightly wrong but *knows* it is slightly wrong is safe —
the wide band means the trade filter rejects marginal signals.

A pipeline that is slightly wrong and *claims certainty* is dangerous. Every
small error becomes a confident trade signal. You lose money steadily while
your diagnostics say everything is fine.

**Accuracy tells you how good the answer is. Coverage tells you whether you can
trust the pipeline's opinion of its own answer.** The second is what a trading
decision depends on.

---

## Part 3 — What passed

### Coverage on realistic distributions: good

For a crude-oil-like distribution — a single hump, skewed, with a fat upper
tail, which is what oil actually looks like most of the time:

| what | nominal | actual |
|---|---|---|
| all brackets | 90% | **93%** |
| body (worth 10¢+) | 90% | **94%** |
| tail (worth 1–10¢) | 90% | **95%** |

Slightly conservative — bands marginally wider than strictly needed, which is
the **safe** direction to be wrong.

**The 1–10¢ tail row matters most**, because that's the price range where the
strategy intends to trade.

### It held up under stress

Coverage stayed near 90% when the conditions were made harder:

| stress test | coverage |
|---|---|
| thinned to 8 strikes (the minimum gate) | 97% |
| half the normal bid-ask spreads | 92% |
| double the spreads | 92% |
| fat tails on both sides | 94% |
| two days to expiry instead of one | 96% |
| martingale constraint switched off | 93% |

**The 8-strike result is a useful, concrete finding.** Gate 0 in
[[PIPELINE_MAP]] refuses to run on a date with fewer than 8 quoted strikes. This
confirms the threshold is safe: thinning the chain costs *precision* (typical
error rises from 0.59¢ to 0.69¢) but **not honesty** — the bands widen to
compensate, which is exactly what they should do.

### Accuracy: well inside the noise that matters

| region | typical error | typical bracket value |
|---|---|---|
| body | 0.59¢ | ~14¢ |
| tail | 0.20¢ | ~4¢ |
| far | 0.07¢ | ~0.4¢ |

**And essentially zero bias** — the errors are symmetric, not leaning one way.

That second point matters more than the size. A systematic lean is precisely
what manufactures a fake "edge," because it would push every bracket the same
direction. There isn't one.

For scale: it costs roughly **5¢ per contract** in fees and spreads to put this
trade on. Extraction error under 1¢ is not the thing that decides whether a
trade works.

### The end-to-end consistency check passed

The pipeline has a constraint (Stage 14) that forces the extracted
distribution's average to equal the market's forward price. That's a known
mathematical fact, so it's free information.

But it can also **hide bugs.** If something upstream is broken, forcing the
average into place papers over it while leaving the shape wrong.

So the test ran with the constraint **off** and checked whether the average
landed in the right place unaided.

**It did** — off by 0.16¢ on average, well inside its own uncertainty. That
means Stages 6 through 13 are internally consistent end to end. The constraint
is a safety net, not a crutch.

### Every deliberately injected bug was caught

We broke the pipeline on purpose, in five different ways, and checked whether
it noticed.

| bug we injected | caught? | how often |
|---|---|---|
| Forward price wrong by 5¢ | yes | 100% |
| Forward price wrong by 15¢ | yes | 100% |
| Forward price wrong by 50¢ | yes | 100% |
| Integration grid cut off too narrow | yes | 100% |
| One quote crossed or corrupted | yes | 98% |
| One quote left stale | yes | 100% |
| Sampler stopped before converging | yes | 100% |

**The first three are the important ones**, because a wrong forward price is
the exact failure that produced the previous project's phantom edge. The check
that catches it is also the cheapest one available: the forward computed from
the option chain itself is compared against the forward you supplied, and if
they differ by more than the statistical noise, something is wrong.

It fires at a 5¢ discrepancy — far below the level where it would distort a
trade.

### How much a wrong forward actually hurts

Quantified, which is new information:

- **Average bracket:** moves 0.036¢ for every 1¢ the forward is wrong
- **Worst bracket:** 0.18¢ per 1¢

So a 15¢ error in the forward shifts the most sensitive bracket by ~2.7¢ —
**larger than that bracket's entire 90% band.** This is why the forward must be
computed from the option chain rather than read from a separate source, and now
there's a number behind that requirement.

---

## Part 4 — What failed

### The bimodal test

We planted a distribution with **two humps and a dip between them**. In plain
terms: the market thinks oil ends up either around $82 or around $92, but
probably not $87 in the middle.

That's an unusual but not absurd shape — it's what you'd get if the market were
pricing a binary event, like an OPEC decision that either happens or doesn't.

**What the pipeline did:**

| | result |
|---|---|
| Found both humps? | **yes — 100% of runs** |
| Got the dip right? | **no — overstated by ~8 standard deviations** |
| Did the bands admit the error? | **no — 0.59¢ wide, contained the truth 3% of the time** |
| Did any diagnostic fire? | **no — the fit to observed prices was good** |

Read that as a sentence: **badly wrong, completely confident, and invisible
from the inside.**

The overall coverage on this shape collapses from 93% to **39%**.

### Why this is the worst possible failure mode

The pipeline isn't returning noise. It's returning a *specific wrong answer*
with *tight error bars* and *a clean bill of health from every diagnostic*.

On real data this would appear as a large, persistent disagreement with Kalshi
across the middle brackets — alternating sign across the ladder, which would
look even more like a real market inefficiency than a simple offset would.

It is the previous project's artifact wearing a new disguise.

### The clue that tells you what's really wrong

We ran the same test with **half the noise** — better quotes, tighter spreads,
cleaner data.

**It got worse.**

| noise level | error (in std devs) | coverage of the dip |
|---|---|---|
| normal | +7.8 | 3% |
| **half** | **+10.9** | **0%** |

This is the most diagnostically valuable result in the whole study.

**If the problem were a shortage of information**, better data would help. The
estimate would move toward the truth.

**What actually happened** is the estimate stayed put while the bands shrank.
That is the signature of a **misspecified model**, not an underpowered one —
the pipeline is converging confidently on the wrong answer.

The practical consequence is blunt: **you cannot fix this with better data,
more strikes, or tighter spreads.** Only changing the model helps.

### Where exactly the failure lives

Two bimodal tests, different spacing between the humps:

| humps apart | did the bands stay honest? |
|---|---|
| 1.6 vol-units (close) | **yes — 90% coverage at the dip** |
| 2.6 vol-units (far) | **no — 3% coverage** |

That's a sharper diagnosis than "struggles with two humps."

When the humps are **close**, the option prices genuinely cannot distinguish
one hump from two — and there the pipeline correctly says "I don't know," with
wide bands.

When the humps are **far apart**, the prices *could* tell the difference, but
the pipeline's built-in preference for smooth shapes overrides them — and it
does so confidently.

**The pipeline is honest about ignorance and dishonest about disagreement.**

### It isn't only bimodality

Two other unusual-but-plausible shapes failed the same way:

| planted shape | coverage |
|---|---|
| a narrow spike of probability | 48% |
| a sharp kink at the peak | 49% (body) |

Same mechanism every time. Many different distributions produce option prices
that all fit inside the bid-ask spreads. The pipeline picks the smoothest one
and reports how uncertain it is **among smooth options only** — never admitting
that non-smooth options exist.

### Why we tried to fix it and couldn't

The obvious suspect was the "smoothness dial" — the prior's strength. Weaken
it, and the pipeline should be more willing to accept a bumpy shape.

**Three different settings were tried. The result was identical each time**
(error of −9.3, −9.5, −9.6 standard deviations).

So it isn't the *strength* of the smoothness preference. It's the **form** —
the mathematical shape of the penalty itself, which permits gentle bending
everywhere but never a sharp local feature, no matter how loose the dial is
set.

That's a harder fix, and it's the one thing standing between here and a PASS.

---

## Part 5 — The thing that saves it

### A detector already exists in the output

The pipeline runs two independent methods:

- **Act III** — the Bayesian one, the answer that would be traded
- **Act II** — a simpler curve-fitting method, kept purely as a cross-check

Normally they agree closely. On the broken cases they diverge dramatically:

| situation | disagreement between the two methods |
|---|---|
| normal (healthy chain) | **0.56¢** |
| corrupted quote | 2.77¢ |
| **bimodal** | **8.64¢** |
| stale quote | 10.23¢ |

That's roughly **15× separation** between normal and bimodal, and it fired on
*every* mis-specified shape tested.

### Why this works when nothing else did

Every internal diagnostic failed because they all ask the same question: *"does
my answer fit the observed prices?"* On a bimodal chain, the answer is yes —
the smooth wrong density fits the quotes fine.

The two-method comparison asks a **different** question: *"do two methods with
different built-in assumptions agree?"* When the data doesn't pin the answer
down, each method falls back on its own assumptions, and those assumptions
differ. So they diverge — and the divergence is visible without knowing the
truth.

### What it does and doesn't give you

It's a **detector, not a corrector.** It says *"don't trust this chain,"* not
*"here's the right answer."*

That's enough. Skipping a date is the correct response to an untrustworthy
extraction, and skipping is cheap.

**Recommendation: add it as a fourth gate.** If the two methods disagree by
more than roughly 1.5¢ on any bracket, skip the date and log why. Costs
nothing — both numbers are already computed.

**Update (real-chain runs).** It was added, and on real chains it fired on
64–77% of dates (`FINDINGS_REALCHAIN.md` §4) — not because the densities were
interesting but because Act II differentiates and Act III integrates, so a
chain of mutually inconsistent quotes drives them apart faster than either
method's true error. Gate 4 is now *split-half consistency* (Act III on the
odd vs the even strikes, compared within their own posteriors) plus
leave-one-out residuals, with the Act II disagreement kept in the report as a
second opinion rather than a gate. See `NightKing/PIPELINE_CHOICES.md` §"Gate 4"
and `FINDINGS_REALCHAIN_V2.md` §5.

---

## Part 6 — The plots, and how to read each one

All in `synth/plots/`.

### `example_A_crude_full.png` — the healthy case

![[example_A_crude_full.png]]

Two panels stacked.

**Top:** the probability distribution. Black dashed line is the truth we
planted. Blue line is what the pipeline recovered. Blue shaded region is its
90% band. Red dots are the cross-check method. Grey ticks along the bottom mark
where the actual strikes are.

**Bottom:** the same information converted into Kalshi bracket prices. Black
dashes are true values, blue dots with error bars are the pipeline's estimates,
red crosses are the cross-check.

**What to look for:** blue tracks black closely, the shaded band comfortably
contains the dashed line almost everywhere, and the error bars in the lower
panel cross the true values. This is what "working" looks like.

**Note the strike ticks** — they cluster near the middle and thin out toward
the edges. That's real CME geometry, and it's why the bands widen at the edges.

### `example_C_bimodal_full.png` — the failure, in one image

![[example_C_bimodal_full.png]]

Same layout. **This is the most important plot in the study.**

**What to look for:** the black dashed truth has two humps with a deep dip
between them. The blue recovered line also has two humps — the pipeline did
find them — **but the dip is filled in far too high, and the blue band is
narrow right where it is most wrong.**

That combination — wrong and narrow together — is the entire problem in one
picture. A band that widened over the dip would be a pipeline saying "I'm not
sure here." It doesn't.

### `example_C05_bimodal_halfnoise.png` — better data, worse answer

![[example_C05_bimodal_halfnoise.png]]

Identical setup with half the market noise. **The bands are visibly tighter and
the error at the dip is larger.**

Put next to the previous plot, this is the proof that the problem is structural
rather than statistical. More information should narrow the gap between
estimate and truth. Here it narrows the *band* while the estimate stays wrong.

### `example_F_bimodal_close.png` — the honest failure, for contrast

![[example_F_bimodal_close.png]]

Two humps placed closer together. The pipeline still can't resolve them cleanly
— **but here the band is wide enough to contain the truth.**

Worth comparing directly against `example_C_bimodal_full.png`. Same kind of
shape, same kind of difficulty, opposite behaviour from the error bars. The
difference is whether the prices *could* have told the pipeline it was wrong.

### `example_E_sharp_peak.png` and `example_G_spike_outside_prior.png`

![[example_E_sharp_peak.png]]

![[example_G_spike_outside_prior.png]]

A kinked peak and a narrow spike. Both show the same signature: the recovered
line smooths over the sharp feature and the band doesn't widen to admit it.

These matter because they demonstrate the blind spot isn't specific to
bimodality. **It's about sharpness** — any feature the smoothness prior
dislikes gets flattened with unwarranted confidence.

### `coverage_curves.png` — the headline result

![[coverage_curves.png]]

Three panels: bracket probabilities, density at grid points, and the forward
price.

**Read it like this:** the x-axis is what the pipeline *claims* (50%, 80%, 90%,
95% confidence). The y-axis is what actually happened. **The dashed diagonal is
perfect honesty.**

- **On the line** — the pipeline's confidence is accurate
- **Below the line** — overconfident, which is the dangerous direction
- **Above the line** — too cautious, which is safe but costs you signals

The crude-oil line sits on or slightly above the diagonal. **The bimodal line
sits far below it** — at the 90% mark it lands near 39%.

The third panel (forward price) sits slightly below the line for every
configuration. That's the Stage 6 under-coverage described in Part 7.

### `error_by_region.png` — where accuracy lives

![[error_by_region.png]]

Two panels, both plotted against how far a bracket sits from the current price.

**Left:** error size by position. **Right:** band width by position.

**What to look for:** errors are largest near the middle in absolute cents —
which is just because middle brackets are worth more. The right panel shows the
bands widening as you move away from the money, which is correct behaviour: the
pipeline knows less about the edges and says so.

### `coverage_vs_strikes_and_noise.png` — does it hold under stress?

![[coverage_vs_strikes_and_noise.png]]

**Left:** coverage as the chain is thinned from 23 strikes down to 8 (the
minimum Gate 0 allows).

**Right:** coverage as spreads are halved and doubled.

**What to look for:** both lines stay flat near 90%. That's the result that
validates the 8-strike gate — fewer strikes means less precision, but the
pipeline correctly widens its bands, so the honesty holds.

### `stage14_diagnostic.png` — is the pipeline internally consistent?

![[stage14_diagnostic.png]]

A histogram of how far the extracted distribution's average landed from the
true forward price, with the martingale constraint **off**, measured in
standard deviations.

**What to look for:** a bell shape centred on zero, mostly inside ±2. It is.

Centred means the pipeline finds the right location on its own, using only the
option prices — Stages 6 through 13 agree with each other. If this histogram
were shifted off-centre, something upstream would be broken and the constraint
would have been hiding it.

### `forward_sensitivity.png` — how much does a wrong forward cost?

![[forward_sensitivity.png]]

Bracket price change per cent of forward error, plotted by bracket position.

**What to look for:** a hump in the middle peaking around 0.18¢ per 1¢. The
brackets on the steepest part of the distribution are most sensitive; the flat
tails barely move.

**Why it matters:** at 0.18¢/¢, a 15¢ forward error moves that bracket 2.7¢ —
more than its whole band. This is the quantitative case for computing the
forward from the option chain rather than importing it.

### `unconverged_bands.png` — what a bad sampler run looks like

![[unconverged_bands.png]]

Each dot is one run. X-axis: band width from a properly converged chain.
Y-axis: band width from a deliberately crippled one (5 warmup iterations
instead of 400).

**What to look for:** most dots fall **below** the diagonal. The broken run
produced bands about **13% narrower** than the honest ones.

That's the failure mode in miniature: a sampler that hasn't explored properly
doesn't report noise, it reports **false confidence.** Which is why the
convergence checks are a hard gate rather than a nice-to-have.

---

## Part 7 — Smaller problems found

### The forward's error bar is 25% too small

The pipeline computes the forward price and reports how uncertain it is. The
reported uncertainty is 0.89¢; the actual typical error is 1.17¢.

**Why:** the statistical formula assumes smoothly distributed errors, but real
quotes are rounded to the penny and floored at 1¢, which breaks that
assumption.

**Consequence:** the martingale constraint is tighter than the data justify,
pulling the distribution's position harder than it should.

**Fix:** widen the reported uncertainty by ~1.3×. The study just measured the
right multiplier.

### A genuine error in the strategy document

`nightking-strategy-writeup.md` and [[PIPELINE_CHOICES]] both state that a
particular SVI parameter bound guarantees the fitted curve can't imply a
negative probability. **It doesn't.**

The document's bound is $b(1+|\rho|) \le 4/\sqrt{T}$. The correct one (Lee's
moment bound) is $b(1+|\rho|) \le 2$, and even that doesn't exclude butterfly
arbitrage — a separate function $g(k)$ must be checked directly.

**Consequence:** Act II produced a locally negative probability in **41%** of
fits, and its distribution's average drifted ~$0.50 from the forward.

**This needs correcting in both documents**, and it matters practically: Act II
is the cross-check detector from Part 5, so a partly-broken Act II makes that
detector noisier in both directions.

### Sampler diagnostics below the stated bar

The strategy document asks for R̂ < 1.01 and effective sample size ≥ 400 on
every quantity. Actual: R̂ median 1.014, ESS median 303, with divergences in
most runs.

**How much it matters:** the coverage results say the bracket estimates aren't
biased by this — and coverage is the test that would detect it. But it means
the sampler is working harder than it should. A production run should use ~3×
the draws.

Worth noting that Fable reports three sampler designs were tried and abandoned
before finding one that worked at all. The posterior is genuinely
badly-conditioned — the middle of the distribution is pinned tightly by
penny-wide quotes while the far edges are unconstrained, a spread of about
100-million-to-one in scale.

### Very cheap brackets under thin-tailed distributions

Brackets worth under 1¢ had 70% coverage when the true distribution had thin
tails. Errors are ≤0.1¢ — irrelevant next to 5¢ of trading costs — and the
depth analysis already rules out trading sub-5¢ brackets. Reported for
completeness.

---

## Part 8 — What this means and what happens next

### Why FAIL was the right call

Thirteen of sixteen core criteria passed. The three that failed are all the
same failure.

The brief that commissioned this test named the worst possible outcome
explicitly: *a pipeline that is confidently wrong exactly when the market is
doing something interesting*, and asked that if an unusual shape isn't
recovered, **the bands should widen to admit it.**

They don't. And no downstream check catches it.

Calling that PASS WITH CAVEATS would have buried the one thing the test existed
to find.

### Why this is a good outcome

The blind spot was found in one night of compute, on fake money, with a
complete diagnosis: *what* fails, *when*, *why the obvious fix doesn't work*,
and *a detector that flags it*.

The alternative was finding it after a live trade, as a mysterious string of
losses on brackets the pipeline was most confident about.

**The validation worked. That's the result.**

### Three fixes, in order of cost

**1. Add the two-method disagreement gate.** Free — both numbers already exist.
Turns an invisible failure into a visible skip.

**2. Fix the forward's error bar.** Inflate by ~1.3×. The study measured the
multiplier.

**3. Change the form of the smoothness prior.** The real fix, and the expensive
one. Options in order of effort: fit an explicit two-hump alternative alongside
the smooth one and report the wider of the two; use a heavier-tailed penalty
that lets a few points move freely; or run several penalty forms and report the
envelope of all of them.

Any of these **must be re-run through this same harness, before and after.**
That's what the harness is for.

### The recommended next step

Rather than fixing the prior immediately, **run the extractor on real WTI
chains — descriptively only.**

It answers a question nothing else can: **what shape are real oil
distributions?**

- If they're smooth single humps and the detector almost never fires, the blind
  spot is a rare tail risk you gate against, and the expensive fix can wait.
- If the detector fires often, the fix becomes urgent — and you'd know that
  before investing in it.

**The discipline that makes this safe:** use it only to *characterise*, never to
*decide*. No comparison against Kalshi prices, no trade evaluation. The
pipeline has a known blind spot and must not inform decisions until it's
addressed.

Prerequisites: add the detector, and fix the SVI bound first — a broken Act II
makes the detector unreliable.

---

## Related

- `FINDINGS_SYNTHETIC.md` — every number, 382 lines
- `synth/plots/` — the figures described in Part 6
- [[PIPELINE_MAP]] — where these stages sit
- [[PIPELINE_CHOICES]] — why each stage was chosen
- [[nightking-strategy-writeup]] — the full theory
