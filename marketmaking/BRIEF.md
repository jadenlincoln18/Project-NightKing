# Kalshi ladder market making — project brief

**For: Alfred (autonomous build)**
**Status: not started. Nothing here has been tested live.**
**Workspace: `marketmaking/`. Read anywhere, write only here.**

---

## 0. What this is, in one paragraph

Kalshi lists ladders of price brackets that together form a probability
distribution. Those ladders are quoted wide — mean spread **5.17c** on the
subset tight enough to have a meaningful mid. Every strategy this project has
tried so far *crossed* those spreads and lost to friction. This one **posts**
instead: fit a coherent distribution to the whole ladder, find the brackets
whose quotes are inconsistent with that fit, and quote inside the spread on
them. The spread becomes income rather than cost.

It is market making with a model-based fair value. It is **not** arbitrage —
there is no hedge, and inventory risk is real and unhedged.

---

## 1. Where the idea came from — the evidence

Two prior studies in this repo. Read both before building.

### `ladder/FINDINGS_LADDER_DYNAMICS.md`

Censused 211M adjacent-pair-minutes across 1,435 cumulative ladders for
**executable** inconsistencies — cases where you could buy the lower threshold
for less than you could sell the higher one.

| | |
|---|---|
| executable violations | **0.091%** of pair-minutes |
| 77% of them | exactly **one tick** deep |
| median duration | 2 minutes |
| net positive after taker fees | 18% of episodes, median **0.42c** |
| live sweeps finding any | **0 in 1,160** |

Taker side: dead.

**But section 5 of the same document measured the maker side, and it is 56x
larger:**

| | |
|---|---|
| **mid-based** shape violations | **5.15%** of tight pair-minutes |
| a maker posting one tick inside would be on the right side of the fitted shape | **58%** of the time |
| after maker fee | **38%** |
| mean room inside the spread | **1.83c** |
| mean spread | **5.17c** |

The ladder's shape is wrong at the mid **56x more often** than it is executably
wrong. That gap is the whole opportunity: the inconsistency is there, it is just
on the wrong side of the spread to *take*. A maker does not have to take it.

### `waves/FINDINGS_WAVES.md`

Separately established that ladders reprice coherently and fast — adjacent
brackets move in the same minute 61% of the time against a 19% baseline, and the
response decays slowly with distance (5 strikes away still carries 61% of the
adjacent response).

**Why that matters here:** a ladder is treated as one object by the market, so a
bracket that departs from its ladder's fitted shape is genuinely anomalous
rather than independently priced. It also means your quotes must update as a
set, not one bracket at a time.

### The caveat that defines the project

The 58% figure is measured against **the ladder's own smoothed mids**, which on
a 5c-wide book is a weak fair value. The finding says a coherent quoter would
often have been best bid or offer. **It does not say being there is profitable.**

Closing that gap is the work.

---

## 2. The thesis

**A ladder must be internally coherent.** Cumulative ladders must be monotone;
range ladders must sum to 1 and imply a non-negative density. One distribution
generates all of them.

**Individual brackets drift off that shape.** Quotes go stale, one-sided, or get
set by someone looking at a single bracket rather than the curve.

**Fitting the whole ladder gives a better per-bracket estimate than any single
bracket's own quote**, because you pool ~25 noisy observations of one object.

**Where a bracket's quote departs from the fit by more than the fit's own
uncertainty, quote inside its spread on the side the fit favours.** Collect the
spread when filled, holding a view better than the market's.

---

## 3. What already exists — reuse it, do not rebuild

| what | where | note |
|---|---|---|
| density extractor (Act III) | `wti_arb/synth/act3.py` | B-spline log-density, 48 knots, Gaussian roughness prior, 1c tick floor, hand-rolled NUTS with analytic gradients. Validated: 90% bands contain truth 93% of the time; agrees with an independent venue to within 1c across 535 comparisons. |
| ladder store and parsing | `ladder/store.py`, `ladder/kapi.py` | Candle store, carry-forward grid, the bids-only orderbook normalisation (`yes_ask = 100 - best_no_bid`) |
| fee model | `ladder/fees.py` | Verify against current Kalshi docs before trusting it |
| live book collector | `ladder/collect_books.py` | Resting size over time — the only depth source |
| historical stores | `data/`, `waves_data/` | 50.7M mid changes, 34,921 ladders, 14 categories |

### The architectural insight

**The extractor does not care where the prices came from.** It takes a set of
prices on a strike ladder and returns a smooth density with error bars. Feed it
Kalshi bracket quotes instead of CME option prices and it works on **every
ladder series on the exchange** — 1,859 of them — not just the two WTI series
that happen to have a matching options chain.

That generalisation is what makes this a business rather than a WTI trade.

**Where a CME chain does exist (the two WTI series) you have a second,
independent fair value**, validated against that venue. Use it as a check on the
ladder-fitted one. Where the two disagree on a bracket, that is information.

---

## 4. Architecture

```
collector --> book store --> fitter --> quoter --> (phase-gated) order manager
                   |                       |                    |
                   +-------> risk monitor <+--------------------+
                                  |
                             kill switch
```

**Collector.** Poll Kalshi for orderbooks on the target ladders. Store full
depth, not just the touch — resting size is half of every decision here.
Timestamp everything. Keyless, free, ~30 rps public cap.

**Fitter.** Per ladder, per update: take all brackets' executable quotes, fit the
density, produce a fair value **with a credible band** per bracket. The band is
not optional — it separates "the market is wrong" from "I cannot tell."

**Quoter.** Per bracket, decide whether to post, at what price, in what size.
Post inside the existing spread only where the fit's edge exceeds the fit's own
uncertainty plus the fee.

**Order manager.** Place, amend, cancel. Phase-gated: inert until phase 3.

**Risk monitor.** Inventory per ladder and overall, P&L, fill quality, model
health. Independent of the quoter, and able to halt it.

**Kill switch.** A single file or flag that stops all quoting and cancels
everything, checkable by you and by the operator, honoured within one cycle.

---

## 5. Phases — do not skip, do not reorder

### Phase 0 — resolve the unknowns (no trading code)

**Genuine unknowns. Resolve by querying or reading docs, not by assuming.**
Report findings before building on them.

1. **Does Kalshi charge makers differently from takers?** The known formula is
   ceil(0.07 * C * P * (1-P)) per contract per side. If makers pay less — or
   nothing — the economics change materially. **This is the single most
   important number in the project.**
2. **What does the order API support?** Limit orders, post-only flag, amend in
   place vs cancel-replace, rate limits on order actions (separate from
   market-data limits), minimum sizes, self-trade prevention.
3. **Is there a maker rebate, volume tier, or market-maker programme?**
4. **What determines queue position**, and can you observe it?
5. **Settlement and collateral.** When short a bracket, what collateral is held?
   Does Kalshi net across brackets of one event? **If it nets, the capital
   requirement for a ladder-wide position is far lower than the naive sum** —
   flagged unverified in `ladder/FINDINGS_LADDER_DYNAMICS.md` and it matters
   here too.
6. **Rate limits for a continuously-quoting account**, and the behaviour on
   breach.

### Phase 1 — shadow mode

Full stack, order manager disabled. Every cycle, compute and **log** the quotes
you would have posted. Never place one.

At least two weeks, weekdays and weekends.

Report:
- How often the fit says a bracket is mispriced by more than its own band
- Distribution of edge size, net of fee
- Which series, which moneyness, which time of day
- Quote stability — how often would you be amending?
- Fit health: convergence, the three checks (convexity, normalisation, mean
  consistency), how often the fit itself is untrustworthy

**Gate to phase 2:** a documented, repeatable population of brackets where edge
exceeds band plus fee. If that population is empty, say so and stop.

### Phase 2 — paper fills

Still no orders. Simulate fills **conservatively**:

- Assume you are **last in queue** at your price.
- A fill occurs only when the market trades **through** your price, not at it.
- Model adverse selection explicitly: tag each simulated fill with what the mid
  did over the following 1, 5 and 30 minutes. **A fill that is immediately
  underwater is the thing that kills market makers** — measure it, do not assume
  it away.

Report simulated P&L decomposed into four terms:

    P&L = spread captured - adverse selection - fees +/- inventory P&L

**If adverse selection exceeds spread captured, the strategy does not work**, and
no tuning fixes it — that is the market saying your fair value is worse than
that of the people trading against you.

**Gate to phase 3:** positive simulated P&L after all four terms, across at least
a month, not concentrated in a handful of days.

### Phase 3 — live, minimum size

One ladder. Smallest viable size. Full logging.

The purpose is not profit. It is to test what no simulation can:
- Do fills happen where you modelled them?
- What is your real queue position?
- Latency on place, amend, cancel
- Does anything behave differently with real money attached?

At least two weeks. Compare every simulated assumption against reality and
**report the differences**, especially where reality is worse.

### Phase 4 — scale

Only if phase 3 matches phase 2 within a stated tolerance. More ladders, then
more size, one step at a time, with a stated rule for when to stop.

---

## 6. Non-negotiable discipline

Each exists because this project got it wrong at least once.

**Executable prices, always.** Bid and ask, on the side a trade would hit. Never
a mid, never Kalshi's displayed "chance" figure. The mid-vs-executable gap has
been measured at 3.1c in one study and 12 points on a live $50 order.

**State the bar before you look.** Before phase 2 produces a number, write down
what result would justify phase 3 — and commit it. A threshold chosen after
seeing the P&L is not a threshold. Precedent: `wti_arb/BACKTEST_PROTOCOL.md`,
committed 19:49, first data read 20:04.

**Full friction, every time.** Fees both sides, the spread crossed when
flattening, any funding or collateral cost.

**Report the denominator.** Opportunities attempted, skipped, and why. A hit
rate without the misses is not a hit rate.

**No post-hoc tuning.** If something needs changing after a result, write it
down for the next pass and report the untuned number.

**Say plainly when it does not work.** "Adverse selection is 1.4x spread capture;
this does not work" is the most valuable possible output if true. Four prior
studies here returned nulls and each saved months.

**Never place an order outside the current phase**, whatever the opportunity
looks like.

---

## 7. How this most likely fails

**Adverse selection.** You get filled precisely when you are wrong, because the
taker knows something. Measured as fill-conditional mid drift. This is the
default outcome for a naive maker and the main thing phase 2 exists to detect.

**Your fair value is worse than theirs.** The 58% figure was against smoothed
mids. If existing quoters have a better model, you are the liquidity, not the
maker.

**Queue position.** Being at the best price is not being filled. If established
makers sit ahead of you, you get the leftovers — which correlate with being
wrong.

**Inventory.** No hedge. Long twenty tail brackets when the underlying gaps and
nothing offsets it. Inventory limits must be hard, enforced by the risk monitor,
not by the quoter's good intentions.

**Thin markets.** Where spreads are widest your own quote moves the market; a $50
order has already been observed moving one bracket 12 points.

**Model failure in the tail.** The extractor has a documented blind spot: on a
bimodal truth the trough is overstated with tight bands and no diagnostic fires
(`wti_arb/FINDINGS_SYNTHETIC_V2.md`). Mitigation already identified: **do not
quote a bracket sitting in an interior local minimum of the fitted density.**
Implement that from day one.

---

## 8. Working autonomously

You will run this largely unsupervised. Structure it so that is safe.

**Cron cadence**
- Collector: continuous, with a watchdog that restarts it and logs the gap
- Fitter + quoter: whatever cycle the phase needs; start slow
- Risk monitor: every cycle, independent process
- Daily report: `marketmaking/reports/YYYY-MM-DD.md`
- Weekly summary: phase status, metrics against the stated bar, what changed

**Reporting for an operator who is not watching.** Each daily report, in order:

1. **Status** — phase, running or halted, anything needing a human
2. **What happened** — cycles, opportunities found, (phase 3+) fills and P&L
3. **Model health** — convergence, the three checks, how often the fit was
   rejected
4. **What changed** against yesterday, and your reading of why
5. **Decisions you made and why** — the audit trail

Lead with what needs attention. The operator should read five lines and know
whether to open the rest.

**Escalate rather than decide** when:
- A phase gate is reached (you propose, the operator approves)
- Any spend is required
- Something happens you cannot explain
- The kill switch fires
- A non-negotiable in section 6 would have to bend

**Continuity.** Keep `marketmaking/STATE.md` current: phase, what is running,
what is blocked, what you are waiting on, what you learned recently. Assume the
next session starts cold.

**Fail loudly.** Four prior failures in this repo were silent — a request that
400'd while logs said success, a field name that stored all-null columns while
row counts looked healthy. **Verify by content, not by count.** If a fit
produced 25 fair values, check they are not all identical before trusting them.

**Checkpoint continuously.** One line per completed unit of work. Resume as the
default. Distinguish "failed" from "not attempted" — conflating those cost four
collection runs.

---

## 9. Deliverables

1. `marketmaking/FINDINGS_PHASE0.md` — the six unknowns in section 5, answered
2. The stack: collector, fitter, quoter, risk monitor, kill switch, phase-gated
3. `marketmaking/PROTOCOL.md` — the bar for each gate, committed before the
   corresponding data is read
4. `marketmaking/FINDINGS_SHADOW.md` — phase 1
5. `marketmaking/FINDINGS_PAPER.md` — phase 2, with the four-term P&L
   decomposition
6. `marketmaking/STATE.md` — kept current
7. `marketmaking/reports/` — dailies
8. Tests. The repo's convention is a green suite before anything runs.

---

## 10. Scope

**In:** everything above, confined to `marketmaking/`.

**Out:** the WTI arbitrage (measured and closed — `wti_arb/FINDINGS_BACKTEST_V2.md`),
the propagation and waves studies (active, worked separately — **do not modify
`ladder/` or `waves/`**), any change to the density extractor's model (read and
reuse `wti_arb/synth/`, do not alter it).

**Read-only outside `marketmaking/`.** If something elsewhere needs changing, say
so rather than changing it.

---

## 11. Environment

macOS, Python 3.9-compatible. Kalshi market data is free and keyless; **trading
requires an authenticated API key, which the operator must provide and which must
never be committed.** `.env`, gitignored, as the rest of the repo does it.

No budget. Nothing here requires paid data.

---

## 12. First thing to do

Read `ladder/FINDINGS_LADDER_DYNAMICS.md` section 5 and `waves/FINDINGS_WAVES.md`
verdict. Then phase 0, and report the six answers before writing anything that
quotes.

**Especially the maker fee.** If makers pay the full taker rate, the 38%
after-fee figure is the ceiling and this is much harder than it looks. If makers
pay nothing, the 58% figure applies and the project is substantially more
attractive. Resolve that number before anything else is built.
