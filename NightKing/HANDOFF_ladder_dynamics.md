# Ladder dynamics — propagation, violations, and whether any of it is tradeable

New direction. The WTI arbitrage is closed (`FINDINGS_BACKTEST_V2.md`): the two
venues agree to within a cent and option replication costs 15–25¢ per Kalshi
dollar. That finding stands and nothing here revisits it.

This study drops the CME side entirely. **It is about the Kalshi ladder against
itself** — how a ladder evolves minute to minute, whether it ever becomes
internally inconsistent, and whether any inconsistency is large enough and
lasts long enough to trade.

It needs no option chain, no settlement matching, no basis, no synchronisation.
Those were the hard parts of the last three months and none of them apply.

**Read first:** `venue_scan.py` (the monotonicity check and orderbook
normalisation already exist there), and `FINDINGS_BACKTEST_V2.md` §on friction,
for the discipline about executable prices.

---

## 1. The idea

A Kalshi ladder is a probability distribution, published every minute with bid
and ask. Its shape is constrained:

- **Cumulative ladders** must be monotone — $\mathbb{Q}(>t_1) \ge \mathbb{Q}(>t_2)$
  for $t_1 < t_2$, because the lower threshold pays in strictly more states
- **Range ladders** must sum to 100 and have non-negative implied density
- **Both** must respond coherently when the underlying moves: a shift lifts or
  lowers neighbouring brackets together, it does not move one in isolation

When one bracket reprices and its neighbours do not, the ladder is temporarily
inconsistent. **That is the object of study.**

Two reasons this is worth doing:

**The constraint is mechanical, not informational.** A lead–lag study bets one
venue processes news slower. This bets a venue cannot violate an internal
identity for long — and you can see the violation directly rather than inferring
it.

**It is local.** A monotonicity violation lives between two adjacent contracts,
so capturing it needs **two legs**. The sum constraint spans the whole ladder and
would need twenty-seven. At ~1–2¢ spreads per leg that is roughly a 13×
difference in friction, which is why the study should be built around *shape*
rather than *sum*.

---

## 2. What to measure

All of this runs on the existing store: 162 series, 56,167 markets, 58.9M
1-minute candles with bid and ask separate.

### 2.1 Violation census

For every ladder, every minute, using **executable prices** (yes_bid / yes_ask
from the stored candles — never the mid, never the displayed "chance"):

- **Monotonicity violations** on cumulative ladders: can you buy the lower
  threshold for less than you can sell the higher one? Edge
  $= \text{bid}(t_2) - \text{ask}(t_1)$ for $t_1 < t_2$.
- **Negative implied density** on range ladders: adjacent brackets whose implied
  density is negative under executable prices.
- **Ladder-sum excursions**: how far the ask sum sits from 100 plus the summed
  spread.

For each: frequency, magnitude distribution, and **duration** — how many
consecutive minutes it persists. Duration is the new thing. A prior snapshot
sweep found only 3 violations across 78 ladders; a violation lasting 30 seconds
would not appear in a snapshot but will appear here.

### 2.2 Propagation / impulse response

The core measurement. When bracket $i$ moves by $\Delta$ at minute $t$:

- How much do brackets $i\pm1, i\pm2, i\pm3$ move over the following minutes?
- **Response function in distance and time.** Does the body reprice before the
  tails? An actively-quoted near-the-money bracket may move instantly while a 3¢
  tail sits stale for ten minutes.
- Is the neighbour's response **predictable in direction** from the initiating
  move?

Define "a move" by a stated threshold on the executable price, fixed in advance.
Your judgement on the threshold; state it and show sensitivity.

### 2.3 Tradeability, built in from the start — not bolted on

**This is the requirement that determines whether the study is useful.**

For every violation and every propagation opportunity, compute the **net after
crossing the spreads you would actually have to cross**:

$$\text{net} = \text{edge} - \sum_{\text{legs}} \text{spread}_\ell - \sum_{\text{legs}} \text{fee}_\ell$$

Kalshi's fee is $\lceil 0.07 \times C \times P(1-P) \rceil$ per contract per
side; check whether maker and taker differ, since that matters for §5.

**Report the net distribution, not the gross.** A 3¢ violation on a market with
2¢ spreads on both legs is not a 3¢ opportunity. The last three months were
repeatedly rescued by insisting on executable prices; keep that.

### 2.4 Depth, jointly with everything above

Impact is the other half. Report **resting size at the touch on the side you
would hit**, per bracket, alongside every violation.

Do not pre-filter by liquidity. **Measure violation magnitude and available
depth together across all 162 series** and plot one against the other.

The expected tension, stated so the result can confirm or refute it:

| | violation size | tradeable depth |
|---|---|---|
| illiquid (AAA gas, thin commodities) | large? | no — a $50 order moved one 12 points |
| liquid (WTI weekly) | small? | yes |

**The question is whether a middle exists.** Produce the scatter — violation
magnitude against depth, with a line marking where magnitude exceeds the full
friction stack. If a region clears, that is the target market. If none does,
that is the answer.

---

## 3. What is already known, so it is not rediscovered

- A snapshot sweep of 78 cumulative ladders found **3 monotonicity violations**,
  sized 1, 2 and 100 contracts. Real, rare, untradeable *in a single instant*.
  The time dimension is what is new.
- A 27-bracket KXWTIW ask sum measured **127¢** — that is 100 plus 27 brackets of
  ~1¢ spread. The sum constraint is weak because the spread band is wide. Expect
  sum excursions to be mostly invisible inside it; the shape constraints are
  tighter.
- A live observation on `KXAAAGASDCA` (California gas, 2026-10-04): `Above 6.3800`
  showed 86% while `Above 6.3850` showed 95% — a visible violation on a
  Pyth/AAA-settled market with no hedge available and a nearly empty book. Worth
  locating in the stored data and checking whether it was tradeable at any size.
- Earlier work established that **TBBO-style trade-sampled data is biased toward
  tight moments** — a quote is recorded when someone crosses it. The Kalshi store
  is candle-based rather than trade-sampled, but check the candle construction
  before trusting quiet minutes.

---

## 4. New data, if it helps

Allowed, and probably needed for part of this.

**Kalshi orderbook snapshots.** The stored candles give top-of-book bid/ask but
not resting size over time; `venue_scan.py` pulls live orderbooks but only at
the moment it runs. If depth-over-time matters for the §2.4 analysis — and it
probably does — propose a collection script and say what it would cost in
runtime. Kalshi market data is free and keyless, so this is time, not money.

**Finer candles.** The store is 1-minute. If violation durations cluster under a
minute, that resolution is the binding constraint and the answer is "we cannot
see it." Say so rather than reporting a floor as a finding.

Anything billable gets a cost preflight and explicit approval first. Nothing in
§2 needs it.

---

## 5. If something is found — scope note

The natural follow-on is posting rather than crossing: quote inside the spread
on brackets where your fair value is better than the market's, and let the
violation come to you instead of paying to reach it.

**Do not build that here.** But do report the one number that decides whether it
is worth considering: across the stored history, **how often does a ladder's own
implied fair value sit inside its quoted spread** — i.e. would a maker quoting
the ladder as a coherent curve have been able to improve on the posted market?

---

## Foundational

- **Executable prices only.** Bid/ask from the stored candles, on the side the
  trade would hit. Never a mid, never the displayed "chance" figure.
- **Net of full friction, always.** Gross edges are not reported without their
  net alongside.
- **Duration is the headline**, not frequency. A violation that exists for one
  minute at 1-minute resolution may not exist at all.
- **State thresholds in advance** — what counts as "a move", what counts as a
  violation — and show sensitivity to them.
- **Report the null plainly if that is the result.** "Violations are 0.5¢ deep
  and last under a minute; prediction market ladders are tighter than they look"
  is a genuine finding and closes a direction cheaply.
- **Do not reopen the WTI arbitrage.** It is measured and closed.

## Your judgement

- Which series to lead with, and whether to run all 162 or a representative
  spread across the liquidity range
- The definition of "a move" and of a violation
- How to handle the 1-minute resolution limit
- Whether orderbook collection is worth starting now in parallel
- Presentation of the magnitude-vs-depth scatter

**If a foundational item looks wrong, say so rather than working around it.**
Three briefs in this project have been overturned that way and each correction
was right.

## Deliverables

1. `FINDINGS_LADDER_DYNAMICS.md` — violation census, propagation response
   functions, the magnitude-vs-depth scatter, and a plain verdict on whether any
   region is tradeable net of friction
2. Reusable analysis code under `ladder/`
3. A short proposal for orderbook collection if §4 warrants it
4. A list of what the next pass should examine, written after the result and
   kept separate from it

## Long runs

Operator starts these and walks away. Retry with backoff, pause and resume
rather than exit, checkpoint per completed job, resume as the default,
distinguish "failed" from "not attempted". Timestamped logs.

## Environment

macOS, Python 3.9-compatible. `data/` and `data_cme/` read-only. Existing test
suites stay green. The extractor is not involved in this study and should not be
modified.
