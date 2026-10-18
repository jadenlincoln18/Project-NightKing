# Project NightKing — A Pedagogical Treatment

## Cross-venue density arbitrage: extracting risk-neutral distributions from options chains and trading them against prediction-market bracket ladders

**Author:** Alfred (for Jaden Patel) **Companion to:** `/Users/patel/Desktop/PROJECT_NIGHTKING_writeup.md` (Jaden's own writeup — the ground truth) **Repo:**
`/Users/patel/.openclaw/workspace/Project-NightKing/` **Predecessor project:** *fedarb* (Kalshi Fed-rate vs ZQ, 2026). See `kalshi-arb-overnight-brief.md` and `Jadens_equations.md` for the historical
fedarb work that NightKing supersedes. **Status:** pre-backtest. Data collection in progress. No capital deployed. **Target reader:** a bright college quant-club member or finance-adjacent friend who
has seen calculus and basic probability but has not necessarily seen options, prediction markets, Markov chain Monte Carlo, or ill-posed inverse problems. If that describes you: read straight through.
If you already know parts, skip freely — every section is self-contained enough to survive being read out of order.

---

# Table of contents

-  **Part 0** — Prologue: what died, what changed, and why
-  **Part 1** — The thesis: two venues, two probability estimates, and why they should disagree
-  **Part 2** — Theoretical foundation (P vs Q, martingale property, Breeden–Litzenberger, the three consistency checks)
-  **Part 3** — Why the naive approach fails (catastrophic cancellation, bias-variance, the ill-posed inverse problem)
-  **Part 4** — The extraction pipeline: 20 stages in 5 acts
-  **Part 5** — Trade structure (Case 1 vs Case 2, sizing, contract selection)
-  **Part 6** — Empirical findings to date
-  **Part 7** — Engineering notes (the debugging archaeology)
-  **Part 8** — Where the project stands, next steps
-  **Part 9** — Standing methodological commitments
-  **Part 10** — Glossary / notation reference

---

# Part 0 — Prologue: what died, what changed, and why

## 0.1 The one-sentence version

NightKing is what you build after you've run one arbitrage strategy to completion, found a real edge, and had it die on you for reasons that were invisible until the last five minutes of the project.
Everything about NightKing's design — the pipeline, the discipline, the empirical checks that happen before any capital moves — is a direct response to a specific way *fedarb* failed. This prologue
exists so that when you read Part 4 and wonder why some stage is doing what looks like extra work, you can trace it back to the failure mode it exists to prevent.

## 0.2 fedarb, in one page

**The trade.** Kalshi lists prediction-market contracts on FOMC decisions: "Will the Fed raise rates by 25 bps at the September meeting?" These contracts pay $1 if yes, $0 if no, so their price *is* a
probability. Meanwhile CME lists 30-day Fed Funds futures (ticker ZQ), and the settlement price of those futures is a linear function of the arithmetic average of the effective Federal Funds rate for
that calendar month. From a ZQ futures price you can back out the market-implied *expected* rate for the meeting month, and from that expected rate you can construct a probability distribution over
the FOMC decision under a two-state assumption (either they hike by X or they don't).

The trade: if the ZQ-implied probability of a hike disagrees with the Kalshi price for that same event, and the disagreement exceeds transaction costs, buy the cheap side and sell (or replicate) the
expensive side against the other venue.

**The build.** 41 unit tests. 35 historical FOMC meetings ingested. 390,000 aligned minutes of tick-level Kalshi + ZQ data. Every input verified against the raw API. A settlement mechanism for both
sides. Full backtest logic.

**The finding.** A real, persistent, slow-decaying wedge. Kalshi priced aggressive rate-move outcomes about 4 cents *below* their ZQ-implied fair value, sign-consistent 92% of the time across
meetings, with a median half-life around 20 minutes for the wedge to close.

**The cause of death.** Capacity, not correctness. The natural hedge ratio came out to about 1,042 Kalshi contracts per ZQ futures contract, because one ZQ contract is worth about
$41.67 per basis point and one Kalshi contract is a $1 digital. When Jaden actually looked at the Kalshi order book at that size — the *first* live snapshot he took — the depth cost 2 cents on the
round trip, against a 4-cent signal. Eight FOMC meetings a year, friction roughly equal to signal, so after fees, spreads and any settlement basis, expected P&L was indistinguishable from zero.

That is a strategy that is *correct* — the wedge is real, the sign is right, the diagnostics were clean — but *untradeable*. It was an expensive lesson, and this project is the follow-through.

## 0.3 The three lessons NightKing inherits

Read this list before anything else. Each of the three lessons below is the seed of a specific design choice you'll see recur throughout Part 4. They are not "things Jaden feels strongly about." They
are things that were learned by getting them wrong.

### Lesson 1 — A scalar comparison cannot be diagnosed

fedarb compared one number to one number: Kalshi's implied probability for "25 bps at September" versus ZQ's implied probability for the same event. It found a gap. When a gap of that kind exists,
there are always at least three non-rival explanations:

1.  **Mispricing** — one venue is genuinely wrong, and the gap is edge.
2.  **Risk premium** — the two venues have different marginal investors, so the fair prices under their respective *pricing kernels* are actually different, and the gap is not edge, it is a risk
   premium that is supposed to be there.
3.  **Measurement artifact** — the extraction procedure itself (two-state assumption, contract contamination from adjacent months, $F_0$ sourced from the wrong screen) produces a smooth, plausible,
   sign-consistent gap without any real mispricing at all.

With a scalar comparison — one observation, three candidates — you cannot distinguish. The analysis ends in a shrug, as it should.

**The structural fix in NightKing:** compare a *distribution* to a *ladder*. Kalshi ladders typically have around 25 brackets over the price axis of weekly WTI. That's 25 comparison points, not one.
The three candidate explanations produce **differently shaped fingerprints** across the 25 brackets:

-  **Mispricing** is idiosyncratic across brackets — not a function of any particular variable.
-  **Risk premium** is state-monotone: it produces a smooth lean across the brackets because the pricing kernel is a smooth function of the terminal price.
-  **Favorite–longshot bias** is symmetric in probability: it puffs both tails and thins the middle, because it's a function of $p$ rather than of the underlying state.

Different coordinates. That is the entire reason NightKing works on distributions rather than on scalars — with enough brackets and the right regression, the three explanations become separable. Part
4, Stage 18 makes this concrete: you run a per-sample logit regression of Kalshi bracket probabilities on the extracted risk-neutral probabilities plus a state variable, and read the two innocent
effects off the coefficients.

### Lesson 2 — Measurement artifacts are the dangerous failure mode

fedarb's raw pooled wedge showed a −8 percentage-point average difference before diagnostics. The final diagnostics traced most of that to *measurement breakdown*, not to a real edge:

-  The two-state assumption ("either they hike by X or they don't") was violated by 2022's 50-and-75 basis point moves, which forced probability mass into a residual bucket that the estimator hadn't
  been designed to handle.
-  Contract contamination from the following month's meeting bled into the numbers because Fed Funds futures settle on the arithmetic *monthly* average and a meeting late in the month gave a contract
  price influenced by rates set at the *next* meeting.

The critical observation: those measurement failures **produced a smooth, sign-consistent, plausible-looking wedge**. They looked *exactly* like an edge. This is the general phenomenon that has to be
internalized before you extract risk-neutral distributions for money:

>  A mis-specified extraction that fails silently looks indistinguishable from a genuine edge to any diagnostic that isn't specifically hunting for the extraction failure.

The mis-centred density is the archetype. If your extracted density's mean lands 20 cents below the true forward, it is smooth, convex, normalized, passes every automated check — and it disagrees with
every single Kalshi bracket in the same direction by the same amount. That looks like a persistent, sign-consistent edge. It is a bug in Stage 6.

**The fix in NightKing** is not one check. It is a discipline: **every stage of the pipeline carries a diagnostic aimed at some specific extraction-failure mode.** Convexity as a proxy for
non-negativity; normalization as a truncation check; mean-equals-forward as a location check; the martingale constraint in the MCMC likelihood; convergence diagnostics on the sampler; the SVI
arbitrage bounds in the optimizer. The measurement-artifact warning appears at every stage where it matters. It is not an appendix.

### Lesson 3 — Mid-vs-executable is not a detail

fedarb measured a 3.1-cent average gap between mid prices (the midpoint of bid and ask) and executable prices (the price you actually get if you cross the spread and take liquidity). If you run a
backtest on mids, you are measuring an edge that you cannot capture. On a 4-cent signal, 3.1 cents of mid-vs-executable gap is fatal.

This is one of the oldest known ways to fool yourself in quantitative finance, and it is worth restating it in the general form: **any quoted price that is not the price at which you can actually
transact is a fiction that looks like data.** Bid-ask midpoints, last-trade prices, index values, implied prices computed from other prices — all fiction, in this sense, and none of them are the
number your P&L will be denominated in.

**The fix in NightKing** is a standing commitment: any backtest, any diagnostic, any live signal will use executable prices only. Storage is built to preserve bid and ask separately, never a mid (see
Part 7 and `kalshi_common.py`'s comment "Bid and ask must be stored separately — never a mid. A stored mid permanently destroys the half-spread"). The liquidity check in Part 6.2 is on live order-book
depth, not screen sizes. The Stage 19 trade filter uses half-spread cost, not mid-to-mid difference.

## 0.4 The pivot: distributions vs ladders, not scalars vs scalars

The change from fedarb to NightKing is one idea deep, and everything downstream is the consequence of taking it seriously. The change:

>  Compare a **continuous probability distribution** implied by one venue to a **discretely-bracketed ladder** on another venue.

The distribution is extracted from an options chain via Breeden–Litzenberger. The ladder is a Kalshi RANGE market (brackets like "WTI settles between $87.00 and $87.99"). You integrate the extracted
density over each Kalshi bracket's edges, get a probability per bracket, and compare against the Kalshi price of that bracket.

The consequence is that you now have a *vector* of comparisons instead of a scalar. You get 20-ish independent tests of the disagreement, and the different innocent causes leave different fingerprints
across them, so a regression can separate them. That is the single most important design change from fedarb to NightKing.

Everything else — the SVI smile fit, the exp-basis density parameterization, the Bayesian MCMC on the extraction, the martingale constraint, the range telescoping, the four-leg digital replication —
is engineering in service of that pivot. Each stage exists because *some specific way of doing the comparison naively* is either too noisy or too biased to trust.

Read Part 4 with that in mind: every stage is either (a) making the density robust, (b) making the density's error bars real, or (c) protecting against a measurement artifact that would otherwise fool
you.

## 0.5 What this document is and isn't

**Is:** a pedagogical companion to Jaden's writeup. Every equation gets intuition alongside the derivation. Every design choice is traced to the failure mode it addresses. Every stage is
cross-referenced against the actual code in `Project-NightKing/` when relevant. The reader should finish this document able to read Jaden's writeup, read the repo, and understand *why* everything is
where it is.

**Isn't:** a claim that NightKing works. It is pre-backtest. It has not deployed capital. It rests on assumptions (in particular, that some combination of institutional risk premium and retail
favorite-longshot bias produces a tradable, stable cross-venue disagreement on WTI weekly brackets after fees) that are not yet empirically confirmed. Every part of the writeup preserves the caveats
from Jaden's original — one snapshot of depth, sample size smaller than headline count, unmeasured ICE-vs-NYMEX basis — and does not soften them.

---

# Part 1 — The thesis

## 1.1 The setup

Two venues quote something about the same underlying event.

**Venue A — CME options chain on WTI crude futures.** The chain lists calls and puts across many strikes on a specific WTI weekly futures contract (one that expires on a particular Friday). Each option price is what someone paid, right now, for the right to a specific payoff at expiry. Collectively, all the option prices at all the strikes contain — in a precise mathematical sense — the market's entire probability distribution over where the futures contract will settle. That distribution is not some subjective belief about the world; it is a construct extractable from prices by a formula called *Breeden–Litzenberger* (Part 2, §2.5).

**Venue B — Kalshi RANGE ladder on WTI weekly settlement.** Kalshi lists a ladder of price brackets — twenty-something of them — for the *same* weekly settlement event as the CME options. Each bracket is a contract that pays $1 if the settlement price lands in that bracket, and $0 otherwise. It's a digital option, priced in the range $0.00 to $1.00, and the quoted price is (up to a small subtraction for the exchange fee and market spread) the market's implied probability that the settlement will land in that bracket.

**So you have two independent probability estimates of the same event.** Not one probability compared to one probability — 20-something Kalshi bracket probabilities compared to 20-something integrals of the Breeden–Litzenberger density over those same bracket edges.

## 1.2 Why should they disagree at all?

You might think: if both venues price the same event, both are quoting prices, and both are (presumably) driven by rational agents responding to new information, then in equilibrium the two probability vectors should be identical up to bid-ask friction. What is there to trade?

The answer is that both venues quote prices under the *risk-neutral* measure $\mathbb{Q}$, not the real-world probability $\mathbb{P}$. Neither of them is quoting real-world beliefs. Both are quoting
the effective probability implied by *prices*, which by construction incorporates each venue's marginal investor's risk aversion, hedging needs, and information set. Under the assumption of a single
frictionless integrated market, all venues would price under the same $\mathbb{Q}$ and there would be no gap.

**But the market is not integrated.** The two venues have structurally different marginal investors:

-  **CME options** on WTI crude are dominated by institutional participants — energy producers, refiners, airlines, oil-service companies, and the professional market makers who intermediate for them.
  These participants have real physical exposure to the price of crude, and they buy or sell options as a hedge for physical positions. They pay above the actuarially fair price for that hedge,
  because paying a hedging premium is cheaper for them than carrying the exposure.

-  **Kalshi WTI-bracket contracts** are dominated by retail participants, many of them making directional bets on where oil settles this week based on a Bloomberg headline or a Reddit thread. There is
  no meaningful institutional flow at the Micro sizes the venue supports (that is a key empirical claim, verified in Part 6).

These two populations do not arbitrage each other. There is a partial regulatory wall — Kalshi is a CFTC-designated contract market, but the size at which anyone can trade there in practice is small
enough that professional arb desks don't bother; the operational overhead of integrating a new venue for a low-capacity edge exceeds the P&L. Anyone who trades one venue actively doesn't trade the
other. Hence the two venues sustain **different effective pricing kernels**, and the barrier between them keeps that difference from being arbed away.

That is the *segmentation thesis*. It is a stronger foundation for a strategy than "one of them is wrong," because it doesn't require anyone to be wrong. It requires only that the two populations
pricing the same event are different enough that their equilibrium prices differ.

## 1.3 Two forces, two fingerprints

The segmentation thesis is directional but not specific. It says disagreement should exist; it doesn't say what shape the disagreement should have. To be able to actually *trade* the disagreement, you
need to know what fingerprint each innocent cause leaves, so you can distinguish "cross-venue effect I intend to harvest" from "measurement bug I want to find and fix."

Two forces should drive most of the disagreement. They come from opposite sides of the venue split.

### Force 1: Institutional risk premium (CME side)

Commercial hedgers on the CME side pay a **hedging premium** — they pay above fair value for the option that hedges their physical position. Different players hedge in different places on the strike
axis. In WTI specifically:

-  **Refiners and airlines** buy upside protection (calls) on crude, because if crude prices spike, their input costs rise and their margins compress. To lock in a maximum input cost, they buy OTM
  calls on crude, and they pay above fair value for those calls because doing so is cheaper than the exposure to a price spike.
-  **Producers** buy downside protection (puts), similarly.

The net effect is that **out-of-the-money options on both sides carry a hedging premium**, but the exact tilt depends on the balance of hedgers. In crude specifically, upside protection tends to
dominate, so OTM calls are the most inflated leg.

**Fingerprint of this force:** the distortion is *monotone in the state*. The pricing kernel that transforms the real-world density $f^{\mathbb{P}}$ into the risk-neutral density $f^{\mathbb{Q}}$ is a
smooth function of the terminal price $F_T$ — states in which money is scarce (a big crude spike, if you're an airline; a big crash, if you're a producer) get more weight under $\mathbb{Q}$ than under
$\mathbb{P}$. That produces a **smooth directional lean** across the strike axis, not a symmetric fattening of both tails. When you regress the Kalshi-vs-density gap against the bracket midpoint
(Stage 18), this force shows up as a nonzero *slope-in-state* coefficient.

### Force 2: Retail favorite–longshot bias (Kalshi side)

One of the most-documented patterns in betting markets, from horse racing to sports books to prediction markets, is the **favorite–longshot bias**: participants overpay for longshots and underpay for
near-certainties. The reasons are behavioral (bettors like the "big payoff" of a low-probability, high-multiple bet, so they systematically overpay for it; conversely, they get bored by low-multiple
bets on high-probability outcomes). The magnitude in commercial sports books is well-measured; in prediction markets like Polymarket and Kalshi it's been noted anecdotally and has structural reasons
to persist (the class of participants who trade there overlaps heavily with sports bettors).

**Fingerprint of this force:** the distortion is *symmetric in probability*. Both tail brackets (low-probability outcomes) get inflated. Middle brackets (high-probability outcomes) get discounted.
Whether the tail bracket is on the up-side or the down-side of the distribution doesn't matter — what matters is only that its probability is low. When you write

$$\text{logit}(p^{\text{mkt}}) = a + b \cdot \text{logit}(p^{\mathbb{Q}}) + c \cdot m + \varepsilon,$$

the favorite-longshot force shows up as $b < 1$ (see Stage 18 for why). That's what "symmetric in probability" means algebraically: the transformation is a shrinkage in logit space, not a location
shift.

### Different coordinates

The critical point about the two forces is that they live in **different coordinate systems.** The institutional risk premium is a function of the state $F_T$. The favorite-longshot bias is a function
of the probability $p$. These are not the same coordinate. A regression with both variables can distinguish them: the state-monotone effect loads on $m$ (the bracket midpoint), the
symmetric-in-probability effect loads on $b$ (the shrinkage in logit space).

That is *exactly* the structure that lets you separate them, and it is *exactly* what fedarb couldn't do with a scalar. This is the payoff of the whole "distributions vs ladders" pivot.

**Important caveat (preserved from Jaden's writeup, and worth stressing).** In the tails the two forces push in the *same direction* — both inflate low-probability outcomes on both sides of the
distribution — so they partially cancel rather than add. fedarb specifically found the institutional risk premium *dominating* the favorite-longshot effect: Kalshi priced aggressive rate-move outcomes
**below** their ZQ-implied level, which is the opposite sign from what a pure favorite-longshot prediction would suggest. That's consistent with the interpretation that the hedging premium on the CME
side was pushing option-implied probabilities of the aggressive outcomes *up* relative to Kalshi's more retail-driven prices, and the effect was stronger than the reverse push from favorite-longshot
on the Kalshi side.

**Whether crude behaves the same way is a fully empirical question.** The crude options market has different hedgers, different flows, and different retail attention than the Fed-rate futures market
did. NightKing does not assume anything about the sign of the effect. It's designed to identify whichever combination of the two forces is present in the data, cleanly enough that you can trade the
residual after they've been accounted for.

## 1.4 Why the whole distribution matters

Suppose for a moment that you tried to run NightKing on a *single scalar* comparison — say, the probability that WTI settles above $90 this week, computed both from the options chain (as one integral)
and from the Kalshi ladder (as a sum of relevant bracket prices). You would be back in fedarb-land. One number, no way to diagnose which of mispricing, risk premium, or measurement artifact is driving
any observed gap.

Now suppose you have 25 bracket comparisons. Suddenly you can do a regression. You can test whether the gap is *shaped* like a monotone lean across the state, or whether it's *shaped* like a symmetric
tail-fattening in probability, or whether it's *shaped* like idiosyncratic noise plus mispricing. The whole distribution matters because the *shape* of the disagreement is what tells you what's
causing it.

A closely related consequence: even after fitting for the two innocent forces, any *residual* gap that remains — the part of the disagreement not explained by state-monotone lean or
symmetric-in-probability shrinkage — is a candidate for real mispricing. That residual is what the strategy is trying to trade. And the credible interval around the residual (the *width* of the
posterior on the density, propagated through the regression) is what tells you whether the residual is large enough to survive the measurement noise plus transaction cost.

## 1.5 The "gap is not an edge" discipline

If there is one sentence to take away from Part 1, it is this:

>  A raw disagreement between two venues is not automatically an edge, because part of it is a risk premium that is supposed to be there.

This is the standing discipline that pervades every part of the strategy. When you see a smooth, sign-consistent gap between the two venues, your first hypothesis is not that you've found a
mispricing. Your first hypothesis is either that you've found the risk premium, or that you've found a bug in your extraction. Only after excluding both of those, and propagating uncertainty from the
extraction into the comparison, can you call what's left an edge.

This is the discipline that failed for fedarb the first time, and it's why the current design routes the extraction through a Bayesian pipeline whose output is a *distribution of possible densities* —
with real error bars — rather than a single point estimate that is confidently wrong.

---

# Part 2 — Theoretical foundation

This part is the mathematics that makes the whole strategy work. It's also the mathematics that the reader has to understand to appreciate why each stage of the pipeline exists. We build it up in the
order the pipeline uses it: risk-neutral measures, why they exist, and why they matter to this project (§2.1); the martingale property of futures under $\mathbb{Q}$ and its two immediate consequences
(§2.2); the master identity relating call prices to the density (§2.3); its first derivative and how that relates to a digital option (§2.4); its second derivative, the Breeden–Litzenberger identity,
and the butterfly intuition (§2.5); and the three consistency checks that any candidate density must satisfy (§2.6).

## 2.1 Risk-neutral pricing, and why it matters here

### The two probability measures

Two probability measures appear throughout options theory:

-  $\mathbb{P}$ — the **real-world (physical) probability** measure. This is what would-be forecasters try to estimate. It's the answer to "what is the actual probability that WTI settles above $90
  this week?" — a question about the world, not about prices.

-  $\mathbb{Q}$ — the **risk-neutral (equivalent martingale) probability** measure. This is *reality re-weighted* so that prices become plain discounted expected values under $\mathbb{Q}$.

These are two different measures on the same sample space. They agree on which events have zero probability (that's what "equivalent" means in "equivalent martingale measure") but they can disagree
substantially on the actual probabilities of individual events.

### Why $\mathbb{Q}$ exists

The reason $\mathbb{Q}$ exists at all is that pricing under risk aversion is *awkward*. Under $\mathbb{P}$, the fair price of an asset is not just its expected payoff — you have to subtract a risk
adjustment for the uncertainty:

$$\text{price under } \mathbb{P} = \mathbb{E}^{\mathbb{P}}[\text{payoff}] - \text{(risk adjustment)}.$$

The risk adjustment is a function of the risk aversion of the marginal investor, the correlation of the payoff with the investor's other wealth, and other properties of the utility function. Ugly.
Depends on things about the investor that you don't observe.

The mathematically clean move is to **absorb the risk adjustment into the probability weights.** Redefine the probabilities so that outcomes people hate (states of the world with low marginal utility
of wealth, i.e. bad states) get *more* weight than they deserve, and outcomes people love get *less* weight than they deserve. Then price is just a plain discounted expectation:

$$\text{price} = e^{-rT} \, \mathbb{E}^{\mathbb{Q}}[\text{payoff}].$$

No separate risk term. The risk aversion has not disappeared — it's been folded into the weights.

**This is not a trick. It's the fundamental theorem of asset pricing.** Under the assumption of no-arbitrage in an integrated market, an equivalent measure $\mathbb{Q}$ exists such that all discounted
price processes are $\mathbb{Q}$-martingales. That measure is *unique* if the market is complete (all payoffs are replicable by trading in the underlying assets), which is what makes Black-Scholes
give a single price for the option.

### What "risk-neutral" means concretely

Concretely: outcomes people pay to hedge against get *more* weight under $\mathbb{Q}$ than they deserve under $\mathbb{P}$. This is because when you're rational and risk-averse, you're willing to pay
above the actuarially fair price for insurance against bad outcomes, and that excess-over-fair is what the reweighting captures. From the perspective of prices, the "insurance-worthy" bad states are
systematically weighted up, and the "boring good" states are systematically weighted down.

**The wedge only opens for risk that correlates with states where money is scarce.** Diversifiable risk — risk that doesn't correlate with aggregate wealth or the state of the economy — earns no
premium. A fair coin's outcome is uncorrelated with anything the market cares about, so its $\mathbb{Q}$ equals its $\mathbb{P}$: both are 0.5 for heads. But a payoff that arrives *during a market
crash*, when investors' marginal utility of wealth is highest, is worth more than its odds — and $\mathbb{Q}$ reflects that by up-weighting the crash state.

This is a useful mental model for what makes crude oil interesting: periods of large crude spikes correlate with real macroeconomic pain (inflation, supply shocks, geopolitical stress), and hedging
demand for those states is real and large. So the $\mathbb{Q}$ vs $\mathbb{P}$ wedge in crude options is not just a theoretical construct — it's expected to be economically material, and it should
show up as inflated OTM call prices.

### The consequence for NightKing

Here is the point that determines almost everything downstream about the strategy:

>  **Breeden–Litzenberger extracts $\mathbb{Q}$, not $\mathbb{P}$.**

The identity relates the second derivative of the *call price* — a price — to a density. Because the price is what's being differentiated, and prices sit under $\mathbb{Q}$, the density that pops out
is the risk-neutral density $f^{\mathbb{Q}}$. There is no version of Breeden–Litzenberger that gives you $f^{\mathbb{P}}$.

**So a disagreement with a prediction market is *partly supposed to be there*.** If Kalshi is pricing more toward $\mathbb{P}$ (because its marginal participant is less risk-averse, or has different
exposures, or is compensating for a different risk than the CME side) and CME is pricing more toward its own $\mathbb{Q}$, the two probabilities differ for structural reasons. Neither is "wrong."
Neither has any obligation to be equal to the other.

You cannot treat the extracted $f^{\mathbb{Q}}$ as if it were $f^{\mathbb{P}}$ — as if it were the "true" probability of settlement — and interpret Kalshi's deviation from it as pure mispricing. That
is the single most common way to fool yourself in this class of strategy. The whole point of Stage 18 (the gap decomposition) is to give you a *statistical framework for separating the innocent
risk-premium effect from the tradeable residual*, without ever pretending you've computed $f^{\mathbb{P}}$.

## 2.2 The martingale property

### Statement

Under the risk-neutral measure $\mathbb{Q}$, a futures price is a martingale:

$$\mathbb{E}^{\mathbb{Q}}[F_T \mid \mathcal{F}_t] = F_t \quad \text{for all } t \le T,$$

where $F_t$ is the futures price at time $t$ and $\mathcal{F}_t$ is the information available at time $t$. In particular, taking $t = 0$:

$$\mathbb{E}^{\mathbb{Q}}[F_T] = F_0.$$

### Two-line derivation

The proof is one economic fact plus one line of algebra:

**Fact:** *Entering a futures contract costs nothing today.* Unlike buying a stock or paying for an option, opening a futures position requires no initial cash outlay (only a margin deposit, which is
a good-faith bond, not a purchase). Whatever the futures price does between now and expiry, your P&L is $F_T - F_0$ (per contract, long side), and neither party pays the other anything upfront to get
into the trade.

**Algebra:** Under $\mathbb{Q}$, the price of any tradable asset is the discounted expected payoff. So the price *today* of taking on the futures position (which pays $F_T - F_0$ at time $T$) must
equal $e^{-rT} \cdot \mathbb{E}^{\mathbb{Q}}[F_T - F_0]$. And that price is zero (fact above). Setting the two equal:

$$0 = e^{-rT} \mathbb{E}^{\mathbb{Q}}[F_T - F_0] \implies \mathbb{E}^{\mathbb{Q}}[F_T] = F_0.$$

Done.

### What the derivation does and doesn't require

Notice what the derivation *doesn't* invoke: it doesn't require any particular model of storage costs, convenience yield, dividends, or the shape of the forward curve. Those things determine *where*
$F_0$ sits relative to spot — the cost-of-carry relationship — but they don't affect the martingale property once $F_0$ is given. Whatever the market has set $F_0$ to, the risk-neutral expected value
of $F_T$ has to equal $F_0$, because otherwise you'd have a positive-expected-value trade at zero cost, which is arbitrage.

Contrast with a *spot* asset. Spot prices are not $\mathbb{Q}$-martingales: under $\mathbb{Q}$, spot drifts at the risk-free rate $r$ (or more generally, at $r$ minus any dividend yield or convenience
yield). $\mathbb{E}^{\mathbb{Q}}[S_T] = S_0 \cdot e^{rT}$ for a non-dividend stock. The reason is that holding spot ties up capital; the zero-cost- entry argument doesn't apply. Only *futures* are
martingales under $\mathbb{Q}$.

### Consequence 1: Black-76 rather than Black-Scholes

The standard Black-Scholes call formula assumes a spot underlying. The version for futures — sometimes called Black-76 or Black's formula for futures — has the $r$ inside the $d_1$ term deleted,
because the underlying's drift under $\mathbb{Q}$ is zero rather than $r$. The discount factor $e^{-rT}$ is still there (you still discount cash flows back to today), but the drift correction to the
log-moneyness disappears.

Black-Scholes:

$$d_1 = \frac{\ln(S/K) + (r + \tfrac12 \sigma^2) T}{\sigma \sqrt{T}}$$

Black-76:

$$d_1 = \frac{\ln(F/K) + \tfrac12 \sigma^2 T}{\sigma \sqrt{T}}$$

That single deleted $r$ is the entire difference between the two, and it comes directly from the martingale property. When you invert an option price on a *futures* underlying to get an implied
volatility, you have to use Black-76, or you'll get a systematically biased $\sigma$. Stage 7 implements Black-76 inversion for exactly this reason.

### Consequence 2: a free diagnostic

If you extract the risk-neutral density $f^{\mathbb{Q}}$ from the options chain, the martingale property gives you a *free consistency check*:

$$\int_0^\infty s \, f^{\mathbb{Q}}(s) \, ds = F_0.$$

The mean of the extracted density has to equal the forward. This is not an assumption; it's a theorem, and any extracted density that fails it by more than measurement noise is either wrong or
wrong-in-a-specific- diagnosable way (usually: the forward $F_0$ was sourced from the wrong place, or the extraction missed mass in one tail).

This is the single most useful diagnostic in the entire pipeline. §2.6 argues in detail why: a mis-centred density looks smooth and plausible by every *other* check, but it disagrees with every Kalshi
bracket in the same direction, and that looks like a persistent, sign-consistent edge — which is precisely fedarb's failure mode reincarnated. The mean-equals-forward check catches it before it
becomes a live trade. Stage 14 (the martingale constraint in the MCMC likelihood) enforces this check *during* the extraction, not just after.

## 2.3 The master equation

Everything the pipeline computes downstream is one identity, differentiated in various ways. The identity comes from writing out the price of a European call on the futures under $\mathbb{Q}$:

$$C(K) = e^{-rT} \, \mathbb{E}^{\mathbb{Q}}\big[(F_T - K)^+\big] = e^{-rT} \int_K^\infty (s - K) \, f(s) \, ds,$$

where:

-  $C(K)$ is the price today of a call struck at $K$ that expires at time $T$.
-  $F_T$ is the futures price at expiry — a random variable.
-  $(F_T - K)^+ = \max(F_T - K, 0)$ is the call's payoff at expiry.
-  $f(s)$ is the risk-neutral density of $F_T$, evaluated at $s$.
-  $e^{-rT}$ is the discount factor from time $T$ back to today.

### Reading the integral

The integral is a weighted sum over all possible values of $F_T$ above the strike $K$. For each possible landing price $s > K$, you take the payoff $(s - K)$, weight it by the probability density
$f(s) \, ds$ of landing near $s$, sum (integrate) over all such $s$, and discount back to today.

$s < K$ scenarios don't contribute to the integral because the call is worthless there — the max in the payoff is zero, and zero times any density is zero.

### What the master equation says about the strategy

The master equation is the bridge between two worlds:

-  The world of **options prices**, which is what CME quotes.
-  The world of **the underlying's probability distribution**, which is what NightKing needs to compare against Kalshi.

The equation says: *given the density, you can compute every call price by integration*. What Breeden–Litzenberger (Part 2, §2.5) does is run the equation in reverse: given the call prices, extract
the density by differentiation. The reverse direction is where all the numerical difficulty lives, which is what Part 3 is about.

For now: understand that the master equation is *exact* — it's a consequence of the definitions of risk-neutral price, call payoff, and density — and that everything downstream is derived from
differentiating it with respect to $K$.

## 2.4 First derivative — the survival function

### The derivation

Differentiate both sides of the master equation with respect to the strike $K$. Note that $K$ appears in *two* places: as the lower limit of integration, and as a term inside the integrand $(s - K)$.
So Leibniz's rule (the rule for differentiating an integral whose limits and integrand both depend on the differentiation variable) gives us two pieces:

$$\frac{\partial C}{\partial K} = e^{-rT} \Big[ \underbrace{-(s - K) f(s) \big|_{s = K}}_{\text{boundary term}} + \int_K^\infty \frac{\partial}{\partial K} \big[(s - K) f(s)\big] \, ds \Big].$$

The boundary term comes from the lower limit moving: as $K$ increases, the integration domain shrinks from below, so we subtract the integrand evaluated at the moving endpoint (with a minus sign
because the lower limit is being raised).

### The boundary term vanishes for a beautiful reason

$-(s - K) f(s) \big|_{s = K}$ has an extra factor of $(s - K)$, which is *exactly zero when $s = K$*. So the boundary term is zero. This is not luck; it's the whole point.

**Economic reading:** as you raise the strike by $dK$, the outcomes you stop counting in the integral are outcomes near $s = K$ — outcomes right at the money. But at exactly the money, the payoff
$(F_T - K)^+$ is zero. So the outcomes you stop counting were contributing nothing to the integral anyway. Dropping worthless outcomes costs you nothing.

More generally: whenever you're differentiating an integral whose integrand vanishes at the moving boundary, the boundary term drops out for free. Options theory is full of these — the whole trick of
the digital-option derivation, the call-spread limit, and the butterfly intuition all hinge on this cancellation.

### The interior term

Inside the integral, $s$ is a dummy variable (it's being integrated over), and $f(s)$ contains no $K$. So the only piece of the integrand that depends on $K$ is the factor $(s - K)$, whose derivative
with respect to $K$ is $-1$:

$$\int_K^\infty \frac{\partial}{\partial K} \big[(s - K) f(s)\big] \, ds = \int_K^\infty (-1) f(s) \, ds = -\big[1 - F(K)\big],$$

where $F(K)$ is the CDF of the density $f$ evaluated at $K$, so $1 - F(K) = \mathbb{Q}(F_T > K)$ — the survival function, i.e. the risk-neutral probability that $F_T$ ends up above the strike $K$.

Putting it together:

$$\boxed{\; \frac{\partial C}{\partial K} = -e^{-rT} \, \mathbb{Q}(F_T > K) \;}$$

### Interpretation

The minus sign is bookkeeping: $C$ is a *decreasing* function of $K$ (higher strike → less valuable call → lower price), while probabilities are positive, so their slopes have opposite signs.

**Economic reading, no calculus required.** Raise the strike by $\$1$. In every scenario where the option ends up in the money — every scenario where $F_T > K$ — the payoff is now exactly $\$1$
smaller. In every scenario where it ends out of the money, nothing changes. So the value lost per dollar of strike increase is $\$1$ times the probability of finishing in the money, discounted back to
today. That's exactly what the formula says.

### The tradeable object

Here's the thing about this first derivative that is *not* obvious from the calculus, and that makes it structurally important for the strategy:

>  **The first derivative is the price of a digital option struck at $K$.**

A digital option (also called a binary or cash-or-nothing option) is a contract that pays exactly $\$1$ if $F_T > K$ and $\$0$ otherwise. Its fair value is:

$$D(K) = e^{-rT} \mathbb{Q}(F_T > K) = -\frac{\partial C}{\partial K}.$$

So $-\partial C / \partial K$ isn't an abstraction — it's the market fair value of an instrument that exists on Kalshi. A Kalshi "above $K$" contract *is* precisely a digital option struck at $K$. The
survival-function first derivative is therefore not just a mathematical convenience; it is *the same object as the Kalshi bracket price*.

This is the "loop closes" moment that comes back explicitly in Stage 20. The way you replicate a Kalshi bracket digital using CME options is a combination of two of these first derivatives — one at
each bracket edge. And the reason the strategy can hedge is that the underlying options can be assembled into a portfolio that pays exactly the same digital payoff, modulo the discrete-strike ramp
discussed in Stage 20.

## 2.5 Second derivative — Breeden–Litzenberger

### The derivation

We now have

$$\frac{\partial C}{\partial K} = -e^{-rT} [1 - F(K)],$$

where $F$ is the CDF. Differentiate again. The constant $1$ has derivative zero, and $F'(K) = f(K)$ by the fundamental theorem of calculus:

$$\frac{\partial^2 C}{\partial K^2} = -e^{-rT} \cdot \big(-f(K)\big) = e^{-rT} f(K).$$

Rearranging:

$$\boxed{\; f(K) = e^{rT} \, \frac{\partial^2 C}{\partial K^2} \;}$$

This is the **Breeden–Litzenberger identity** (Breeden and Litzenberger, Journal of Business, 1978). It is the mathematical bridge that lets us extract the entire risk-neutral density from option
prices. Just take the second derivative of the call price with respect to strike, un-discount, and you have $f(K)$.

### Intuition via the butterfly

The second derivative can feel abstract. There is a beautiful option-portfolio interpretation that makes it concrete.

**Construct:** Buy one call at strike $K - h$. Sell two calls at $K$. Buy one call at $K + h$. This is called a **butterfly** (with $h$ as the "wing width").

**Payoff at expiry:** at $F_T \le K - h$, all three calls are worthless; payoff is 0. At $F_T = K$, the long $K - h$ call pays $h$, the two short $K$ calls pay zero, the long $K + h$ call is
worthless; payoff is $h$. At $F_T \ge K + h$, the long $K - h$ call pays $F_T - (K - h) = F_T - K + h$, the two short $K$ calls pay $-2(F_T - K)$, and the long $K + h$ call pays
$F_T - (K + h) = F_T - K - h$. Sum: $(F_T - K + h) - 2(F_T - K) + (F_T - K - h) = 0$. So the payoff is zero on both sides and $h$ in the middle: it's a **tent** centred at $K$, with height $h$ at the
peak and zero outside $[K - h, K + h]$.

**Price:** by no-arbitrage, the price today of this tent-shaped payoff is $C(K - h) - 2 C(K) + C(K + h)$. Note that this expression is exactly the **centred second difference** of the call price:
$C(K - h) - 2 C(K) + C(K + h)$ is the numerical formula for the second derivative, up to a factor of $h^2$.

**The identity in this language:** the price of a butterfly is approximately the probability of landing in the tent's window, times the tent's height:

$$C(K - h) - 2 C(K) + C(K + h) \approx e^{-rT} \cdot f(K) \cdot h^2.$$

Rearranging: $f(K) \approx e^{rT} [C(K-h) - 2C(K) + C(K+h)] / h^2$, which is the discrete Breeden–Litzenberger. **The tent literally *is* the second difference.** The math and the option portfolio are
the same object.

### Equivalent framing via curvature

Here's an equivalent way to see it that some people find more intuitive than the tent. Draw the call price curve $C(K)$ as a function of strike. Pick three consecutive strikes $K - h, K, K + h$ and
look at the middle price. Draw the chord connecting the two outer prices $(K - h, C(K - h))$ and $(K + h, C(K + h))$. The chord passes through the point $(K, (C(K-h) + C(K+h))/2)$ at strike $K$.

The middle price $C(K)$ sags *below* the chord by the amount $(C(K-h) + C(K+h))/2 - C(K) = [C(K-h) - 2C(K) + C(K+h)] / 2$, which is half the second difference.

Straight price curve ⟹ zero sag below chord ⟹ zero second difference ⟹ zero density. Curved (specifically, convex) price curve ⟹ positive sag below chord ⟹ positive second difference ⟹ positive
density mass.

The intuition here: **probability mass at a strike shows up as curvature in the call price around that strike.** If there's a lot of probability that the underlying lands near $K$, then options struck
right around $K$ are worth a lot compared to what a linear interpolation of neighbouring strikes would suggest, because that middle bracket of outcomes contributes to the value. Curvature is density.

### Why this is exact and yet computationally hard

The identity $f(K) = e^{rT} \partial^2 C / \partial K^2$ is *exact*. There is nothing approximate about it. Given a continuously differentiable call price function on a continuous strike axis,
Breeden–Litzenberger returns the density exactly.

The catch — the whole reason Parts 3 and 4 exist — is that in practice, you have neither a continuous strike axis nor an exact call price function. You have twenty or forty strikes, on a discrete
grid, with prices that are each uncertain by roughly a half-spread. Taking a numerical second derivative of noisy discrete data is famously ill-conditioned. That's Part 3.

## 2.6 The three consistency checks

Because the extraction is numerically fragile, the pipeline uses three consistency checks — three properties that any legitimate density must satisfy — to catch failures. Understanding what each check
does, and what failure mode it catches, is essential to understanding the pipeline's stages.

### Check 1: Convexity ⟺ non-negativity

A density is non-negative: $f(K) \ge 0$ for all $K$. Via Breeden–Litzenberger this is equivalent to $\partial^2 C / \partial K^2 \ge 0$, i.e. the call price must be a *convex* function of strike.

Geometrically: no matter which three consecutive strikes you pick, the middle price must lie at or below the chord connecting its neighbours. Equivalently, the price differences $C(K) - C(K + h)$ (how
much the price drops as you move one strike up) must be *decreasing* in $K$ — each successive move up costs you less than the last one.

**Why it matters.** This is the *no-butterfly-arbitrage* condition. A concave patch in the call price curve would mean a butterfly whose price is *negative*, which is a free portfolio that pays
$\ge 0$ at expiry — an arbitrage. That cannot survive in a liquid market: someone would put on the trade until the prices moved. So convexity is a property real markets enforce automatically.

**What it catches when it fails.** Non-convex call prices in your input data mean one of two things: (a) the raw quotes are broken (stale, outlier, wrong-side of the market), which is a data-cleaning
issue; or (b) your extracted density has negative regions, which is a fit issue. Stage 10 exists to make (b) structurally impossible via SVI parameter bounds, so any observed non-convexity in the
pipeline is a signal about (a).

### Check 2: Normalization

A density integrates to 1: $\int_0^\infty f(s) \, ds = 1$.

You can derive this directly from what we already have:

$$\int_0^\infty f(K) \, dK = e^{rT} \int_0^\infty \frac{\partial^2 C}{\partial K^2} \, dK = e^{rT} \big[C'(\infty) - C'(0^+)\big].$$

Using $C'(K) = -e^{-rT}[1 - F(K)]$:

-  $C'(\infty) = -e^{-rT} \cdot 0 = 0$ (a call with infinite strike has probability zero of being in the money).
-  $C'(0^+) = -e^{-rT} \cdot 1 = -e^{-rT}$ (a call with strike zero is certain to be in the money).

So $\int_0^\infty f(K) \, dK = e^{rT} [0 - (-e^{-rT})] = 1$. Normalized.

**Why it matters.** It's automatic given exact prices on the full strike axis, but in practice you have a *finite* grid that starts at some positive strike $K_{\min}$ and ends at some $K_{\max}$. Any
mass that should live outside $[K_{\min}, K_{\max}]$ is silently lost. If your grid is too narrow — if you truncate too aggressively in one or both tails — the integrated density will be less than 1
by whatever fraction of the mass you missed.

**What it catches.** A normalization check on the extracted density is a truncation diagnostic. If $\int f \, dK$ comes out to, say, 0.94, then 6% of the mass is outside your grid, and any probability
calculation you do will be systematically off by that amount. Stage 11 addresses this by extending the grid well past the outermost strike (Kalshi has "Below $70" and "Above $99" brackets whose
implicit widths reach far into the tails; mass has to exist there for the comparison to make sense).

### Check 3: Mean equals forward

The martingale property from §2.2 says $\mathbb{E}^{\mathbb{Q}}[F_T] = F_0$. So the mean of the extracted density must equal the forward:

$$\int_0^\infty s \, f(s) \, ds = F_0.$$

This is the check the pipeline treats as sacred, because it is the check that catches the specific failure mode that killed fedarb.

**Why it matters.** Consider the following scenario. You extract a density $\hat f$ that is smooth, convex, normalized, passes every other check, and has all its mass in a plausible range around the
current market. It looks perfect. Now suppose that, unbeknownst to you, its mean sits at $F_0 - 0.30$ — thirty cents below the true forward. Why might this happen? Any number of reasons: you sourced
$F_0$ from a stale screen; you used a spot price instead of a forward; a data lag misaligned the options and futures snapshots; a tail smoother pulled the mean off; a bug in the extraction miscentred
the fit.

The consequence: **every Kalshi bracket comparison will be off by approximately the amount that the density is mis-centred, in the same direction, sign-consistent across all brackets.** That is what a
persistent, tradeable edge is supposed to look like. If your position sizing is driven by "how often is the density above/below Kalshi," you'll deploy capital into a signal that is entirely a bug.

That was *exactly* fedarb's -8 percentage-point pooled wedge, in the end. When Jaden dug into it, the biggest single component was measurement breakdown that produced a smooth sign-consistent number.

**What it catches.** The mean-equals-forward check catches location errors in the density — the class of extraction failure that is most dangerous, precisely because it doesn't show up in any of the
other checks. It should be enforced *during* the extraction, not just after, because a post-hoc "did the mean come out right?" check tells you the extraction was wrong but doesn't tell you how to fix
it. Stage 14 enforces the constraint during MCMC via a Gaussian penalty on the posterior; Stage 6 anchors $F_0$ from the chain itself (via put-call parity) so that the check is against an internally
consistent number rather than an external screen.

### The failure-mode taxonomy

The three checks are not redundant. Each catches a different failure mode:

| check | catches | example failure mode |
|---|---|---|
| convexity | data anomalies, negative-density fits | stale outlier quote; overfit smile |
| normalization | truncation errors | grid too narrow; mass in the wings not captured |
| mean = forward | location errors | wrong $F_0$; smoother bias; data-lag misalignment |

The dangerous one is the third, because a mis-centred density is *smooth, convex, normalized* — passes both of the first two checks — and produces a persistent-looking edge that isn't real. That is
why so much of Part 4 is about pinning the density's location precisely (Stage 6 in Act II; Stage 14 in Act III).

---

# Part 3 — Why the naive approach fails

Part 2 gave us the identity: $f(K) = e^{rT} \partial^2 C / \partial K^2$. Part 3 is about what happens when you try to compute the right-hand side from real option prices on a real strike grid.
Spoiler: it doesn't work, and the *way* it doesn't work is important — the failure mode is counterintuitive (finer strike spacing makes things *worse*, not better), and it explains why the pipeline in
Part 4 has as many stages as it does.

## 3.1 The discrete estimator

You have $n$ option prices at strikes $K_1 < K_2 < \ldots < K_n$, not a smooth call price function. To estimate $\partial^2 C / \partial K^2$ at some strike $K_i$, you use a numerical
second-difference estimator.

For evenly spaced strikes with spacing $h$, the standard second-difference formula is:

$$\frac{\partial^2 C}{\partial K^2}\bigg|_{K_i} \approx \frac{C_{i-1} - 2 C_i + C_{i+1}}{h^2}.$$

Real options chains are *not* evenly spaced — they're denser near the money and sparser in the wings. So the more general formula for unequal spacing $h_1 = K_i - K_{i-1}$ and $h_2 = K_{i+1} - K_i$
is:

$$\frac{\partial^2 C}{\partial K^2}\bigg|_{K_i} \approx 2 \left[ \frac{C_{i-1}}{h_1 (h_1 + h_2)} - \frac{C_i}{h_1 h_2} + \frac{C_{i+1}}{h_2 (h_1 + h_2)} \right].$$

**Derivation.** Compute the slope on each side of $K_i$: $m_L = (C_i - C_{i-1}) / h_1$ and $m_R = (C_{i+1} - C_i) / h_2$. Each slope is the average rate of change over its interval and best represents
the *midpoint* of that interval — so $m_L$ estimates the first derivative at $K_i - h_1/2$ and $m_R$ estimates it at $K_i + h_2/2$. The distance between those two midpoints is $(h_1 + h_2) / 2$.
Divide the slope change by that distance:

$$\frac{m_R - m_L}{(h_1 + h_2)/2} = \frac{2 (m_R - m_L)}{h_1 + h_2}.$$

Expanding gives the unequal-spacing formula. Setting $h_1 = h_2 = h$ recovers the standard second-difference $(C_{i-1} - 2C_i + C_{i+1}) / h^2$.

So far so good. This is a standard estimator, has second-order accuracy when applied to noise-free data, and is what any numerical methods textbook would tell you to use. The problem is that
noise-free data isn't what you have.

## 3.2 Three distinct error sources

There are three error sources when computing $f(K)$ via this estimator, and they behave very differently as a function of the strike spacing $h$. Understanding them separately is critical, because
they suggest opposite fixes.

### Error source (a): noise amplification — dominant

Each observed price $C_i$ is a bid-ask midpoint (typically), and the midpoint is uncertain by roughly the half-spread. In liquid crude weekly chains, half-spreads for ATM strikes are around
$0.01–0.03$ per option (a few cents). Call this noise $\sigma_C$ per price.

The second-difference formula combines three noisy prices linearly. If the three noise terms are independent (a reasonable approximation), their contribution to the second difference is:

$$\text{error in second difference} \sim \sqrt{1^2 + 2^2 + 1^2} \cdot \sigma_C = \sqrt{6} \cdot \sigma_C.$$

That's the standard error of a linear combination of three independent Gaussians with weights $1, -2, 1$. Note that the *middle* price counts double (weight $-2$), because it appears in both the left
slope and the right slope of the second-difference calculation.

**Critical observation:** this noise contribution is independent of $h$. Whether your strikes are $0.25 apart or $5.00 apart, the noise on the second difference itself is $\sqrt{6} \sigma_C$. The
strike spacing enters through the *denominator* $h^2$, and *only* through the denominator. So the noise on $f(K)$ scales as:

$$\text{noise on } f(K) \sim \frac{\sqrt{6} \, \sigma_C \, e^{rT}}{h^2}.$$

Meanwhile the *signal* — the true second difference of the call price — scales approximately as $f(K) \cdot h^2$ (that's how curvature works; over a small interval of width $h$, the "amount of
curving" is proportional to $h^2$ times the curvature).

So the **relative** noise (noise / signal) scales as $1 / (h^4 f(K))$ if we combine both factors, or looking at it another way, the estimator is signal-dominated only when $h$ is large enough that
$f(K) h^2$ exceeds $\sqrt{6} \sigma_C / e^{rT}$.

Let's put actual numbers on this.

### A concrete cancellation example

For crude at 3-cent quote noise, at three strikes spaced $h$ apart, with a true density value of about $0.05$ per dollar (a typical ATM value for a distribution with standard deviation around a few
dollars):

| gap $h$ | true 2nd diff $\approx f \cdot h^2$ | error $\sqrt{6} \cdot 0.03$ | relative error |
|---|---|---|---|
| $\$5.00$ | $0.05 \cdot 25 = 1.25$ | $0.073$ | $\approx 6\%$ |
| $\$1.00$ | $0.05 \cdot 1 = 0.050$ | $0.073$ | $\approx 146\%$ |
| $\$0.25$ | $0.05 \cdot 0.0625 = 0.0031$ | $0.073$ | $\approx 2{,}350\%$ |

**At CME's actual weekly strike increment of $0.25, the noise on the second difference is roughly 25 times the quantity being measured.** The estimator returns garbage — frequently negative, which is
impossible for a density (a density is non-negative by definition).

The mechanism is **catastrophic cancellation**. When you compute $C_{i-1} - 2 C_i + C_{i+1}$ at fine spacing, you're subtracting three numbers that are nearly equal from each other, and the result is
essentially zero plus noise. To make this concrete, imagine a representative chain with ATM strikes $\$86.75, \$87.00, \$87.25$ and call prices around $\$6.72$ per option. The prices might be
$6.72317, 6.72019, 6.71731$. The second difference is:

$$6.72317 - 2 \cdot 6.72019 + 6.71731 = 6.72317 - 13.44038 + 6.71731 = 0.00010.$$

Each of those three numbers is uncertain by, say, $\pm 0.03$ per side (the half-spread). The result, $0.00010$, is smaller than any single error term by a factor of 100+. You're subtracting two
numbers that agree to five decimal places and then keeping the change. Any noise in the inputs completely dominates the output.

This is *the* signature of catastrophic cancellation, and it's the reason numerical differentiation is a first-year cautionary tale in scientific computing. It hits especially hard here because option
prices naturally satisfy the smooth-and-slowly-varying property that maximizes cancellation.

### The counterintuitive consequence

More strikes = more data = better estimator, right?

**Wrong.** More strikes means smaller $h$, means larger $1/h^2$ amplification of noise, means worse estimator. **Finer strike spacing makes the naive Breeden–Litzenberger estimator worse.** More data
produces less information about the density.

This is not a coincidence. It's the signature of an **ill-posed inverse problem**. The forward map — density → prices via integration — is smoothing: it takes wiggly densities and turns them into
smooth prices, because integrals average things. So the inverse map — prices → density via differentiation — must be *un-smoothing*: it takes small perturbations of the prices and turns them into
large perturbations of the density. Un-smoothing amplifies noise. That's inherent to the problem, not to any particular algorithm.

The correct response is not "get a better differentiator." A better differentiator does not exist for this problem in the naive sense — the information about the density's fine structure is *not in
the prices* below the noise floor. The correct response is to *not differentiate at all*, which is what Act III of the pipeline does (by integrating instead of differentiating).

### Error source (b): truncation — small

Second, there's a **truncation error** — the error you'd have even with perfect prices. Three points determine a unique parabola, and the second-difference estimator returns *that parabola's*
curvature. But the true call price curve is not a parabola; its curvature varies across the strike span. The single fitted value is a *compromise* dragged toward the local curvatures at $K_{i-1}$ and
$K_{i+1}$.

For a representative crude chain at $h = 5$: this truncation costs about $0.0015$ of curvature error against a true density of $\approx 0.048$ — roughly a 3% bias. Bigger $h$ means the true curve
deviates more from a parabola over that span, so **truncation gets worse as $h$ gets larger.** Which is *opposite* to the noise behavior.

### Error source (c): off-centre bias from unequal spacing — smallest

When $h_1 \ne h_2$, the two slope midpoints ($K_i - h_1/2$ and $K_i + h_2/2$) are *not* symmetric about $K_i$. Their arithmetic mean sits at $K_i + (h_2 - h_1)/4$, not at $K_i$. So the
second-difference estimator computes curvature *there*, not at $K_i$, and you get an "where am I really evaluating this?" error.

The leading term in this error is:

$$\text{off-centre bias} \approx \frac{h_2 - h_1}{3} \cdot C'''(K),$$

which is first-order in the asymmetry $(h_2 - h_1)$ and vanishes when $h_1 = h_2$. You get it back to zero for *free* by re-gridding to uniform spacing before differentiating. (This is what Stage 10
does at the end of Act II — after fitting the SVI smile, reprice onto a fine, even grid before taking the second difference.)

## 3.3 The bias-variance trade-off — and the actual optimum

Truncation error grows with $h$; noise error shrinks with $h$. So there's an optimum. Cool. Where?

Working through the algebra for a representative WTI weekly chain with 3-cent quote noise:

| $h$ ($\$$) | bias | noise | total RMSE |
|---|---|---|---|
| 0.25 | 0.00000 | 1.17576 | 1.17576 |
| 0.50 | 0.00001 | 0.29394 | 0.29394 |
| 1.00 | 0.00006 | 0.07348 | 0.07348 |
| 2.00 | 0.00025 | 0.01837 | 0.01838 |
| 3.00 | 0.00056 | 0.00816 | 0.00819 |
| 5.00 | 0.00149 | 0.00294 | 0.00330 |
| **6.00** | **0.00215** | **0.00204** | **0.00296** |
| 10.00 | 0.00475 | 0.00073 | 0.00481 |
| 15.00 | 0.01022 | 0.00033 | 0.01022 |

The optimum sits at roughly $h = 6$ with a relative error around 6% at a true $f(K) \approx 0.048$.

**Now think about what "using $h = 6$" actually means for a real chain.** CME weekly WTI has strikes at $0.25 increments over the ATM region and maybe $0.50 or
$1.00 farther out. A typical chain might have 40 strikes spread over $\$20$. Using $h = 6$ means picking three strikes: $K_i - 6, K_i, K_i + 6$. If you want $f(K)$ at, say, $\$85, \$86, \$87, \ldots$,
you'd need triples like $(79, 85, 91), (80, 86, 92), (81, 87, 93), \ldots$ — but you only have three strikes per triple, and you're using each strike in many triples, so you effectively have a lot of
overlap and your "estimates" at nearby $K$ are highly correlated.

Worse: you get the density at a *handful* of specific points determined by which strike-triples you can construct, not on a fine grid. You cannot integrate the density over Kalshi's $\$1$-wide
brackets if your density is only defined at $\$6$-apart points.

**So the naive estimator, even at its optimal $h$, is unusable for NightKing.** It:

-  Discards about 90% of the strike information.
-  Returns the density at only a few points, not a curve.
-  Has no error bars.
-  Has no way to integrate over bracket-scale intervals.

The estimator answers a question the strategy doesn't need answered (point densities at specific strikes) using inputs that would allow a much better question (the whole density with error bars) to be
answered.

## 3.4 The actual question the pipeline answers

Reframing: the naive estimator asks "given three consecutive strikes, what is the density at the middle one?" The pipeline asks "given a whole chain of maybe 40 strikes, each with a bid, an ask, and a
half-spread, what is the *posterior distribution over risk-neutral densities* — the set of densities consistent with the data — and how does that distribution integrate over Kalshi's specific bracket
intervals?"

The second question is what NightKing actually needs. Getting a good answer to it requires *not* differentiating at all, and instead inverting the forward map (density → prices) directly using
integration plus regularization. Which is exactly what Act III (Stages 11–15) does.

Act II (Stages 6–10) is a different route to the same object: instead of directly extracting the density, first smooth the *implied volatility* surface (a friendlier object because it varies slowly
and smoothly across strikes), then compute call prices from the smoothed IV surface on a fine grid, then differentiate *those* smoothed prices twice.

The two acts are alternatives, not sequential steps. Act II is faster and gives you a single density estimate. Act III is more expensive computationally but gives you the entire posterior distribution
over densities, with error bars. They should agree; if they don't, something is wrong. Part 4 walks through the twenty stages that make up the two acts.

## 3.5 Framing: this is an ill-posed inverse problem

Everything in Part 3 can be summarized in one sentence: extracting a density from prices is a canonical **ill-posed inverse problem**.

The pattern:

1.  There is a *forward map* from parameter space to observation space. In this case: density → call prices via integration.
2.  The forward map is *smoothing*: many different parameters produce very similar observations, because the mapping loses information.
3.  Therefore the inverse map is *un-smoothing*: small changes in observations correspond to large changes in parameters.
4.  Any noise in the observations gets amplified by the inverse map, often catastrophically.

This pattern shows up all over applied mathematics: medical imaging (CT reconstruction from X-ray projections), atmospheric physics (retrieving temperature profiles from satellite radiances),
geophysics (reconstructing subsurface density from seismic data), spectroscopy, etc. The mathematics is well-understood, and there's a standard toolkit:

-  **Regularization:** add a penalty for wiggliness. The Bayesian version is a *prior* over the parameters that favors smooth ones. Stage 12 does exactly this (curvature penalty on the log-density).

-  **Parameterize in a low-dimensional but flexible space:** don't try to fit an infinite-dimensional function; fit a spline with a modest number of coefficients. Stage 11 does this (a 20–30
  coefficient exp-basis parameterization).

-  **Use the forward map, not the inverse map, in the likelihood:** compare observed prices to *predicted prices from the candidate density* (which requires only integration, a smoothing operation),
  rather than trying to differentiate the observed prices. Stage 13 does this.

-  **Propagate uncertainty:** don't return a point estimate; return a posterior. Stage 15 (MCMC) does this.

Understanding the ill-posed-inverse framing helps make sense of why the Part 4 pipeline looks the way it does. It's not doing anything clever that's specific to options. It's applying the standard
toolkit for ill-posed inverse problems, tuned to the specific structure of the options-pricing forward map.

---

# Part 4 — The extraction pipeline: 20 stages in 5 acts

Everything through Part 3 was setup. Part 4 is the actual pipeline.

**Structure at a glance.** Twenty numbered stages, grouped into five acts. Read them in order the first time.

-  **Act I — the identity** (Stages 1–5). The mathematical foundation and the failure analysis. Everything is Part 2 and Part 3 above, restated as stages so the pipeline has a common numbering.
-  **Act II — Defense 1: clean the prices, then differentiate** (Stages 6–10). The classical approach. Fit a smooth implied volatility surface to the observed prices; reprice onto a fine even grid;
  take the second difference of the smooth prices.
-  **Act III — Defense 2: never differentiate** (Stages 11–15). The Bayesian approach. Parameterize the density directly; compare candidate densities against observed prices via integration (which is
  smoothing, not un-smoothing); sample the posterior with MCMC.
-  **Act IV — from density to decision** (Stages 16–19). Turn the extracted density (or posterior over densities) into concrete bracket-level probabilities, compare against Kalshi, decompose the gap
  into innocent and tradeable components, apply the trade filter.
-  **Act V — execution** (Stage 20). Replicate a Kalshi bracket digital as a four-leg options structure. Handle the ramp and granularity constraints.

**Two independent routes to the same object.** Act II and Act III are *alternatives*, not sequential steps. Act II is a fast, single-point estimate of the density. Act III is an expensive,
full-posterior estimate that gives you error bars. Both use the shared preparation in Stages 6–8 (put-call parity anchoring $F_0$, Black-76 inversion, OTM-only selection). They should agree on the
point estimate; if they don't, one of them is wrong. The strategy relies on Act III for the error bars because "the spread is the deliverable" (see Stage 15) but uses Act II as a sanity check and as a
fast diagnostic during development.

**For every stage, this Part answers four questions.**

1.  What does this stage do?
2.  Why is it necessary — what would break without it?
3.  How does it work mechanically?
4.  What failure mode does it address?

## Act I — the identity (Stages 1–5)

### Stage 1 — Write down the master equation

$C(K) = e^{-rT} \int_K^\infty (s - K) f(s) \, ds$.

This is Part 2 §2.3. It's here as a stage so that the pipeline has a canonical starting point and everything downstream can reference it.

**What it does:** establishes that call prices are integrals of the risk-neutral density weighted by the option's payoff.

**Why it's necessary:** every subsequent stage is a manipulation of this identity. Without it there is no strategy.

**How it works:** by definition of risk-neutral pricing (Part 2 §2.1) and definition of call payoff.

**Failure mode addressed:** the stage exists so that when Stage 13 computes predicted prices from a candidate density, it's using an exact formula, not an approximation. Any deviation from an observed
price must therefore be attributable to (a) the density being wrong or (b) the observed price being noisy — not to a modeling error in the pricing formula.

### Stage 2 — First derivative: the survival function

$\partial C / \partial K = -e^{-rT} \mathbb{Q}(F_T > K)$.

This is Part 2 §2.4. As a stage, it says: differentiating the master equation once gives you the price of a digital option, which is what Kalshi's "above $K$" contracts pay.

**What it does:** links the first derivative of the call price to a tradeable Kalshi instrument.

**Why it's necessary:** it establishes that a Kalshi "cumulative" ladder (prices of "above $K$" for a series of thresholds $K_1 < K_2 < \ldots$) is directly the first derivative of the call price
curve. In particular, Stage 16 shows that the *range probability* $\mathbb{Q}(a < F_T < b)$ is the difference of two first derivatives, and therefore an integral (not a differentiation!) of the
density — which is why bracket-level comparisons are the numerically robust quantity to trade.

**How it works:** Leibniz's rule with the boundary term vanishing because the integrand carries a factor $(s - K)$ that is zero at $s = K$.

**Failure mode addressed:** without this stage, you might think of Kalshi bracket comparisons as needing point densities (second derivatives). They don't. They need range probabilities (first
derivatives at two endpoints, subtracted). The distinction is enormously important for numerical robustness (Stage 16 unpacks why).

### Stage 3 — Second derivative: Breeden–Litzenberger

$f(K) = e^{rT} \partial^2 C / \partial K^2$.

This is Part 2 §2.5. As a stage, it says: differentiating the master equation *twice* gives you the risk-neutral density.

**What it does:** the density-extraction identity. Every other stage is either helping you compute this well or helping you avoid computing it naively.

**Why it's necessary:** it's *the* reason the strategy exists. Without Breeden–Litzenberger there would be no way to compare an options chain to a Kalshi ladder.

**How it works:** differentiate Stage 2 once more.

**Failure mode addressed:** none directly. This is the identity that subsequent stages defend against numerical failure of.

### Stage 4 — The three consistency checks

Convexity, normalization, mean-equals-forward. Part 2 §2.6.

**What it does:** provides a battery of tests that any candidate density must pass. Each test catches a different failure mode: convexity catches data anomalies and negative-density fits,
normalization catches truncation errors, and mean-equals-forward catches the deadliest one — location errors that make the extracted density smoothly biased against every bracket in the same
direction.

**Why it's necessary:** the pipeline is complex, has many places to go wrong, and needs standing diagnostics. These three checks are the ones that catch specific failure modes cheaply.

**How it works:** compute the three quantities (integrated density, integrated $K f(K)$, sign of $C''$) on the extracted density and compare to $1$, $F_0$, and $\ge 0$.

**Failure mode addressed:** all three — but especially the third. The mean-equals-forward check is the one that would have caught fedarb's measurement breakdown if fedarb had been operating on a
distribution rather than a scalar. Stage 14 enforces this check *during* the extraction (via a Gaussian penalty in the MCMC likelihood) so that a mis-centred density doesn't even reach the diagnostic
output.

### Stage 5 — Fragility analysis of the naive estimator

This is Part 3. As a stage, it says: catalog exactly how the naive Breeden–Litzenberger estimator fails on real data, so that every design choice in Acts II and III is a targeted response to a
specific failure mode.

**What it does:** provides the diagnosis that motivates the rest of the pipeline.

**Why it's necessary:** without this stage you'd write a naive implementation, get garbage, and not know why. Understanding catastrophic cancellation, the bias-variance trade-off, and the ill-
posed-inverse framing tells you *what to change* to fix it.

**How it works:** Part 3. Simulate. Walk through numerical examples by hand. Note the counterintuitive fact that finer strikes make the estimator worse. Recognize the pattern as an ill-posed inverse
problem whose textbook remedies are regularization, low-dimensional flexible parameterization, and forward-map likelihoods.

**Failure mode addressed:** the "confident implementation of a broken estimator" failure mode. This is the failure mode where you write `C_second_diff = (C[i-1] - 2*C[i] + C[i+1]) / h**2` and think
you've extracted a density. Stage 5 explains why that's wrong.

## Act II — Defense 1: clean the prices, then differentiate

Act II is the classical approach — fit a smooth implied-volatility surface to the observed option prices, reprice onto a fine even grid, then take the second difference of the *smoothed* prices. This
is the route almost every textbook and every practitioner starts with. It returns *a* density (not a distribution of densities), it's fast, and it's a good sanity check on Act III.

Act II has one structural weakness — it hands you one density and no error bars — which is why the pipeline treats it as a diagnostic rather than the deliverable. Act III (the Bayesian route) is the
deliverable. But you build Act II first because if you can't get the *point* estimate right, you can't trust the posterior either.

### Stage 6 — Forward and discount factor from the chain itself

**What it does:** extract the discount factor $D = e^{-rT}$ and the forward $F_0$ directly from the options chain, via linear regression on put-call parity. Do *not* trust an externally-sourced $F_0$.

**Why it's necessary:** the extracted density's location — the actual value of $\mathbb{E}[F_T]$ — has to equal $F_0$ (martingale property, Part 2 §2.2). If your $F_0$ is off (stale screen, wrong
contract, snapshot lag), the density's location will be off in the same direction, and every bracket comparison will be biased the same way. This is the fedarb -8pt failure mode reincarnated. Sourcing
$F_0$ from the chain itself makes the location internally consistent with the prices you're extracting from.

**How it works.** Buy one call and sell one put at the same strike $K$ with the same expiry. The combined payoff at expiry is:

$$(F_T - K)^+ - (K - F_T)^+ = F_T - K$$

for *every* value of $F_T$ — no max, no kink, no case analysis. If $F_T > K$, the call pays $F_T - K$ and the put pays zero; if $F_T < K$, the call pays zero and the short put costs you $K - F_T$; in
either case you net $F_T - K$. So this synthetic portfolio is exactly a forward contract paying $F_T - K$ at time $T$.

The price today of this synthetic forward, by risk-neutral pricing, is $e^{-rT} \mathbb{E}^{\mathbb{Q}}[F_T - K] = e^{-rT}(F_0 - K)$ (using the martingale property
$\mathbb{E}^{\mathbb{Q}}[F_T] = F_0$). And the price of the portfolio is just $C(K) - P(K)$. So:

$$C(K) - P(K) = e^{-rT}(F_0 - K) = D \cdot F_0 - D \cdot K.$$

This is **linear in $K$**. Take the observed pairs $(C_i, P_i, K_i)$ for every strike where both a call and a put trade, form $y_i = C_i - P_i$, and regress against $K_i$:

-  The slope is $-D = -e^{-rT}$ (so $r$ is the negative log of $-\text{slope}$, divided by $T$).
-  The intercept is $D \cdot F_0$, so $F_0 = \text{intercept} / D$.

**Verified numerically:** on synthetic data with no noise, this recovers $F_0$ to four decimal places. With 3-cent Gaussian noise added to every quote, it's still accurate to under a cent, because the
regression averages the noise across all the strikes you use. The noise enters *linearly* into the fit, not as a difference of nearly-equal numbers, so the noise averages out with $1/\sqrt{N}$ where
$N$ is the number of strike-pairs.

**Contrast with the second-difference formula.** Same inputs (noisy call and put prices). Opposite operation (averaging vs subtracting). Opposite outcome (recovery of $F_0$ to sub-cent precision vs
$2000\%$ relative error in the density). This is the general theme of the pipeline: whenever you can, *average*; whenever you can, *avoid differencing*.

**Why not just read the futures screen?** If you look up $F_0$ from an external source (the CME futures screen for the corresponding weekly futures contract), nothing errors out. You get a number. You
use it. But if that external number disagrees with what the chain implies — because of a snapshot lag between when you pulled the options data and when the futures screen updated, or because you
accidentally grabbed the wrong contract, or because the exchange is in a fast-market period where quotes move faster than the vendor updates — then your extracted density is *smoothly* off in location
by that disagreement. It's still smooth, convex, normalized, and passes the first two consistency checks. Only the mean-equals-forward check catches it, and only if "the forward" in the check is the
internally-consistent $F_0$ from the chain — which is what Stage 6 provides.

**Free bonus: bad-quote detection.** Put-call parity is an exact arbitrage identity. If it holds in the market, every observed pair $(C_i - P_i, K_i)$ *must* lie on the same line. Residuals to the
line tell you where the parity is broken, which is a signal that one of those quotes is stale or wrong. This is the cheapest bad-data detector in the pipeline — no model, no fit, just a linear
regression whose residuals should be zero up to noise, and any strikes whose residuals are large-outlier candidates are broken data that should be excluded before any downstream work.

**Cross-reference to fedarb.** fedarb's contract-contamination problem was a variant of this same issue: the Fed Funds futures price for a month with a late-month meeting was influenced by rates set
at the *next* meeting, contaminating the extraction. Sourcing "the forward" from the correct internal object matters. NightKing generalizes the lesson: always compute $F_0$ from the same chain you're
extracting the density from, not from a separate feed.

### Stage 7 — Invert price to implied volatility (Black-76)

**What it does:** convert each observed option price $C(K)$ into an implied volatility $\sigma(K)$ via inversion of Black's formula for futures.

**Why it's necessary:** you're going to smooth in a moment (Stage 9), and smoothing works better on a flat surface than on a steep, curved one. Prices span three orders of magnitude across a chain
($45 down to 2 cents), and their shape (a hockey-stick with sharp curvature at strike ~$F_0$) is hostile to smoothing. Implied volatilities span a tight range (call it 25%–50% across most strikes) and
their shape (a gentle U-shape called a "smile") is friendly to smoothing. So convert prices to IVs, smooth the IVs, then convert back to prices.

**Black-76 formula.** For a European call on a futures underlying $F$ with strike $K$, time to expiry $T$, volatility $\sigma$, and risk-free rate $r$:

$$C = e^{-rT} \big[ F \cdot \mathcal{N}(d_1) - K \cdot \mathcal{N}(d_2) \big],$$

where $\mathcal{N}(\cdot)$ is the standard normal CDF and

$$d_1 = \frac{\ln(F/K) + \tfrac{1}{2} \sigma^2 T}{\sigma \sqrt{T}}, \qquad d_2 = d_1 - \sigma \sqrt{T}.$$

Note the absence of $r$ inside $d_1$ — that's the martingale property of futures under $\mathbb{Q}$ showing up (Part 2 §2.2). If you used Black-Scholes here (which has $+ rT$ in the numerator of
$d_1$) you'd get a biased $\sigma$.

**What $d_1$ and $d_2$ actually mean.** The formula has two "probability-like" objects, $\mathcal{N}(d_1)$ and $\mathcal{N}(d_2)$, and understanding what each represents is critical for the reader who
wants to reason from first principles rather than plug in a formula.

$d_2$ is *literally a z-score*: it's the number of standard deviations between the strike and the centre of the terminal log-price distribution. Concretely, under $\mathbb{Q}$ the futures price at
expiry has a lognormal distribution with $\ln F_T \sim \mathcal{N}(\ln F - \tfrac{1}{2} \sigma^2 T, \sigma^2 T)$ (the $-\tfrac{1}{2}\sigma^2 T$ is Itô's correction for the difference between
$\mathbb{E}[F_T]$ and $F \cdot e^{\text{drift}}$). So the probability of finishing above $K$ is:

$$\mathbb{Q}(F_T > K) = \mathbb{Q}(\ln F_T > \ln K) = \mathbb{Q}\Big(\frac{\ln F_T - (\ln F - \tfrac{1}{2}\sigma^2 T)}{\sigma \sqrt{T}} > \frac{\ln K - \ln F + \tfrac{1}{2}\sigma^2 T}{\sigma \sqrt{T}}\Big).$$

The right-hand side inside the probability is exactly $-d_2$, and by symmetry of the standard normal, $\mathbb{Q}(Z > -d_2) = \mathcal{N}(d_2)$. So $\mathcal{N}(d_2) = \mathbb{Q}(F_T > K)$ — the
risk-neutral probability that the option ends in the money. This is a *headcount*: what fraction of Monte Carlo scenarios finish ITM.

$\mathcal{N}(d_1)$ is the same probability but *asset-weighted*. Specifically:

$$\mathcal{N}(d_1) = \frac{\mathbb{E}^{\mathbb{Q}}[F_T \cdot \mathbb{1}\{F_T > K\}]}{F}$$

— it's the risk-neutral expected value of $F_T$ conditional on the option being ITM, times the ITM probability, divided by $F$. In words: "what fraction of the futures's expected value comes from the
ITM scenarios."

### The headcount vs dollar-count example

This is the piece that most textbooks fail to explain cleanly, and it's worth taking a beat on.

Imagine five equally likely scenarios for terminal WTI: $F_T \in \{79, 83, 87, 91, 95\}$, each with probability $0.2$. Then $\mathbb{E}[F_T] = 87$. Now imagine a call struck at $K = 88$. Which
scenarios are ITM? The ones where $F_T > 88$: $91$ and $95$. That's *two out of five*, so the ITM headcount fraction is $\mathbb{Q}(F_T > 88) = 0.4$. So $\mathcal{N}(d_2) = 0.40$.

Now compute the asset-weighted version. In the two ITM scenarios, the values of $F_T$ are $91$ and $95$, so the *contribution* to $\mathbb{E}[F_T]$ from those scenarios is
$0.2 \cdot 91 + 0.2 \cdot 95 = 18.2 + 19 = 37.2$. Divide by $\mathbb{E}[F_T] = 87$ (or more precisely, by $F$ which is what appears in the formula): $37.2 / 87 = 0.4276$. So
$\mathcal{N}(d_1) \approx 0.4276$.

Notice: **$\mathcal{N}(d_1) > \mathcal{N}(d_2)$ always**, and the inequality reflects the fact that the ITM scenarios are, on average, "more valuable" than the overall average — they're above $K$, so
they're pulling above the mean. And $d_1 - d_2 = \sigma \sqrt{T}$ exactly (a fact that comes back below in the vega derivation).

**Why does Black-76 have two of these?** Look at the formula:

$$C = e^{-rT} \big[ F \mathcal{N}(d_1) - K \mathcal{N}(d_2) \big].$$

Read it: "the call pays out the asset $F$ in the ITM scenarios (an asset-value-weighted quantity, hence $\mathcal{N}(d_1)$) minus the strike $K$ in each ITM scenario (a headcount-weighted quantity,
hence $\mathcal{N}(d_2)$)." The strike is a fixed cash payment made every time you exercise — headcount. The asset value is what you receive back — dollar-count. The two probabilities are appropriate
to their respective payoff components.

This is Jaden's headcount-vs-dollar-count example, and it's the clearest exposition of the two $d$'s I've seen. It generalizes: whenever a payoff has two components — one that scales with the
underlying and one that doesn't — you get two probabilities in the formula, one asset-weighted, one not.

### The inversion

Given an observed price $C^{\text{obs}}$, find the $\sigma$ that makes $C(\sigma) = C^{\text{obs}}$. There's no closed-form solution because $\sigma$ appears inside $\mathcal{N}(\cdot)$, an integral
with no elementary antiderivative. But $C$ is monotone increasing in $\sigma$ (a well-known property: options with more volatility are worth more), so any root-finding method will converge to the
unique solution.

Newton's method with vega:

$$\text{vega} = \frac{\partial C}{\partial \sigma} = e^{-rT} F \varphi(d_1) \sqrt{T},$$

where $\varphi$ is the standard normal PDF, and

$$\sigma_{k+1} = \sigma_k - \frac{C(\sigma_k) - C^{\text{obs}}}{\text{vega}(\sigma_k)}.$$

**Where does vega come from?** Differentiate $C = e^{-rT}[F \mathcal{N}(d_1) - K \mathcal{N}(d_2)]$ with respect to $\sigma$. The two terms give:

$$\frac{\partial C}{\partial \sigma} = e^{-rT} \Big[ F \varphi(d_1) \frac{\partial d_1}{\partial \sigma} - K \varphi(d_2) \frac{\partial d_2}{\partial \sigma} \Big].$$

There's a beautiful identity: $F \varphi(d_1) = K \varphi(d_2)$. This is not obvious at first, but comes from expanding $\varphi$'s argument, using $d_2 = d_1 - \sigma \sqrt{T}$, and the definition of
$d_1$. When you work it through, the ratio $F \varphi(d_1) / K \varphi(d_2)$ collapses to $1$.

That identity means we can factor $F \varphi(d_1)$ out of both terms:

$$\frac{\partial C}{\partial \sigma} = e^{-rT} F \varphi(d_1) \Big[ \frac{\partial d_1}{\partial \sigma} - \frac{\partial d_2}{\partial \sigma} \Big] = e^{-rT} F \varphi(d_1) \cdot \frac{\partial (d_1 - d_2)}{\partial \sigma}.$$

But $d_1 - d_2 = \sigma \sqrt{T}$, so $\partial (d_1 - d_2) / \partial \sigma = \sqrt{T}$. Combining:

$$\text{vega} = e^{-rT} F \varphi(d_1) \sqrt{T}.$$

That's where the $\sqrt{T}$ comes from — from the fact that the difference $d_1 - d_2$ is $\sigma \sqrt{T}$. Every options textbook has this formula; most don't show the derivation. Understanding it
makes the whole formula less mysterious.

### Why the inversion is worth doing at all

The inversion is a **lossless relabeling** — you're not gaining information, you're just changing coordinates from $(K, C)$ to $(K, \sigma)$. Both are equivalent representations of the same option. By
itself, this earns you nothing.

The earn comes at Stage 9, when you smooth. Prices vary by three orders of magnitude, with sharp curvature at $K \approx F_0$; smoothing them directly loses the wings and mangles the ATM curvature.
IVs vary in a tight band with a slow smile shape; smoothing them is clean. Black-76 is *graph paper, not a theory*: it lets you replot your data in coordinates where the underlying smooth structure is
visible.

**Where the inversion breaks: vega dies in the wings.** Newton's step is $(C^{\text{obs}} - C(\sigma)) / \text{vega}$, so the error in the implied $\sigma$ is approximately (error in price) / (vega).
Vega is a strong function of moneyness — it's large ATM and dies exponentially as you go deep OTM or deep ITM. Measured on a representative 2-day WTI weekly chain with $F_0 = \$87$ and 35% ATM vol:

| strike | vega | IV error per $0.01 of price error |
|---|---|---|
| $\$87$ (ATM) | 2.57 | 0.4 vol pts |
| $\$82$ (moderately OTM put / ITM call) | 0.18 | 5.5 vol pts |
| $\$78$ (deep) | 0.0003 | **2,963 vol pts** |

With realistic 3-cent noise, wing strikes returned wild IV values *and outright failures* — the noisy price landing below the option's intrinsic value, where no volatility can produce it. Deep ITM
options carry almost all their value as intrinsic (the
$78 call in this example has one-tenth of a cent of time value); adding 3 cents of noise puts the price below intrinsic value, and there's no $\sigma \ge 0$ that satisfies the equation.

**This is not an algorithm problem.** No inversion algorithm can extract information that isn't in the price. Deep-ITM/OTM options simply do not encode much information about volatility, because their
price is either almost entirely intrinsic (deep ITM) or almost zero regardless of vol (deep OTM). The correct response is *not* to try harder; it's to downweight those strikes in the fit (Stage 9) and
*use put-call parity to avoid deep-ITM strikes entirely* (Stage 8).

### Stage 8 — Select OTM only

**What it does:** for each strike, pick either the call or the put but not both, choosing whichever is out-of-the-money. Calls above $F_0$, puts below.

**Why it's necessary:** deep-ITM options are numerically bad citizens (vega tiny, mostly intrinsic value, close to noise-dominated at inversion time) *and* they carry early-exercise premium if the
contract is American-style. OTM options are the informative ones — they're all time value, vega is largest there, and there's no early-exercise contamination.

**How it works.** By put-call parity (Stage 6), a put and a call at the same strike carry the *same* implied volatility. So there's no information loss in choosing one over the other — the choice is
purely numerical.

Three reasons to pick OTM:

1.  **Equal information from either.** By parity, $\sigma_{\text{call}}(K) = \sigma_{\text{put}}(K)$ in theory. So it's a wash from a data-content perspective.

2.  **OTM options are all time value.** Time value is the price component that responds to volatility. Intrinsic value doesn't. So an option that is 90%+ time value has vega concentrated where it
   matters, and Newton's inversion is well-conditioned.

3.  **Early-exercise premium concentrates deep ITM.** If the option is American-style (which CME weekly WTI options *are*), then a deep-ITM option carries some premium for the option to be exercised
   early — which is not captured by Black-76 (a European formula). OTM options have negligible early-exercise premium (why exercise early on an OTM option? there's no intrinsic value to lock in), so
   treating them as European is a good approximation.

**Note the asymmetry.** OTM-only fixes *deep-ITM* strikes by not using them at all (using the OTM equivalent instead). It does *not* fix *deep-OTM* strikes — those are still uninformative, because
both the call and the put at a deep-OTM strike are near zero and dominated by noise. Deep OTM strikes are down-weighted (not read from the other side) in Stage 9. There's no fix for "the deep tails
have no information"; that's a structural fact about the data.

### Stage 9 — Fit the smile, weighted by informativeness

**What it does:** fit a smooth parametric curve $\sigma(k)$ through the observed implied volatilities, where $k = \ln(K/F_0)$ is log-moneyness.

**Why it's necessary:** the observed IVs are noisy point estimates. The density will be extracted from the *fitted* curve, not from the raw points. A good fit is smooth, respects the observed data
more where the data is more informative, and can extrapolate sensibly into the wings.

**Coordinates: log-moneyness.** $k = \ln(K/F_0)$ centres the strike axis at zero ($k = 0$ is ATM, $k > 0$ is OTM call region, $k < 0$ is OTM put region), removes the level dependence of $F_0$, and is
the natural coordinate for lognormal-adjacent distributions. Whether $F_0$ is $\$87$ or $\$187$, the smile shape in log-moneyness is comparable.

**Weights.** IV uncertainty per strike is approximately half-spread divided by vega:

$$\sigma_{\text{IV}}(K) \approx \frac{\text{half-spread}(K)}{\text{vega}(K)}.$$

So the weight for each strike in a weighted-least-squares fit is:

$$w_i \propto \frac{1}{\sigma_{\text{IV}}(K_i)^2} = \frac{\text{vega}(K_i)^2}{\text{half-spread}(K_i)^2}.$$

This is inverse-variance weighting, the standard result for combining noisy observations of a common parameter.

**Not volume.** A tempting alternative would be to weight by trading volume — "the strikes where more people traded are more informative." But volume is *cumulative history*, not current information
content. Weighting by volume would down-weight the wing strikes that are exactly the ones that pin the tails of the density, while piling redundant weight on the ATM strikes that are already
well-determined by any sensible fit. Half-spread / vega is the correct informativeness proxy because it reflects *what the current market tells you about the IV at that strike*, not what the market
told you last week.

This is a general point: **weight by information content, not by activity.** Volume-weighting is a subtle way to poison a fit because it correlates with everything (liquid ATM strikes get more
attention and thus more volume, but they also have low IV uncertainty and thus don't need extra weight). Half-spread / vega weighting is what the statistics says to use, and using it makes the wings,
where the tails of the density live, actually matter.

**Parameterization: SVI.** *Stochastic Volatility Inspired* (Gatheral
2004)  is a 5-parameter formula for the total-variance surface $w(k) = \sigma^2(k) T$:

$$w(k) = a + b \Big[ \rho (k - m) + \sqrt{(k - m)^2 + s^2} \Big].$$

The parameters have physical meanings:

-  $a$: baseline variance level.
-  $b$: wing slope (how fast the smile rises in the wings).
-  $\rho$: skew (a positive value tilts the smile toward positive $k$, a negative value toward negative $k$).
-  $m$: horizontal shift of the smile.
-  $s$: curvature at the ATM point.

Five parameters is enough to fit a wide variety of smile shapes with no wiggles (five is exactly the number needed to capture level, slope, curvature, skew, and asymmetry). It's much more constrained
than a free spline, which is exactly what you want — a spline through noisy points will overfit locally and produce a smile that isn't smooth in the wings.

Why choose SVI over other parameterizations? Two reasons: (a) SVI has *known* parameter constraints that guarantee no-butterfly-arbitrage (Stage 10 exploits this), and (b) SVI is asymptotically
consistent with lognormal-based option-pricing models in the wings (Roger Lee's moment formula), so it doesn't extrapolate crazily into strikes where you have no data.

### Stage 10 — No-arbitrage, enforced not checked

**What it does:** guarantee that the SVI fit produces a call-price surface satisfying $\partial C / \partial K \le 0$ (monotonicity) and $\partial^2 C / \partial K^2 \ge 0$ (convexity), so the
extracted density is nonnegative *by construction*.

**Why it's necessary:** the conditions are on $C$, but the fit is on $\sigma$. A smooth, sensible-looking IV curve can *still* imply a negative density somewhere, because the transformation from IV to
call price is nonlinear. If you don't enforce no-arb, you can get a density with negative regions, which is a hard failure downstream — you can't sample from a signed measure, you can't call anything
a "probability," and any downstream logic that assumes non-negativity breaks silently.

**The trap.** A common bug: fit SVI freely, then check whether the resulting density is nonneg, and if not, either edit the fit or reject the extraction. This is fragile because the check is
*post-hoc* and adds complexity. And numerical investigation of a wide range of SVI smiles shows that *symmetric* smiles (positive $\rho$ zero, big-but-symmetric wings) are remarkably safe — even
extreme smiles (35 vol ATM to 95 vol in the wings) stayed arbitrage-free. **Skew is what breaks things.** Pushing $\rho$ more negative and steeper drove the minimum density from
$0.00316 \to 0.00094 \to 0.00008 \to 0.00000$, approaching the boundary. Real crude smiles are skewed. So the wing- control matters.

**Fix.** SVI has known no-arb constraints (Gatheral & Jacquier, 2014). The key one is:

$$b (1 + |\rho|) \le \frac{4}{\sqrt{T}}.$$

Enforce this (and a couple of other Gatheral-Jacquier constraints, on $a$, $\sigma$, etc.) as bounds in the optimizer. Then the fit *cannot* produce a negative density — the feasible region of
parameter space excludes it.

**Consequence for the pipeline.** Stage 10 becomes verification instead of repair: after fitting, you *check* that the density is nonneg (which it always is if the constraints were respected), but you
never have to handle the "and if not?" branch. The failure mode "extracted density has negative regions" is structurally impossible under the constrained optimization.

**Reprice onto a fine, even grid.** After SVI is fit, evaluate $\sigma(k)$ on a fine grid of $k$ values (say, 0.001 apart in log- moneyness), convert each to a price via Black-76, and take the second
difference of the *smoothed prices* on this fine grid. This gives you the density on the fine grid.

Two reasons the grid is even:

1.  Even spacing restores the second-order accuracy of the second- difference estimator that would otherwise be lost to the off-centre bias from unequal spacing (Part 3, §3.2c).

2.  Fine spacing lets you integrate the density over Kalshi's exact bracket edges in Stage 17. If your grid is coarser than the bracket width, you can't do the integral accurately.

Note that the noise-amplification problem from Part 3 (§3.2a) does *not* apply here, because the SVI fit has already smoothed away the noise. The second differences of the fitted prices are stable
because the fitted prices themselves are a smooth function of $K$, not a noisy one. This is the whole point of the "clean the prices first" approach.

### End of Act II — what you have, what you don't

At the end of Act II you have a smooth risk-neutral density $\hat f(K)$ on a fine grid, extracted from a smoothed-then-differentiated call price surface. You can integrate this over Kalshi's brackets
and get a point-estimate vector of probabilities.

What you *don't* have: error bars. The SVI fit gives you point estimates of five parameters (plus their covariance, if you're careful with the optimizer, but that only captures the parametric
uncertainty of the SVI model, not the model-selection uncertainty of "why SVI at all?"). And the SVI model itself is a *choice*: many different densities are consistent with the same options prices,
and picking SVI as the parameterization is picking one of them without acknowledging the alternatives.

This is why Act III exists. Not because Act II is *wrong* — for the point estimate, Act II is fast and pretty good. But because "one density and no error bars" isn't enough to trade against. You need
to know how much you should distrust the density before you decide that a Kalshi bracket is mispriced. Act III delivers the distrust.

## Act III — Defense 2: never differentiate

Act III is the Bayesian route: parameterize the density directly, compute predicted option prices from candidate densities via integration (which is *stabilizing*, not destabilizing), and sample the
posterior distribution over densities with MCMC. The output is not a density; it's an ensemble of thousands of concrete densities, each consistent with the observed prices to within measurement error.
From that ensemble you get error bars on everything downstream — bracket probabilities, gap decompositions, everything.

The philosophy of Act III can be stated in one line: **the inverse problem is ill-posed, so the answer is a distribution over solutions, not a single solution.** Pretending otherwise (by returning a
single point estimate) is dishonest about the underlying uncertainty.

### Why Act II is structurally insufficient

Before Stage 11, one more thing to say about Act II: it gives you *one* density and *no error bars*, and there is a specific way that this is not just aesthetically bad but *dangerous* — it will
occasionally hand you a confidently wrong answer without any signal.

Consider the following empirical fact (which the pipeline developers verified with a numerical experiment): on a realistic WTI options chain, a *single-humped* density and a *bimodal* density can
produce option prices that agree at every strike to within the bid-ask spread. Specifically: two densities differing by 40% in $f(87)$ (0.1534 for one, 0.1094 for the other) produced call prices at
most strikes that differed by less than the bid-ask half-spread. Both are consistent with the same observed chain.

**Why?** Because each option price is an *integral*:

$$C(K) = e^{-rT} \int_K^\infty (s - K) f(s) \, ds.$$

An integral is a summary statistic — it compresses the entire density above $K$ into one number. Two very different densities can have very similar integrals above every strike. The forward map
(density → prices) is many-to-one. The inverse map (prices → density) is not a function at all — it's a set-valued relation.

So Act II picks *one* density from the consistent set and hands it to you without warning. Which one? Whichever the SVI parameterization plus the smoothness of the fit happens to prefer. That's a
*choice*, not data. And you have no way to tell how different other consistent densities would have looked, so you have no way to say how uncertain your bracket probabilities really are.

The forward map (density → prices) is a proper function — every density maps to a unique price vector. The reverse (prices → density) is underdetermined — many densities map to the same price vector
(or, more accurately, to prices differing by less than measurement error). Act III addresses the underdetermination head-on by returning the whole posterior over densities.

### Stage 11 — Parameterize so illegal states are unrepresentable

**What it does:** choose a parameterization of the density in which every point of parameter space is a valid density. No negative regions, no violation of normalization, ever.

**Why it's necessary:** MCMC works by proposing candidate parameter values and evaluating a likelihood. If some proposals are "illegal" (the density they imply is negative somewhere, or doesn't
integrate to 1), you have to either reject them (which fights the sampler and wastes computation) or add a penalty term (which distorts the posterior). The cleaner move is to reparameterize so that
the constraints hold automatically.

**How it works.** Define:

$$f(s; \theta) = \frac{\exp\big(\phi(s; \theta)\big)}{\int \exp\big(\phi(u; \theta)\big) \, du},$$

where $\phi$ is the log-density, built as a linear combination of fixed basis functions:

$$\phi(s; \theta) = \sum_{j=1}^{m} \theta_j B_j(s).$$

-  The $\exp$ makes negativity *impossible*: $e^x > 0$ for every real $x$, and the whole density is $\exp(\text{something}) / \exp(\text{something else})$, which is strictly positive everywhere.
-  The denominator makes integrating-to-1 *automatic*: no matter what $\theta$ is, the numerator divided by its own integral integrates to 1.
-  $\theta$ ranges freely over all of $\mathbb{R}^m$ — every point is a valid probability distribution. The sampler has no boundaries to fight. No rejections. No penalties.

The basis functions $B_j$ are fixed overlapping bump functions (say, cubic B-splines or Gaussian kernels) placed on a grid across the support of $f$. Only $\theta$ moves during sampling; the basis
functions are fixed.

**Why log-space.** A density spans orders of magnitude — a representative crude density might be $0.15$ at the peak and $10^{-8}$ in the wings. That's 7 orders of magnitude. If you tried to
parameterize $f$ directly (say, as a spline in linear space), you'd need extreme dynamic range in the coefficients to represent that. Working in log-space (parameterizing $\phi = \log f$) collapses
those 7 orders of magnitude to a range of 18 (natural log of $10^7$). The spline is on a friendly axis.

There's a second reason log-space is nice: for a lognormal distribution, $\log f$ is a *parabola* (quadratic in $\log s$). And we expect real densities to be lognormal-*ish* (in the sense that
Black-76 is a lognormal model, and the empirical smile is a perturbation of the lognormal). Penalizing curvature of $\phi$ (which we do in Stage 12) says "be close to a straight line in log-space
unless the data insists otherwise," which is a sensible default — straight-in-log-space corresponds to exponentially decaying tails, which is what real risk-neutral densities look like.

**Grid design.** Knots for the basis functions are placed *densely* where strikes are dense (i.e., near the money, where there's a lot of data to fit) and *sparsely* in the wings (where fewer strikes
constrain the fit and the prior does most of the work). The grid extends *well past* the outermost observed strike, so that Kalshi's "Below $\$70$" and "Above $\$99$" brackets have somewhere to
integrate over — the extracted density has to have mass out there, even if no CME strike is listed there.

**Number of coefficients.** Typically 20–30 coefficients for a chain with ~20 observed strikes. Yes, this is *more parameters than observations*. That's intentional. The problem is *genuinely*
underdetermined — many densities fit the data — and the point of the parameterization is not to *reduce* the dimensionality (which would be saying "there is a unique best density") but to *represent*
the uncertainty faithfully. The regularizer (Stage 12), not a shortage of parameters, is what makes the posterior well-defined.

### Stage 12 — The prior

**What it does:** define a prior distribution on $\theta$ that expresses the belief "smooth densities are more probable than wiggly ones," with the smoothness strength controlled by a hyperparameter
$\lambda$ that is itself sampled from a hyperprior.

**Why it's necessary:** with more parameters than observations, the likelihood alone doesn't uniquely determine $\theta$. A candidate density can wiggle wildly *between* strikes while matching every
observed price exactly — the observations are integrals, and integrals don't see between-strike wiggles. Without a prior, the posterior is undefined (or, more precisely, extremely diffuse). The prior
is what regularizes.

**Form.** The prior on $\theta$ (given $\lambda$) is:

$$p(\theta \mid \lambda) \propto \exp\!\Big(-\lambda \int \phi''(u)^2 \, du\Big).$$

This penalizes the integrated squared curvature of the log-density. Smooth curves (small $\phi''$) get high prior probability; wiggly curves (large $\phi''$) get low probability. $\lambda$ controls
the strength of the penalty — large $\lambda$ enforces very smooth, small $\lambda$ allows more wiggle.

**Why curvature specifically?**

-  Penalizing $\phi$ itself would say "be flat" — i.e., pull the log- density toward zero, which is a uniform prior, which makes no sense for a probability distribution.
-  Penalizing $\phi'$ (the slope of the log-density) would say "don't slope" — i.e., prefer flat log-densities, which are exponential in linear space. That's the wrong bias.
-  Penalizing $\phi''$ (the curvature) says "be close to a straight line in log-space" — i.e., prefer densities that are exponential in the wings and Gaussian-ish in the middle, which is what real
  distributions look like.

The generalization to arbitrary orders is Tikhonov regularization; the choice of order (second, in this case) reflects the specific belief about which shapes are a priori plausible.

**Why the hyperprior on $\lambda$ is not optional.** This is the critical point that most textbook treatments of Bayesian density estimation gloss over, and it's exactly the thing that makes
NightKing's tails trustworthy vs untrustworthy.

Here's the setup. In the wings — say, at $F = \$70$ or $F = \$99$ — no CME strike constrains the density. The likelihood has essentially no influence there. The posterior in the wings is *dominated by
the prior*. Whatever the prior says the density looks like in the wings, that's what the posterior says.

So if you *fix* $\lambda$ at some value you picked ahead of time — say, $\lambda = 10$ because that "looks right" on a diagnostic plot — then the tail probabilities of the extracted density are *your
assumption wearing a data costume*. Kalshi's tail brackets are exactly where the tradeable bias might live (both risk premium and favorite-longshot inflate the tails), so having your tail
probabilities be a hand-tuned knob is deeply wrong. It looks like data. It isn't.

**Fix:** put a prior on $\lambda$:

$$\lambda \sim \text{Gamma}(a, b),$$

with $a, b$ chosen to be reasonably diffuse (weakly informative). Then sample $\lambda$ *alongside* $\theta$ in the MCMC. The posterior on $\lambda$ is influenced by the data — if the data has a lot
of constraints on smoothness (which it does at the ATM region, where many strikes cluster), $\lambda$ concentrates on values that fit that constraint. In the wings, $\lambda$'s uncertainty propagates
to uncertainty on the tail density — you get *wider error bars in the wings*, which is exactly what "we don't know much about the tails" should look like.

The slogan: **the wings ARE the prior; put a prior on the prior so that the wings' uncertainty is honest.** If your MCMC output shows narrow error bars in the wings, you have almost certainly
hand-tuned $\lambda$ and are lying to yourself about the tail uncertainty.

### Stage 13 — The likelihood: integrate, don't differentiate

**What it does:** for each candidate $\theta$, compute predicted call prices by integrating the implied density against the payoff, then compare against the observed prices via a Gaussian likelihood
weighted by half-spread.

**Why it's necessary:** this is the crux of Act III. The whole reason Act III doesn't have the noise-amplification problem of the naive estimator is that it operates in the *forward* direction — from
density to prices via integration — rather than the *inverse* direction — from prices to density via differentiation.

**The forward computation.** For candidate $\theta$ and each observed strike $K_i$:

$$\hat C_i(\theta) = e^{-rT} \int_{K_i}^\infty (s - K_i) f(s; \theta) \, ds.$$

This is a numerical integral against a smooth density. It's a *smoothing* operation — the density's local wiggles get integrated over the payoff kernel $(s - K_i)$, which is a linear function. Small
changes in $f$ produce small changes in $\hat C$. There is *no* $1/h^2$ blowup, no catastrophic cancellation, no ill-conditioning. The forward map is well-conditioned, and we're using it in the
direction it's well- conditioned in.

Compare to the naive estimator: the naive estimator computes $f(K_i) \approx (C_{i-1} - 2 C_i + C_{i+1}) / h^2$, which requires differentiating noisy prices twice. Bad idea. Stage 13 avoids the
differentiation entirely.

**The likelihood.** Assume each observed price is corrupted by independent Gaussian noise with standard deviation equal to the half- spread at that strike:

$$p(C^{\text{obs}} \mid \theta) = \prod_{i=1}^{n} \mathcal{N}\big(C_i^{\text{obs}}; \hat C_i(\theta), \sigma_i^2\big),$$

with $\sigma_i = \text{half-spread}(K_i)$.

The **product** over $i$ means the likelihood is small unless *every* strike matches. One badly missed strike drives the product to nearly zero regardless of how well the others match. This is what
you want: you're demanding that the candidate density fit the whole chain, not just the ATM region.

The **weighting by half-spread** means tight quotes discipline the fit hard (the Gaussian is narrow, so small deviations penalize significantly) while wide wing quotes barely constrain (the Gaussian
is wide, so even large deviations don't penalize much). This is the *third* appearance of the "weight by informativeness" principle:

1.  Stage 6 (put-call parity regression): every strike contributes equally, but noise averages by $1/\sqrt{N}$.
2.  Stage 9 (SVI weighted least squares): weight $= 1/\sigma_{\text{IV}}^2 = \text{vega}^2 / \text{half-spread}^2$.
3.  Stage 13 (MCMC likelihood): tolerance $= \text{half-spread}$, so tight quotes contribute more.

In each case, the operational statement is: *quotes with tighter bid-ask spreads are more informative and should have more weight.*

**Numerical hygiene.** In practice, work in log space (sum of squared standardized residuals):

$$\log p(C^{\text{obs}} \mid \theta) = -\frac{1}{2} \sum_i \frac{(C_i^{\text{obs}} - \hat C_i(\theta))^2}{\sigma_i^2} + \text{const}.$$

Products of small Gaussians underflow to zero in double precision; the sum of squared standardized residuals doesn't. This is standard MCMC practice; the sum is what NUTS actually operates on.

### Stage 14 — The martingale constraint

**What it does:** add a term to the likelihood that constrains $\mathbb{E}_\theta[F_T] \approx F_0$, where $F_0$ is the forward from Stage 6.

**Why it's necessary:** OTM option prices are insensitive to the *location* of the density. Specifically: if you shift the whole density left or right by a small amount $\delta$ while keeping its
shape, the predicted OTM prices change only slightly, because the payoff $(s - K)^+$ is a linear function of $s$ and the shift's effect on each integral is a small first-order correction. So the
location of the density is only *weakly* identified by the OTM prices themselves.

But location matters enormously for the bracket comparison. A density mis-centred by $\$0.30$ produces bracket probabilities that are all biased in the same direction — the mean-equals-forward failure
mode from Part 2, §2.6. That's the fedarb -8pt reincarnated.

**The constraint.** Add a Gaussian factor to the likelihood:

$$\mathcal{N}\big(F_0; \mathbb{E}_\theta[F_T], \sigma_F^2\big),$$

where $\sigma_F$ is a small but nonzero tolerance (say, 5 cents — the uncertainty of $F_0$ from the parity regression in Stage 6).

**Why not a hard constraint.** A hard constraint ( $\mathbb{E}_\theta[F_T] = F_0$ exactly) would create a boundary in parameter space and mess with MCMC dynamics. A soft Gaussian constraint with a
tight tolerance does the same job without the boundary. It also correctly handles the fact that $F_0$ from Stage 6 has its own uncertainty (the regression has residuals; the intercept has a standard
error). Using a Gaussian with $\sigma_F$ = parity-regression standard error is the honest choice.

**Development diagnostic.** Run the MCMC *once without* the martingale constraint, and check whether the posterior mean of $\mathbb{E}[F_T]$ lands on $F_0$ unaided. If yes, Stages 6–13 are internally
consistent and Stage 14 is just belt-and-suspenders. If no, there's a bug upstream — and *adding the constraint would mask the bug*. This is a subtle but important point: constraints hide problems as
easily as they fix them, and adding a constraint before you've verified the underlying inconsistency is a way to ship a broken pipeline that looks fine.

**Failure mode addressed.** The most dangerous artifact in options extraction: a mis-centred density that is smooth, convex, normalized, fits every price to within the half-spread, and produces a
persistent sign-consistent bias against every Kalshi bracket. Stage 14 makes this artifact impossible by construction. Combined with Stage 6, the location is pinned twice (once from the chain via
parity, once from the density's mean during MCMC), and both anchors have to be consistent with each other.

### Stage 15 — MCMC

**What it does:** sample from the posterior distribution $p(\theta, \lambda \mid C^{\text{obs}})$ using Hamiltonian Monte Carlo with NUTS (No-U-Turn Sampler), or if gradients aren't available,
random-walk Metropolis as a fallback.

**Why it's necessary:** the posterior lives in 20–30 parameter dimensions plus $\lambda$. Grid-based methods are impossible — even 10 points per dimension gives $10^{30}$ evaluations, which is
astronomical. Rejection or importance sampling would require a proposal distribution close to the posterior, which we don't have. MCMC is the standard tool for high-dimensional posterior sampling.

**Why HMC/NUTS specifically.** Random-walk Metropolis explores parameter space by taking small local steps. In high dimensions with strong correlations between parameters (which is what
curvature-penalized splines have — adjacent coefficients are correlated), random-walk Metropolis mixes extremely slowly. You'd need millions of iterations to get a decent effective sample size.

HMC uses the gradient of the log-posterior to move *ballistically* through parameter space, taking long trajectories that respect the posterior's local geometry. It's dramatically more efficient in
high dimensions. NUTS is an adaptive variant that picks trajectory lengths automatically. For 20–30 dimensional problems with a smooth log- posterior, NUTS is close to state-of-the-art.

The gradient requires you to differentiate the forward map with respect to $\theta$ — which is doable, either by hand or by automatic differentiation. If the pipeline is implemented in JAX or PyTorch
or Julia, AD handles this for free.

**Convergence diagnostics are not box-ticking here.** In many MCMC applications, you can get away with running enough iterations and inspecting a trace plot. Here, that's not enough. The reason:

>  **The spread IS the deliverable.**

If the chain hasn't mixed properly — hasn't fully explored the posterior — the *sampled* spread of the density will be narrower than the *actual* posterior spread. That means the credible intervals on
bracket probabilities will be narrower than they should be, which means the trade filter (Stage 19) will see more brackets as "tradeable" than actually are. **A badly-mixed chain manifests as false
trading signals.** Not a bad-looking plot. A false trade.

Standard diagnostics:

-  $\hat R < 1.01$ — the potential scale reduction statistic, which compares within-chain variance to between-chain variance across multiple independent chains. Values close to 1 indicate mixing.
-  Effective sample size $\gtrsim 400$ per parameter — the actual number of independent-equivalent samples, given the autocorrelation of the chain. High autocorrelation means low ESS.
-  Trace inspection — visually verify that the chains are stationary and mixing between modes if any exist.
-  Divergence count — HMC has a specific pathology (divergent trajectories) that indicates the sampler is failing to explore some region of parameter space. Zero or near-zero divergences are the goal.

If any of these fail, the fix is to reparameterize (e.g., a non- centred parameterization if the sampler is failing due to funnel geometry), tighten the priors, or add more integration steps. Do *not*
simply run longer chains — long chains from a broken sampler are still broken.

**Output.** The MCMC produces a posterior sample of $(\theta^{(1)}, \lambda^{(1)}), \ldots, (\theta^{(M)}, \lambda^{(M)})$ of size $M$ (typically several thousand after burn-in and thinning). Each
sample $\theta^{(m)}$ gives you a full density $f(\cdot; \theta^{(m)})$ via Stage 11's parameterization. So the deliverable is *thousands of concrete densities*, each consistent with the observed
prices and the smoothness prior.

## Act IV — from density to decision

Act IV takes the ensemble of posterior densities from Act III and turns it into per-bracket probabilities with credible intervals, then compares those against Kalshi and decides which brackets are
tradeable.

### Stage 16 — Range probabilities, and why they are the robust quantity

**What it does:** for each Kalshi bracket $[a, b]$, compute the posterior distribution over the risk-neutral probability of finishing in that bracket:

$$p^{(m)}[a, b] = \int_a^b f(s; \theta^{(m)}) \, ds \quad \text{for } m = 1, \ldots, M.$$

The mean of $\{p^{(m)}[a, b]\}$ over the posterior samples is the point estimate. The 5th and 95th percentiles are the 90% credible band. The spread of the posterior is what tells you how much you
should trust the point estimate.

**Why range probabilities are the robust quantity.** Here's the critical identity that justifies the whole "compare ranges, not points" design of the strategy:

$$\mathbb{Q}(a < F_T < b) = F(b) - F(a) = e^{rT} \big[ C'(b) - C'(a) \big].$$

The right-hand side depends on the *first* derivative at two points, not on the second derivative anywhere. It's not a density evaluation. It's a difference of two survival probabilities.

Discretely, this is a **telescoping sum**. If you write the range probability as a sum of butterflies:

$$\sum_{i=j}^{k} \big[ C_{i-1} - 2 C_i + C_{i+1} \big] = C_j - C_{j-1} - C_k + C_{k+1} = -(C_{k+1} - C_k) + (C_j - C_{j-1}),$$

wait, let me redo this more carefully. The butterfly at strike $K_i$ (with unit spacing) has payoff peaking at $K_i$ and price $C_{i-1} - 2 C_i + C_{i+1}$. Summing butterflies from $i = j$ to $i = k$:

$$\sum_{i=j}^{k} (C_{i-1} - 2 C_i + C_{i+1}) = (C_{j-1} - C_j) + (C_{k+1} - C_k).$$

Every interior term cancels — the coefficient of $C_i$ for $j < i < k$ is $1 - 2 + 1 = 0$. Only the endpoint terms survive. That's telescoping.

**Consequence for numerical robustness.** The naive Breeden–Litzenberger estimator gives you a point density via the noisy second difference at each strike. Adding those noisy second differences to
get a range probability sounds like it would add noise linearly — but the algebraic cancellation means the interior noise *cancels exactly*. What survives is only the noise at the two endpoints, which
is a first-difference noise (not amplified by $1/h$, unlike the second difference).

The **hierarchy of numerical robustness** is:

| quantity | operation on prices | how noise flows |
|---|---|---|
| point density $f(K)$ | 2nd derivative | amplified $\sim 1/h^2$ |
| threshold prob $\mathbb{Q}(F_T > K)$ | 1st derivative | amplified $\sim 1/h$ |
| **range prob $\mathbb{Q}(a < F_T < b)$** | **integral** (or diff of 1st derivs) | **averaged / cancelled** |

**This is why the strategy is built on range-vs-bracket comparisons, not point-vs-point comparisons.** Kalshi's brackets *are* ranges. The comparison is like-for-like. And it happens to land on the
most numerically robust quantity you can extract from an options chain.

There is a *second* robustness advantage: range probabilities let you choose the endpoints. The bracket edges are what they are (set by Kalshi), but you can pick which CME strikes anchor the first
differences on either end. Pick the densest, tightest-quoted strikes you have. The strategy naturally routes its estimate through the region of the strike axis where measurement is strongest.

### Stage 17 — Compare like with like

**What it does:** for each Kalshi bracket $j$, compute the gap $g_j = p^{\text{mkt}}_j - \bar p^{\mathbb{Q}}_j$, where $p^{\text{mkt}}_j$ is the Kalshi bracket price (the executable price, not the mid
— see Part 7) and $\bar p^{\mathbb{Q}}_j$ is the posterior mean of the integrated density over that bracket's edges.

**Why it's necessary:** the gap is the raw signal. It's what the strategy is trying to characterize.

**But: the gap is not the edge.** By construction, part of the gap is risk premium (institutional side, Force 1 from Part 1) and part is favorite-longshot bias (retail side, Force 2). The gap is a
*scalar per bracket*, and there are typically ~25 brackets, so you have ~25 gap values. Stage 18 fits a model to the vector of gaps to separate the innocent components from the residual.

### Stage 18 — Decompose the gap by fingerprint

**What it does:** for each posterior sample $m$ of the density (hence each set of implied $p^{\mathbb{Q}}_j$ values), fit a logistic regression of Kalshi bracket prices on the density-implied
probabilities plus a state variable:

$$\text{logit}\big(p^{\text{mkt}}_j\big) = a + b \cdot \text{logit}\big(p^{\mathbb{Q}, (m)}_j\big) + c \cdot m_j + \varepsilon_j,$$

where $m_j$ is the bracket midpoint (a natural state variable — the midpoint price of the bracket).

Running this regression per posterior sample gives you a *distribution* over $(a, b, c)$. Not a point estimate of each coefficient — a full posterior credible interval on each.

**Why the logit transform.** Probabilities are bounded to $[0, 1]$; raw regressions on probabilities can produce fitted values outside $[0, 1]$, which is invalid. The logit transform
$\text{logit}(p) = \log(p / (1 - p))$ maps $[0, 1]$ to $(-\infty, +\infty)$. So a linear regression in logit space produces fitted values in $(-\infty, +\infty)$, and you can inverse-logit them back
to $[0, 1]$ if you need probabilities out. Standard move.

**Interpretation of the coefficients.**

-  **$b = 1$ (and $a = 0, c = 0$)**: the Kalshi price is exactly the density-implied probability, in logit space. No bias, no lean. The two venues agree.
-  **$b < 1$**: **favorite-longshot bias.** Look at a longshot bracket, where $p^{\mathbb{Q}} = 0.05$. In logit space, $\text{logit}(0.05) = -2.94$ (very negative). Applying a shrinkage $b < 1$ makes
  it *less negative*, say $\text{logit}(p^{\text{mkt}}) = -2.94 \cdot 0.7 = -2.06$, which corresponds to $p^{\text{mkt}} = 0.113$. So the Kalshi price is *higher* than the density-implied probability
  — the longshot is overpriced. For a favorite ($p^{\mathbb{Q}} = 0.95$), $\text{logit} = +2.94$, shrunk to $+2.06$, $p^{\text{mkt}} = 0.887$ — the favorite is underpriced. That's the whole
  favorite-longshot bias, in one parameter. $b$ measures the *strength* of the shrinkage.
-  **$c \ne 0$**: **risk-premium tilt.** The bracket midpoint $m$ is a proxy for the state (the underlying price). A nonzero $c$ means the gap is systematically related to *where* on the state axis
  the bracket sits — i.e., a monotone lean, which is what a pricing kernel produces when transforming $f^{\mathbb{P}}$ to $f^{\mathbb{Q}}$. $c > 0$ means Kalshi is biased upward in higher states;
  $c < 0$ means downward. The sign is empirical.
-  **$a \ne 0$**: a location bias in logit space that isn't captured by shrinkage or state-monotone tilt. Usually should be near zero; if it's significantly nonzero, that's a warning.
-  **$\varepsilon_j$**: the residual per bracket. This is where any *actual mispricing* would show up — after accounting for the regression's fit of the two innocent forces, whatever's left is a
  candidate for the tradeable component.

The regression is run **per posterior sample**, so what you get is a posterior distribution over $(a, b, c)$ and over the residuals $\{\varepsilon_j\}$. Instead of "is $b < 1$?" you can ask "is the
95% credible interval on $b$ entirely below 1?" That's a Bayesian hypothesis test with real error bars, propagated from the density extraction uncertainty all the way through to the regression.

**When Stage 18 is optional vs mandatory.** In a perfectly hedged trade held to settlement (Case 1 from Part 5), the gap decomposition is strictly not needed: both legs resolve on the same underlying
number, and you keep the gap regardless of what caused it (risk premium, mispricing, whatever). You don't need to know which was which.

Stage 18 becomes **mandatory when the hedge is imperfect.** With discrete strikes (which is always the case in practice), the hedge has a residual ramp (see Stage 20). That residual is retained
exposure to the underlying. If the "gap" you're harvesting is actually risk premium, then the retained residual is *exactly the exposure the risk premium was compensating for* — you're selling
insurance, not arbitraging. That's a very different trade with a very different risk profile. Stage 18 tells you which one you're in.

### Stage 19 — The trade filter

**What it does:** decide, per bracket, whether to trade it.

**Rule.**

$$\text{trade bracket } j \iff |g_j| > \underbrace{\text{posterior spread}_j}_{\text{credible band width}} + \underbrace{\text{friction}_j}_{\text{fees + spreads, both legs}}.$$

-  **Posterior spread** is the width of the 90% credible band on $p^{\mathbb{Q}}_j$ (from Stage 15's MCMC output). If the extracted probability has a wide credible interval — because the density is
  poorly constrained in that region, or because $\lambda$ is uncertain — then a small $|g_j|$ isn't distinguishable from measurement noise. Wide bands raise the trade threshold.

-  **Friction** is the total round-trip transaction cost: Kalshi's bracket spread and fees on one leg, plus the CME options structure's spread and fees on the other. All-in, per contract, per side.

Only when $|g_j|$ exceeds *both* the posterior uncertainty and the transaction cost do you trade. This is the "gap is not an edge" discipline made mechanical.

**Note on symmetry.** The filter uses $|g_j|$ because you can trade either direction: if $p^{\text{mkt}}_j > \bar p^{\mathbb{Q}}_j$ (Kalshi too expensive), sell Kalshi and buy the equivalent options
structure; if $p^{\text{mkt}}_j < \bar p^{\mathbb{Q}}_j$ (Kalshi too cheap), buy Kalshi and sell the equivalent options structure. The sign of the gap determines direction; the magnitude determines
whether to trade at all.

## Act V — execution

### Stage 20 — Building the bracket digital

**What it does:** replicate a Kalshi bracket digital (pays $1 if $a \le F_T < b$, $0 otherwise) using CME options.

**Why it's necessary:** you need a hedge. If you buy a Kalshi bracket because the density says it's underpriced, you want to be *cash-neutral at settlement* — the P&L on the Kalshi side should be
offset by the P&L on the options side, and you keep only the gap you locked in. That requires a hedge that pays the same digital payoff. From CME's product suite, the only way to build that digital
payoff is with a portfolio of options.

**Single digital: the limit of a call spread.** Start with the case of a *one-sided* digital at strike $K$ (pays $1 if $F_T > K$, $0 else). This is the limit of a call spread as the width goes to
zero:

$$D(K) = \lim_{\varepsilon \to 0} \frac{C(K - \varepsilon) - C(K + \varepsilon)}{2 \varepsilon} = -\frac{\partial C}{\partial K} = e^{-rT} \mathbb{Q}(F_T > K).$$

**The loop closes.** This is exactly the first-derivative object from Stage 2 — the survival function, which is the digital price. So a Kalshi "above $K$" contract is the same object as
$-\partial C / \partial K$, which is the same object as the limit of a call spread. Three different lenses on the same thing.

**Bracket digital = two one-sided digitals.**

$$\mathbb{1}\{a \le F_T < b\} = \mathbb{1}\{F_T > a\} - \mathbb{1}\{F_T > b\}.$$

So the bracket digital's price is $D(a) - D(b)$. Replicated as call spreads, that's four option legs: long $C(a - \varepsilon)$, short $C(a + \varepsilon)$, short $C(b - \varepsilon)$, long
$C(b + \varepsilon)$. This is your hedge.

**Two consequences that cannot be designed away.**

### The ramp

The problem: $\varepsilon$ cannot go to zero because strikes are *discrete*. The finest strike spacing CME lists is $\$0.25$ on WTI weeklies, so the smallest call spread you can build has
$\varepsilon = 0.125$ (a $0.25$ spread centred on the bracket edge).

The consequence: the "digital" you build with a $0.25 spread isn't a sharp step from $0$ to $1$ at strike $K$; it's a *ramp* that rises linearly from $0$ (at $F_T = K - \varepsilon$) to $1$ (at $F_T =
K + \varepsilon$). Inside the ramp region, the option spread pays somewhere between $0$ and $1$ while the Kalshi bracket pays either $0$ or $1$ sharply. The legs don't cancel inside the ramp — you
have residual exposure.

**Design trade-off.** A narrower ramp (smaller $\varepsilon$) means a tighter hedge but more contracts (because you need more call spreads to cover the same notional) and more fees. A wider ramp means
fewer contracts and lower fees but a bigger uncovered residual. This is a design parameter, and it's what sets the real maximum loss on the trade — the loss when $F_T$ lands inside the ramp.

There is no way to make the ramp zero; the only way to make it smaller is to trade smaller (finer) strikes if the exchange lists them. CME doesn't list finer than $0.25 on WTI weeklies, so the ramp is
set by the exchange.

### Granularity

The problem: options come in fixed contract sizes. Standard CME crude options are on 1,000 barrels each, so one $0.50-wide call spread has maximum payoff $500
($0.50 × 1,000). If you're hedging Kalshi contracts that pay $1 each, one options structure hedges $500 Kalshi contracts. You cannot fractionally hedge fewer.

Micro WTI options are on 100 barrels each, so a $0.50-wide micro spread has max payoff $50. That hedges 50 Kalshi contracts per structure.

**Consequence for the trade.** You can't trade a fraction of an option, so the granularity of the hedge sets the *minimum hedged unit*. If Micro is available (100-barrel contracts), your minimum is 50
Kalshi contracts per bracket. If only standard CL is available (1,000-barrel), your minimum is 500. That in turn sets the *minimum depth requirement on the thin leg* (Kalshi), because you have to be
able to actually get filled on 50 or 500 contracts without cratering the price. Part 6.2 verifies that Kalshi depth clears at 50 Micro-sized. It does not clear at 500 standard-sized.

**This decides the contract choice.** Not preference: data. If the Kalshi book won't fill the minimum unit for standard-sized structures, you can't run standard structures. Micro it is.

### End of the pipeline

That's twenty stages. The pipeline maps from raw options quotes and raw Kalshi ladder quotes to a per-bracket trade decision plus the concrete four-leg options structure to hedge it. Every stage
exists to prevent a specific failure mode:

-  Stages 1–5 establish and analyze the identity (why we need the pipeline at all).
-  Stages 6–10 clean the prices before differentiating (Act II).
-  Stages 11–15 avoid differentiating entirely (Act III).
-  Stages 16–19 convert densities to trade decisions with proper uncertainty propagation.
-  Stage 20 hedges the trade with a real portfolio.

The next parts turn this into a trade structure and empirical program.

---

# Part 5 — Trade structure

The pipeline gives you per-bracket trade decisions and a four-leg options structure per trade. Part 5 is about the *structure of the trade itself* — what you actually do at execution, how you size it,
which contract you use, and why the legal/entity infrastructure that was necessary for earlier crypto strategies is *not* necessary here.

## 5.1 Case 1 versus Case 2 — the load-bearing distinction

There are two ways to run the strategy, and choosing between them is not a design detail — it's the fundamental commitment that determines whether the strategy is trading arbitrage or trading a
directional bet dressed up in arbitrage clothing.

### Case 1: both legs, held to settlement

**The setup.** Sell the CME options structure at bracket edges $a$ and $b$. Simultaneously buy the Kalshi bracket. Hold both to settlement. At settlement, both legs resolve on the same underlying
number (WTI weekly settlement), and their P&Ls cancel out except for the gap you locked in at execution.

More precisely: if you sold the options structure for $\$X$ and bought the Kalshi bracket for $\$Y$, and both legs pay the same digital payoff (which they do, up to the ramp — see below), then at
settlement:

-  If $F_T$ lands inside $[a, b]$: options structure pays $\$1$, Kalshi pays $\$1$. Your P&L per structure: $X - Y - 1 + 1 = X - Y$.
-  If $F_T$ lands outside $[a, b]$: options structure pays $\$0$, Kalshi pays $\$0$. Your P&L: $X - Y$.

Either way, you keep the difference $X - Y$ (the gap you locked in), regardless of what caused the gap in the first place. **You never need to know whether the gap was risk premium, favorite-longshot
bias, mispricing, or a bug in the extraction.** All three innocent components and the tradeable component collapse into the single P&L number.

This is the design target. When the strategy works, it works because Case 1 works.

### Case 2: use the options number as "truth" and bet Kalshi directionally

**The trap.** Skip the CME hedge. Interpret the options-implied probability as the "true" probability, and bet Kalshi directionally on the difference.

Concretely: if options imply $\mathbb{Q}(F_T \in [a, b]) = 0.10$ and Kalshi is priced at $0.06$, the naive Case 2 view is "Kalshi is $0.04$ too cheap; buy Kalshi." You buy at $0.06$, hoping to
eventually see it converge to $0.10$ and sell for a profit — or hoping that settlement lands in the bracket 10% of the time, giving you $\$1 - 0.06 = \$0.94$ per fill 10% of the time and losing
$\$0.06$ 90% of the time, for expected P&L $= 0.10 \cdot 0.94 - 0.90 \cdot 0.06 = 0.094 - 0.054 = \$0.04$.

**The problem.** *If* the options number is the true probability, this math is correct. But **the options number is $\mathbb{Q}$, not $\mathbb{P}$.** It's the risk-neutral probability, inflated by
hedging premium. The *real* probability that $F_T$ lands in $[a, b]$ might be $0.06$, and the $0.10$ from options is the retailer overpaying for hedging in that region.

If that's the case, then betting Kalshi directionally has *zero expected P&L* — Kalshi's $0.06$ is the true probability, and you're betting on a fair coin. **You have zero edge while believing you
have four points**, and you'd size accordingly. The bet doesn't just fail to work; it fails while looking like it's working, because you're using a biased number as your benchmark for "truth."

### The commitment

The strategy is built for Case 1 exclusively. That decision has consequences:

-  **More work per trade.** Case 1 requires the four-leg options structure, which involves four executions at potentially different times, margin management for the two written legs, and monitoring
  the discrete-strike ramp.
-  **More capital.** Options margin plus Kalshi collateral, held for the full week to settlement.
-  **Harder ops.** Two exchanges to reconcile, two settlement procedures, matched expiry dates required (see Part 6.3 on the CME-weekly-calendar fix).
-  **The frictions push toward Case 2.** Every time an execution is slow, or a leg partially fills, or the margin is annoying, there's a temptation to skip the CME hedge. "It's just a small position,
  Kalshi is cheap, let's just buy it." That's Case 2 with extra steps.

**Resisting that drift is a standing discipline, not a one-time choice.** Every time a trade opportunity comes up, ask: am I doing Case 1 or Case 2? If Case 2, don't trade. This is worth stating
explicitly because it's the failure mode that quietly kills strategies — you build for Case 1, you actually run Case 2 because it's easier, and you lose money because Case 2 has no edge.

### Note on the intraday variant

A related trap: "enter and exit before market close, no overnight exposure." Sounds like it reduces risk. It quietly assumes you *can* exit.

On a thin prediction-market book, the exit may not exist. You entered because Kalshi was cheap; if the reason it was cheap was a temporary imbalance and it fills back up, great, you exit. But if the
reason it was cheap was a *structural* mispricing that hasn't corrected — or worse, has gotten *worse* — you can't unwind at a good price. And the force that guarantees convergence between the two
venues (both legs settling on the same number) *only fires at settlement*. Before settlement, nothing links them.

So an intraday plan on a thin book silently becomes a hold-to- settlement plan anyway — but unhedged, unplanned, and un-sized for that. **Size as hold-to-settlement.** Treat early exit as a bonus if
it happens.

## 5.2 Sizing rules

Two rules, fixed now while there is no money on the line. This is on purpose: sizing rules committed to before deployment are much less likely to bend under the pressure of an actual trade opportunity
than sizing rules invented on the fly.

### Rule 1: Size as hold-to-settlement

Assume you cannot exit early. Do not size for the "expected P&L across a 5-day holding period assuming average liquidity," because that expected value depends on assumptions about liquidity that may
not hold at the moment you actually want to exit.

Instead, size for the worst-case outcome at settlement, discounted back to today, and ensure that even that worst case is survivable at the position size you're taking.

### Rule 2: Size for the unhedged residual, not the locked gap

With discrete strikes, the hedge has a ramp (Stage 20). If settlement lands inside the ramp, the two legs don't offset perfectly — you have residual exposure. Model the worst case where settlement
lands *exactly inside the ramp* and the legs are maximally uncanceled. That plus any settlement basis (see Part 6.3) is the *real* max loss.

Do not size to "the gap I locked in" as though it were guaranteed — the gap is only guaranteed *outside the ramp*. Inside the ramp, you're exposed. Size for that exposure.

### The mechanical form of the rules

For each candidate trade:

1.  Compute the maximum loss inside the ramp: $\text{max\_loss\_ramp} = \text{ramp\_width} \times \text{contracts} \times \text{options\_notional}$.

2.  Compute the maximum loss from cross-exchange basis (Part 6.3): $\text{max\_loss\_basis} = \text{expected\_basis\_std\_dev} \times \text{sensitivity}$.

3.  The total max loss per trade is $\text{max\_loss} = \text{max\_loss\_ramp} + \text{max\_loss\_basis}$.

4.  Position size is capped so that $\text{max\_loss} \le \text{risk\_budget\_per\_trade}$, where the risk budget is set at the portfolio level as a fraction of total capital.

## 5.3 Contract selection: Micro WTI vs standard CL

The choice of underlying contract is not a preference. It's data-driven.

### Why the choice matters

Options on standard CL crude futures are on 1,000 barrels per contract. Options on Micro WTI crude futures (ticker /MCL) are on 100 barrels per contract. A
$0.50-wide call spread on standard CL has max payoff $\$500$; on Micro, $\$50$.

The four-leg options structure (Stage 20) hedges roughly one options-payoff unit per structure. So:

-  Standard CL structure hedges ~500 Kalshi contracts per structure.
-  Micro CL structure hedges ~50 Kalshi contracts per structure.

The minimum hedged unit is the granularity of the strategy.

### The Kalshi depth constraint

Kalshi depth is measured empirically: how many contracts can you buy or sell without cratering the price? Part 6.2 records a live orderbook scan showing that at 50 contracts, all nine moderate-tail
brackets on KXWTIW cleared both sides with zero slippage and 1–2¢ spreads. At 500 contracts, the ask side failed in 6 of 9 brackets.

So: **standard CL cannot fill the minimum hedged unit at Kalshi.** If you tried to run standard CL, you'd either not get filled (which kills the trade), or you'd move the Kalshi price by more than the
gap you were trying to trade (which kills the P&L).

Micro CL clears. Micro CL is the contract.

### What this looks like in practice

Micro WTI has been listed since July 2021. Liquidity in the front month is decent — bid-ask spreads on Micro are typically wider than on standard CL (because there are fewer market makers), but the
weekly options on Micro have real quotes at the relevant strikes. Volumes are much smaller than standard, but that's fine for the strategy's size.

The trade-off: Micro has wider spreads. So the *friction* term in the trade filter (Stage 19) is larger for Micro than it would have been for standard. But since standard doesn't clear at Kalshi
anyway, the comparison is moot — Micro is the only option.

## 5.4 Why the entity structure is not needed

The original ArbCoin design (BVI parent, Delaware subsidiary) existed to reach offshore crypto venues that exclude US persons. It was a legal-structure-driven strategy: the edge existed *because* US
regulation walled off US persons from global crypto, and the entity structure was how you got around the wall.

**NightKing does not need this.** Both legs are US-regulated:

-  **Kalshi** is a CFTC-designated contract market (DCM). Anyone with a Kalshi account can trade Kalshi.
-  **CME** is CME. Anyone with a futures-enabled brokerage account (tastytrade, Interactive Brokers, TD, etc.) can trade CME options.

There is no legal barrier between the two venues. There is no need for an offshore entity, no need for a KYC evasion, no CFTC extraterritoriality concern, no need to move to Puerto Rico for tax
purposes. It's a trade any US individual can put on with two brokerage accounts.

This is a major reduction in operational complexity from the earlier crypto plan. It also means the strategy is *fully compliant by construction* — nothing about it depends on hiding from any
regulator, so there's no future-regulation risk that could unwind the trade.

## 5.5 Why latency infrastructure is not needed

fedarb measured wedge decay in about 20 minutes (median half-life). That's slow. If the same order of magnitude holds for NightKing (which is an empirical question — WTI markets may be faster or
slower than Fed-rate markets), then colocation and low-latency execution are irrelevant. You can put the trade on manually at a Bloomberg terminal.

More generally: this is a *hold-to-settlement* trade on *weekly* contracts. The whole holding period is a week. The exposure to milliseconds of latency is negligible against a week of price movement.
Even a couple of minutes of execution lag is fine.

Consequence: no expensive infrastructure. A laptop, two brokerage accounts, and a spreadsheet is enough.

---

# Part 6 — Empirical findings to date

The pipeline is theoretical, but everything about the strategy that can be tested against real data *before* deploying capital gets tested first. This part records what's been empirically verified so
far.

## 6.1 Within-venue arbitrage: ruled out

**The check.** Kalshi RANGE ladders are mutually exclusive and exhaustive: exactly one bracket pays $\$1$ at settlement, and no more than one. If you can buy every bracket for a total cost less than
$\$1.00$, you have a locked profit — you've bought a guaranteed $\$1$ payoff for less than $\$1$.

**The measurement.** On a live scan of KXWTIW (Kalshi's weekly WTI range ladder, 27 brackets), the sum of ask prices across all brackets was $\mathbf{127.0\text{¢}}$. Payoff: $\$1.00 = 100\text{¢}$.
Difference: $27\text{¢}$, which is exactly $27 \times 1\text{¢}$ — the per-bracket spread. Pure friction, no anomaly.

**Conclusion.** Within-venue arbitrage on Kalshi range ladders is dead. Not that it might be dead — measurably, decisively dead. It took five minutes to establish.

### Methodological note: the false-positive scan

An earlier scan reported *47 "arbitrage" signals*. All false positives. The bug: the scan summed *cumulative* ladders as if they were mutually exclusive.

A cumulative ladder is a series of "Above $K$" contracts for increasing $K$: "Above $\$85$", "Above $\$86$", "Above $\$87$", ... These are *nested*, not exclusive. Every bracket that pays $\$1$ has
all the bracket*below it also paying $\$1$ (because if $F_T > \$87$ then $F_T > \$86$ and $F_T > \$85$).

The correct check on a cumulative ladder is *monotonicity*: $\mathbb{Q}(F_T > K_1) \ge \mathbb{Q}(F_T > K_2)$ for $K_1 < K_2$. Under this correct check, only 3 monotonicity violations were found
across 78 cumulative ladders, and all three were untradeable (resting sizes of 1, 2, and 100 contracts).

**Lesson.** Kalshi's event objects carry the field `mutually_exclusive` as a boolean, which distinguishes RANGE from CUMUL ladders definitively. The original bug was *inferring* the ladder type from
label text ("Above X" vs "X to Y") instead of reading the authoritative field. Verify, don't infer.

This shows up in the repo as `kalshi_common.py`:

```python
def ladder_kind(mutually_exclusive: Any, labels: Optional[List[str]] = None) -> Tuple[str, str]:
    """(kind, source). VERIFIED: event.mutually_exclusive is definitive."""
    if isinstance(mutually_exclusive, bool):
        return ("RANGE" if mutually_exclusive else "CUMUL"), "mutually_exclusive"
    # ... fallback to label parsing only if the boolean is missing
```

The fallback to label parsing exists for old events where the field wasn't present, but it's marked as a fallback and its source is recorded on every row for downstream diagnostics.

## 6.2 Depth: the fedarb killer, cleared at Micro size

**The check.** For each moderate-tail bracket on KXWTIW (probabilities in the 5–20¢ range, which is where the favorite-longshot bias should show up most strongly), record the best bid, best ask, and
resting sizes on both sides. Then simulate the market impact of buying and selling 50 contracts and 500 contracts on each bracket.

**The measurement (one snapshot).**

| bracket | bid | resting bid size | ask | resting ask size |
|---|---|---|---|---|
| Above $95.99 | 13¢ | 5,284 | 14¢ | 3,100 |
| $94.00–94.99 | 5¢ | 1,556 | 6¢ | 1,200 |
| $93.00–93.99 | 7¢ | 1,131 | 8¢ | 950 |
| $89.00–89.99 | 8¢ | 1,071 | 9¢ | 800 |
| (and 5 more brackets — 9 total in the 5–20¢ range) | | | | |

At **50 contracts per side**, all nine brackets cleared with **zero slippage** and 1–2¢ spreads. Depth was more than enough at that size.

At **500 contracts per side**, the ask side failed in 6 of 9 brackets — i.e., you couldn't get filled for 500 contracts at the top-of-book price; you'd have to walk the book and pay materially worse
prices.

**Consequence for contract choice.** The Micro CL structure hedges 50 Kalshi contracts (Part 5.3). The standard CL structure hedges 500. Kalshi cleared 50, didn't clear 500. So the strategy runs on
Micro CL. This is a data-driven decision, not a preference.

### Contrast with fedarb

fedarb's minimum hedged unit ate 2¢ of depth on the first snapshot, which was the killer — 2¢ of friction on a 4¢ signal.

NightKing's Micro-sized structure, at 50 contracts, ate essentially no depth on the Kalshi side. First time the depth gate has cleared for this class of strategy.

### Important caveat

**One snapshot at one instant.** Kalshi's depth is not necessarily representative across the trading session. Someone with 5,000 contracts resting at 13¢ might pull them at any moment. Depth needs to
be *sampled* across a session — many snapshots, at different times of day, on different days of the week — before this can be a conclusion rather than a hint.

This is listed in Part 8 as an open item owned by the operator.

## 6.3 Settlement sources: the finding that constrains everything

Kalshi's event objects carry a field `settlement_sources`, a list of name/URL pairs stating what the exchange uses to determine settlement. This field is authoritative — it's what Kalshi looks at when
the market resolves.

**The measurement.** Query `settlement_sources` for the five main commodity series:

| series | settles on | ladder type | implication |
|---|---|---|---|
| KXWTIW (weekly) | **ICE** WTI Crude Futures | RANGE | hedgeable, but cross-exchange basis |
| KXWTI (daily) | **ICE** WTI Crude Futures | CUMUL | same |
| KXBRENTD | **Pyth** — Brent | CUMUL | aggregated oracle index |
| KXGOLDD | **Pyth** — Gold | CUMUL | aggregated oracle index |
| KXNATGASD | **Pyth** — NATGAS | CUMUL | aggregated oracle index |

### On the ICE finding

Kalshi settles WTI weekly on ICE (Intercontinental Exchange) — not on NYMEX (CME's crude venue). The natural CME hedge is a NYMEX CL option. So the hedge is:

-  Kalshi: bracket digital settling on **ICE** WTI weekly.
-  CME: options structure settling on **NYMEX** CL weekly (via exercise into a NYMEX CL futures contract).

Both track "WTI crude oil for delivery to Cushing, OK" on the same nominal expiration date. But the two exchanges do their own settlement procedures, potentially referencing different snapshot times
or different trades. The **basis** — the difference between ICE-settled WTI and NYMEX-settled WTI on the same date — is typically very small (a few cents, arbitraged tightly by professional
cross-exchange traders), but it's *not* zero.

**Implication.** The hedge is not perfect. There is a residual whose size is the ICE/NYMEX basis, and that basis is a random variable on each expiry.

**What to measure (Part 8 next steps).** Not correlation — the correlation between ICE and NYMEX WTI is going to be ~0.999, and that tells you essentially nothing about the strategy risk. The relevant
quantity is the **distribution of the difference**:

-  **Mean offset:** if ICE consistently settles $\$0.05$ above NYMEX, the strategy has a systematic bias (every bracket comparison is shifted by $\$0.05$ of "true" underlying).
-  **Standard deviation:** the noise on the residual. This is unhedged P&L noise. On a $\$1$-wide bracket, even $\$0.20$ of settlement basis noise is a lot.
-  **Tails:** for the settlement dates where the basis was unusually wide (say, a supply disruption day), how wide did it get? This is the tail risk of the strategy.

The measurement is a *distribution*, not a point estimate. It has to be computed from historical data joining Kalshi's `expiration_value` (the ICE-settled number, which Kalshi records) with public
NYMEX CL settlement prices from the same dates.

### On the Pyth finding

Pyth is a decentralized oracle network. Its price feeds are aggregated from many sources, updated at high frequency, and used primarily by DeFi protocols. Kalshi's Brent, gold, and natgas markets
settle on Pyth's aggregated feeds.

**Are these hedgeable?** Uncertain. Pyth's feeds are aggregations, not snapshots of a specific contract. Options on ICE Brent, COMEX gold, and NYMEX natural gas are among the most liquid commodity
options in the world, so hedging *the underlying commodity* is easy. But hedging against a *Pyth-aggregated* number is a different problem — the basis between Pyth's aggregated feed and any specific
futures contract's settlement is not obviously small, and it's likely wider and less stable than ICE/NYMEX WTI.

**What needs to be measured (Part 8 next steps).** Read `rules_primary` per Pyth-settled series to determine exactly what Pyth feed is referenced and how it's constructed. If the feed is "Pyth's
front-month Brent index," and you can identify a specific ICE Brent contract that tracks that index tightly, the strategy generalizes. If not, Brent/gold/ natgas are ruled out.

### On the expiry mismatch

**The problem.** ICE crude contracts expire *one day before* the corresponding NYMEX contracts. If you naively pair a Kalshi ICE-settled market on Friday with a NYMEX CL futures contract on the same
Friday, one contract has already expired and the other hasn't. You'd carry one day of unhedged exposure.

**Sizing that risk.** WTI crude at $\$87$ with 35% annualized volatility, over one calendar day (which is about $1/252$ of a trading year):

$$1\text{-sigma daily move} \approx \$87 \times 0.35 \times \sqrt{1/252} \approx \$1.92.$$

Against a $\$1$-wide bracket, $\$1.92$ of one-sigma movement would dominate everything. It's not "extra noise around a hedge that mostly works"; it's larger than the bracket. Naive pairing is a
non-starter.

**The fix is structural.** CME lists WTI weeklies expiring *every day of the week* — not just Fridays. You can find a CME weekly whose expiration matches Kalshi's ICE settlement date exactly. Do that,
and the timing gap is eliminated. What remains is the cross-exchange basis only (see above), which is a much smaller quantity.

Note: this is a structural fix, not an analytical one. The wrong response to the one-day gap would be to model it — build a stochastic model of the overnight WTI process, size the residual, and take
the trade with the extra risk explicitly. That would be worse, not better: the model would give you a *number* for the residual risk, which would make you feel like the exposure was under control, but
you'd still be carrying $\$1.92$ of one-sigma movement into settlement. **Do not build a model of a problem you can eliminate with a structural fix.**

## 6.4 Data availability: the sample is much smaller than it appears

KXWTIW has 201 historical events in Kalshi's database, reaching back to December 2024. Sounds like a lot. It isn't.

**The measurement.** For each month, count (a) total number of bracket markets, (b) number that returned zero candlesticks when queried, (c) percent live (nonzero candles), (d) total candles across
all brackets.

| month | brackets | zero-candle | % live | total candles |
|---|---|---|---|---|
| 2025-08 | 75 | 69 | 8% | 11 |
| 2025-09 | 45 | 42 | 7% | 8 |
| 2025-10 | 45 | 35 | 22% | 20 |
| 2025-11 | 15 | 11 | 27% | 10 |
| *(gap — no events 2025-12 to 2026-04)* | | | | |
| 2026-05 | 49 | 0 | **100%** | 207,491 |
| 2026-06 | 60 | 0 | **100%** | 113,632 |
| 2026-07 | 99 | 0 | **100%** | 281,973 |
| 2026-08 | 108 | 0 | **100%** | 205,328 |

**What's happening.** The 2024–2025 markets existed in Kalshi's database but *never traded*. Total lifetime volume across all of them: 5.00 contracts. The candlesticks endpoint returns 404 (not found)
for these markets — they had no trading activity, so there's nothing to report.

The series only became actively traded around May 2026, with 100% market-live rates from that point onward. Before that, Kalshi listed the markets but nobody bought.

**Implication.** The **usable backtest window is roughly 19 weekly events over five months**, not 201. That's what the pipeline can actually test itself against.

### Why this matters twice

**First, it scopes the Databento purchase.** Databento is where NightKing plans to buy historical CME options data. Historical options data is expensive, quoted per-symbol-per-day. If you buy 4 years
of history, you pay for 4 years. If you scope the purchase to the ~19 specific dates that have usable Kalshi coverage plus a warm-up buffer on either side, you pay much less.

**Second, it sets an honest expectation about statistical power.**
-  Brackets within an expiry share the same underlying density (they're slices of the same distribution).
-  Consecutive weeks share the same regime (crude vol regime doesn't change dramatically week-to-week).
-  So the *effective* sample size for a statistical claim about the strategy — is the gap real? is the gap stable? — is much smaller than $19 \times 25 = 475$ bracket-observations. It's closer to
  something like 19 independent-ish observations, or maybe $\sim 40$ with within-expiry variation counting.

**That is enough to detect a large persistent effect and not enough to detect a subtle one.** If the risk premium plus favorite-longshot combination produces, say, a 30% average deviation from Kalshi
prices, 19 weeks will show it clearly. If the effect is $5\%$ per bracket, 19 weeks will not distinguish it from noise.

Worth deciding what would be convincing *before* seeing results. That's a general methodological point — pre-registering a decision rule prevents post-hoc rationalization — and it applies here.

### The daily-series option

**KXWTI (daily WTI series)** has 837 historical events reaching into the same active window. That's ~5x the observations of the weekly series. But daily events settle at end-of-day, which means:

-  Time to expiry at any given snapshot is at most one day.
-  $\sqrt{T}$ is tiny (about $1/\sqrt{252} = 0.063$).
-  Vega collapses across the whole chain.
-  The call price curve degenerates toward a hockey stick (kinked around ATM, linear on either side).

So the extraction is much harder on daily markets: everything about the ill-posed inverse problem is worse when the density is more concentrated. The trade-off is more observations at the cost of a
harder extraction per observation.

Pursuing daily markets is on the "future work" list (Part 8) but is not the current focus. Weeklies first.

---

# Part 7 — Engineering notes

This part records the specific engineering choices in the repo that exist because of specific failures observed in prior data-collection attempts. Four earlier collectors failed silently — each
producing output that looked successful but wasn't — and the current design encodes tests for each observed failure mode.

## 7.1 The five API quirks that killed prior collectors

### Quirk 1: candlestick cap is 5,000, not 10,000

**What happened.** Earlier collectors requested candlesticks in 10,000-per-request chunks under the assumption (from an old note in the documentation) that Kalshi's cap was 10,000. Every request
returned HTTP 400 with the error message `"max candlesticks: 5000"` — so no candles were ever stored — but the collector logged "success" because the exception was caught and logged as a warning
rather than an error.

**The fix.** Every candle request now respects the 5,000 cap. And when a 400 is received, the response body is *parsed* for the actual cap number, so if Kalshi changes it in the future, the collector
re-chunks automatically instead of failing silently.

**In the repo.** `kalshi_common.py`:

```python
CAP_RE = re.compile(r"max\s+candlesticks?\s*[:=]?\s*(\d+)", re.I)

def parse_cap_error(text: Any) -> Optional[int]:
    """'... max candlesticks: 5000' -> 5000."""
    if not text:
        return None
    m = CAP_RE.search(str(text))
    return int(m.group(1)) if m else None

def candle_windows(start: int, end: int, period: int, cap: int = DEFAULT_CANDLE_CAP
                   ) -> List[Tuple[int, int]]:
    # Consecutive (start, end) spans so each holds at most `cap` candles.
    # ...
```

And in `fetch_market_candles`, the response is checked for the cap error and the shared `CapHolder` learns any lower cap the API reports, triggering a re-chunking of the request in progress.

Tested in `tests/test_chunking.py`.

### Quirk 2: OHLC fields are `*_dollars` suffixed decimal strings

**What happened.** Earlier collectors read `block["close"]` expecting an integer number of cents. The API actually returns `block["close_dollars"]` as a decimal string (e.g., `"0.0100"` for one cent).
Reading the non-existent `"close"` key returned `None` for every row. The collector stored a table where every bid and ask was `null`. The smoke test — which only counted rows — passed. The data was
useless.

**The fix.** All OHLC parsing now looks for the `*_dollars` variant first and falls back to the legacy integer-cent key. Values are scaled to cents (float64) internally.

**In the repo.** `kalshi_common.py`:

```python
OHLC = ("open", "high", "low", "close")

def ohlc(block: Any, prefix: str) -> Dict[str, Optional[float]]:
    """VERIFIED: keys are open_dollars/high_dollars/... as decimal-dollar strings.
    Legacy integer-cent keys (open/high/...) are accepted as a fallback."""
    out: Dict[str, Optional[float]] = {"%s_%s" % (prefix, k): None for k in OHLC}
    if not isinstance(block, dict):
        return out
    for k in OHLC:
        if ("%s_dollars" % k) in block:
            out["%s_%s" % (prefix, k)] = cents(block.get("%s_dollars" % k), dollars=True)
        elif k in block:
            out["%s_%s" % (prefix, k)] = cents(block.get(k), dollars=False)
    return out
```

Volume and open interest similarly: `volume_fp` and `open_interest_fp` are the current field names.

Tested in `tests/test_parse.py`, and — critically — `verify.py` now *fails* if any bid or ask close column comes out all-null in a stored parquet file, so this specific failure can't slip through
smoke tests anymore:

```python
for col in kc.BIDASK_CLOSE:
    if df[col].isna().all():
        all_null_files.append("%s/%s %s all null" % (parts.get("series"), parts.get("event"), col))
```

### Quirk 3: orderbooks return bids only, on both sides

**What happened.** Kalshi's orderbook endpoint returns two arrays: `yes` and `no`. Reading them as "yes bids and yes asks" gives garbage spreads (asks look like they're at 7¢ when they should be at
93¢).

**The reality.** Kalshi returns `yes` bids (people offering to buy YES contracts at these prices) and `no` bids (people offering to buy NO contracts at these prices). A NO bid at 7¢ is equivalent to a
YES ask at 93¢, because if someone will pay 7¢ for the NO side, they'd also (equivalently) sell the YES side for 93¢. So:

$$\text{yes\_ask} = 100 - \text{best\_no\_bid}.$$

**The fix.** All orderbook parsing converts NO bids to YES asks:

```python
def book_from_kalshi(raw: Any) -> Dict[str, List[Tuple[float, int]]]:
    """Kalshi gives yes BIDS and no BIDS. A no bid at p is a yes ASK at 100-p."""
    # ... handles both "orderbook.yes/no" (cent-integer) and
    # "orderbook_fp.yes_dollars/no_dollars" (decimal-string) formats
    return {
        "yes_bids": sorted(yes, key=lambda x: -x[0]),
        "yes_asks": sorted(((round(100.0 - p, 4), c) for p, c in no), key=lambda x: x[0]),
    }
```

Tested in `tests/test_parse.py`.

### Quirk 4: paging must run until the cursor is empty

**What happened.** Earlier collectors capped pagination at 40 pages. KXWTI (the daily WTI series) has enough markets that the paginated response was truncated at exactly 8,000 markets. When the cap
was raised, the endpoint returned 10,813 markets — so ~2,800 markets had been silently lost.

**The tell.** The count landing on an exact multiple of the page size (8,000 = 40 × 200) is a truncation warning. If the underlying reality were 8,000 markets exactly, the count would be 8,000. If it
were 7,973 or 8,152, that's what you'd see. Exactly 8,000 means "I asked 40 pages of 200 and stopped." That's a bug signature.

**The fix.** The paging function has *no page cap*. It follows the cursor until it's empty. And it explicitly flags any final count that lands on an exact multiple of the page size as a warning:

```python
class PageResult:
    items: List[dict]
    pages: int
    ended_cleanly: bool
    last_status: int
    limit: int

    @property
    def truncation_warning(self) -> bool:
        """An exact multiple of the page size is how the 8,000 bug looked."""
        return bool(self.items) and len(self.items) % self.limit == 0
```

Tested in `tests/test_client.py`.

### Quirk 5: live vs historical host routing is not what it looks like

**What happened.** Kalshi has two API hosts: `api.elections.kalshi.com` (live) and `external-api.kalshi.com/historical` (historical). The naming suggests you use live for currently-open markets and
historical for settled ones. That is *not* reliable.

**The reality.** A finalized (settled) July market was served by the *live* endpoint and 404'd on *historical*. The host routing is counterintuitive.

**The fix.** Every candle fetch tries both hosts. Which one delivered is recorded on the row (`source` column). The manifest records HTTP status codes for both hosts, so if a market fails on both, the
manifest can distinguish (a) "genuinely not found" (404 on both) from (b) "network failure" (0 or 5xx on either).

```python
def fetch_market_candles(client: Client, series: str, ticker: str, ...
                         hosts: Tuple[str, ...] = ("live", "historical"),
                         ...):
    """Try each host in order. Classification:
        200 on some host, >=1 candle     -> ok        fetch_ok=True
        200 on some host, 0 candles      -> empty     fetch_ok=True
        404 on every host                -> not_found fetch_ok=True
        anything else (0, 4xx, 5xx, ...) -> error     fetch_ok=False
    """
```

## 7.2 Manifest design: distinguish failure from empty

The failure mode that four earlier collectors all suffered from is that "no data stored for this market" was ambiguous. It could mean:

-  The market genuinely never traded (never-traded markets 404 on the candles endpoint).
-  The API request failed (network error, 5xx, 429 rate-limit).
-  The parser failed to extract data even though the API returned 200.

Recording all three as `rows: 0` in the manifest makes them indistinguishable. Which means resume can't retry the ones that actually need retrying, and the collector can't tell if it succeeded or if
the exchange was down.

**The fix.** Every manifest entry records `status`, `fetch_ok`, `http_live`, `http_hist`, and `source`. Four possible values of `status`:

-  `ok`: request succeeded, candles stored (`rows > 0`).
-  `empty`: request succeeded, zero candles. This is the never-traded case.
-  `not_found`: HTTP 404 on both hosts. Market genuinely doesn't exist or has no candle endpoint.
-  `error`: network failure, 5xx, or any 4xx other than 404 (`fetch_ok: false`). This is what needs retrying on resume.

Resume behavior:

```python
def decide(self, ticker, period, retry_errors=True,
           retry_not_found=False, repull=False) -> Tuple[bool, str]:
    """(fetch?, why). Resume is the default; re-pulling is explicit."""
    if repull:
        return True, "repull"
    e = self.entries.get(manifest_key(ticker, period))
    if not e:
        return True, "new"
    st = e.get("status")
    if st in ("ok", "empty"):
        return False, "done:%s" % st
    if st == "not_found":
        return (True, "retry:not_found") if retry_not_found else (False, "done:not_found")
    if st == "error":
        return (True, "retry:error") if retry_errors else (False, "skip:error")
    return True, "unknown-status:%s" % st
```

So the standard resume path retries only errors, skips everything else. A crashed collector re-run picks up exactly where it left off without re-doing any completed work.

Tested in `tests/test_store.py`.

## 7.3 Storage design: bid and ask stored separately, parquet not CSV

Two design choices that matter more than they seem:

**Bid and ask separately, never a mid.** A stored mid permanently destroys the half-spread that drives Stage 9 weights (SVI fit weighting) and Stage 13 tolerance (MCMC likelihood). Once you've
averaged bid and ask into a mid at storage time, there's no way to recover the half-spread. So the storage layer keeps bid and ask separately. `spread` and `half_spread` are stored too, but marked as
*derived* — they can always be recomputed from bid and ask. Bid and ask are the source of truth.

**Parquet, not CSV.** CSV loses types. In an earlier collection, the same column was inferred as Integer in one file and Float in another across separate exports. When you later concat them, you
either get type coercion errors or silent up-casting. Parquet preserves the schema explicitly — column dtypes are written into the file — so concatenation across files works cleanly.

Parquet also compresses well (snappy is the default here) and reads columnarly, which is fast for the analytical queries the pipeline runs.

## 7.4 Manifest as append-only checkpoint

The manifest is a JSONL file (one JSON object per line). Every market-fetch outcome is *appended* — never overwritten. If the collector crashes in the middle of writing, the partial last line might be
malformed, but everything before it is intact. Reading the manifest is "replay every line, later entries override earlier entries for the same key" — so a crashed-and-restarted collector sees a
consistent state.

Contrast with a "manifest.json" that gets rewritten on every update: if the rewrite is interrupted, the whole manifest is corrupted. The JSONL append pattern is crash-safe by construction.

`kalshi_common.py`:

```python
def record(self, entry: dict) -> None:
    """Append one line = the checkpoint. Crash-safe by construction."""
    entry = dict(entry)
    entry["key"] = manifest_key(entry["ticker"], entry["period"])
    entry["at"] = now_iso()
    line = json.dumps(entry, sort_keys=True) + "\n"
    with self._lock:
        # ... appends to manifest.jsonl
```

There's also a `manifest.json` human-readable snapshot that IS overwritten periodically for convenience — but it's not authoritative. JSONL is the ground truth.

## 7.5 verify.py: check what's stored, not what was logged

The specific failure mode of earlier smoke tests: they counted rows and called it success. But rows can be present with every column null. So `verify.py` reads the actual parquet files and checks:

-  Every candle file matches the expected column schema and dtypes.
-  Bid/ask close columns are populated (a file with all-null bid or ask is a FAIL, not a warning).
-  Prices are in $[0, 100]$ cents.
-  `ask_close >= bid_close` (no crossed spreads).
-  Timestamps are unique per `(ticker, ts)` tuple.
-  Timestamps fall within the market's `open_time..close_time` lifetime (a warning; sometimes candles slightly precede or follow the market timestamps due to API rounding).
-  Manifest ok entries have matching stored files.
-  Manifest row counts match actual parquet row counts.

Anything that FAILs exits 1, so the data store cannot be used until the issue is resolved. Anything that WARNs is printed and exit 0 (unless `--strict` is passed).

This is the "check what's stored, not what was logged" discipline made mechanical. Logs can be misleading (a caught exception is still a caught exception); actual stored data cannot.

## 7.6 Cross-referenced field authority

The final engineering theme: **verify, do not infer.** Kalshi's API carries authoritative fields for many things the earlier collectors inferred from label text or free-form fields:

| what to know | authoritative field | inferred before, broke silently |
|---|---|---|
| ladder type (RANGE vs CUMUL) | `mutually_exclusive` | inferred from label text |
| what the market settles on | `settlement_sources` | assumed from series name |
| which futures month the strike references | `custom_strike.front_month_contract` | inferred from date parsing |
| what actually happened at settlement | `expiration_value`, `result` | not captured |
| what the market's rules are | `rules_primary` | not captured |

The current collector reads *every* authoritative field into the markets table, so nothing needs a re-pull because a field wasn't anticipated. `MARKET_TYPED` in `kalshi_common.py` explicitly lists the
typed columns, and any additional scalar fields from the raw records are also captured as string columns:

```python
MARKET_TYPED = [
    "ticker", "event_ticker", "series", "yes_sub_title",
    "open_time", "close_time", "expiration_time",
    "settlement_ts", "occurrence_datetime",
    "status", "result",
    "strike_type", "floor_strike", "cap_strike",
    "expiration_value", "expiration_value_num",
    "custom_strike_json", "custom_strike.front_month_contract",
    "custom_strike.strike_date",
    "rules_primary", "rules_secondary",
    "volume_fp", "open_interest_fp", "liquidity_fp",
    "settlement_sources", "settlement_source_name", "settlement_source_url",
    "mutually_exclusive", "ladder_kind", "ladder_kind_source",
    # ... plus 20 more typed columns, plus all remaining scalars as strings
]
```

Every row in `parquet/kalshi_markets` has these columns filled in from the API's authoritative response. Downstream code reads these fields directly rather than inferring from other fields. This is
the protection against the "I guessed a field name and got a plausible- looking wrong answer" failure mode.

## 7.7 The probe / verify / collect / findings split

The repo separates four concerns:

-  **`probe.py`** — asks the API every question the pipeline needs answers to (cap, field style, hosts, cadence, rate limits, etc.) and writes `data/probe.json`. Doesn't collect anything for real;
  just measures. `collect.py` refuses to start without a probe file.
-  **`collect.py`** — the actual collector. Reads `probe.json`, discovers series, fetches events and markets and candles, writes to parquet. Resumable, `--smoke` for a quick test run.
-  **`verify.py`** — validates what's stored. Exit 1 on FAIL. Does not fetch anything; reads only what's on disk.
-  **`findings.py`** — writes `FINDINGS.md` from the store. Per-series usable window, settlement source, ladder type, candle counts, Databento shortlist.

This separation forces every failure to be attributable to a specific stage. A collection failure never contaminates the verification. Verification is independent of the network. The findings summary
is derived from stored data, not from live queries, so it's reproducible.

---

# Part 8 — Where the project stands, next steps

## 8.1 What is complete

-  The theoretical pipeline is specified end-to-end (20 stages).
-  Within-venue arbitrage on Kalshi RANGE ladders has been tested and ruled out.
-  Depth has been verified at Micro-sized structure on moderate-tail brackets in one snapshot.
-  Settlement sources have been identified for five commodity series.
-  Data availability has been mapped; the usable Kalshi backtest window has been established (~19 weekly events across five months).
-  The collection tooling has been debugged through four failure modes and rebuilt with tests covering each.

## 8.2 What is in progress

-  Historical Kalshi collection across five commodity series at 1- minute resolution, using the rebuilt collector.

## 8.3 What is next, in order

1.  **Read `rules_primary` per series** to determine what Pyth-settled markets actually reference. If the reference is a specific futures contract (or a well-defined index tightly tracking one),
   Brent/ gold/natgas remain candidates for the strategy. If the reference is diffuse (an aggregated multi-source index), those series are ruled out.
2.  **ICE/NYMEX basis test.** Join Kalshi's stored `expiration_value` (the realized ICE-settled WTI number) with public NYMEX CL settlements on the same dates. Compute the **distribution** of the
   difference: mean, standard deviation, tails. Not correlation (which will be ~0.999 and communicates nothing useful). The distribution tells you the systematic bias (mean offset) and the unhedged
   noise on a $\$1$-wide instrument (standard deviation).
3.  **CME weekly calendar check.** Determine which specific CME weekly option series expires on each Kalshi settlement date, and which underlying futures month it exercises into. This is a mapping
   table that needs to be built before Databento is purchased.
4.  **Build the extractor against synthetic data.** Plant a *known* density, generate a chain of "prices" by integrating against Black-76 payoffs, add realistic noise, and verify that the pipeline
   recovers the density with error bars that cover the true value at the stated credibility level (i.e., a 90% credible interval should contain the true density value ~90% of the time across many
   synthetic runs). This is the only stage where "my code is broken" and "the market is interesting" can be distinguished. Do it before spending money on real data.
5.  **Scoped Databento purchase.** Only after 1–3 have identified a viable pair, and only for the ~19 dates that have usable Kalshi coverage plus a warm-up buffer on either side. Use `bbo-1m` (bid and
   ask separately, one-minute matching the Kalshi resolution). Use `stype_in="parent"` for whole-chain requests. Cost-preflight every pull — Databento charges per symbol per day, and unbounded queries
   can be expensive.
6.  **Aligned backtest** on executable prices, never mids. Use the collected Kalshi orderbook data for executable prices on the prediction market side, and Databento's bid/ask on the CME side.
   Simulate the strategy trade-by-trade with real transaction costs. Report P&L, Sharpe, max drawdown, breakdown by bracket type (favorite vs longshot).
7.  **One minimum-size live trade** before any scaling. Simulators never capture: actual fill prices, the lag between the two legs, real margin behavior, whether settlement resolves as expected. Do
   one trade at the minimum hedgeable unit (50 Micro CL contracts or so on the CME side, corresponding to 50 Kalshi contracts on one bracket) and observe. If everything behaves as modeled, consider
   scaling. If not, debug before doing another trade.

## 8.4 Open items owned by the operator

The following items are Jaden's to work out — deliberately not delegated, because they're the kind of thing that needs the operator's own judgment.

-  **Hedge ratio derivation.** Exact number of options contracts per Kalshi contract given the bracket width, the option contract's notional (100 barrels for Micro), and the ramp geometry.
-  **Depth sampling across a session.** The one-snapshot measurement is not enough. Depth needs to be measured at multiple times of day across multiple days to establish that the Micro-sized structure
  actually clears reliably.

## 8.5 What is not on the roadmap

Worth stating explicitly what the strategy is *not* going to become:

-  **Multi-asset rollout.** The framework generalizes to any Kalshi market with a hedgeable CME (or ICE, or LME) options chain, but the effort to scale is real and the marginal edge per new market is
  unknown. Start with weekly WTI. If it works, consider daily WTI or Brent. Do not build a "Kalshi strategy factory" until at least one market has traded profitably.
-  **HFT / latency infrastructure.** Not needed (Part 5.5). No plans.
-  **Machine learning on the residual.** The regression in Stage 18 is a simple parametric decomposition. It's tempting to think "we have residuals per bracket over many weeks; let's fit a model to
  predict the residual from market state." But: 19 weeks is not enough data to fit anything with more than a few parameters without overfitting, and the whole point of the strategy is that the *simple
  decomposition* already captures the two innocent forces, leaving anything else as candidate mispricing. Adding an ML layer is a way to *reintroduce* the bug (Case 2 in disguise) by claiming the
  "predicted residual" is a signal to trade on.

---

# Part 9 — Standing methodological commitments

These are stated explicitly, because each was learned by getting it wrong. Each rule is followed by the mistake that generated it.

## Rule 1 — A gap is not an edge

**The rule.** Part of any cross-venue disagreement is a risk premium that is supposed to be there. The two venues have different marginal investors, so their $\mathbb{Q}$-measures differ, so their
fair prices differ, so the raw gap contains a component that isn't tradeable no matter how persistent it is.

**The mistake that generated it.** fedarb's initial reaction to seeing a persistent 4¢ gap between Kalshi and ZQ was "we have an edge." Only after building the whole pipeline and running diagnostics
did the alternative interpretation — "we're measuring the difference in hedging premiums between the two venues, and much of it is not capturable" — become visible. By then, a lot of engineering had
been spent on the assumption that the gap was pure signal.

**How NightKing enforces it.** Stage 18 (the gap decomposition) separates the risk premium from the residual explicitly. Only the residual — the part of the gap not explained by state-monotone lean or
symmetric-in-probability shrinkage — is a candidate for trading. Stage 19 (the trade filter) further requires the residual to exceed both the posterior uncertainty *and* the transaction cost before it
becomes an actual trade.

## Rule 2 — Error bars are the deliverable, not the density

**The rule.** A point estimate of the density is not enough. A point estimate cannot distinguish signal from measurement noise, and the tails — where the tradeable bias lives — are precisely where
measurement is weakest. The output of the extraction must be a posterior distribution with real credible intervals.

**The mistake that generated it.** Act II of the pipeline gives you a single density. That single density will occasionally look like it disagrees with Kalshi by, say, 3¢ on some bracket. Without an
error bar, that 3¢ looks like an edge. With an error bar showing that the posterior on that bracket's density is ±5¢, the 3¢ is noise. Building Act III to deliver error bars is a lot of extra
engineering, but it's the only way to distinguish signal from noise in this class of strategy.

**How NightKing enforces it.** Act III (Stages 11–15) exists specifically to deliver a posterior over densities via MCMC. Stage 15 emphasizes that convergence diagnostics are load-bearing here: "the
spread IS the deliverable," and a badly-mixed chain produces false trading signals. Stage 19 uses the posterior spread as part of the trade threshold.

## Rule 3 — Executable prices only

**The rule.** Never mids, never displayed percentages, never last-trade prices. The order book is the only source of truth for what a trade will actually cost.

**The mistake that generated it.** fedarb measured a 3.1¢ average mid-vs-executable gap. Any backtest run on mids was measuring an edge that didn't exist — the mid was
$X, the market you could actually transact at was $X + 3.1$ cents on average, and the "edge" evaporated in real execution.

**How NightKing enforces it.** The Kalshi collector stores bid and ask separately at every snapshot, never a mid (Part 7.3). The half-spread is derived from these but never replaces them. Stage 9
weights use the half-spread. Stage 13 tolerances use the half-spread. Stage 19 friction uses the executable price, not the mid. Storage is architected to make it *impossible* to accidentally end up
with a mid-based backtest, because the mid was never stored in the first place.

## Rule 4 — Measurement artifacts look exactly like edges

**The rule.** A mis-specified extraction that fails silently produces output that is smooth, persistent, and sign-consistent — which is exactly what a real edge looks like. Every stage of the pipeline
must carry a diagnostic aimed at some specific artifact.

**The mistake that generated it.** fedarb's initial -8pt pooled wedge looked like a real, persistent, sign-consistent signal. When Jaden dug in, the biggest single component was measurement breakdown
(the two-state assumption failing on 50/75bp meetings; contract contamination from the following meeting's rate). The extraction failure was smooth, persistent, and sign-consistent, so it *looked
exactly like an edge*. Diagnostics saved the day only because Jaden had built enough of them to eventually cover the specific failure mode that occurred.

**How NightKing enforces it.** The three consistency checks (Part 2 §2.6) are computed at every extraction. Convexity, normalization, and mean-equals-forward each catch a different failure mode. Stage
14 (the martingale constraint) enforces mean-equals-forward *during* the extraction. Stage 15 (MCMC convergence diagnostics) catches sampler failure. Stage 10 (SVI arb bounds enforced in the
optimizer) makes negative-density fits impossible. The measurement- artifact warning appears wherever it's relevant, not just in this methodology section.

## Rule 5 — Structural fixes over analytical ones

**The rule.** When a problem can be eliminated by choosing a different setup (structural fix), do that instead of modeling around the problem (analytical fix). Structural fixes remove risk; analytical
fixes make you feel like the risk is under control without actually reducing it.

**The mistake that generated it.** The ICE/NYMEX one-day expiry gap initially looked like something to model — build a small stochastic model of the overnight WTI process, size the residual, take the
trade. This would have been the wrong response. The right response was to notice that CME lists WTI weeklies expiring every day and to pair the Kalshi ICE-settlement date with a CME weekly on the same
day, eliminating the gap entirely.

Other examples in the pipeline:

-  Stage 6: extract $F_0$ from the chain via parity regression (structural: internal consistency by construction) rather than sourcing $F_0$ externally and checking it after (analytical:
  detect-and-repair after the fact).
-  Stage 10: enforce SVI arbitrage constraints in the optimizer bounds (structural: no-arb by construction) rather than fitting freely and checking for arbitrage after (analytical: detect-and-
  repair).
-  Stage 11: parameterize the density as $\exp(\phi) / Z$ (structural: positive and normalized by construction) rather than fitting an arbitrary function and rejecting negative candidates (analytical:
  detect-and-reject).

**How NightKing enforces it.** As a design habit. When a candidate problem is identified, the first question is: can this problem be structurally eliminated? If yes, do that. Only fall back to
analytical modeling if there's no structural option.

## Rule 6 — Capacity is checked before cleverness

**The rule.** Before spending effort on the intellectual problem of extracting the density well, check that the resulting trade — if it worked — could actually be sized to a meaningful position
without eating its own edge. Capacity is a first-order property, not a last-mile detail.

**The mistake that generated it.** fedarb was mathematically correct and diagnostically clean, and it was killed by depth. The whole strategy was untradeable at any meaningful size because the Kalshi
book at 1,042 contracts was too thin. That check would have taken 5 minutes at the beginning of the project and saved months of work. Instead it was the *last* check performed, after everything else
was built.

**How NightKing enforces it.** Depth on the thin leg (Kalshi) is verified *first*, before any density extraction is attempted. Part 6.2 records the depth-clearance measurement. Contract selection
(Micro CL vs standard CL) is decided by the depth data, not by preference. If depth failed at Micro too, the strategy would be dead on arrival and no further engineering effort would go into it.

## Rule 7 — Verify, do not infer

**The rule.** When an authoritative source is available (an API field, a settled contract, an exchange-published rulebook), use it directly. Do not infer from labels, filenames, or context.

**The mistake that generated it.** Multiple. The 47 false-positive "arbitrage" signals from summing cumulative ladders as if they were mutually exclusive (Part 6.1). The 40-page truncation that lost
2,800 KXWTI markets (Part 7.1, Quirk 4). The all-null bid/ask storage from reading `"close"` instead of `"close_dollars"` (Part 7.1, Quirk 2). Each was a case where the collector inferred what a field
should be called or what a value should mean, was wrong, and the wrongness looked like success.

**How NightKing enforces it.** Every authoritative Kalshi field (`mutually_exclusive`, `settlement_sources`, `expiration_value`, `result`, `rules_primary`, `custom_strike.front_month_contract`, etc.)
is read into the markets table and used directly by downstream logic. `ladder_kind` is populated from `mutually_exclusive` by default; label-based inference is a fallback for old events, and the
source is recorded on every row so a human can tell which records used which method.

---

# Part 10 — Glossary / notation reference

A reader might encounter these terms; the definitions below are functional (what does this thing *mean* in the context of NightKing) rather than exhaustively formal.

## Measure theory / stochastic calculus

-  **$\mathbb{P}$ (physical measure)** — the "real-world" probability distribution. What would actually happen in the world. Cannot be observed directly from prices.

-  **$\mathbb{Q}$ (risk-neutral measure)** — an equivalent probability measure under which discounted prices are martingales. All prices in the strategy live under $\mathbb{Q}$. Extractable from
  options via Breeden–Litzenberger. Differs from $\mathbb{P}$ by the pricing kernel, which encodes risk aversion + hedging demand.

-  **Martingale** — a stochastic process whose expected future value (given information available today) equals its current value. Under $\mathbb{Q}$, futures prices are martingales.

-  **Pricing kernel / stochastic discount factor (SDF)** — the ratio $d\mathbb{Q}/d\mathbb{P}$ (formally, the Radon-Nikodym derivative). It re-weights states of the world. In an economy where all
  investors have the same utility, the SDF is proportional to their marginal utility of wealth. In a segmented market (like Kalshi vs CME), different venues can have different effective SDFs.

-  **Girsanov's theorem** — the technical result that says $\mathbb{Q}$ exists under no-arbitrage and characterizes how to transform processes between $\mathbb{P}$ and $\mathbb{Q}$. Not directly used
  in the pipeline but underlies the whole framework.

## Options / prediction markets

-  **Call option** — the right (not obligation) to buy the underlying at strike $K$ at expiry. Payoff at expiry: $(F_T - K)^+$.

-  **Put option** — the right to sell the underlying at strike $K$ at expiry. Payoff: $(K - F_T)^+$.

-  **Put-call parity** — the identity $C(K) - P(K) = e^{-rT}(F_0 - K)$, which comes from the fact that buying a call and selling a put at the same strike gives a payoff equivalent to a forward.

-  **Digital option / cash-or-nothing option / binary option** — an option that pays $\$1$ if the underlying is above (or in a range around) a strike, and $\$0$ otherwise. A Kalshi bracket is a
  digital. Its fair value is a discounted probability.

-  **Bracket** — one of a set of mutually exclusive, exhaustive discrete outcomes on Kalshi. "WTI settles between $\$87.00$ and $\$87.99$" is a bracket.

-  **RANGE ladder** — Kalshi's term for a set of brackets that are mutually exclusive and exhaustive. Sum of bracket probabilities is 100¢ up to spread.

-  **CUMUL ladder** — Kalshi's term for a set of "Above $K$" contracts at increasing $K$. Nested, not exclusive. Sum is not 100¢. The correct sanity check is monotonicity:
  $\mathbb{Q}(F > K_1) \ge \mathbb{Q}(F > K_2)$ for $K_1 < K_2$.

-  **Butterfly (option strategy)** — long one call at $K - h$, short two at $K$, long one at $K + h$. Payoff is a tent centred at $K$. Price is exactly the numerical second difference of call prices.

-  **Vega** — sensitivity of an option's price to volatility. $\partial C / \partial \sigma$. Large ATM, dies exponentially in the wings.

-  **Delta** — sensitivity to the underlying. Not directly used here except in Black-76 where $\Delta = \mathcal{N}(d_1)$ for a call.

-  **Implied volatility** — the $\sigma$ that Black-76 requires to produce the observed option price. A relabeling of price into a more analytically tractable coordinate.

-  **Smile** — the shape of implied volatility as a function of strike. In liquid markets, IV rises in the wings on both sides (hence "smile" — or "smirk" if it's asymmetric). Reflects the market's
  assessment that extreme outcomes are more likely than a pure Black-76 model would predict.

-  **SVI (Stochastic Volatility Inspired)** — a 5-parameter parameterization of the total variance $w(k) = \sigma^2 T$ as a function of log-moneyness $k = \ln(K/F_0)$. Used in Stage 9 to smooth the
  implied volatility surface.

-  **Log-moneyness** — $k = \ln(K/F_0)$. Centred at zero (ATM), scale- free. The natural coordinate for lognormal-adjacent distributions.

-  **Half-spread** — half the difference between bid and ask, an estimator of the mid's uncertainty. Used as the noise scale for option prices in the pipeline's likelihood.

## Numerical / statistical

-  **Breeden–Litzenberger identity** — $f(K) = e^{rT} \partial^2 C / \partial K^2$. The mathematical link between call prices and the risk-neutral density. Exact given continuous prices. Numerically
  fragile on real discrete noisy data.

-  **Catastrophic cancellation** — the loss of precision that happens when you subtract two nearly-equal numbers. The signal is small and rounding errors from the inputs dominate. The reason the naive
  Breeden–Litzenberger estimator fails.

-  **Ill-posed inverse problem** — a problem where the forward map is smoothing (many inputs give similar outputs), so the inverse map is un-smoothing (small output perturbations blow up in the
  input). Density extraction from prices is a canonical example.

-  **Tikhonov regularization** — the general technique of solving ill-posed problems by penalizing solutions that are "too rough." In Bayesian terms, adding a prior on smoothness. Stage 12 does
  Tikhonov via a curvature penalty on the log-density.

-  **Bayesian posterior** — the probability distribution over parameters given data: $p(\theta \mid \text{data}) \propto p(\text{data} \mid \theta) p(\theta)$. Combines likelihood (data-driven fit)
  with prior (regularization).

-  **Hyperprior** — a prior on the parameters of a prior. In NightKing, the smoothness strength $\lambda$ has a Gamma hyperprior, so uncertainty about how smooth to make the density propagates into
  the posterior.

-  **MCMC (Markov chain Monte Carlo)** — a family of algorithms for sampling from a posterior distribution when direct sampling isn't possible. Constructs a Markov chain whose stationary distribution
  is the target.

-  **Metropolis / Metropolis-Hastings** — the simplest MCMC algorithm. Propose a new state, accept or reject based on a probability that depends on the ratio of posterior densities.

-  **HMC (Hamiltonian Monte Carlo)** — an MCMC algorithm that uses gradient information to move ballistically through parameter space. Much more efficient than random-walk Metropolis in high
  dimensions with correlated parameters.

-  **NUTS (No-U-Turn Sampler)** — an adaptive variant of HMC that automatically picks trajectory lengths. Modern default for gradient-based sampling.

-  **$\hat R$ (Gelman-Rubin statistic)** — a convergence diagnostic comparing within-chain variance to between-chain variance across multiple parallel MCMC chains. Values close to 1 indicate mixing.
  Target: $\hat R < 1.01$.

-  **Effective sample size (ESS)** — the number of "independent- equivalent" MCMC samples, given the autocorrelation of the chain. Target: $\gtrsim 400$ per parameter.

-  **Divergence (HMC)** — a specific failure mode where HMC's numerical integration of the Hamiltonian dynamics fails to conserve energy, indicating the sampler is having trouble with local geometry.
  Zero or near-zero divergences is the goal.

-  **Credible interval** — Bayesian analog of a confidence interval. A 90% credible interval on a parameter is a range that contains the true value with 90% posterior probability.

## Prediction-market specific behavioral effects

-  **Favorite-longshot bias** — the empirical pattern that participants in prediction / betting markets overpay for longshots and underpay for near-certainties. Standard in horse racing, sports
  betting, and likely applicable to Kalshi. Manifests as $b < 1$ in the Stage 18 regression.

-  **Hedging premium (institutional risk premium)** — the amount above actuarial fair value that commercial hedgers pay for options. In crude, refiners and airlines pay above fair for OTM calls.
  Manifests as a nonzero $c$ (state-monotone tilt) in the Stage 18 regression.

## Practical / operational

-  **Micro WTI / MCL** — CME's smaller-notional WTI futures/options, 100 barrels per contract (vs 1,000 for standard CL). Necessary for NightKing because standard CL's $500 hedge size is too big
  relative to Kalshi's depth.

-  **Databento** — a data vendor that sells historical CME market data. NightKing's plan is to buy historical bid/ask on Micro CL options for the ~19 usable Kalshi dates.

-  **Kalshi** — a US-regulated prediction market (CFTC-designated contract market). Lists commodity/economic/political binary contracts. Retail-dominated, thin books relative to CME.

-  **ICE (Intercontinental Exchange)** — the exchange whose WTI futures settle Kalshi's WTI weekly markets. Distinct from NYMEX (CME's crude venue), with a small cross-exchange basis.

-  **NYMEX / CME** — the exchange where standard CL and Micro CL WTI futures/options trade. Where NightKing's hedge leg lives.

-  **Case 1** — the design target for NightKing: both legs held to settlement, gap locked in at execution, kept regardless of what caused the gap.

-  **Case 2** — the trap NightKing must not fall into: treating the options-implied number as "truth" and betting Kalshi directionally, which has zero expected P&L when the disagreement is risk
  premium rather than mispricing.

-  **The ramp** — the discrete-strike residual in a call-spread digital. Because you can't build a call spread with zero width, the "digital" hedge is actually a ramp from 0 to 1 over the spread's
  width, and inside the ramp region the hedge doesn't perfectly cancel. Sets the real max loss on the trade.

-  **fedarb (predecessor project)** — the Fed-rate / ZQ futures arbitrage against Kalshi FOMC-decision markets. Correct mathematically, killed by insufficient Kalshi depth on the ~1,042-contract hedge
  ratio. NightKing supersedes fedarb by moving from scalar-vs-scalar comparisons to distribution-vs-ladder comparisons on higher-capacity crude markets.

-  **Segmentation** — the structural fact that Kalshi's marginal investor is different from CME's, so the two venues can sustain different effective pricing kernels ($\mathbb{Q}$-measures). The
  economic thesis of NightKing.

---

# Appendix — A worked numerical example of catastrophic cancellation

To make Part 3.2 concrete, walk through the numbers by hand.

**Setup.** WTI weekly options chain, $F_0 = \$87.00$, time to expiry $T = 3/365$ years (three days), risk-free rate $r = 5\%$, ATM implied volatility $\sigma = 35\%$. Strikes at $\$0.25$ increments.

**Three consecutive ATM call prices from Black-76.**

$$C(K) = e^{-rT}[F \mathcal{N}(d_1) - K \mathcal{N}(d_2)],$$

with

$$d_1 = \frac{\ln(F/K) + \tfrac{1}{2}\sigma^2 T}{\sigma \sqrt{T}}, \qquad d_2 = d_1 - \sigma \sqrt{T}.$$

Compute for $K = 86.75, 87.00, 87.25$:

-  $\sigma \sqrt{T} = 0.35 \cdot \sqrt{3/365} = 0.35 \cdot 0.0906 = 0.03172$.
-  $\tfrac{1}{2}\sigma^2 T = 0.5 \cdot 0.35^2 \cdot 3/365 = 0.000503$.
-  $e^{-rT} = e^{-0.05 \cdot 3/365} = 0.999589$.

For $K = 86.75$:
-  $\ln(87/86.75) = 0.002879$.
-  $d_1 = (0.002879 + 0.000503) / 0.03172 = 0.10667$.
-  $d_2 = 0.07495$.
-  $\mathcal{N}(d_1) = 0.5425$, $\mathcal{N}(d_2) = 0.5299$.
-  $C = 0.999589 \cdot [87 \cdot 0.5425 - 86.75 \cdot 0.5299]$ $= 0.999589 \cdot [47.198 - 45.969] = 0.999589 \cdot 1.229 = 1.2285$.

For $K = 87.00$:
-  $\ln(87/87) = 0$.
-  $d_1 = 0.000503 / 0.03172 = 0.01586$.
-  $d_2 = -0.01586$.
-  $\mathcal{N}(d_1) = 0.5063$, $\mathcal{N}(d_2) = 0.4937$.
-  $C = 0.999589 \cdot [87 \cdot 0.5063 - 87 \cdot 0.4937] = 0.999589 \cdot 87 \cdot 0.0126 = 1.0954$.

For $K = 87.25$:
-  $\ln(87/87.25) = -0.002869$.
-  $d_1 = (-0.002869 + 0.000503) / 0.03172 = -0.07461$.
-  $d_2 = -0.10633$.
-  $\mathcal{N}(d_1) = 0.4703$, $\mathcal{N}(d_2) = 0.4577$.
-  $C = 0.999589 \cdot [87 \cdot 0.4703 - 87.25 \cdot 0.4577] = 0.999589 \cdot [40.916 - 39.934] = 0.999589 \cdot 0.982 = 0.9816$.

**True second difference (per unit strike squared).**

$$\frac{C(86.75) - 2 C(87) + C(87.25)}{(0.25)^2} = \frac{1.2285 - 2 \cdot 1.0954 + 0.9816}{0.0625} = \frac{0.0193}{0.0625} = 0.3088.$$

**Extracted density.** $f(87) \approx e^{rT} \cdot 0.3088 = 1.000411 \cdot 0.3088 \approx 0.3089$ per dollar. (For a 3-day WTI density, this is a reasonable ATM density value.)

**Now add noise.** Suppose each observed price has a half-spread of $\$0.03$, so the observed prices are the true prices plus independent Gaussian noise with $\sigma = 0.03$. A single simulated
realization:

-  $C^{\text{obs}}(86.75) = 1.2285 + 0.021 = 1.2495$
-  $C^{\text{obs}}(87.00) = 1.0954 - 0.037 = 1.0584$
-  $C^{\text{obs}}(87.25) = 0.9816 + 0.015 = 0.9966$

**Naive second difference on the noisy data.**

$$\frac{1.2495 - 2 \cdot 1.0584 + 0.9966}{0.0625} = \frac{0.1293}{0.0625} = 2.069.$$

**Extracted density (naive):** $\approx 2.069$ per dollar — nearly 7× the true value.

The signal is $0.31$ and the noise-on-second-difference is $\sqrt{6} \cdot 0.03 / 0.0625 = 0.073 / 0.0625 = 1.17$. Signal-to-noise ratio: about $0.26$. Any single estimate from three noisy prices is
dominated by noise.

**A different noise realization gives a different answer.** Simulate 1,000 independent noise draws, compute the naive estimator each time, histogram the results. You'd find a distribution centred near
$0.31$ (unbiased) with a standard deviation near $1.17$ — spanning negative to positive values, frequently negative, never precise.

**This is what "catastrophic cancellation" looks like on real numbers.** The noise is *not* larger than the underlying price (a 3-cent half-spread on a $\$1$ price is only 3%). It's larger than the
*second difference* of the prices, which is the small algebraic combination the density extraction lives inside. The pipeline in Part 4 is the answer to "how do you use all 40 strikes' worth of
information to constrain the density, given that any single second- difference is unusable?"

---

# End of writeup

If you got here in one sitting: you now know why NightKing is structured the way it is, why every stage of the pipeline exists, what failure mode each stage prevents, and where the strategy sits in
its development lifecycle (pre-backtest, no capital deployed, several open empirical questions to resolve before deployment).

The next time this document gets a revision, it will probably be after (1) the ICE/NYMEX basis test has produced a real number for the residual noise, (2) the synthetic-data extractor test has
validated the pipeline end-to-end, and (3) the Databento scoped purchase has produced the first backtest results. At that point Parts 6 and 8 will look substantially different — Part 6 will have real
numbers instead of "measurement pending," and Part 8 will either read "one live trade attempted, here's what happened" or "strategy shelved, here's why."

Until then: read Jaden's original writeup for the ground-truth statement of the design; read the repo for how it's implemented; read this document for why any of it exists.
