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
