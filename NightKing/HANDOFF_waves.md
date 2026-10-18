# Do propagation waves exist? — a descriptive census, no model

The previous study (`ladder/FINDINGS_LADDER_DYNAMICS.md`) tested one specific
propagation trade — a 2¢ move, buy the adjacent bracket at the ask, unwind at
the touch five minutes later — and it lost 5.5¢ on average.

**That was too narrow.** A 2¢ threshold on a ladder whose brackets routinely
move 2¢ is noise, and pooling every series, every time-to-expiry and every
liquidity regime averages any structure into nothing.

This pass asks the prior question: **do propagation waves exist at all?**

No model. No trade. No profitability claim. Just: when a bracket makes a move
that is unusual *for that bracket*, what happens to the rest of the ladder, how
far does it travel, and how long does it take?

The purpose is to decide whether this is worth pursuing before any effort goes
into how to capture it.

**Read first:** `ladder/FINDINGS_LADDER_DYNAMICS.md` §0 (data construction — the
store is sparse by design, carry-forward applies) and §2 (the propagation study
being superseded).

---

## 1. The definition that changes everything

The previous study called a move ≥2¢ absolute, pooled across all brackets. That
treats an unremarkable move on an active daily bracket the same as a six-sigma
move on a quiet yearly one.

**Normalise per bracket instead.** For each bracket, build the empirical
distribution of its own minute-to-minute mid changes. An **event** is a move in
the tail of *that* distribution.

This is the single most important change in this brief. Most of what the old
study measured was almost certainly noise with a cent sign on it.

### Do not set the bar too high

The failure mode in both directions is real. Too loose and you are measuring
noise again, which is what the old study did. **Too strict and you end up with
forty events across the whole store, a response curve built on nothing, and no
way to tell a wave from a coincidence.**

So: **sweep the threshold, do not pick one.** Report the full census at a range
of percentiles — somewhere around the 90th, 95th, 99th and 99.9th is a sensible
span, and extend it if the counts warrant. The interesting output is **how the
response changes as the threshold rises**, which is a stronger result than any
single cutoff:

- If the response looks the same at the 90th and the 99.9th, the effect is not
  about unusual moves and the "event" framing is wrong.
- If it strengthens monotonically with the threshold, that is the hypothesis
  confirmed and it tells you where the usable boundary sits.
- If it strengthens and then falls apart at the extreme, that is sample size,
  not a finding — say so.

**Report event counts beside every response number.** A threshold that yields
fewer than a few hundred events after conditioning is too strict to support a
conclusion, and the right response is to loosen it rather than report the thin
cell.

The operator's instruction on this is explicit: **do not be too strict.** Prefer
the loosest threshold that still separates signal from noise, and let the sweep
show where that is.

---

## 2. What to measure

For each event, with no trading assumption anywhere:

**Response amplitude by distance.** The initiating bracket moves by $\Delta$.
How much do brackets at distance 1, 2, 3, … move? Report the response as a
fraction of $\Delta$, so it is comparable across event sizes.

**Response timing by distance.** How long until each neighbour moves? Resolve to
the minute, and report the share that move in the same minute separately — that
is the ceiling on what minute-resolution data can say, and it was 62% for 2¢
moves.

**Decay with distance.** Does the response fall off, and how fast? Exponential,
linear, a cliff? This is the shape of the wave and it is the headline.

**Persistence of the initiator.** Does the initiating bracket hold its move, or
snap back within minutes? **This is the trap check.** A large single-bracket
jump is often a market order sweeping a thin book, which mean-reverts
immediately — chasing that is buying the top of a spike, not catching a wave.
Report the share of events that persist versus revert, by event size.

**Conditioning.** Report the above split by:

- **time to expiry** — days / hours / minutes. Expect the wave to travel less
  far as expiry approaches, since the distribution concentrates and distant
  strikes become unreachable. If the response width scales roughly with
  $\sigma\sqrt{T}$, that is a real structural finding; if it is flat in time,
  that is also informative.
- **series and market type** — commodity vs non-financial (see §3)
- **bracket spread and depth** at the time of the event
- **time of day**

**Event frequency.** How often do events occur per ladder per day, at each
percentile threshold? If a given definition yields one event per ladder per
month, no strategy exists regardless of how clean the wave looks.

---

## 3. Data — the commodity store is not enough

The existing store (`data/parquet/kalshi_candles`, 58.9M candles) is
**commodities only**, and ends 2026-09-10.

The hypothesis is that waves are largest where no underlying forces the ladder
to stay coherent. That points at the non-financial ladders — net worth, awards,
company metrics, political and economic thresholds — **none of which are in the
store.**

**Pull them.** Kalshi market data is free and keyless; `collect.py` and
`kalshi_common.py` already do this and handle the archived-host routing, the
5,000-candle cap, the `*_dollars` fields and the cursor paging. Scope:

- Discover series across **all categories**, not just Commodities — the
  existing discovery takes a category list
- Prefer ladders (`mutually_exclusive` on the event object tells you
  definitively; do not infer from labels)
- 1-minute candles, bid and ask separate, same as the commodity store
- Settled and archived markets included, since events need history

Expect this to be large. Report the scale before pulling everything, and use
judgement about what to prioritise — breadth across market types matters more
here than depth on any one.

**Also extend the store forward.** It ends 2026-09-10; three more weeks exist.

**The live book collector** (`ladder/collect_books.py`) should keep running. It
is the only source of resting size over time, and depth is half of whether a
wave is catchable.

---

## 4. What this is not

- **Not a trading study.** No P&L, no friction model, no filter. Those come
  after, and only if waves exist.
- **Not a model.** Do not fit a propagation kernel, do not predict. Describe.
- **Not a reopening** of the WTI arbitrage or the executable-violation census.
  Both are measured and closed.

The one number that matters is whether a measurable, repeatable wave exists —
and if it does, how big, how far, how fast, and how often.

---

## 5. The sub-minute limit, stated honestly

The previous study found intra-minute crossings 3× more common than
end-of-minute ones, and concluded 1-minute resolution is binding.

**That limit applies here too.** If a wave propagates in seconds, this study
cannot see it and will report "same minute" for everything.

So: report the same-minute share prominently as the ceiling on what is
knowable from candles. If a large fraction of events show same-minute response
across all distances, the honest conclusion is **"the wave may exist but is
invisible at this resolution"**, and the next step is websocket book deltas
rather than a better analysis of candles.

Do not build the websocket collector in this pass. Say whether it is warranted.

---

## 6. Foundational

- **Per-bracket normalisation**, not absolute cent thresholds.
- **Report event counts at every conditioning level.** Conditioning on time
  bucket *and* spread *and* series will thin the sample fast. A clean-looking
  response built on nine events is not a finding.
- **Describe, do not fit.**
- **The initiator-persistence check is required**, not optional. It is the
  difference between a wave and a spike.
- **Say plainly if waves do not exist.** "Responses are same-minute at every
  distance and every threshold; there is nothing to catch at this resolution"
  is a complete and valuable answer that closes a direction cheaply.
- **Executable prices where a price is needed**; mids are acceptable for
  measuring *movement*, but say which is used where.

## 7. Your judgement

- Percentile thresholds for the event definition, and how many to report
- How to handle the sparse store when normalising (a bracket with few candles
  has a poorly estimated move distribution)
- Scope and prioritisation of the new pull
- Whether to measure response on mids, on the touch, or both
- How to present decay-with-distance so the shape is legible

**If a foundational item looks wrong, say so rather than working around it.**
Several briefs in this project have been overturned that way and each
correction was right.

## 8. Deliverables

1. The expanded store — non-financial ladders plus the commodity store brought
   current. Report scale and coverage.
2. `FINDINGS_WAVES.md` — the census: event frequency, response amplitude and
   timing by distance, decay shape, initiator persistence, all conditioned per
   §2, with event counts everywhere.
3. A plain verdict: **do waves exist, are they large enough and slow enough to
   be worth investigating further, and at what resolution would you need to
   observe them.**
4. A short list of what a follow-on study would need to test catchability,
   written after the result and kept separate from it.

## 9. Long runs

Operator starts these and walks away. Retry with backoff, pause and resume
rather than exit on connection loss, checkpoint per completed job, resume as the
default, distinguish "failed" from "not attempted". Timestamped logs including
pauses. The new pull needs network; nothing else does. No spend.

## 10. Environment

macOS, Python 3.9-compatible. Existing stores read-only; the new pull writes to
its own directory. Existing test suites stay green.
