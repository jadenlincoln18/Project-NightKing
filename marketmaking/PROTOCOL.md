# PROTOCOL — gates, definitions and pre-registered tests

**Status: committed before the stack produced any shadow output.** That ordering
is the point. Every threshold below was written without having seen a single
phase-1 number, and the ones inherited from phase 0 are cited to the document
that established them.

This file is the bar. `FINDINGS_SHADOW.md` and `FINDINGS_PAPER.md` report against
it. If a gate is missed, the result is that the gate was missed — not that the
gate was the wrong gate.

**Amendment rule.** Nothing in §2–§5 may be changed after phase-1 collection
begins. If a definition turns out to be unworkable, the amendment is made in a
new dated section at the bottom of this file, with the original left intact and
the reason recorded. A threshold that moves after the data arrives is not a
threshold.

---

## 1. Quoting universe

**The 38% branch is retired.** It described a world in which every ladder series
pays a maker fee. Exactly one does. Carrying it forward as a "conservative case"
would be carrying a fiction.

| | |
|---|---|
| **Quoting universe** | the **51 maker-free ladder series** (`fee_type: quadratic`, maker coefficient 0) |
| **Excluded from quoting** | `KXAAAGASM` — the only maker-fee series (0.0175) |
| **Collection universe** | **all 52**, including `KXAAAGASM` |

`KXAAAGASM` keeps being collected for three reasons, none of them sentimental:
it is the control group for the fee arithmetic; it is the largest LIP payer among
the ladders ($39,000/period) and so the natural place to test whether LIP income
ever justifies a fee-paying book; and it is the worst microstructure in §5
(43.06% improvable against 58.50% elsewhere), which makes it the negative control
for the designated-provider proxy in §4.

**Maker fee is therefore 0 throughout phase 1.** Not "assumed zero" — `post_only`
is cancel-on-cross and the maker coefficient on these 51 series is zero, so a
`post_only` order on them is *structurally incapable* of incurring a maker fee.
Where a formula below carries a `fee` term it is retained for phase 3 generality
and evaluates to zero. See `FINDINGS_PHASE0.md` §1.

**Standing monitor, not a one-time check.** `tick_size` has been removed from the
API and other Kalshi markets now quote $0.001 and $0.0001. The collector reads
`price_ranges` per market per cycle and the daily report alarms on any change.
A tick change silently invalidates every cent-denominated threshold in this file.

---

## 1A. Universe selection — what may and may not inform it

### The rule

**Universe selection may use coverage status, volume, spread/microstructure, and
structural facts about where a price originates. It may NOT use fit residuals,
improvable fraction, edge, simulated fills, or P&L — any quantity that is an
output of the fitter or a proxy for the strategy's return.**

Why the line falls there. Volume and spread are properties of the market,
observable to anyone, and knowable before a model exists. They are not the
outcome variable. Choosing a universe on them is choosing where to run the
experiment. Improvable fraction and edge *are* the outcome variable; choosing on
them is choosing the answer and calling it a universe. The first is design, the
second is peeking, and it is how a 58.50% that means nothing gets reported as a
finding.

Enforced by ordering, not intention: the coverage build reads the LPP snapshot,
`/incentive_programs`, and historical volume/spread. It does not import the
fitter and cannot — the density extractor is not in its dependency path.

### The covered / uncovered split

| Term | Definition |
|---|---|
| **covered** | on `lpp/lpp_2026-10-18.json` with ≥1 named provider, **or** carrying an active retail LIP program |
| **unknown** | plausibly matching one of the 8 prose LPP rows that name no tickers |
| **uncovered** | neither of the above |

`unknown` is never promoted to `uncovered`. Treating a covered series as
uncovered means quoting head-to-head against a contracted, subsidised provider
while believing the book is unattended — the expensive direction to be wrong in.

### Pre-registered bars (written before the coverage table was read)

The uncovered set is promoted to primary only if all three hold:

1. **Breadth** — ≥8 live uncovered series, so a result can generalise.
2. **Depth** — projected tight-spread volume ≥50% of the commodity comparison
   group.
3. **Concentration** — no single series >40% of the uncovered total. This is the
   `KXAAAGASM` denominator lesson from §5 as a precondition.

"The uncovered set is too thin to run" is a permitted and complete outcome.

### Amendment, 2026-10-18 — a fourth criterion, added after reading the table

**Disclosed as post-hoc.** Bars 1–3 were written blind. The coverage table then
returned an uncovered set that is 92.5% sports by tight-spread volume, and sports
**passes all three bars at 55× the comparison group.** Promoting it would have
been wrong, so the bars were incomplete.

**Criterion 4 — price origin.** A series is ineligible for the primary universe
if a thicker external venue already quotes the same claim continuously.

Admissible under the rule above because it uses no fitter output: it is a
structural fact about the market, knowable without running anything. It is still
post-hoc and is weighted accordingly. Its justification predates the table — it
is the generalised lesson recorded in `_audit/NIGHTKING_AUTOPSY.md` (2026-10-04):
*ask who sets the price on the thinner venue, and whether they are looking at the
thicker one.* Sports ladders are quoted by a global sportsbook market with more
capital and better data; uncovered-and-tight there is evidence of maximum
competition, not its absence. Daily temperature has no such venue.

**Criterion 4 is a hypothesis and phase 1 must test it, using no external data.**
Decompose per-bracket repricing into a ladder-wide common-mode component and an
idiosyncratic per-bracket residual. Report the common-mode variance share per
series. A universe whose repricing is almost entirely common-mode offers the
fitter nothing to work on however tight its book appears. Sports is collected
specifically as the negative control for this cut.

### Universe as fixed, 2026-10-18

| | |
|---|---|
| **Primary** | the **51 live uncovered daily city temperature ladders** (`KXHIGH*`/`KXLOW*`) — breadth 51, depth 2.42×, concentration 31.9%, no thicker external venue |
| **Comparison group** | the **commodity ladders** (99 census series from the collected set, 62 covered) — the subsidised-competitor control |
| **Negative control** | **sports** — collected, never quoted; the test case for criterion 4 |
| **Dropped** | **economics** — 158 of 282 already covered, uncovered remainder 0.5% of the set, and discrete scheduled releases leave no continuous underlying to fit |
| **Provisional on** | the 3,000-page LIP re-sweep converging without finding retail programs on `KXHIGH*`. The 500-page sweep behind this decision was **not exhaustive** (100,000 records, 0% duplicates, still fresh at the cap), so `lip_active=false` is absence of observation, not observation of absence |

Evidence and limitations: `COVERAGE.md`.

### The caveat that travels with every uncovered claim

**Absence from the LPP list is not evidence of an unattended book.** A series can
be uncovered because no provider would take the slot at any subsidy.
`KXAAAGASM` is exactly that — off the LPP list, and simultaneously the worst
microstructure measured anywhere in §5 (43.06% improvable against 58.50%). So
"uncovered" is ambiguous between *the room is unclaimed* and *the room is a
mirage*. Volume, spread and price origin separate the two. The comparison group
exists so the ambiguity is measurable rather than argued: if the uncovered set
underperforms the subsidised-competitor set, the mirage reading wins.

---

## 1B. Phase 0.5 — does the fit know anything? (pre-registered 2026-10-18)

**This gate precedes phase 1 in logic, not in time.** Phase 1 measures whether a
disagreement between the fit and the quote is *capturable*. Phase 0.5 asks the
prior question: when they disagree, **is the fit right?** A quoting strategy
built on a fit that is merely *different* from the market is a machine for
buying adverse selection. If Test A fails, phase 1's numbers are irrelevant
whatever they say, and the project stops.

Every definition below is written **before any phase 0.5 output has been
produced**. Both tests run on historical settled ladders from the staged stores.

### The disagreement set

The unit is a (bracket, minute) observation on a settled ladder where:

- the bracket is **two-sided and executable** — both a bid and an ask exist.
  Fair value is scored against the **quote midpoint of executable bid/ask**,
  never last trade, which is stale and not transactable.
- the fit's fair value lies **outside the fit's own credible band** relative to
  the quote midpoint. The band is the fitter's existing interval; phase 0.5 does
  not invent a new one.
- **No look-ahead.** The fit at time $t$ is constructed from quotes available at
  or before $t$. Any accidental use of $t+$ data invalidates the run.

#### Band rule — ruling, 2026-10-20 (before any Test A data was read)

The second bullet above has two implementable readings and phase 0.5 refused to
pick one by fiat (`FINDINGS_PHASE05.md` §3). **The protocol's author ruled.** The
bullet is left exactly as written; this subsection is what implements it, and it
was committed and pushed before Test A read any data.

**PRIMARY (the gate).** A disagreement is a (bracket, minute) where both sides
are quoted and the **quote midpoint lies outside the fit's 90% credible interval**
for that bracket:

```
m_t < q_05   or   m_t > q_95
```

**Use the interval's actual asymmetric quantiles.** Do not convert to a
symmetric half-width. If the band is skewed — e.g. `[0.48, 0.90]` around a fair
value of `0.50` — **that skew is the fit's uncertainty**, and symmetrising it
throws the information away. This closes the ambiguity in favour of the reading
that keeps the band where the fitter put it.

**The level is 90%, not 95%.** `band90` is what the fitter emits and the only
level validated (93% coverage on synthetic). Any other level would smuggle in an
unstated choice.

**SECONDARY (reported, NOT a gate).** The **executable** disagreement set:

```
ask < q_05   or   bid > q_95
```

Reported alongside the primary because it shows how many disagreements were
actually tradeable. It **cannot rescue a failed primary** and must never be
presented as an alternative verdict.

> Recorded for the audit trail: §2's `e = |F - Q| > w + f` is the *symmetric
> half-width* reading, and phase 0.5 had flagged it as evidence for that
> reading. **The ruling goes the other way on purpose** — §2's `w` is a phase-1
> quoting threshold, and the asymmetry of the fitted band is exactly what
> phase 0.5 is testing the fit's knowledge of.

### Gate 0 — synthetic check of the fit on temperature-shaped ladders (added 2026-10-20, before it was run)

**Mandatory, and it runs BEFORE Test A.** Added by the protocol's author after
phase 0.5 reported that the §1A universe averages **6.00 brackets per event**.

**Why it exists.** The thesis is that the fit beats a single bracket's quote by
**pooling ~25 noisy observations of one distribution** (`BRIEF.md` §2). At six
brackets there is far less to pool, and a 48-knot spline against six prices is
mostly the smoothness prior interpolating between them. There is also a design
mismatch: the extractor infers a density from **how option prices curve across
strikes**, whereas Kalshi brackets are **already probabilities**. Bridging that
needs an adapter, and an adapter is new, unvalidated code. If the fit cannot
beat a noisy quote when the truth is *known and handed to us*, it cannot beat
one on real data, and Test A's result would be uninterpretable.

**Construction.**

- **Adapter lives in `marketmaking/`.** `wti_arb/synth/` is not modified. It
  reuses the existing WTI synthetic pattern in the repo.
- **Known truths**, temperature-shaped, at **~6 brackets per ladder**. The truth
  families are fixed here: **unimodal**, **skewed**, and **bimodal
  (two-peaked)**. Well-behaved unimodal truths alone would flatter the fit;
  a spline through six points is exactly where a second peak gets smoothed away.
- **Quote noise matched to the observed spreads** on the real temperature
  ladders. The measured spread distribution is reported with the result. Spread
  is microstructure, not an outcome variable, and §1A already permits its use.
- **Scored identically to Test A**: the same Brier score, the same band rule
  (the PRIMARY ruling above, asymmetric `q_05`/`q_95`), and the same
  disagreement definition. Fit against **noisy midpoint**, both against the
  **known truth**.

**Pass bar, fixed before the run:**

> **The fit's Brier score is strictly lower than the noisy quote's on the
> disagreement set.**

That is the whole bar. Reported alongside but **explicitly not gating**: the
event-clustered 95% bootstrap CI on the difference, the secondary executable
set, and the per-truth-family breakdown. **The per-family breakdown may not be
used to re-gate** — a pass on the unimodal family alone is a fail.

**On failure: STOP. Do not run Test A. Report.** A failure here means Test A
cannot pass on real data, and the response is to reconsider the universe toward
ladders with more brackets. **That is the protocol author's decision, not the
runner's**, and it is made with this result in hand.

---

### Test A — settlement calibration (the decisive one)

Score two competing probability forecasts of the realised binary outcome: the
fit's fair value, and the bracket's own quote midpoint.

- **Primary:** Brier score, the mean squared error between stated probability
  and the 0/1 settlement outcome. Lower is better.
- **Secondary:** log score. Reported always, including when it disagrees with
  Brier — a disagreement between the two is itself a finding about tails.
- **Clustering.** Brackets of one event share a single settlement outcome and
  are therefore *not* independent observations. Bootstrap **by event**, never by
  bracket. Bracket-level resampling would overstate significance by roughly the
  square root of the brackets per event and is forbidden.

**Pass:** the fit's Brier score is strictly lower than the quote's on the
disagreement set, with the **95% event-clustered bootstrap interval on the
difference excluding zero**.

**On failure: stop and report.** Do not proceed to Test B, do not start phase 1
analysis, do not re-cut the disagreement set looking for a subset that passes.
A post-failure subgroup search is the exact move this protocol exists to
prevent. Reporting *where* it failed is allowed; re-gating on that is not.

### Test B — who converges to whom

Run only if A passes. For each disagreement, track the following **5, 30 and 60
minutes**: did the deviating bracket move back toward the fit (**laggard** — the
quote was stale and we were early), or did the rest of the ladder move toward
the deviating bracket (**leader** — the bracket knew something first and we
would have been run over)?

**"First to move", defined before looking.** Adopted from `waves/` (read, not
modified; see `waves/FINDINGS_WAVES.md` §"Per-bracket normalisation"):

- A **move** is a non-zero minute-to-minute change in a bracket's mid on the
  one-minute grid, on tight two-sided brackets only.
- An **event** is a move at or above the **95th percentile of that bracket's own
  absolute non-zero changes**. Per-bracket normalisation, because a 1c move
  means different things on different books. A bracket with fewer than 50
  non-zero changes borrows its ladder's pooled distribution and is flagged; a
  ladder with fewer than 50 changes in total is skipped. Mids move in half-cent
  steps, so these thresholds are discrete and ties are common — "at or above the
  p95 value" takes materially more than 5% of changes, and the band is labelled
  by the percentile cleared, not by an assumed share.
- The deviating bracket is **first to move** in a preceding window of **W = 15
  minutes** if it recorded an event in that window and **no other bracket in the
  same ladder recorded an event at a strictly earlier minute** within it. Ties
  at the same minute resolve to **not first** — simultaneous repricing is a
  batch update by one maker, which is precisely the case where there is nothing
  to catch.

**Underlying control.** For the two WTI series, the neighbours' later move may
simply be oil moving. Align events against the **CL futures path at one-minute
resolution** where the data exists (the CME intraday bars already bought cover
WTI) and report the laggard share both raw and residual to the underlying's move
over the same horizon. `waves/NEXT_STUDY.md` item 1 flags this as the
direction-deciding control; a "wave" fully explained by the underlying is a
trend, not a propagation.

**Pass:** laggard share **above 50% with the 95% confidence interval excluding
50%**, in at least the **non-leader subset** (deviations where the bracket was
not first to move).

**Interpretation, fixed in advance:**

- A passes, B laggard-dominated → the thesis survives both gates; phase 1
  proceeds on the full disagreement set.
- A passes, **leaders dominate** → the strategy narrows to **non-leader
  deviations only**, and "was this bracket first to move?" becomes a hard
  pre-trade filter in the quoter. Quoting against a leader is adverse selection
  in its purest form.
- **A fails** → stop. Report, and do not start phase 1 analysis.

### What phase 0.5 may not do

It runs on **settled historical** ladders and touches no live collection. It may
not change the universe fixed in §1A, may not alter the density extractor in
`wti_arb/synth/`, and may not modify `ladder/` or `waves/`. Its outputs go to
`FINDINGS_PHASE05.md`.

---

## 2. Phase 1 gate — the population test

**This gate measures opportunity. It does not measure profitability.** Passing it
means there exists a documented, repeatable set of brackets where the fit can
tell the market is wrong by more than the fit's own uncertainty. It does not mean
those brackets are tradeable, and it does not mean quoting them makes money.
Adverse selection is not tested here. It is tested in §3, against a different
gate, from different data.

### Definitions

Per bracket, per update:

```
fair value        F       from the density fit (wti_arb/synth/, unmodified)
credible band     w       half-width of the fit's credible interval for that bracket
executable quote  Q       the price we would have to beat to be BBO on the side we would post
edge              e = |F - Q|
fee               f = 0   (51 maker-free series; see §1)
```

A **bracket-minute qualifies** when

```
e > w + f
```

and the fit passes all three health checks that minute (convexity, normalisation,
mean consistency). **A bracket-minute from an unhealthy fit never qualifies**, and
is counted separately rather than dropped silently — the rate of unhealthy fits
is itself a phase-1 deliverable.

### The gate

A qualifying population that is **non-empty, documented and repeatable**. All
four conditions, pre-stated:

| # | Condition | Threshold |
|---|---|---|
| 1 | Non-empty | ≥ 1 qualifying bracket-minute |
| 2 | **Temporally repeatable** | qualifying bracket-minutes occur on **≥ 10 of the 14 collection days** |
| 3 | **Not day-concentrated** | **no single day contributes > 25%** of all qualifying bracket-minutes |
| 4 | **Not series-concentrated** | **≥ 3 distinct series** each contribute **≥ 5%** of qualifying bracket-minutes |

Conditions 2–4 are my operationalisation of the brief's word *repeatable*; the
brief left it qualitative. Condition 4 is the generalised §5 lesson: a headline
that rests on one series is a headline about one series. Had condition 4 been in
force earlier, the KXAAAGASM denominator question would have been answered before
it was asked.

**If the population is empty, the finding is that it is empty, and the project
stops at the phase-1 gate.** That is a permitted and genuinely useful outcome.

### Required reporting cuts

Reported for the qualifying population **and** for the full population, so the
selection effect is visible:

- **By series** — all 51, not aggregated; `KXAAAGASM` reported separately and
  excluded from totals
- **By moneyness** — bracket centre relative to spot, bucketed; ATM / near / wing
  boundaries fixed before collection and recorded in `FINDINGS_SHADOW.md`
- **By time of day** — UTC hour, with CME pit hours, CME electronic hours and the
  overnight gap marked; weekends reported separately and never pooled with weekdays
- **Edge size distribution** net of fee — full distribution, not just a mean
- **Quote stability** — how often we would amend, and the amend-to-fill-opportunity
  ratio. Relevant because amend does **not** preserve queue priority on a reprice
  (`FINDINGS_PHASE0.md` §4), so a high amend rate is a hidden cost, not a detail
- **Fit health** — convergence rate and each of the three checks, by series and hour

### What phase 1 must not report

**No win rate. No P&L. No "accuracy".** Any such number requires a fill model,
and phase 1 has no fill model. If a number in `FINDINGS_SHADOW.md` can be read as
"how often we would have been right", it is out of scope and must be removed.

---

## 3. The 58.50% is not a win rate

This has its own section because it is the single most likely misreading of this
project's own prior work, and because the two gates must not bleed into each other.

**What 58.50% is.** The share of bracket-minutes in which a 1-cent improvement on
at least one side was *possible* — i.e. there was room on the book to post inside
the prevailing quote — and that improvement survives the maker fee. Source:
`FINDINGS_PHASE0_S5_RECOMPUTE.md`, computed over bracket-minutes on the 51
maker-free series.

**What it therefore means.** "We could have been best bid or offer." Nothing more.
It is a statement about **the state of the book**, not about our fair value, not
about our fit, and not about the outcome of any trade.

**Why it is not a win rate, stated as plainly as possible.** Being BBO is the
*entry condition for* adverse selection, not protection against it. A quoter that
is best bid or offer 100% of the time can lose money on 100% of its fills — in
fact that is the canonical way market makers die. The 58.50% figure is measured
on the book *before* anyone trades against it; adverse selection is a fact about
what happens *after*. They are not the same population, the same measurement, or
the same question.

**And the room may not be ours to take.** Phase 0 established that a Kalshi-paid
designated provider operates in these exact series under a maximum-spread and
minimum-uptime mandate. The 5.17c mean spread and the 1.83c of room were measured
**in that participant's presence**. The most likely reading of the room is that it
is *the cost of the subsidy* — the width a contracted quoter is permitted to leave
— rather than an unattended opportunity. §4 exists to test that.

**Operationally:** 58.50% is a prior on how often the book has room. It enters
phase 1 as context and enters phase 2 not at all. The phase-2 gate is computed
from simulated fills alone.

---

## 4. The designated-provider proxy

Phase 2 requires every simulated fill to be tagged with **whether the designated
provider was quoting at that moment, and how wide.** If our fills cluster where it
has deliberately widened, that is the cost-basis problem measured directly, and it
is the test that decides this project.

**Kalshi's book is anonymous.** There is no participant identifier on any public
endpoint. The provider cannot be observed; it can only be inferred. Everything in
this section is therefore an inference with a falsification test attached, and
every phase-2 number that depends on it carries that caveat in the same sentence.

### What the contract implies

The Liquidity Provider Program mandates (`FINDINGS_PHASE0.md` §3): **Maximum
Spread**, **Minimum Size within Spread**, **Minimum Uptime**, and **Market
Coverage — all markets in the Designated Series**. The contracted *values* are set
by reverse auction and are not public. So the proxy must **infer the constraints
from their footprint**, not look them up.

A constrained quoter leaves four signatures. The fourth is the discriminating one.

| | Signature | Why a contract produces it |
|---|---|---|
| **a** | **Spread ceiling** — probability mass piles up just under a specific width, with a sharp right edge instead of a smooth tail | Exceeding the maximum spread breaches the agreement, so the quoter widens *to* the cap and stops |
| **b** | **Size floor** — a recurring exact size at or inside the touch | Minimum size within spread is a contracted number, so it is posted repeatedly and exactly |
| **c** | **Continuity** — near-unbroken two-sided presence | Minimum uptime is measured and paid on |
| **d** | **Series-wide simultaneity** — the above holding across *essentially all markets in a series at once* | **Market Coverage obliges every market in the designated series.** No retail quoter does this. This is the signature that separates a contracted provider from merely a persistent one |

### Proxy definition

Per series, estimate from the **first 7 days only**, then **freeze for the
remainder of the run**:

```
Ŝ   spread ceiling : the width at which the spread distribution's right edge breaks
                     (largest w with P(spread = w) >= 3 x P(spread = w+1c))
Q̂   size floor     : the modal resting size at touch, taken over two-sided minutes
```

A **market-minute is flagged DMM-present** when all four hold:

1. a two-sided quote exists
2. `spread <= Ŝ`
3. `min(bid_size, ask_size) >= Q̂`
4. conditions 1–3 also held in **≥ 90% of the preceding 30 minutes**

A **series-minute is flagged DMM-active** when **≥ 80% of open markets in that
series are simultaneously DMM-present** — signature (d), the discriminating one.

Freezing Ŝ and Q̂ after 7 days means the second week is an out-of-sample test of
parameters fitted on the first. The split is pre-registered here so it cannot be
chosen later to flatter the result.

### Pre-registered validation — phase 1 must run this

The proxy has a **labelled control group**, which is what makes it testable rather
than decorative. Phase 0 recovered the Incentivized Series list, so each ladder
series is known-positive or known-negative *before* any proxy output is examined:

- **Known-positive** — on the LPP list: WTI (**2 providers**), Brent, Corn, Gold,
  Silver, Copper daily/weekly, hourly commodities, Diesel, Gas daily & weekly
- **Known-negative** — ladder series absent from the LPP list

**Primary test.** Let `R+` and `R−` be the DMM-active minute rates on known-positive
and known-negative series.

| Outcome | Verdict | Consequence |
|---|---|---|
| `R+ / R− ≥ 3` | Proxy **discriminates** | Use for phase-2 fill tagging, caveated as an inference |
| `2 ≤ R+ / R− < 3` | **Weak** | Usable only as a reported sensitivity, never in a headline |
| `R+ / R− < 2` | Proxy **fails** | It is detecting "a persistent quoter", not the designated one. Phase 2 reports DMM presence as **unidentifiable** and says so in the verdict line |

These three thresholds are fixed now. The failing branch is a real branch: it is
written down because it is a plausible outcome, and the honest report of a failed
proxy is more valuable than a proxy tuned until it agrees.

**Secondary test (weak, reported either way).** WTI carries **2 providers** against
1 elsewhere. If the proxy resolves structure, WTI should show either roughly double
the depth resting at `Ŝ` or two distinct modes in the size distribution. A null
here does not invalidate the proxy; a positive strengthens it.

**Known confounds, recorded before the fact.** LIP pays retail for exactly the
behaviour the proxy detects — two-sided resting depth meeting a target size — so a
LIP-motivated retail quoter can mimic a contracted one. The ladder series where
this is most likely are the largest LIP payers, `KXAAAGASM` and `KXAAAGASW`. Both
are reported separately and excluded from `R−`. And the programs terminate
2026-12-31, after the phase-1 window, so the natural experiment of the signature
disappearing is unavailable to us.

**The ceiling on all of this.** An anonymous book cannot yield a verified
true-positive. The proxy can be shown to *discriminate*; it can never be shown to
be *correct*. No phase-2 sentence may state that the designated provider was
quoting — only that a market-minute matched the designated-provider signature.

---

## 5. Phase 2 gate — four-term P&L

Unchanged from the brief. Reproduced here so both gates sit in one file, in
separate sections, and neither can be read as the other.

```
P&L = spread captured - adverse selection - fees +/- inventory P&L
```

**Fill simulation is conservative by construction** — these are the brief's terms,
not softened:

- **last in queue** at our price, always
- a fill occurs only when the market trades **through** our price, **never at it**
- every simulated fill tagged with what the mid did over the following **1, 5 and
  30 minutes**

**Gate:** positive simulated P&L after all four terms, across **at least a month**,
**not concentrated in a handful of days.** Operationalised — my wording, the brief
left it qualitative:

| # | Condition |
|---|---|
| 1 | Total four-term P&L > 0 over ≥ 28 collection days |
| 2 | No single day contributes > 25% of total positive P&L |
| 3 | **Removing the best 3 days leaves total P&L still > 0** |

Condition 3 is the one that matters. A month of flat performance carried by three
good days is a strategy with three good days in it, not an edge.

**Additional phase-2 requirement — the decisive test.** Every simulated fill is
tagged with the §4 proxy state at the moment of the fill:

- DMM-present or not, by the §4 definition
- the prevailing spread, and its distance from the frozen `Ŝ`

and the four-term P&L is **reported separately for fills taken while DMM-present
and while not.** The headline question: **do our fills concentrate in minutes when
the provider has widened?** If simulated profit lives predominantly in
DMM-present-and-widened minutes, that is the cost-basis problem measured directly,
and it is a phase-2 **failure** regardless of whether condition 1 passes — because
it means the apparent edge is the subsidy's slack, available precisely when the
subsidised quoter has judged it not worth taking.

**If adverse selection exceeds spread captured, the strategy does not work, and no
tuning fixes it.** That sentence is the brief's and it is reproduced verbatim
because it is the whole reason phases 1 and 2 are separate.

---

## 6. Data retention — full depth from day one

**The constraint that cannot be fixed retroactively.** The §4 proxy needs size at
and inside the touch, per market, per minute, continuously. A store that keeps
only the touch cannot produce it later. Phase 2 needs the proxy. Therefore phase 1
stores full depth from the first sweep or phase 2 is impossible.

| | |
|---|---|
| **Depth captured** | **all price levels, both sides, no truncation** |
| **Universe** | all 52 ladder series, every open market |
| **Cadence** | every sweep, not sampled |
| **Retained** | raw, for the life of the project |

Explicitly **not** the existing `ladder/collect_books.py` behaviour, which keeps
the top 10 levels only and sweeps books every 5th touch sweep. That is correct for
the propagation study and insufficient here. `ladder/` is read-only to this project
and is not modified; `marketmaking/` carries its own collector.

Full depth is affordable: the tick is 1c on a 1–99c range, so a side cannot exceed
99 levels, and the real distributions are far thinner. There is no case for
truncating a bounded structure.

Also captured every cycle, because each silently invalidates something above:
`price_ranges` per market (tick change), and `/incentive_programs` daily (LIP
coverage change).

---

## 7. Phase 1 escalation

**The phase-1 gate is reported, not crossed.** When the 14 days are complete,
`FINDINGS_SHADOW.md` states the gate result and the run stops there. Phase 2
begins only on explicit instruction, regardless of the result.

The order manager is inert for the entire phase. There is no code path from the
quoter to an authenticated endpoint, and the kill switch is checkable by both
operator and agent and honoured within one cycle.
