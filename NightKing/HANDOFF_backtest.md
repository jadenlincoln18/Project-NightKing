# The backtest — extracted densities against Kalshi bracket prices

This is the first time Kalshi prices enter the pipeline. Every brief until now
has said "descriptive only, no Kalshi price read, no gap computed." That
constraint lifts here.

**It lifts for the measurement, not for the method.** Everything the extractor
does is now fixed. Nothing about the prior, the basis, the error model, the
synchronisation or the gates changes in this pass, whatever the gaps look like.
If the result is disappointing, that is the result.

**Read first:**

1. `nightking-strategy-writeup.md` Part 4 Act IV (Stages 16–19) and Part 5 —
   the decision rules and the trade structure
2. `NightKing/PIPELINE_CHOICES.md` — Stage 18, and the two sizing rules
3. `FINDINGS_TICKFLOOR.md` §2 — the real-chain state the backtest inherits
4. `FINDINGS_REALCHAIN_V4.md` — gate behaviour and the watch chains

---

## 0. Before reading a single Kalshi price

**Write `BACKTEST_PROTOCOL.md` and commit it before any Kalshi data is loaded.**
Timestamped, in git, so the order is verifiable afterwards.

It must fix, in advance:

- **The evidentiary bar.** What result would count as a real edge? The effective
  sample is ~34 hedgeable KXWTIW dates. Brackets within an expiry share a
  density and consecutive weeks share a regime, so effective n is nearer 34 than
  the ~850 bracket-comparisons it will look like. State what magnitude,
  consistency and sign-stability you require. **A bar chosen after seeing the
  gaps is not a bar.**
- **The friction stack**, per leg, with the arithmetic shown: Kalshi's fee
  formula, Kalshi's spread, CME per-contract fees across all four option legs,
  CME spreads. The writeup's working figure is ~5¢ per contract round trip —
  derive it properly rather than inheriting it.
- **The filter thresholds.** Stage 19 is `|gap| > band + friction`. Any
  additional threshold (minimum bracket price, maximum band width, minimum
  depth) is fixed here.
- **The gate set**: split-half, Act II as the shape signal, Gate 0, plus the
  interior-local-minimum rule below.
- **How a date gets excluded**, and the commitment that every exclusion is
  logged with its reason so the denominator is auditable.

This document is the protection against the one failure this project has not
yet had an opportunity to make: deciding what is convincing after seeing what
happened.

---

## 1. The gates, including one new one

Per date and snapshot, before any comparison:

- **Gate 0** — same-day CME weekly expiry, contract month matching Kalshi's
  `rules_primary`, 8+ strikes with 3+ per wing
- **Split-half** — the data-consistency gate, currently firing on 3% of T-1d
  chains with the tick floor
- **Act II disagreement** — reported as the shape signal, not a hard gate
  (`FINDINGS_ACTII_V2.md`)

**New: the interior-local-minimum rule.** Do not trade a bracket that sits in an
interior local minimum of the extracted density. In a unimodal density the
low-probability regions are the outer tails; a dip in the *middle* is the
signature of the residual bimodal blind spot (trough coverage 57%, so roughly
two in five such cases are wrong). Costs nothing, needs no model change, and
covers the one failure mode the gates miss. Apply it per bracket, not per date,
and report how many brackets it removes.

**LOO proximity.** LOO still flags a strike on 87% of T-1d chains even with the
floor, while split-half says the chains are globally consistent. Those measure
different things. A misfitting strike adjacent to the bracket being priced
matters far more than one in the far wing. **Report, per candidate trade,
whether a LOO-flagged strike sits within some stated distance of the bracket
edges**, and treat that as a reported risk factor rather than a gate unless the
data says otherwise.

---

## 2. Executable prices, never mids

**This is the single most important mechanical requirement.** fedarb measured a
3.1¢ average gap between mid and executable, which was the same size as its
entire apparent edge. A backtest on mids measures something that does not exist.

- Kalshi: use the **bid/ask from the stored 1-minute candles**, on the side you
  would have to hit. Buying a bracket means paying the ask. Never the "chance"
  percentage, never a mid.
- CME: the TBBO quotes, same discipline, on all four legs.
- Where a side is unquoted, the trade is not available. Log it, do not infer a
  price.
- **Depth.** Lifetime bracket volume is not resting depth. Where the stored data
  cannot establish that the size was available, say so rather than assuming.

---

## 3. The comparison

For each surviving date, snapshot and bracket:

1. **Stage 16/17** — integrate each posterior draw over Kalshi's exact bracket
   edges, giving a distribution of model probabilities per bracket
2. Gap $g_j = p^{\text{mkt}}_j - \bar p^{\mathbb{Q}}_j$, with the band from the
   posterior spread
3. **Stage 18 decomposition**, per posterior draw:

$$\text{logit}(p^{\text{mkt}}_j) = a + b\,\text{logit}(p^{\mathbb{Q}}_j) + c\,m_j + \varepsilon_j$$

   $b < 1$ is the favourite–longshot bias; $c \neq 0$ is the risk-premium tilt,
   monotone in the state. Running it per draw gives a distribution over
   $(a,b,c)$, so "is $b$ meaningfully below 1" has a credible interval rather
   than a point estimate.

**Stage 18 is required, not optional.** `PIPELINE_CHOICES.md` explains why: with
discrete strikes the hedge always has a ramp, so you always retain residual
exposure, and you need to know whether you are harvesting a retail bias or
selling insurance. Those are different businesses with different tail risk.

4. **Stage 19** — the filter, at the thresholds fixed in §0

---

## 4. Sizing, and a constraint that is still unresolved

`PIPELINE_MAP.md` carries this as an open problem and it bears directly on what
the backtest should simulate.

Micro WTI options (**MCO**) expire on the **monthly cycle only**. Kalshi's
weekly market settles on a Friday, and only the standard-size weeklies
(ML/WL/LO) expire that day. So:

- Micro gives the right size (~50 Kalshi contracts per structure) and the
  **wrong expiry**
- The weeklies give the right expiry and **too large a size** (~500 contracts
  per structure)

And the depth scan found that at 500 contracts the **ask side failed in 6 of 9**
moderate-tail brackets, while 50 cleared everywhere.

**So the backtest must simulate the size that is actually available**, which for
weekly Kalshi dates is the standard-CL unit. Simulating 50-contract positions
where 500 would be required overstates feasibility, and that is precisely the
error that made fedarb look tradeable longer than it was.

Report feasibility at **both** 50 and 500, state which applies per date, and
make the shortfall visible.

**The two sizing rules** (`PIPELINE_CHOICES.md`) hold: size as
hold-to-settlement, assuming no early exit; and size for the **unhedged ramp
residual**, not the locked gap.

**The hedge ratio** is operator-owned and he intends to derive it himself. The
backtest needs one to compute P&L. Compute what you need, **state the derivation
explicitly** so he can check it against his own, and keep the gap analysis in §3
independent of it so that work is not blocked.

---

## 5. What to report

**The gap distribution is the deliverable. P&L is a consequence, not the
headline.**

- Gaps by bracket moneyness, with bands — is there structure, or noise around
  zero?
- **Sign stability across dates.** A real effect is consistent; an artifact
  often is too, which is why §6 matters.
- $(a, b, c)$ from Stage 18 with credible intervals
- How many brackets clear the filter, and **which dates they come from.** If
  most of the edge comes from three weeks, that is a regime observation, not a
  strategy.
- P&L net of the full friction stack, held to settlement, at realistic size
- **The full denominator**: dates attempted, dates gated out and why, brackets
  removed by the interior-minimum rule, brackets with no executable price
- Signals that did not clear the filter, logged anyway — the out-of-sample
  record accumulates whether or not you would have acted

---

## 6. The traps, named

**Measurement artifacts look exactly like edges.** This project has already seen
one: fedarb's −8pt, which was a mis-centred density producing a smooth,
persistent, sign-consistent disagreement. Before concluding anything, check that
the gap is not explained by residual forward error, residual asynchronicity, or
a systematic error at one snapshot.

**Do not tune anything.** No threshold adjustment, no gate retuning, no prior
work, no re-examination of the extractor. If something looks like it needs
tuning, write it down for the next pass and report the untuned result.

**Do not drop inconvenient dates.** Every exclusion traces to a rule in
`BACKTEST_PROTOCOL.md`.

**Watch for the ramp.** The hedge is four option legs against a sharp digital.
Inside the ramp the legs do not cancel. P&L that ignores it is overstated.

**A null result is a result.** "The gaps are indistinguishable from zero at this
sample size" is a finding, and reporting it honestly is worth more than a number
that survives only because the bar moved.

---

## 7. Inherited open items — do not solve them here

- **June 15, −$4.70** ICE/NYMEX divergence, one day before Kalshi's roll. Blocks
  sizing, not backtesting. If it falls inside the window, flag that date's
  results separately.
- **Bimodal trough** at 1.4σ / 57% coverage. Gated by the interior-minimum rule.
- **Spike config** at 60%. Deprioritised.
- **Harness noise model** cannot arbitrate the tick floor. Drawing-board.
- **Kalshi's roll convention** — the referenced month switches on the 16th,
  independent of either exchange's expiry. Gate 0 handles it; make sure the
  backtest's contract matching uses `rules_primary`, not front month.

---

## Foundational

- **`BACKTEST_PROTOCOL.md` is committed before any Kalshi price is read.**
- **Executable prices only.**
- **No change to the extractor**, whatever the gaps look like.
- **Every exclusion logged with its reason.**
- **Report the denominator**, not just the hits.
- **Say plainly if there is no edge.**

## Your judgement

- Which snapshot to lead with — T-4h is closest to decision time but T-1d is the
  better-conditioned extraction; defensible either way, report both
- Whether to include KXWTI's 83 hedgeable Mon/Wed/Fri dates alongside KXWTIW's
  34, given the harder short-dated extraction
- The friction stack's exact construction
- How to present gap structure so that regime concentration is visible
- The LOO-proximity distance threshold

**If a foundational item looks wrong, say so rather than working around it.**
Two prior briefs were overturned that way and both corrections were right.

## Deliverables

1. `BACKTEST_PROTOCOL.md` — committed first, before any Kalshi data is loaded
2. The backtest implementation, resumable, with every skip logged
3. `FINDINGS_BACKTEST.md` — gap distribution, Stage 18 decomposition, filter
   results, P&L at realistic size, the full denominator, and a plain verdict
   against the bar set in the protocol
4. A short list of what the next pass should examine, written *after* the
   result, kept separate from the result itself

## Long runs

Operator starts these and walks away. Retry with backoff, pause and resume
rather than exit, checkpoint per completed job, resume as the default,
distinguish "failed" from "not attempted". Timestamped logs. No network, no
spend — all data is local.

## Environment

macOS, Python 3.9-compatible, numpy/scipy. `data/` and `data_cme/` read-only.
Both test suites stay green. 48 knots and the 1¢ tick floor are the defaults.
