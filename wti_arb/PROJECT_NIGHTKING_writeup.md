# Project NightKing

## Cross-venue density arbitrage: extracting risk-neutral distributions from
## options chains and trading them against prediction-market bracket ladders

**Status:** pre-backtest. Data collection in progress. No capital deployed.
**Last updated:** September 2026

---

# 0. Executive summary

The strategy compares two independent market estimates of the same probability
distribution and trades where they disagree by more than measurement error and
transaction costs.

**Source A — an options chain.** Option prices on a futures contract implicitly
encode the market's full probability distribution over where that contract will
settle. The Breeden–Litzenberger identity recovers it exactly: the risk-neutral
density is the second derivative of the call price with respect to strike.

**Source B — a prediction market ladder.** Kalshi lists ladders of price
brackets on the same underlying ("WTI settles between $87.00 and $87.99"). Each
bracket is a digital option, and its quoted price *is* a probability.

Integrate the extracted density over Kalshi's bracket edges and you get two
probabilities for the same event, produced by two populations with different
information, different constraints, and different regulatory access. Where they
disagree by more than the extraction's own uncertainty plus the cost of
trading, there may be an edge.

**The central methodological problem** is that the extraction is numerically
fragile — a second derivative of noisy prices — and the central *economic*
problem is that a raw disagreement is not automatically an edge, because part
of it is a risk premium that is supposed to be there.

Most of this document is about those two problems and how the pipeline
addresses them.

---

# 1. Thesis and origin

## 1.1 Where this came from

The project descends from two earlier efforts, and its design is a direct
response to how each failed.

**Crypto arbitrage (ArbCoin).** The original thesis: US regulation has walled
off American crypto exchanges from global ones, so the same asset trades at
different prices in the two zones, and a legal structure with access to both
could harvest the difference. The instrument choice was deliberate — meme coins
and low-cap assets specifically *because* major quant firms will not touch
them. That is a capacity argument, and it is correct.

It died on a regulatory change, but the design principle survived: **look for
edges defended by something other than secrecy.**

**Fed funds arbitrage (fedarb).** Kalshi's Fed-decision markets versus CME fed
funds futures. Fully built: 41 unit tests, 35 meetings, 390k aligned minutes.
It found a real, persistent, slow-decaying wedge — Kalshi priced aggressive
outcomes ~4¢ below futures-implied, 92% sign-consistent across meetings, with
divergences taking a median ~20 minutes to decay.

It died on **capacity**, not on being wrong. The hedge ratio was ~1,042 Kalshi
contracts per futures contract, and the first live snapshot showed a 2¢ depth
penalty selling that quantity into a thin bid. Eight events a year, friction
roughly equal to signal.

## 1.2 What fedarb taught, and what changed

Three lessons carried forward.

**Lesson 1: a scalar comparison cannot be diagnosed.** fedarb compared one
number to one number. When a gap appeared, there was no way to tell whether it
was mispricing, risk premium, or measurement artifact — one observation, three
candidate explanations. The analysis correctly ended in a shrug.

The fix is structural: compare a *distribution* to a *ladder*. With ~25
brackets you get 25 comparison points, and the candidate explanations leave
**differently shaped fingerprints** across them, which makes them separable.
This is the single most important design change.

**Lesson 2: measurement artifacts are the dangerous failure mode.** fedarb's
raw pooled wedge showed −8pt, which diagnostics traced mostly to measurement
breakdown (a two-state assumption violated by 2022's 50/75bp moves, and
contract contamination from the following meeting). A mis-specified extraction
produces a smooth, plausible, *sign-consistent* disagreement — which is exactly
what a real edge looks like. Every stage of the current pipeline carries
diagnostics aimed at this.

**Lesson 3: mid-vs-executable is not a detail.** fedarb measured a 3.1¢ average
gap between mid prices and executable prices. Any backtest run on mids is
measuring an edge that does not exist.

## 1.3 The economic thesis

Why should two venues disagree at all?

Both quote prices, so both quote under the risk-neutral measure $\mathbb{Q}$ —
neither is quoting real-world beliefs. But $\mathbb{Q}$ is only pinned down
when markets are linked. **Segmentation means the marginal investor differs**:
CME's is an institutional hedger, Kalshi's is retail. Each venue prices under
its own effective pricing kernel, and the barrier between them sustains the
difference.

That is the segmentation thesis stated precisely, and it is a stronger
foundation than "one of them is wrong."

Two forces should produce the disagreement:

**Risk premium (institutional side).** Commercial hedgers pay above fair value
for protection. In crude, refiners and airlines buy upside protection, which
inflates OTM calls. This distortion is **monotone in the state** — a smooth
lean across strikes, because the pricing kernel is a function of the terminal
price.

**Favorite–longshot bias (retail side).** One of the most documented patterns
in betting markets: participants overpay for longshots and underpay for
near-certainties. This distortion is **symmetric in probability** — it puffs
*both* tails and thins the middle, because it is a function of $p$, not of the
state.

Different coordinates. That is what makes them separable given enough brackets,
and it is why the whole distribution matters rather than a single number.

**Important caution.** In the tails these two effects push the *same
direction*, so they partially cancel rather than add. fedarb found the
institutional premium dominating: Kalshi priced aggressive outcomes *below*
futures-implied, which is the opposite sign from a naive longshot-bias
prediction. Whether crude behaves the same way is an empirical question, not an
assumption.

---

# 2. Theoretical foundation

## 2.1 Risk-neutral pricing, and why it matters here

Two probability measures appear throughout:

- $\mathbb{P}$ — real-world probability. What will actually happen.
- $\mathbb{Q}$ — risk-neutral probability. Reality re-weighted so that prices
  are plain discounted expectations.

$\mathbb{Q}$ exists because risk aversion can be folded into the probabilities
rather than carried as a separate adjustment term. Instead of

$$\text{price} = \mathbb{E}^{\mathbb{P}}[\text{payoff}] - \text{risk adjustment}$$

you write

$$\text{price} = e^{-rT}\,\mathbb{E}^{\mathbb{Q}}[\text{payoff}]$$

The risk adjustment has not disappeared; it has been absorbed into the weights.
Outcomes people pay to hedge against get *more* weight under $\mathbb{Q}$ than
they deserve under $\mathbb{P}$.

**The wedge only opens for risk that correlates with states where money is
scarce.** Diversifiable risk earns no premium: a fair coin uncorrelated with
anything has $\mathbb{Q} = \mathbb{P} = 0.5$. But a payoff that arrives during
a crash is worth more than its odds, and $\mathbb{Q}$ reflects that.

**The consequence for this strategy is unavoidable:** Breeden–Litzenberger
extracts $\mathbb{Q}$, because prices are what you differentiate. So a
disagreement with a prediction market is *partly supposed to be there*. You
cannot treat the extracted density as truth and call the other venue wrong.

This is the single most common way to fool yourself here, and Stage 18
(§4.18) exists specifically to address it.

## 2.2 The martingale property

Under $\mathbb{Q}$, a futures price is a martingale:

$$\mathbb{E}^{\mathbb{Q}}[F_T] = F_0$$

This follows from a single fact: **entering a futures contract costs nothing
today.** Zero cost implies zero expected discounted gain, hence no drift. It
holds regardless of storage costs, convenience yield, dividends, or the shape
of the forward curve — those explain *where* $F_0$ sits, and the martingale
property holds whatever value that turns out to be.

Two consequences used throughout:

1. **Black-76 rather than Black-Scholes.** Spot drifts at $r$ under
   $\mathbb{Q}$; a futures price does not. So the $r$ inside $d_1$ disappears,
   surviving only in the discount factor.
2. **A free consistency check.** The extracted density's mean *must* equal the
   forward. This is the most useful diagnostic in the pipeline (§4.14).

## 2.3 The master equation

Everything downstream is this one identity, differentiated:

$$C(K) = e^{-rT}\,\mathbb{E}^{\mathbb{Q}}\big[(F_T-K)^+\big]
       = e^{-rT}\int_K^{\infty}(s-K)\,f(s)\,ds$$

In words: for every possible landing price $s$ above the strike, take the
payoff $(s-K)$, weight by how likely that landing is under $\mathbb{Q}$, sum,
and discount.

## 2.4 First derivative — the survival function

Differentiate with respect to $K$. The strike appears in two places (the lower
limit and inside the integrand), so Leibniz's rule gives a boundary term plus
an interior term:

$$\frac{\partial C}{\partial K} = e^{-rT}\Big[\underbrace{-\,(s-K)f(s)\big|_{s=K}}_{\text{boundary}} + \int_K^\infty \frac{\partial}{\partial K}\big[(s-K)f(s)\big]\,ds\Big]$$

**The boundary term vanishes**, and not by luck: the integrand carries the
factor $(s-K)$, which is exactly zero at $s = K$. Economically — as you raise
the strike, the outcomes you stop counting are those at the money, where the
option pays exactly nothing. Dropping worthless outcomes costs nothing.

The interior term: inside the integral $s$ is a dummy variable and $f(s)$
contains no $K$, so only $(s-K)$ responds, contributing $-1$:

$$\int_K^\infty (-1) f(s)\,ds = -\big[1 - F(K)\big]$$

Hence

$$\boxed{\;\frac{\partial C}{\partial K} = -e^{-rT}\,\mathbb{Q}(F_T > K)\;}$$

The minus sign is bookkeeping: $C$ slopes down in $K$ while probabilities are
positive.

**Economic reading, no calculus required.** Raise the strike by $1. In every
scenario where the option finishes in the money, the payoff is now exactly $1
smaller. In every other scenario, nothing changes. So the value lost is
$1 × \mathbb{Q}(\text{ITM})$, discounted.

**This quantity is directly tradeable.** It is the price of a digital option at
$K$, and a Kalshi "above $K$" contract *is* that digital. So the first
derivative is not an abstraction — it is the fair value of the instrument on
the other venue.

## 2.5 Second derivative — Breeden–Litzenberger

We now have $C'(K) = -e^{-rT}[1 - F(K)]$. Differentiate again. The constant
vanishes, and $F'(K) = f(K)$ by the fundamental theorem of calculus:

$$\frac{\partial^2 C}{\partial K^2} = -e^{-rT}\cdot\big(-f(K)\big) = e^{-rT} f(K)$$

$$\boxed{\;f(K) = e^{rT}\,\frac{\partial^2 C}{\partial K^2}\;}$$

**Intuition via the butterfly.** Buy one call at $K-h$, sell two at $K$, buy one
at $K+h$. The payoff is a tent: zero outside $[K-h, K+h]$, peaking at $K$. Its
price is therefore the probability of landing near $K$ — which is the density.
And the recipe $C_{i-1} - 2C_i + C_{i+1}$ *is* the discrete second derivative.
The math is not a coincidence; the second derivative literally is the tent.

**Equivalent framing:** the second difference measures how far the middle price
sags below the chord joining its neighbours. A straight price curve implies
zero density; curvature implies probability mass.

## 2.6 The three consistency checks

**Convexity $\iff$ non-negativity.** $f \ge 0$ requires $C'' \ge 0$, i.e. the
call curve must be convex in strike. This is the no-butterfly-arbitrage
condition: a concave patch would mean a butterfly with negative cost, which
cannot survive in a liquid market. Visible directly in quotes — consecutive
price drops must shrink monotonically.

**Normalization.**
$$\int_0^\infty f\,dK = e^{rT}\big[C'(\infty) - C'(0^+)\big] = e^{rT}\big[0 - (-e^{-rT})\big] = 1$$
Automatic. In practice it catches a truncated integration grid — mass leaking
past the ends.

**Mean = forward.** $C(0) = e^{-rT}\mathbb{E}^{\mathbb{Q}}[F_T]$ and $C(0) =
S_0$-equivalent, so by the martingale property the density's mean must be
$F_0$. **This is the most important check.** A mis-centred density is smooth,
convex, normalized, and passes everything else — while disagreeing with every
bracket in the same direction. That is precisely fedarb's −8pt failure mode.

---

# 3. Why the naive approach fails

The identity is exact. The computation is not, and understanding why is
essential to understanding the rest of the pipeline.

## 3.1 The discrete estimator

You have $n$ prices, not a function. Real chains are unevenly spaced (dense
near the money, sparse in the wings), so with $h_1 = K_i - K_{i-1}$ and
$h_2 = K_{i+1} - K_i$:

$$f(K_i) \approx e^{rT}\cdot 2\left[\frac{C_{i-1}}{h_1(h_1+h_2)} - \frac{C_i}{h_1h_2} + \frac{C_{i+1}}{h_2(h_1+h_2)}\right]$$

Derivation: measure the slope on each side, note that each average slope best
describes its interval's *midpoint*, and divide the slope change by the
distance between those midpoints, $(h_1+h_2)/2$. Setting $h_1 = h_2 = h$
recovers the butterfly $\frac{C_{i-1}-2C_i+C_{i+1}}{h^2}$.

## 3.2 Three distinct error sources

**(a) Noise amplification — dominant.**

Each observed price is a bid-ask midpoint, uncertain by roughly the
half-spread. Those errors flow through the formula with the same weights as the
prices:

$$\text{error in second difference} = e_{i-1} - 2e_i + e_{i+1}$$

For independent errors of size $\sigma_C$, the combined error is
$\sigma_C\sqrt{1^2 + 2^2 + 1^2} = \sigma_C\sqrt{6}$ — **independent of strike
spacing.** The middle price's error counts double, because that strike is the
shared endpoint of both slope calculations.

Meanwhile the *signal* — the second difference itself — scales as $f \cdot h^2$.
So as strikes get closer:

| gap $h$ | true second difference | error (3¢ quotes) | relative |
|---|---|---|---|
| $5.00 | 1.152 | 0.073 | **6%** |
| $1.00 | 0.048 | 0.073 | **153%** |
| $0.25 | 0.003 | 0.073 | **2,300%** |

At CME's actual $0.25 weekly strike increment, **the noise is roughly 25× the
quantity being measured.** The estimator returns garbage — frequently negative,
which is impossible for a density.

The mechanism is catastrophic cancellation: at tight spacing you are
subtracting two nearly identical numbers (`6.72317 − 6.72019 = 0.00297`) each
of which is uncertain by more than the difference.

**The counterintuitive consequence: finer strikes make the naive estimator
worse.** More data, less information. This is the signature of an ill-posed
inverse problem — the forward map smooths, so the inverse must un-smooth, and
un-smoothing amplifies whatever noise is present.

**(b) Truncation — small.**

Three points determine one parabola, and the second difference returns that
parabola's curvature. But the true curve is not a parabola; its curvature
varies across the span, so the single fitted value is a compromise dragged
toward the edge values. With perfect prices at $h=5$ this costs ~0.0015 against
a true density of ~0.0476 — about 3%, and it *shrinks* as $h$ shrinks, exactly
opposite to noise.

**(c) Off-centre bias from unequal spacing — smallest.**

With $h_1 \ne h_2$, the two slope-midpoints are not symmetric about $K_i$;
their centre sits at $K_i + (h_2-h_1)/4$. You compute curvature at one location
and file it under another. The leading error term is $\frac{h_2-h_1}{3}C'''$,
which is first-order and vanishes identically when $h_1 = h_2$. Fixable for
free by re-gridding.

## 3.3 The bias–variance optimum

Truncation and noise pull in opposite directions, so there is an optimal
spacing. For a representative crude chain with 3¢ quote noise:

| $h$ | bias | noise | total RMSE |
|---|---|---|---|
| 0.25 | 0.00000 | 1.17576 | 1.17576 |
| 1.00 | 0.00006 | 0.07348 | 0.07348 |
| 3.00 | 0.00056 | 0.00816 | 0.00818 |
| **6.00** | 0.00215 | 0.00204 | **0.00296** |
| 15.00 | 0.01022 | 0.00033 | 0.01022 |

Optimum around $6 spacing, 6% error. But using $6 spacing means **discarding
roughly 90% of your strikes** and getting the density at only a handful of
points — with no way to integrate over a $1-wide bracket.

**So the real question the pipeline answers is: how do I use all forty strikes
when any three of them, used alone, destroy the signal?**

Two answers, and they are alternatives rather than sequential steps.

---

# 4. The extraction pipeline

Twenty stages in five acts. Acts II and III are **two independent routes** to
the same object; Stages 6 and 8 are shared data preparation.

## Act I — the identity (Stages 1–5)

Covered in §2–3 above. Stages 1–3 are the mathematical core, Stage 4 the three
checks, Stage 5 the fragility analysis that motivates everything after.

## Act II — Defense 1: clean the prices, then differentiate

### Stage 6 — Forward and discount factor from the chain itself

Buy a call and sell a put at the same strike. The payoff is exactly $F_T - K$
in *every* scenario — no max, no kink. That is a synthetic forward, so:

$$C(K) - P(K) = e^{-rT}\,(F_0 - K)$$

This is **linear in $K$**. Regress $y_i = C_i - P_i$ against $K_i$:

- slope $= -e^{-rT}$ → the discount factor $D$
- intercept $= D \cdot F_0$ → the forward $F_0 = \text{intercept}/D$

**Verified numerically:** on synthetic data this recovers $F_0$ to four decimal
places, and with 3¢ noise added to every quote it is still accurate to under a
cent — because a regression across many strikes *averages* errors. Direct
contrast with the second difference, which amplifies the same errors. Same
inputs, opposite operation, opposite outcome.

**Why not read the futures screen:** if an externally-sourced $F_0$ disagrees
with what the chain implies, nothing errors out. You get a smooth, convex,
normalized density that is *positioned wrong*, which then disagrees with every
bracket in the same direction. Sourcing $F_0$ from the chain makes this failure
structurally impossible.

**Free bonus:** parity is an arbitrage identity, so the points *must* lie on a
line. Residual outliers are broken quotes — the cheapest bad-data detector in
the pipeline.

**Revision (September 2026, after the real-chain run).** The mis-centring
argument stands; its premise did not survive real data. On thirty KXWTIW
dates the parity regression had 2–6 usable pairs and missed the NYMEX
settlement of the same contract at the same instant by 23–38¢ RMSE
(`FINDINGS_REALCHAIN.md` §7) — a ~5¢ location error on the steepest bracket
at the measured 0.18¢/¢ sensitivity, i.e. the artifact this stage was meant
to prevent. Parity is an identity, so the parity forward and the futures are
two measurements of the same number: the forward now comes from the futures
(the NYMEX settlement of the option's own underlying at the 14:30 snapshots;
live, the CL quote at decision time) and the parity regression runs as a
check that flags stale option books. The protection is completed by
synchronising every quote to the snapshot instant and level before fitting
(`synth/sync.py`), so the forward and the quotes cannot disagree. Details:
`NightKing/PIPELINE_CHOICES.md` §"Stage 6", results `FINDINGS_REALCHAIN_V2.md`.

### Stage 7 — Invert price to implied volatility (Black-76)

$$C = e^{-rT}\big[F\,\mathcal{N}(d_1) - K\,\mathcal{N}(d_2)\big]$$
$$d_1 = \frac{\ln(F/K) + \tfrac12\sigma^2T}{\sigma\sqrt T},\qquad d_2 = d_1 - \sigma\sqrt T$$

Note the absence of $r$ inside $d_1$ (§2.2).

**What $d_1$ and $d_2$ mean.** $d_2$ is literally a z-score: how many standard
deviations the strike sits from the centre of the terminal log-price
distribution. So $\mathcal{N}(d_2) = \mathbb{Q}(F_T > K)$ — the probability of
finishing in the money. (Verified against 4M Monte Carlo paths: formula 0.1867
vs simulation 0.1866 at one strike.)

$\mathcal{N}(d_1)$ is the **asset-weighted** version. Concretely, with five
equally likely outcomes $\{79, 83, 87, 91, 95\}$ and a call struck at 88:

- two of five scenarios are ITM → $\mathcal{N}(d_2) = 40\%$ *(a headcount)*
- value in those scenarios is $0.2(91) + 0.2(95) = 37.2$ out of a total of 87
  → $\mathcal{N}(d_1) = 42.76\%$ *(a dollar-count)*

40% of the scenarios, 42.76% of the value — more, because the ITM scenarios are
the expensive ones. $\mathcal{N}(d_1) > \mathcal{N}(d_2)$ always, and
$d_1 - d_2 = \sigma\sqrt T$ exactly.

So Black-76 reads: **collect what you receive, minus what you pay, each scaled
by the appropriate fraction, discounted.** Two different d's because the strike
is fixed every time you exercise (needs a headcount) while the asset is worth
more in some exercise scenarios than others (needs a dollar-count).

**Inversion.** $\sigma$ sits inside $\mathcal{N}(\cdot)$, an integral with no
closed form, so it cannot be isolated algebraically. Solve numerically via
Newton with vega:

$$\text{vega} = \frac{\partial C}{\partial\sigma} = e^{-rT}F\varphi(d_1)\sqrt T,\qquad
\sigma_{k+1} = \sigma_k - \frac{C(\sigma_k) - C^{\text{obs}}}{\text{vega}(\sigma_k)}$$

*(Derivation note: the identity $F\varphi(d_1) = K\varphi(d_2)$ makes the two
chain-rule terms collapse, leaving only $\partial(d_1-d_2)/\partial\sigma =
\sqrt T$. That is where the $\sqrt T$ comes from.)*

**Why the inversion is worth doing at all:** it is a lossless relabeling and
gains nothing by itself. It earns its keep in Stage 9 — prices span $45 down to
2¢ with steep curvature that a smoother destroys, while IVs across the same
strikes sit around 0.30 in a gentle U that smooths cleanly. **Black-76 is graph
paper, not a theory.**

**Where it breaks — vega dies in the wings.** Newton divides by vega, so IV
error ≈ price error / vega. Measured on a 2-day WTI chain at 35 vol:

| strike | vega | IV error per 1¢ of price error |
|---|---|---|
| $87 (ATM) | 2.57 | 0.4 vol pts |
| $82 | 0.18 | 5.5 vol pts |
| $78 | 0.0003 | **2,963 vol pts** |

With realistic 3¢ noise, wing strikes returned wild values *and outright
failures* — the noisy price landing below intrinsic value, where no volatility
can produce it. Deep ITM options are almost entirely intrinsic (the $78 call
carried one-tenth of a cent of time value).

**This is not an algorithm problem.** The information is not in the price. A
better solver does not help.

### Stage 8 — Select OTM only

Take puts below $F_0$, calls above. Three reasons:

1. By parity, put and call at the same strike carry the *same* IV — nothing is
   lost by mixing.
2. OTM options are nearly all time value, where vega is largest and inversion
   is best conditioned.
3. Early-exercise value concentrates deep ITM, so OTM-only removes most
   American-style contamination without needing a European product.

Note the asymmetry: this fixes *deep ITM* (wrong instrument — switch sides).
It does **not** fix deep OTM, where both instruments are genuinely
uninformative. Those strikes get down-weighted, not re-read.

### Stage 9 — Fit the smile, weighted by informativeness

Fit smooth $\sigma(k)$ where $k = \ln(K/F_0)$ is log-moneyness — centred at
zero, scale-free, and the natural coordinate for a lognormal.

**Weights.** IV uncertainty $\approx$ half-spread / vega, so
$w_i \propto 1/(\text{half-spread}_i/\text{vega}_i)^2$. Inverse variance, the
standard weighted-least-squares result. **Not volume** — volume is cumulative
history, and weighting by it would down-weight exactly the wing strikes that
pin the tails while piling redundant weight on the ATM strikes already
well-determined.

**Parameterization: SVI**, for total variance $w(k) = \sigma^2T$:

$$w(k) = a + b\Big[\rho(k-m) + \sqrt{(k-m)^2 + s^2}\Big]$$

Five parameters with individual meanings (level, wing slope, skew, shift,
curvature). Chosen over a free spline because of Stage 10.

### Stage 10 — No-arbitrage, enforced not checked

Conditions: $-e^{-rT} \le \partial C/\partial K \le 0$ (monotone) and
$\partial^2 C/\partial K^2 \ge 0$ (convex).

**The trap:** the conditions are on $C$, but you are fitting $\sigma$. A
perfectly smooth, plausible vol curve can imply a negative density, and you
cannot tell by looking.

Numerical investigation found that *symmetric* curvature is remarkably safe —
even extreme smiles (35 vol ATM to 95 vol in the wings) stayed arbitrage-free.
**Skew is where it degrades**: pushing the tilt steeper drove the minimum
density from 0.00316 → 0.00094 → 0.00008 → 0.00000, approaching the boundary.
Since real crude smiles *are* skewed, this is the direction that bites.

SVI has a known wing bound — Lee's moment formula, $b(1+|\rho|) \le 2$ on
total variance (an earlier version of this document gave $4/\sqrt T$; wrong,
there is no $T$ in a bound on $\sigma^2 T$) — but the bound alone does **not**
exclude butterfly arbitrage: Gatheral–Jacquier's $g(k) \ge 0$ must be verified
over the whole range the density is used on, and the fit must keep
$|\rho| < 1$, $s > 0$ away from the degenerate hockey-stick. The synthetic
study (`FINDINGS_SYNTHETIC.md` §10) found 41% of Act II fits locally negative
before this was enforced. Stage 10 is therefore *enforce, then verify, then
skip on failure* — never "cannot produce a negative density".

Reprice onto a **fine, even grid** — which also restores the second-order
accuracy lost to unequal spacing (§3.2c) and provides the resolution needed to
integrate over bracket edges later.

## Act III — Defense 2: never differentiate

### Why Act II is insufficient

It hands you **one density and no error bars.** That is a false answer to an
underdetermined question, for a structural reason:

**Each option price is an integral — a summary statistic compressing the entire
density above that strike into one number.** Summaries discard detail. And ~20
prices cannot pin down an infinitely flexible shape.

Demonstrated numerically: a single-humped density and a **bimodal** one —
describing genuinely different worlds, differing 40% in density at $87 (0.1534
vs 0.1094) — produced option prices differing by **less than the bid-ask
spread** at most strikes. Both are consistent with the same observed chain.
Act II picks one and reports it without warning.

The forward map (density → prices) is a proper function. The reverse is **not a
function at all.**

### Stage 11 — Parameterize so illegal states are unrepresentable

$$f(s;\theta) = \frac{\exp\big(\phi(s;\theta)\big)}{\displaystyle\int\exp\big(\phi(u;\theta)\big)\,du},
\qquad \phi(s;\theta) = \sum_{j=1}^{m}\theta_j B_j(s)$$

- The $\exp$ makes negativity **impossible**, not merely checked. $e^x > 0$ for
  every real $x$.
- The denominator makes integrating-to-1 **automatic**.
- $\theta$ therefore ranges freely over all of $\mathbb{R}^{m}$ — every point is
  a valid probability distribution, so the sampler has no boundaries to fight.

$\phi$ is the log-density, built as a spline: $B_j$ are fixed overlapping basis
bumps, $\theta_j$ their heights. Only $\theta$ moves during sampling.

**Why log space.** A density spans orders of magnitude (0.15 at the peak to
$10^{-8}$ in the tail); its log spans ~18. Tails decay roughly exponentially,
so $\log f$ is roughly linear and extrapolates gracefully. And a lognormal has
a *parabolic* log-density, so penalizing $\phi''$ says "be lognormal-ish unless
the data insists otherwise" — a sensible default.

Knots dense where strikes are dense, sparse in the wings. Grid extended well
past the outermost strike (Kalshi has a "Below $70" bracket; mass must exist
there). 20–30 coefficients for ~20 strikes — deliberately more parameters than
data, because the problem genuinely *is* underdetermined and the prior, not a
shortage of parameters, is what regularizes it.

**Revision (September 2026, `FINDINGS_PRIOR.md`).** "20–30 coefficients" was
too few. The synthetic study's bimodal blind spot was traced to the basis, not
the prior: 24 uniform knots over ±7 vol-scales are 0.7 vol-scales apart and
cannot represent a trough between humps 2.6 apart at any smoothness. 48 knots
with the same Gaussian roughness prior take the trough error from 6.8σ to
1.3σ with no loss of calibration elsewhere; heavy-tailed and local-scale priors
on 24 knots change nothing. The implementation uses 48 uniform knots; "dense
where strikes are dense" remains the next refinement.

### Stage 12 — The prior

$$p(\theta)\;\propto\;\exp\!\left(-\lambda\int \phi''(u)^2\,du\right)$$

Smooth curves probable, wiggly curves improbable, $\lambda$ setting the
strength. Curvature specifically: penalizing $\phi$ would say "be flat";
penalizing $\phi'$ would say "don't slope"; penalizing $\phi''$ says "be close
to a straight line in log space unless data pushes otherwise."

**Why this is load-bearing:** with more parameters than prices, a candidate can
wiggle violently *between* strikes while matching every observed price exactly.
The likelihood alone cannot rule that out.

**The hyperprior is not optional.** In the wings no strike constrains the
density, so **out there the posterior *is* the prior.** Hand-picking $\lambda$
means your tail probabilities are your own assumption wearing a data costume —
and the tails are where the tradeable bias lives. Put $\lambda \sim
\text{Gamma}(a,b)$ and sample it alongside $\theta$, so uncertainty about *how
smooth the truth is* propagates into the final bands.

### Stage 13 — The likelihood

For each candidate, compute implied prices by **integration**:

$$\hat C_i(\theta) = e^{-rT}\int_{K_i}^{\infty}(s-K_i)\,f(s;\theta)\,ds$$

$$p(C^{\text{obs}}\mid\theta) = \prod_{i=1}^{n}\mathcal{N}\big(C_i^{\text{obs}};\;\hat C_i(\theta),\;\sigma_i^2\big)$$

with $\sigma_i$ = that strike's half-spread — floored at one tick (1¢) on real
chains since September 2026 (`FINDINGS_TICKFLOOR.md`): a 1¢-wide market does not
locate the price to half a cent, and the unfloored tolerance made the tightest,
best quotes look like the worst ones.

**This is the crux of Act III.** An integral is an average, so independent
errors shrink like $1/\sqrt n$. A derivative is a difference, so they amplify.
The entire computation is routed through the friendly operation; the $1/h^2$
blow-up simply does not exist here.

The product means a candidate must fit the **whole chain** — one badly missed
strike drives the product near zero regardless of the others. And the
half-spread as tolerance means tight quotes discipline hard while wide wing
quotes barely constrain, which is the third appearance of the same
weight-by-informativeness principle.

In practice, work in log space (sum of squared standardized residuals) to avoid
underflow.

### Stage 14 — The martingale constraint

$$\mathcal{N}\big(F_0;\;\mathbb{E}_\theta[F_T],\;\sigma_F^2\big),\qquad
\mathbb{E}_\theta[F_T] = \int s\,f(s;\theta)\,ds$$

with $\sigma_F$ tight but not zero (the parity regression has its own small
uncertainty, and a hard constraint would create a boundary).

**Why it is needed despite the likelihood.** OTM prices are insensitive to the
distribution's *location* — a candidate can be slightly mis-centred and still
fit every price within its half-spread. Location is only weakly identified.

And a mis-centred density is the most dangerous artifact available: smooth,
convex, normalized, fits all prices, and shifts *every* bracket probability the
same direction — producing a persistent, sign-consistent apparent edge. fedarb's
−8pt, reincarnated.

The constraint costs nothing: it uses a fact already known from §2.2 and a
forward $F_0$ already computed in Stage 6, and it pins a degree of freedom
nothing else constrains.

**Development diagnostic:** run once *without* it and check whether the
posterior mean lands on $F_0$ unaided. If yes, Stages 6–13 are internally
consistent. If no, there is a bug upstream — and adding the constraint would
mask it.

### Stage 15 — MCMC

The posterior lives in 20–30 dimensions with a nonlinear forward map. Gridding
is impossible ($10^{25}$ evaluations at 10 points per dimension); uniform
sampling is useless because the posterior concentrates in a thin sliver.

HMC/NUTS if gradients are available through the forward map (worth the effort
at this dimensionality); random-walk Metropolis as a fallback for a first
version.

**Convergence diagnostics are not box-ticking here.** $\hat R < 1.01$, adequate
effective sample size, trace inspection, divergence count. If the chain has not
mixed, the posterior spread is too narrow — and **the spread is the
deliverable.** A badly-converged chain produces confidently narrow error bars,
which makes marginal gaps look tradeable. The failure mode is a false trading
signal, not a bad plot.

Output: thousands of concrete densities — the ensemble.

## Act IV — from density to decision

### Stage 16 — Range probabilities, and why they are the robust quantity

For each posterior sample: $p^{(m)}[a,b] = \int_a^b f(s;\theta^{(m)})\,ds$.
Mean is the estimate; spread is the credible band.

The identity that justifies the whole range framing:

$$\mathbb{Q}(a<F_T<b) = F(b) - F(a) = e^{rT}\big[C'(b) - C'(a)\big]$$

**A range probability depends only on the first derivative at the two
endpoints.** No second derivative, nothing from the interior.

Discretely this is telescoping — summing butterflies across the interval:

$$\sum_{i=j}^{k}\big(C_{i-1}-2C_i+C_{i+1}\big) = \big(C_{k+1}-C_k\big) - \big(C_j - C_{j-1}\big)$$

Every interior term cancels **by algebra**. The noisy middle annihilates itself,
leaving two first-differences at endpoints you get to choose — pick the
densest, tightest-quoted strikes.

**Hence the robustness hierarchy:**

| quantity | operation | noise behaviour |
|---|---|---|
| point density | 2nd derivative | amplified $\propto 1/h^2$ |
| threshold $\mathbb{Q}(>K)$ | 1st derivative | amplified $\propto 1/h$ |
| **range $\mathbb{Q}(a,b)$** | **integral** | **averaged** |

This is why the strategy is built on **range-versus-bracket** comparisons.
Kalshi's brackets *are* ranges, so the comparison is like-for-like and lands on
the most numerically robust quantity available. It also routes the estimate
through the region where measurement is strongest.

*Correction (October 2026, `FINDINGS_LEGCOUNT.md`).* Not every ICE-settled WTI
ladder is a range ladder. KXWTI, the daily series, is a **threshold** ladder
("Above $X", 3,082 markets since January 2026), and its digital is $D(a)$ alone
— one survival-function evaluation and **two option legs**, half the spread
crossing and half the fees of a four-leg bracket. An earlier brief had put
threshold markets with the hourly and Pyth-settled series as unhedgeable; that
was an error, and the daily ladder is in the backtest as the cheaper structure.
On the contract Kalshi references: it is the month named in `rules_primary`
(from June 2026); before that, the settlement values show the switch one to
four business days before the NYMEX last trading day, not on the 16th as this
project's docs once said, and the backtest checks every date's assignment
against the realised settlement.

### Stage 17 — Compare like with like

Integrate the posterior over Kalshi's **exact** bracket edges. Gap for bracket
$j$: $g_j = p^{\text{mkt}}_j - \bar p^{\mathbb{Q}}_j$.

### Stage 18 — Decompose the gap by fingerprint

With ~25 brackets there are enough points to separate the two innocent causes.
Fit, per posterior sample:

$$\text{logit}\big(p^{\text{mkt}}_j\big) = a + b\cdot\text{logit}\big(p^{\mathbb{Q}}_j\big) + c\cdot m_j + \varepsilon_j$$

where $m_j$ is the bracket midpoint (a state variable).

- **$b < 1$ is exactly the favorite–longshot bias.** For a longshot,
  $\text{logit}(p)$ is very negative; shrinking by $b<1$ makes it less negative,
  so $p^{\text{mkt}} > p^{\mathbb{Q}}$ — longshot overpriced. For a favorite it
  works the other way. The whole bias in one parameter.
- **$c \ne 0$ is the risk-premium tilt** — monotone in the state, which is what
  a pricing kernel does to $f^{\mathbb{P}}$ to produce $f^{\mathbb{Q}}$.

Running it per sample gives a *distribution* over $(a,b,c)$, so "is $b$
meaningfully below 1?" is answerable with a credible interval.

**When this is mandatory.** In a perfectly hedged trade held to settlement it is
not needed — both legs resolve on the same number and you keep the gap whatever
caused it. It becomes mandatory when the hedge is imperfect (which, with
discrete strikes, it always is), because then you retain residual exposure and
need to know whether you are harvesting a bias or **selling insurance**.

### Stage 19 — The trade filter

$$\text{trade bracket } j \iff |g_j| \;>\; \underbrace{\text{band}_j}_{\text{posterior spread}} + \underbrace{\text{friction}_j}_{\text{fees + spreads, both legs}}$$

## Act V — execution

### Stage 20 — Building the bracket digital

A Kalshi bracket is a digital paying $1 if $a \le F_T < b$. Replicate from
options.

A single digital at $K$ is the limit of a call spread:

$$D(K) = \lim_{\varepsilon\to 0}\frac{C(K-\varepsilon)-C(K+\varepsilon)}{2\varepsilon} = -\frac{\partial C}{\partial K} = e^{-rT}\,\mathbb{Q}(F_T>K)$$

**The loop closes:** Stage 2's first derivative, the price of a digital, and the
discounted probability are the same object. The bracket digital is
$D(a) - D(b)$ — **four option legs**.

Two consequences that cannot be designed away:

**The ramp.** $\varepsilon$ cannot go to zero because strikes are discrete. The
hedge has a finite ramp where Kalshi pays a sharp $1-or-$0 while the spread
pays something in between. Inside the ramp the legs do not cancel. Narrower
ramp means better hedge but more contracts and more fees — a design parameter,
and the residual that sets real max loss.

**Granularity.** A standard CL option covers 1,000 barrels, so a $0.50-wide
spread has max payoff $500 — one structure hedges ~500 Kalshi contracts. Micro
(100 barrels) brings that to ~50. You cannot trade a fraction of an option, so
this sets the minimum hedged unit and therefore the depth required on the thin
leg.

---

# 5. Trade structure

## 5.1 Case 1 versus Case 2

**Case 1 — both legs, held to settlement.** Sell the option structure, buy the
Kalshi bracket, hold. At settlement both resolve on the same number and cancel;
you keep the gap **regardless of what caused it.** You never need to know P or
Q. This is the design target.

**Case 2 — use the options number as "truth" and bet Kalshi directionally.**
The trap. If options imply 10% and Kalshi shows 6%, buying Kalshi looks like 4
points of edge — but if the real probability was 6% and the 10% was inflated by
hedging demand, you have **zero edge while believing you have four points**, and
you would size accordingly.

The decision is to build for Case 1 exclusively. This has a cost: Case 1 is
harder (four option legs, two spreads, margin, discrete-strike ramp, matched
settlement) and the frictions push toward Case 2. Resisting that drift is a
standing discipline, not a one-time choice.

**Note on the intraday variant.** "Enter and exit before close, no overnight
risk" quietly assumes you *can* exit. On a thin prediction-market book the exit
may not exist, and the force that guarantees convergence only fires at
settlement. An intraday plan on a thin book silently becomes hold-to-settlement
anyway — but unhedged and unplanned. Size as hold-to-settlement; treat early
exit as a bonus.

## 5.2 The residual, and how to size

With discrete strikes the hedge always has a ramp. If the position is
systematically short the CME tail and long the Kalshi tail, the retained
residual is **exactly the exposure the hedging premium was compensating** —
which makes it insurance-selling with a mostly-effective hedge, not arbitrage
with a rounding error.

Two sizing rules, fixed now while there is no money on the line:

1. **Size as hold-to-settlement.** Assume no early exit.
2. **Size for the unhedged residual, not the locked gap.** Model the worst case
   where settlement lands inside the ramp and the legs do not offset. That,
   plus any settlement basis, is real max loss.

## 5.3 Why the entity structure is not needed

The original plan (BVI parent, Delaware subsidiary) existed to reach offshore
venues that exclude US persons. **Both legs here are US-regulated** — Kalshi is
a CFTC-designated contract market, CME is CME. Tradeable as an individual with
a futures-enabled account.

Latency infrastructure is also unnecessary: this is a hold-to-settlement trade
on weekly contracts, not a speed race. fedarb measured wedge decay in ~20
minutes.

---

# 6. Empirical findings to date

## 6.1 Within-venue arbitrage: ruled out

Kalshi RANGE ladders are mutually exclusive and exhaustive, so exactly one
bracket pays $1. If the asks sum below 100¢ you buy the whole ladder for a
locked profit.

**Measured on KXWTIW (27 brackets): ask sum = 127.0¢** against a 100¢ payout.
That is exactly 100 + 27 × ~1¢ spread — pure spread cost, no anomaly. Ladder
arbitrage is dead, as expected, and it cost five minutes to establish.

**Methodological note:** an earlier scan reported 47 "arbitrage" signals, all
false positives from summing **cumulative** ladders. A cumulative ladder ("Above
$89.99", "Above $90.09", …) is nested, not exclusive, and does not sum to 100.
The correct check there is monotonicity — $\mathbb{Q}(>t_1) \ge \mathbb{Q}(>t_2)$
for $t_1 < t_2$ — which found 3 violations across 78 cumulative ladders, all
untradeable (sizes of 1, 2, and 100 contracts).

Kalshi's event objects carry `mutually_exclusive` as a boolean, which
distinguishes the two definitively. Inferring it from label text was the error.

## 6.2 Depth: the fedarb killer, cleared at Micro size

Live orderbook scan of KXWTIW moderate-tail brackets (5–20¢, where the
favorite-longshot bias should live):

| bracket | bid | resting size |
|---|---|---|
| Above $95.99 | 13¢ | 5,284 |
| $94.00–94.99 | 5¢ | 1,556 |
| $93.00–93.99 | 7¢ | 1,131 |
| $89.00–89.99 | 8¢ | 1,071 |

All nine moderate-tail brackets cleared 50 contracts on both sides with **zero
slippage** and 1–2¢ spreads. At 500 contracts the ask side failed in 6 of 9.

**This decides the contract: Micro WTI.** Not a preference — the data says
standard CL cannot fill the minimum hedged unit on the offer side.

Contrast with fedarb, where the minimum hedged unit ate 2¢ of depth on the
first snapshot. This is the first time the depth gate has cleared.

**Important caveat:** one snapshot at one instant. Depth must be sampled across
a session before this is a conclusion.

## 6.3 Settlement sources: the finding that constrains everything

Kalshi's event objects carry `settlement_sources`, stating what the exchange
settles against:

| series | settles on | ladder | implication |
|---|---|---|---|
| KXWTIW (weekly) | **ICE** WTI Crude Futures | RANGE | hedgeable, but cross-exchange basis |
| KXWTI (daily) | **ICE** WTI Crude Futures | CUMUL | same |
| KXBRENTD | **Pyth** — Brent | CUMUL | aggregated oracle index |
| KXGOLDD | **Pyth** — Gold | CUMUL | aggregated oracle index |
| KXNATGASD | **Pyth** — NATGAS | CUMUL | aggregated oracle index |

**On the ICE finding.** Kalshi settles WTI on ICE; a tastytrade account reaches
CME Group (CME, CBOT, NYMEX, COMEX) but **not ICE**. So the natural hedge is a
NYMEX CL option against an ICE-settled contract — same oil, same month, same
nominal settlement time, different exchange and different settlement procedure.
That leaves a residual whose size is unknown and must be measured.

**On the Pyth finding.** Pyth is an oracle network. Its commodity feeds do track
front-month futures, and options on Brent, gold, and natural gas are among the
most liquid in the world — so these are *not* ruled out. But an aggregated 24/7
index and a specific contract's daily settlement are different random variables,
and that basis is likely wider and less stable than ICE-vs-NYMEX. Requires
reading `rules_primary` per series to determine what is actually referenced.

**On the expiry mismatch.** ICE contracts expire one day before the
corresponding CME contracts. A naive pairing would leave one day of unhedged
exposure — roughly $87 × 0.35 × \sqrt{1/252} \approx \$1.92$ of one-sigma
movement against a **$1-wide bracket**, which would dominate everything.

**The fix is structural, not analytical:** CME lists WTI weeklies expiring every
day of the week. Selecting the weekly that expires on Kalshi's settlement date
eliminates the timing gap entirely. What remains is the cross-exchange basis
only. *(A model of the one-day gap would be the wrong response — it would not
remove the exposure, only make carrying it feel justified.)*

## 6.4 Data availability: the sample is much smaller than it appears

KXWTIW has 201 events reaching back to December 2024. Coverage by month:

| month | brackets | zero-candle | % live | total candles |
|---|---|---|---|---|
| 2025-08 | 75 | 69 | 8% | 11 |
| 2025-09 | 45 | 42 | 7% | **8** |
| 2025-10 | 45 | 35 | 22% | 20 |
| 2025-11 | 15 | 11 | 27% | 10 |
| *(gap — no events 2025-12 to 2026-04)* | | | | |
| 2026-05 | 49 | 0 | **100%** | 207,491 |
| 2026-06 | 60 | 0 | **100%** | 113,632 |
| 2026-07 | 99 | 0 | **100%** | 281,973 |
| 2026-08 | 108 | 0 | **100%** | 205,328 |

Investigated directly: those 2024–25 markets have **total lifetime volume of
5.00 contracts** and return 404 on candlesticks. They existed and never traded.

**Implication: the usable backtest window is roughly 19 weekly events over five
months, not 201.** You cannot extract a comparison from a ladder where 90% of
brackets never quoted.

This matters twice. It scopes the Databento purchase to ~19 specific dates
rather than four years. And it sets an honest expectation about statistical
power: brackets within an expiry share a density and consecutive weeks share a
regime, so effective sample size is closer to 19 than to 500. **That is enough
to detect a large persistent effect and not enough to detect a subtle one** —
worth deciding what would be convincing *before* seeing results.

**The daily series (KXWTI, 837 events) reach the same window with ~5× the
observations**, at the cost of a much harder extraction: at one day to expiry
$\sqrt T$ is tiny, so vega collapses across the *whole* chain and the price
curve approaches a kinked hockey stick.

---

# 7. Engineering notes

Documented because four data-collection attempts failed on these, each
producing output that looked successful.

**Kalshi API.** No authentication required for market data. Live host
`api.elections.kalshi.com/trade-api/v2`; archived
`external-api.kalshi.com/trade-api/v2/historical` — but host routing is not
reliable (a finalized July market was served by *live* and 404'd on
*historical*).

**Candlestick cap is 5,000 per request, not 10,000.** Exceeding it returns HTTP
400. Every 1-minute request for a week-long market failed while the collector
logged success.

**OHLC fields are `*_dollars` suffixed decimal strings**, not bare keys.
Reading `block["close"]` returns `None` for every row — producing a table where
every bid and ask was null, which passed a row-count-based smoke test. Also
`volume_fp` / `open_interest_fp`.

**Orderbooks return bids only, on both sides.** A YES bid at 7¢ is a NO ask at
93¢, so `yes_ask = 100 − best_no_bid`. Treating the raw book as yes-bid/yes-ask
produces garbage spreads.

**Paging must run until the cursor empties.** A 40-page cap truncated KXWTI at
exactly 8,000 markets; raising it revealed 10,813. A count landing on an exact
multiple of the page size is a truncation warning.

**Authoritative fields exist and should be used rather than inferred:**
`mutually_exclusive` (ladder type), `settlement_sources`,
`custom_strike.front_month_contract`, `expiration_value` (realized settlement —
free backtest ground truth), `result`.

**Storage: parquet, not CSV.** CSV loses types; the same column was inferred as
Integer in one file and Float in another across earlier exports. **Bid and ask
must be stored separately — never a mid.** A stored mid permanently destroys the
half-spread that drives Stage 9 weights and the Stage 13 likelihood.

**A manifest must distinguish "request failed" from "no data exists."**
Recording both as `rows: 0` makes a network outage indistinguishable from a
never-traded market and prevents resume from retrying real failures.

---

# 8. Where the project stands

## Complete

- Theoretical pipeline specified end to end (20 stages)
- Ladder arbitrage tested and ruled out
- Depth verified at Micro size on moderate-tail brackets
- Settlement sources identified for five series
- Data availability mapped; usable window established
- Collection tooling debugged through four failure modes

## In progress

- Historical Kalshi collection across five series at 1-minute resolution

## Next, in order

1. **Read `rules_primary` per series** — determines what Pyth-settled markets
   actually reference, and whether Brent/gold/natgas remain candidates.
2. **ICE/NYMEX basis test.** Using `expiration_value` (realized ICE settlements,
   already captured) joined to public NYMEX CL settlements on the same dates.
   Measure the **distribution** of the difference — mean, standard deviation,
   tails. *Not correlation*, which will be ~0.999 and tell you nothing. A
   persistent mean offset shifts every bracket the same way; the standard
   deviation is unhedged noise on a $1-wide instrument.
3. **CME weekly calendar check** — which weekly expires on Kalshi's settlement
   date, and which futures month it exercises into.
4. **Build the extractor against synthetic data.** Plant a known density,
   generate a chain, add realistic noise, verify recovery *with error bars that
   cover the truth at the stated rate*. This is the only stage where "my code is
   broken" and "the market is interesting" are distinguishable, and it is
   independent of every settlement question above.
5. **Scoped Databento purchase** — only after 1–3 identify a viable pair, and
   only for the ~19 dates that have usable Kalshi coverage. Use `bbo-1m`
   (needs bid and ask separately, and one-minute matches the Kalshi resolution);
   `stype_in="parent"` for whole-chain requests; cost-preflight every pull.
6. **Aligned backtest** on executable prices, never mids.
7. **One minimum-size live trade** before any scaling — to test what no
   simulator can: actual fill prices, the lag between the two legs, real margin,
   and whether settlement resolves as expected.

## Open items owned by the operator

- Hedge ratio derivation (deliberately not delegated)
- Depth sampled across a session rather than one snapshot

---

# 9. Standing methodological commitments

Stated explicitly because each was learned by getting it wrong.

1. **A gap is not an edge.** Part of any cross-venue disagreement is a risk
   premium that is supposed to be there.
2. **Error bars are the deliverable**, not the density. A point estimate cannot
   distinguish signal from measurement noise, and the tails — where the
   tradeable bias lives — are where measurement is weakest.
3. **Executable prices only.** Never mids, never displayed percentages. The
   orderbook is the only source of truth.
4. **Measurement artifacts look exactly like edges.** Smooth, persistent, and
   sign-consistent. Every stage carries a diagnostic aimed at this.
5. **Structural fixes over analytical ones.** Matching expiry dates beats
   modelling the gap; SVI constraints beat post-hoc arbitrage repair;
   $\exp(\phi)$ beats rejecting negative densities.
6. **Capacity is checked before cleverness.** fedarb was correct and
   untradeable. Depth on the thin leg gates everything.
7. **Verify, do not infer.** `mutually_exclusive`, `settlement_sources`, and
   the API's own field names were all available and all initially guessed at,
   producing false positives and silent data loss.
