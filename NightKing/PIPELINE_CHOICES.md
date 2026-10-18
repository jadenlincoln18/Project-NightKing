---
tags: [nightking, pipeline, decisions]
---

# NightKing — Pipeline Choices and Alternatives

Companion to [[PIPELINE_MAP]]. For each decision: what was chosen, why, what
the alternatives were, and what would make us revisit it.

The 20-stage spec is a menu. Not every stage belongs in the build, and two of
them are in for validation only. This is the reasoning.

---

## Gate 0 — which dates enter the pipeline at all

**Chosen:** three gates, applied before any computation. Same-day CME weekly
expiry → contract month matching Kalshi's `rules_primary` → at least 8 strikes
quoted with 3 or more per wing inside the final hour.

**Why.** Each gate removes a class of trade that cannot work regardless of how
good the signal looks.

*No same-day expiry* means carrying an open option position into the next
session after Kalshi has already settled. One day of WTI at 35% vol is ~$1.92
of one-sigma movement against a **$1-wide bracket** — it dominates everything.
This gate costs 53 of KXWTI's 134 dates and 3 of KXWTIW's 37.

*Wrong contract month* leaves you exposed to the calendar spread. Kalshi's
referenced month is **the one named in `rules_primary`** (present on every event
from June 2026), and that month diverges from the exchange front month for
roughly the last week of each contract's life. *Corrected (October 2026,
`FINDINGS_LEGCOUNT.md`):* the "rolls on the 16th" convention recorded here
earlier was inferred from events that named no contract and is not what the
settlements show. Measured from the settlement values, Kalshi switched months on
2026-02-20, 03-17, 04-20, 05-18, 06-16, 07-16 and 08-17 — one to four business
days before the NYMEX last trading day, not on a calendar date, and not exactly
the "2 business days before the current contract's last trading day" that
Kalshi's rules page states either (that rule gives 02-18, 03-18, 04-17, 05-15,
06-18, 07-17, 08-18). The backtest used the rules text where present, the
calendar fallback before June, and an ex-post check against the settlement
value that caught every misassignment (three KXWTIW weeks, eight KXWTI days).
The June 15 anomaly (−$4.70) matches no month and remains unexplained.

*Insufficient strikes* means no fittable smile. Measured: 109 of 117 dates pass.

**Alternatives considered.**

- *Trade the unhedged dates anyway and model the overnight gap.* Rejected —
  this is exactly the Rule 5 failure. A model produces a number, the number
  makes the exposure feel controlled, and you still carry $1.92 of one-sigma
  movement. Eliminate structurally or do not trade.
- *Use the monthly LO for Tue/Thu dates.* It covers only 5 of 53, and on those
  the expiry match is coincidental rather than systematic.
- *Relax the strike threshold to 5.* Rejected for now — a 5-point smile fit has
  effectively no wing information, and the wings are where the tradeable bias
  lives. Revisit if 8 proves too strict in the backtest.

**Revisit if:** CME lists Tue/Thu weeklies, or the backtest shows the 8-strike
threshold is dropping dates that would have produced usable extractions.

---

## Stage 5 — the naive finite-difference density: rejected as an estimator

**Chosen:** not used on the trading path. Retained as the pedagogical object it
is and as a cross-check on synthetic data where the answer is known.

**Why.** At CME's actual $0.25 weekly strike increment, the second difference
is roughly **25× smaller than the quote noise**. Measured bias/variance:

| strike gap | truncation bias | noise | total RMSE |
|---|---|---|---|
| $0.25 | ~0 | 1.176 | 1.176 |
| $1.00 | 0.00006 | 0.073 | 0.073 |
| $6.00 | 0.00215 | 0.00204 | **0.00296** |
| $15.00 | 0.01022 | 0.00033 | 0.01022 |

Against a true density of ~0.0476, the optimum sits near **$6 spacing** at ~6%
error. But using $6 spacing means discarding ~90% of the strikes and getting
the density at a handful of points — with no way to integrate over a $1-wide
bracket.

**Alternatives considered.**

- *Use $6 spacing and interpolate between.* Rejected — you would be
  interpolating the quantity you are trying to measure, and the interpolation
  assumption would silently determine the bracket probabilities.
- *Smooth the raw prices directly, then difference.* Rejected — a smoother's
  built-in low-curvature preference is a lie when applied to the price curve,
  because that curvature **is** the density. This is why Stage 7's coordinate
  change exists.

**Revisit if:** never, for this instrument. The arithmetic is not going to
change.

---

## Stage 6 — the forward: from the futures, with parity demoted to a check

**Chosen (revised September 2026, after the real-chain run):** the forward is
the futures price — in the backtest, the NYMEX settlement of the option's own
underlying contract, published at 14:30 ET, the same instant as the T-1d and
T-2d snapshots; live, the CL futures quote at decision time. The put-call-parity
regression still runs on every chain, but as a **check**: a date where the
chain's own forward disagrees with the futures by more than the option spreads
justify (|parity − futures| > 3 se *and* > 10¢) is flagged, because that is a
chain whose option quotes are stale relative to the futures — exactly when not
to trade. The disagreement's distribution is reported in `FINDINGS_REALCHAIN_V2.md` §2.

### The original choice, kept here because the argument is still right

*Regress $C(K) - P(K)$ against $K$ across liquid strikes. Slope gives the
discount factor, intercept over slope gives $F_0$.* Two reasons, and the
second is the important one.

*Numerically it is excellent* — on synthetic data the regression recovers $F_0$
to four decimal places, and with 3¢ of noise on every quote it is still accurate
to under a cent, because a regression **averages** errors across many strikes.
Direct contrast with the second difference, which amplifies the same errors.

*It makes an entire failure mode structurally impossible.* If an externally
sourced $F_0$ disagrees with what the chain implies, nothing errors out. You get
a density that is smooth, convex, normalized — and **positioned wrong**. It then
disagrees with every Kalshi bracket in the same direction, producing a
persistent sign-consistent apparent edge. That is fedarb's −8pt artifact. Taking
the forward from the chain means the forward and the prices cannot disagree.

*Free bonus:* parity is an arbitrage identity, so the points must lie on a
line. Residual outliers are broken quotes — the cheapest bad-data detector
available.

**The argument assumed the regression was reliable. On real chains it is not.**

### What the real chains showed

`FINDINGS_REALCHAIN.md` §7, thirty KXWTIW dates: the parity forward has a
median of 2–6 usable strike pairs per snapshot (Databento TBBO records a quote
only when a strike *trades*; the live book would show every strike two-sided),
and it misses the NYMEX settlement of the same contract at the same instant by
an RMSE of 23–38¢, within 10¢ on only 25–64% of dates. The regression's own
discount-factor estimate came out at 0.947 at expiry, where it must be 1.000: a
slope that wrong is a line fitted through noise. `FINDINGS_SYNTHETIC.md` §8 puts
the cost at up to 0.18¢ of bracket price per cent of forward error, so 30¢ of
forward error moves the steepest bracket by ~5¢ — larger than its 90% band and
larger than the whole friction budget — and, being a location error, it moves
every bracket the same way. That is the artifact the original argument was
built to prevent, produced by the original choice.

Two further reasons the chain's forward is worse than merely noisy here:

- **The quotes in a 60-minute window describe different underlying levels.** WTI
  moves $1+ an hour in this regime; the last quote at each strike was struck at a
  different underlying, so a straight line through $C - P$ across strikes is a
  line through prices from different worlds. On 2026-03-12 the raw parity forward
  sat 70¢ below the settlement; after every quote was moved to the same instant
  (Stage 6a below) it agreed to 1.5¢.
- **CME's standard WTI weeklies are American-style**, so parity is an inequality
  rather than an equality and the distortion is systematically signed. Stage 8's
  OTM-only selection keeps it small, but it is a bias, not scatter.

### The resolution: keep the protection, change the source

Put-call parity is an arbitrage identity, not a model: the synthetic long call /
short put at strike $K$ pays exactly $F_T - K$ in every state. So the parity
forward and the futures price are **two measurements of the same number**, not
two competing numbers, and the right thing is to take the less noisy one and
keep the other as the check. The mis-centring protection survives in three
places:

1. **The parity check** above — the original detector, still run, now with a
   more precise reference to compare against.
2. **Stage 14's unconstrained run** — the density's own mean must land on the
   forward without being told to. On the raw V1 windows it did so on only
   36–56% of dates (|z| median 2.5–3.9); `FINDINGS_REALCHAIN_V2.md` §6 reports
   the same table after the change.
3. **Stage 6a, synchronisation** (`synth/sync.py`): every quote in the window is
   moved to the snapshot instant and to the forward's level *before* fitting
   (sticky-strike Black-76 reprice through the quote's own implied vol, which
   carries delta, gamma and theta). The level of the chain is thereby anchored
   to the futures at the same instant — the forward and the quotes cannot
   disagree, which was the original goal, reached by moving the quotes to the
   forward instead of deriving the forward from the quotes. The underlying's
   path inside the window comes from 1-minute CL futures bars of
   the option's own underlying (`db_pull_futures.py`, ohlcv-1m, $0.70 for the
   study; V3). V2 had to reconstruct it from the option trade stream, anchored to
   the settlement at 14:29, because the store then held only settlements and
   session extremes; that reconstruction is kept as the fallback for holes in the
   bars. Against the real path it was within 16¢ RMSE at T-1d but 61¢ at T-2d and
   24¢ (plus a 24¢ RMSE level error) at T-4h, and the real path fixed exactly
   those two snapshots (`FINDINGS_REALCHAIN_V3.md` §8).

**The discount factor** is now fixed analytically from the rate, $D = e^{-rT}$
with $r = 4\%$. At $T \le 2$ days it is within $2 \times 10^{-4}$ of 1 — under
0.02¢ on any price here — the chain cannot identify it, and with the forward no
longer taken from the regression there is nothing left for the slope to do.

**Alternatives considered.**

- *Keep the parity forward and tighten the window to 10 minutes.* Measured
  (`FINDINGS_REALCHAIN.md` §2): the 10-minute chain is nearly synchronous and fits
  4× better, but clears Gate 0 on 9 of 30 dates at T-1d and 0 of 30 at T-2d.
  Not a fix.
- *Parity on the synchronised window as the forward.* It works — after
  synchronisation the parity forward agrees with the settlement to 10.8¢ RMSE
  at T-1d/60 (37.7¢ raw; within 10¢ on 68% of dates vs 32%) — and V2 used it at
  T-4h (10:30 ET) before intraday bars were in the store. With the bars (V3) the
  futures level at the snapshot instant is the forward on every snapshot; the
  parity-at-10:30 anchor had been off by 24¢ RMSE, and replacing it took T-4h's
  multimodal runs from 23% to 7%.

**Measured effect** (`FINDINGS_REALCHAIN_V2.md`, 30 dates, V1 re-run as the
baseline): the forward change alone moved Act III's χ²/strike at T-1d/60 from
8.1 to 6.4 and made several diagnostics *worse* (the correct forward with
asynchronous quotes is a worse-conditioned problem than the wrong forward the
raw chain was centred on); forward plus synchronisation took it to 1.6 on all
30 dates — better than V1's 10-minute window (2.0 on 9 dates) — and the share
of runs with a multimodal posterior fell from 43% to 0%. The two changes are
one fix.
- *Assume $r$ from a treasury curve.* Now done, for the reason above.

**Where the residual lives now (V3).** With the real path the 60-minute
χ²/strike sits at 1.5–1.8 against 1.1 on synthetic chains and does not move at
T-1d when the path is replaced, so what is left is the model — the sticky-vol
shift and the roughness prior's form — and quote-level inconsistency (LOO names
strikes on 80% of T-1d chains). Those are the next two questions, in that
order, each before/after through the harness.

**Revisit if:** live CL quotes at decision time prove less synchronous with the
option book than the settlement is with the 14:30 chain (then the live forward
needs its own timestamp discipline), or if the parity check flags most dates in
the backtest (then the option quotes, not the forward, are the problem, and the
date should be skipped rather than the forward moved).

---

## Gate 4 — chain consistency: split-half and leave-one-out, Act II demoted

**Chosen (September 2026):** a chain enters Act IV only if Act III fitted to its
odd-indexed strikes and Act III fitted to its even-indexed strikes agree over the
Kalshi ladder within their own posterior uncertainty:
$z_j = (m_{1j} - m_{2j}) / \sqrt{v_{1j} + v_{2j}}$ per bracket, statistic
$\max_j |z_j|$, cutoff the p95 of the same statistic on synthetic
well-specified chains (`python3 -m synth.realchain --calibrate`). Alongside it,
every strike is dropped in turn and predicted from the rest (Laplace refit); a
standardised miss above 3 names the strike the chain cannot explain. The Act II
vs Act III disagreement is still computed and reported, but no longer gates.

**Why the Act II gate was replaced.** `FINDINGS_SYNTHETIC.md` §11 proposed the
Act II / Act III disagreement as Gate 4 because it was the only signal that fired
on the bimodal truth. On real chains it fired on 64–77% of dates
(`FINDINGS_REALCHAIN.md` §4). The reason is structural: Act II differentiates
the fitted call curve and Act III integrates, so on a chain whose quotes are
mutually inconsistent Act II amplifies the inconsistency while Act III averages
it, and the disagreement grows faster than either method's true error. The gate
measured Act II's fragility as much as Act III's trouble — and Act II's
comparison arm was itself partly broken (butterfly-negative in 41% of synthetic
fits before the Stage 10 hardening).

**Why split-half is better.** Same machinery on both sides, so disagreement
indicates inconsistency in the *data*, not in one method's numerics. Both halves
carry posteriors, so "do they disagree more than their own uncertainty allows" is
a well-posed question rather than a hand-picked cent threshold. And it is
directly diagnostic of the actual problem: asynchronous quotes are precisely what
splits a chain against itself. Cost: one extra pair of (smaller) Act III fits per
date.

**What it cannot see, and why Act II stays in the report.** A smooth-prior bias
that both halves share — the bimodal blind spot of `FINDINGS_SYNTHETIC.md` §7 —
does not split a chain against itself, so split-half is not expected to fire on
it (the calibration run plants a bimodal truth to measure this). Act II did fire
there. Two independent implementations agreeing is still evidence; it is just not
a gate.

**Alternatives considered.** Random halves or repeated random splits (more
draws, same information; odd/even keeps both halves spanning the whole strike
range); importance-sampled LOO from the full posterior (free, but the weights
degrade on exactly the influential strikes LOO exists to find; the Laplace refit
costs under a second per chain).

---

## Stage 7 — Black-76, and why the inversion happens at all

**Chosen:** invert each observed price to an implied volatility using Black-76
(futures form, no $r$ inside $d_1$).

**Why Black-76 and not Black-Scholes.** The underlying is a futures price, which
is a $\mathbb{Q}$-martingale — it has no drift. Spot drifts at $r$; a futures
price does not. Using Black-Scholes with a spot would be systematically wrong at
every strike, appearing as a spurious tilt in the smile.

**Why invert at all**, given it is a lossless relabeling that gains no
information: option prices span $45 down to 2¢ with steep curvature, and any
smoother accurate in absolute terms is catastrophically wrong in the cheap tail
— which is exactly where the tradeable probabilities live. IVs across the same
strikes sit around 0.30 in a gentle U that smooths cleanly.

**Black-76 here is graph paper, not a theory.** No claim that prices are
lognormal; a curved $\sigma(K)$ produces a decidedly non-lognormal density.

**Known limitation, handled by Stage 8.** Vega collapses far from the money, and
Newton divides by vega. Measured on a 2-day WTI chain at 35 vol:

| strike | vega | IV error per 1¢ of price error |
|---|---|---|
| ATM | 2.57 | 0.4 vol pts |
| $5 ITM | 0.18 | 5.5 vol pts |
| $9 ITM | 0.0003 | **2,963 vol pts** |

This is not an algorithm problem — the information is not in the price. A deep
ITM option is a futures position wearing an option costume.

**Alternatives considered.**

- *Fit the density directly to prices without the IV detour.* That is Act III,
  and it is the primary route. Stage 7 exists to feed Act II and to produce the
  per-strike IV uncertainty that weights Stage 9.
- *Bachelier (normal) model instead of Black-76.* Reasonable for spread options
  and negative-price regimes; unnecessary here and would break the standard
  smile-fitting toolchain.

---

## Stage 8 — OTM only

**Chosen:** puts below $F_0$, calls above.

**Why.** Three reasons that compound. By parity, put and call at the same strike
carry the same IV, so nothing is lost by switching sides. OTM options are nearly
all time value, where vega is largest and inversion is best-conditioned. And
early-exercise value concentrates deep ITM, so OTM-only removes most
American-style contamination without needing a European product.

That third point matters here specifically: CME's standard WTI weeklies are
American-style, and Breeden–Litzenberger requires European. OTM selection is
what makes the American chain usable.

**Important asymmetry.** This fixes *deep ITM* — wrong instrument, switch sides.
It does **not** fix *deep OTM*, where both the call and the put are
uninformative. Those strikes get down-weighted by Stage 9, not re-read.

**Alternatives considered.**

- *Use the European WTI options (LCE/EU-style).* Cleaner in principle. Rejected
  because liquidity lives in the American weeklies, and the observed TBBO
  density (median 23 strikes) is on those. Revisit if the European chain proves
  deep enough.
- *Model the early-exercise premium and correct for it.* Rejected — adds a model
  where a selection rule suffices.

---

## Stage 9 / 10 — SVI smile: validation, not the trading path

**Chosen:** build it, run it, but as an **independent cross-check** rather than
the production density. Constraints enforced inside the optimizer so Stage 10
becomes verification rather than repair.

**Why keep it at all.** Two independent implementations agreeing is worth more
than either alone. If Act II's smile-based density and Act III's Bayesian
posterior mean disagree materially on the same chain, one of them has a bug —
and that is a far better way to find it than either route's internal
diagnostics. (It is *reported*, not gating: see Gate 4 above for why the
disagreement is dominated by quote inconsistency on real chains.)

**Why not the trading path.** It produces **one density and no error bars**.
With ~20 prices constraining an infinitely flexible shape, many genuinely
different densities fit equally well. Demonstrated: a single-humped and a
**bimodal** density, differing 40% in density at $87, produced option prices
differing by *less than the bid-ask spread* at most strikes. Act II picks one
and reports it without warning.

**Why SVI over a free spline.** SVI has a known wing bound — Lee's moment
formula, $b(1+|\rho|) \le 2$ on total variance (an earlier version said
$4/\sqrt{T}$; wrong, there is no $T$ in a bound on $\sigma^2 T$) — but the
bound alone does **not** exclude butterfly arbitrage. Gatheral–Jacquier's
$g(k) \ge 0$ must be verified separately over the range the density is used,
and the fit must additionally keep $|\rho| < 1$, $s > 0$ away from the
degenerate hockey-stick. The synthetic study found 41% of Act II fits locally
negative before this was enforced. Stage 10 is therefore *enforce, then verify,
then skip on failure* — never "cannot produce a negative density".

This matters more than it sounds. Numerical investigation found that *symmetric*
curvature is remarkably safe — even a 35→95 vol smile stayed arbitrage-free. But
**skew** degrades it: steepening the tilt drove the minimum density
0.00316 → 0.00094 → 0.00008 → 0.00000. Real crude smiles are skewed, so that is
the direction that bites, and it is invisible by eye.

**Weighting: $w_i \propto 1/(\text{half-spread}_i/\text{vega}_i)^2$.** Inverse
variance in IV space. Explicitly **not** volume — volume is cumulative history,
and weighting by it would down-weight exactly the wing strikes that pin the
tails while piling redundant weight on the ATM strikes already well-determined.

---

## Act III over Act II as the primary route

**Chosen:** the Bayesian density is the production path.

**Why, in one sentence:** the error bars are the deliverable, and Act II does
not produce them.

The trade filter is $|g_j| > \text{band}_j + \text{friction}_j$. Without the
band you are comparing a point estimate to a market price and calling any
difference an edge, with no way to separate signal from measurement noise. And
the ambiguity is worst in the wings — few strikes, wide spreads, dead vega —
which is exactly where the favorite–longshot bias lives. You would be most
confident precisely where you are least entitled to be.

**Stage 11 — `f = exp(spline)/Z`.** Non-negativity and normalization become
structurally impossible to violate rather than checked-for. $\theta$ ranges
freely over $\mathbb{R}^{25}$ with every point a valid distribution, so the
sampler has no boundaries to fight. Log space also handles the 8-orders-of-
magnitude dynamic range and extrapolates tails gracefully, since $\log f$ is
roughly linear out there.

*Alternative:* histogram or grid parameterization with explicit constraints.
Rejected — most proposals would be illegal, acceptance rates collapse, and the
chain sticks against constraint boundaries.

**Stage 12 — roughness prior with a hyperprior on $\lambda$.** The hyperprior is
not optional. In the wings **no strike constrains the density, so out there the
posterior *is* the prior**. Hand-picking $\lambda$ means your tail probabilities
are your own smoothness assumption wearing a data costume — and the tails are
where you intend to trade. Sampling $\lambda$ propagates uncertainty about *how
smooth the truth is* into the final bands.

*Alternative:* fixed $\lambda$ chosen by cross-validation. Rejected — produces
bands conditional on a guess, and the guess dominates exactly where it matters.

**Stage 11/12 revised (September 2026, `FINDINGS_PRIOR.md`): the knots, not the
prior.** The synthetic study's bimodal blind spot (`FINDINGS_SYNTHETIC.md` §9:
trough z +7.8, 3% trough coverage, χ² ≈ 1 so nothing fires) was diagnosed there
as the roughness prior's *form* — one scale, Gaussian tails. That diagnosis was
tested and is wrong. Heavy-tailed increments (Student-t ν = 3, ν = 1) and explicit
local scales (a non-centred horseshoe) on the same 24 knots leave the trough
untouched (z +6.8 → +6.4) — the Cauchy and horseshoe versions also mix unusably
(R̂ 1.1–4.2, ESS 13–96), exactly the funnel the sampler notes predicted. What
moves it is resolution: 24 uniform knots over ±7 vol-scales are 0.7 vol-scales
apart, and a cubic B-spline with that spacing cannot represent a trough between
humps 2.6 apart at any τ. With the *unchanged* Gaussian prior on 48 knots the
trough z goes to +1.3 and its coverage to 57%, overall bimodal coverage 42% →
72%, kinked-peak body coverage 53% → 89%; crude-skew coverage is unchanged
(92 / 95 / 95%), every injected fault is still caught, Stage 14 is unchanged,
and bracket R̂ / ESS stay inside the gate (1.020 / 260 vs 1.016 / 290). The cost
is precision on smooth truths: body bands 1.9¢ → 2.7¢, RMSE 0.57¢ → 0.66¢ — the
model admits shapes it used to exclude by construction. 64 knots buys a little
more trough coverage (75%) at 0.77¢ RMSE, over the pre-stated tolerance, and
the spike truth does not improve at any knot count; both point at knots dense
where strikes are dense (a divided-difference penalty) as the next step.

*Consequence:* `act3.M_COEF = 48` is the default; 24 stays runnable as the
baseline. The blind spot is **narrowed, not closed** — a 1.5¢ band that misses
the planted trough by 1.3σ is honest by comparison with 0.7¢ and 6.8σ, but it is
not 90% coverage. The definitive numbers are the full study
(`FINDINGS_SYNTHETIC_V2.md`, 1,840 runs, 24 vs 48 side by side): operating
configurations at or above nominal (crude-skew 95 / 97 / 97%), trough z +7.8 →
+1.4 and coverage 3% → 57%, kinked peak 49% → 76%, spike 48% → 60%, every fault
caught, Stage 14 unchanged, body bands 1.95 → 2.77¢ (+0.8¢ of gap per trade
through the filter), bracket ESS 303 → 253. On the real chains (`FINDINGS_REALCHAIN_V4.md`) the change
leaves χ²/strike, Stage 14 and Gate 4 where V3 had them, widens bands by about
a third, and turns five more chains multimodal — every one of them a chain that
fails the consistency checks, i.e. quote noise, not market structure.

*On a learned prior:* calibrating τ's hyperprior from the real extractions is
sound and cheap once the basis can express what the data ask for; it is not a
substitute for the basis fix and is not done here.

**Stage 13 — integrate forward, never differentiate.** An integral averages, so
independent errors shrink like $1/\sqrt{n}$; a derivative differences, so they
amplify. The entire computation is routed through the friendly operation. The
half-spread as per-strike tolerance means tight quotes discipline hard and wide
wing quotes barely constrain — the same weight-by-informativeness principle
appearing for the third time.

*Revised (September 2026, `FINDINGS_TICKFLOOR.md`): the tolerance is
$\max(\text{half-spread}, 1¢)$ on real chains.* Options trade in 1¢ ticks, so a
1¢-wide market does not locate the price to 0.5¢, and on real chains 26–32% of
quotes are that tight. With the half-spread alone, adjacent tight quotes that
disagree by two cents are 4σ events, and `FINDINGS_PRIOR.md` Part B found the
LOO exclusion rule deleting exactly those quotes. The 1¢ floor fixes the cause
without deleting anything: T-1d/60 χ²/strike 1.8 → 1.4 (T-4h 1.5 → 1.1), the
split-half gate 27% → 3%, Stage 14 87% → 93%, bands 3.8 → 3.2¢, sampler
unchanged; the exclusion rule reaches χ² 1.3 and 0% only by removing 8–10% of
quotes, and on top of the floor it still finds inconsistent strikes on
87% of chains, so it stays as a *diagnostic* that names the chains to distrust,
not a default that edits them. The synthetic harness could not admit any floor
(its quotes are true price + Gaussian noise with sd = half-spread, no tick
inconsistency, so every floor drifts crude coverage to 96–98%); the floor is
adopted on real-chain evidence and the harness's noise model is the limitation
to fix next.

**Stage 14 — martingale constraint.** Free information that pins a degree of
freedom nothing else constrains. OTM prices are insensitive to the
distribution's *location*, so a candidate can be mis-centred and still fit every
price within its half-spread. And a mis-centred density is the most dangerous
artifact available: smooth, convex, normalized, fits everything, and shifts
every bracket the same direction.

*Development protocol:* run once **without** it and check whether the posterior
mean lands on $F_0$ unaided. If yes, Stages 6–13 are internally consistent. If
no, there is a bug upstream that the constraint would mask.

**Stage 15 — NUTS preferred, convergence diagnostics load-bearing.** If the
chain has not mixed, the posterior spread is too narrow — and the spread is the
product. A badly converged chain produces confidently narrow bands, which makes
marginal gaps look tradeable. **The failure mode is a false trading signal, not
a bad plot.**

---

## Stage 16 — ranges, not points or thresholds

**Chosen:** compare range probabilities over Kalshi's exact bracket edges.

**Why.** The identity

$$\mathbb{Q}(a<F_T<b) = e^{rT}\big[C'(b) - C'(a)\big]$$

says a range probability depends **only on the first derivative at the two
endpoints** — no second derivative, nothing from the interior. Discretely this
is telescoping: summing butterflies across the interval cancels every interior
term by algebra, leaving two first-differences at endpoints you get to choose.

The robustness hierarchy:

| quantity | operation | noise |
|---|---|---|
| point density | 2nd derivative | amplified $\propto 1/h^2$ |
| threshold $\mathbb{Q}(>K)$ | 1st derivative | amplified $\propto 1/h$ |
| **range $\mathbb{Q}(a,b)$** | **integral** | **averaged** |

Kalshi's brackets **are** ranges, so the comparison is like-for-like *and* lands
on the most numerically robust quantity available. This is not a convenience —
it is why the strategy targets RANGE ladders specifically.

**Threshold ladders — corrected (October 2026, `FINDINGS_LEGCOUNT.md`).** An
earlier version of this note said the ICE-settled WTI series were all RANGE and
a previous brief said "Above $X" ladders were hourly or Pyth-settled. Both were
wrong: **KXWTI, the daily series, is an ICE-settled threshold ladder** (3,082
"Above $X" markets since January 2026 against 13 range brackets), and a
threshold digital is $D(a)$ alone — **two option legs, not four**, so half the
spread crossing and half the fees of a bracket. The backtest priced it that way
from the first run (two legs of spread; the fee term was charged for four and
is corrected in protocol amendment 7). It compares directly to the survival
function, one derivative instead of two, it is the cheaper structure, and it is
in the study (`FINDINGS_BACKTEST.md` §3, `FINDINGS_LEGCOUNT.md`). KXGOLD (19
events, ICE-settled, RANGE) is the one other exchange-settled ladder in the
store; KXWTIMAX/MIN settle on the period's extreme and are not vanilla-hedgeable.

---

## Stage 18 — gap decomposition: required, not optional

**Chosen:** per-posterior-sample logit regression,

$$\text{logit}(p^{\text{mkt}}_j) = a + b\cdot\text{logit}(p^{\mathbb{Q}}_j) + c\cdot m_j + \varepsilon_j$$

**Why it is needed even though Case 1 should not need it.** In a *perfectly*
hedged trade held to settlement, both legs resolve on the same number and you
keep the gap whatever caused it — no decomposition required.

But the hedge is **never perfect**: discrete strikes mean a finite ramp where
Kalshi pays a sharp $1-or-$0 while the spread pays something in between. Inside
that ramp the legs do not cancel. So you always retain some residual, and you
need to know whether you are harvesting a retail bias or **selling insurance**.

If the position is systematically short the CME tail and long the Kalshi tail,
the retained residual is *exactly the exposure the hedging premium was
compensating*. That is a legitimate business, but it must be sized as
insurance-selling with the tail loss modelled — not as a locked spread.

**What the parameters mean.** $b < 1$ is the favorite–longshot bias in one
number: shrinking a very negative logit makes it less negative, so longshots are
overpriced and favorites underpriced. $c \ne 0$ is the risk-premium tilt,
monotone in the state, which is what a pricing kernel does.

Running it per posterior sample gives a *distribution* over $(a,b,c)$, so "is
$b$ meaningfully below 1?" is answerable with a credible interval.

---

## Stage 20 — Micro WTI, and the ramp

**Chosen:** four-leg call-spread replication on **Micro WTI (MCO)** where
available, standard CL otherwise.

**Why Micro.** Decided by data, not preference. A standard CL option covers
1,000 barrels, so a $0.50-wide spread has max payoff $500 — one structure hedges
~500 Kalshi contracts. Micro (100 barrels) brings that to ~50.

Measured Kalshi depth: **all nine moderate-tail brackets cleared 50 contracts on
both sides with zero slippage**. At 500 contracts, the **ask side failed in 6 of
9**. Standard CL cannot fill the minimum hedged unit on the offer side.

**Caveat:** MCO expires on the **monthly cycle only**. So for weekly Kalshi
dates the hedge must use standard CL weeklies, and the sizing constraint
returns. This is unresolved and matters — it may mean trading fewer, larger
brackets, or accepting partial fills. **Flag for the backtest.**

**The ramp is a design parameter, not a bug.** $\varepsilon$ cannot go to zero
because strikes are discrete. Narrower ramp means better hedge but more
contracts and more fees. The residual it leaves is what sets real max loss, and
it is what position sizing must be built on — not the locked gap.

*Measured (October 2026, `FINDINGS_BACKTEST.md`, `BACKTEST_PROTOCOL.md` §4).*
The replication actually built for the backtest is the outer condor
$C(X-0.5) - C(X) - C(X+1) + C(X+1.5)$ (ramps outside the bracket, 500 Kalshi
contracts per standard structure, hedge ratio stated in the protocol). Its
friction in Kalshi units is dominated not by fees but by the CME spread: each
leg's half-spread divided by the $0.50 width. Measured on the live book
(`bbo-1m` at the snapshot minute, `FINDINGS_LEGCOUNT.md` §B) the half-spread is
**4¢/bbl at the money, 2.5–3¢ two to eight dollars out, 1.5¢ only under $0.05
of premium**, so the stack is **21–25¢ per Kalshi dollar for a four-leg bracket
and 15¢ for a two-leg threshold** against venue gaps of about a cent; the
writeup's ~5¢ working figure is not reachable with this structure. The
trade-sampled TBBO had suggested half that (its quotes are the book at its
tightest) and could price only 2 of 296 brackets at a chosen minute; the live
book priced 311 of 351. MCO's monthly expiry means every weekly date is a
standard-CL date. The replication, not the density, is the open design problem
(`BACKTEST_NEXT_PASS.md` item 1).

---

## Two sizing rules, fixed before there is money at risk

**Rule 1: size as hold-to-settlement.** The Kalshi book may not support an exit.
The force that guarantees convergence only fires at settlement. An intraday plan
on a thin book silently becomes hold-to-settlement anyway — but unhedged and
unplanned.

**Rule 2: size for the unhedged residual, not the locked gap.** Model the worst
case where settlement lands inside the ramp and the legs do not offset. That,
plus any settlement basis tail (see the unresolved June 15 event), is real max
loss.

Both are stated now precisely because later, with a live signal and a reason to
bend them, they will be harder to hold.

---

## Related

- [[PIPELINE_MAP]] — the flowcharts
- [[PROJECT_NIGHTKING_writeup]] — full derivations, 20 stages
- `data_cme/FINDINGS_BASIS.md`, `data_cme/FINDINGS_CHAIN.md`
- `FINDINGS_REALCHAIN.md` (V1) and `FINDINGS_REALCHAIN_V2.md` — the runs behind the Stage 6 and Gate 4 revisions
