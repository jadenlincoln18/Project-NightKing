# FINDINGS_PHASE0 — the six unknowns, answered

Produced 2026-10-16 by Alfred, autonomous. Scope: `marketmaking/` only; `ladder/`,
`waves/` and `wti_arb/` read, not modified. No trading code written, no order ever
placed, no authenticated endpoint called — every finding below comes from a primary
document or the keyless public API.

Brief: `marketmaking/BRIEF.md` §5 phase 0. Supporting raw reports:
`/tmp/nk_ro/phase0_orderapi.md`, `phase0_queue_incentives.md`, `phase0_collateral.md`.

---

## Verdict

**The fee question resolves in the project's favour, and the capital question
resolves better than the brief assumed. But phase 0 surfaced a competitor the
brief did not know about, and it sits in exactly our target series.**

Three things changed:

1. **Makers pay nothing on 51 of the 52 ladder series.** The brief's two branches
   were "makers pay 0.0175 → 38% of bracket-minutes survive the fee" and "makers
   pay nothing → 58%". It is the 58% branch, essentially everywhere we care about.
   `KXAAAGASM` is the sole exception — and it is the series heading §5's table.
   **Recomputed on the maker-free series only: 58.50%, against 57.79% published**
   (`FINDINGS_PHASE0_S5_RECOMPUTE.md`). The headline survives. `KXAAAGASM` heads
   the table by *ladder*-minutes but is only 4.63% of the *bracket*-minutes the
   figure is computed over, so it never dominated it. The 38% branch, however,
   should be retired rather than recomputed: it describes every series paying a
   fee when exactly one does.

2. **Kalshi runs a subsidised, designated market maker in our target series.**
   The Liquidity Provider Program pays up to **$50,000 per week per series** to a
   provider contractually bound to maximum spread, minimum size and minimum uptime.
   Active Incentivized Series include **WTI, Brent, Gold, Silver, Copper, Diesel,
   daily and weekly gas, and hourly commodities** — the ladders this project
   targets. Most have exactly one provider; WTI has two.

3. **Kalshi will also pay *us* to rest orders, filled or not.** The Liquidity
   Incentive Program is open to retail, requires no opt-in and no agreement, and
   pays $1–$1,000 per market per day for two-sided resting depth. It is
   machine-readable and keyless via `GET /incentive_programs`.

(2) and (3) are the same fact seen from both ends: this book is *paid for*. That
cuts against the thesis and for it simultaneously, and neither effect was in the
brief's model. Resolving which dominates is now the central question of phase 1 —
ahead of, and more important than, the edge-versus-band population the brief
nominates as the phase-1 gate.

**Nothing here says the strategy works.** Zero maker fee removes a cost term. It
does not touch adverse selection, which is what kills makers and what phase 2
exists to measure.

---

## 1. Does Kalshi charge makers differently from takers?

**Answered. Taker 0.07; maker 0.0175 where charged; maker fee is ZERO on 51 of our
52 ladder series.**

Official schedule (Feb 5 2026 revision, retrieved as a byte-identical Internet
Archive capture of `kalshi.com/docs/kalshi-fee-schedule.pdf` — the live URL sits
behind a Vercel bot checkpoint, which is the same block that defeated
`ladder/FINDINGS_LADDER_DYNAMICS.md` §8):

> fees = round up(0.07 x C x P x (1-P))
>
> **Maker Fees**
> fees = round up(0.0175 x C x P x (1-P))

> Trading fees are not charged for orders placed that are not immediately matched
> and are instead left as resting orders on the orderbook **unless they are
> included in our 'Maker Fees' section.**

So `ladder/FINDINGS_LADDER_DYNAMICS.md` §8's "0.0175 per secondary sources" is
**confirmed, not refuted** — but applying it flat was wrong. Maker fees are
per-series opt-in, and almost none of our series are in.

### Which series actually charge makers — measured, not assumed

The live keyless series endpoint exposes `fee_type` and `fee_multiplier`. It
distinguishes `quadratic` (taker-only) from `quadratic_with_maker_fees`, and it
cross-validates exactly against the published non-standard table (`KXAAAGASM`
listed with maker multiplier 1; `KXBTCY` listed 0/0 and returning
`fee_multiplier: 0`). That makes the API a trustworthy primary source here.

All 52 ladder series named in `FINDINGS_LADDER_DYNAMICS.md` were queried
(`/tmp/nk_ro/fee_map_ladder.json`):

| fee_type | series | maker coefficient |
|---|---|---|
| `quadratic` | **51** | **0** |
| `quadratic_with_maker_fees` (mult 1) | 1 — `KXAAAGASM` | 0.0175 |

Maker-free includes every series the project would actually target: `KXWTI`,
`KXWTIW`, `KXWTIMAX`, `KXWTIMIN`, `KXNATGASD`, `KXGOLDD`, `KXGOLDW`, `KXGOLDMON`,
`KXSILVERD`, `KXBRENTD`, `KXCOPPERD`, `KXDIESELW`, `KXSOLAR`, `KXBARRELS`,
`KXOILRIGS`, and 36 others.

**Consequence for §5's headline.** §5 reported 58% at maker-fee-zero and 38% at
0.0175. The applicable figure for 51 of 52 series is **58%**, and the mean 1.83c
of room inside a 5.17c spread survives whole.

**The sharp edge of this.** `KXAAAGASM` is the one series that charges a maker fee,
and it is the top row of §5's table by sample size (104,180 minutes, 43.06%
improvable). The largest single contributor to the headline is the one series
where the economics are worst. Any phase-1 population must be reported per series,
never pooled.

**One more thing a quoter must not get wrong.** Fees are per-series and can change;
`GET /series/fee_changes` and `GET /events/{ticker}/fee_changes` publish scheduled
changes, and event-level overrides layer on top of the series. Read fee state
live; never hardcode it.

---

## 2. What does the order API support?

**Answered, from the published OpenAPI spec (`docs.kalshi.com/openapi.yaml`,
v3.34.0) and AsyncAPI spec, cross-checked against the live API.**

| capability | answer |
|---|---|
| Order types | **Limit only.** `type=market` was removed 2026-02-11; FIX accepts `OrdType 2=Limit` only. |
| Post-only | **Yes** — `post_only` boolean, default false. Cancel-on-cross confirmed by four independent citations; rejection surfaces as `PostOnlyCrossCancel`. |
| Amend in place | **Yes** — `POST /portfolio/events/orders/{id}/amend`. **But see queue warning below.** |
| Batch | Create / cancel / cancel-all all exist. No fixed size cap — bounded by the rate-limit bucket. |
| Minimum size | Spec says 0.01 contracts; a Feb 2026 changelog says fractional trading is not enabled. **Assume 1 whole contract.** |
| Self-trade prevention | **Required field** in v2 — `self_trade_prevention_type` ∈ {`taker_at_cross`, `maker`}. |
| WebSocket | **Yes, full depth.** `orderbook_delta` with snapshot + per-price-level deltas and `seq` gap detection. |

**`post_only` is the finding that makes the strategy mechanically safe.** Combined
with a zero maker coefficient it means a quoter on our series can be structurally
incapable of paying a fee: an order that would cross is cancelled rather than
filled as taker. Set it on every order from day one.

### Three API facts that would have cost money

**(a) Amend does NOT preserve queue priority on a reprice.**

> Amending only expiry or decreasing size preserves queue position. Increasing
> size or changing price forfeits queue position and places the order at the back
> of the queue.

A reprice via amend is strictly equivalent to cancel-and-replace for queue
purposes; its only advantage is one round-trip of latency. Given that quotes must
update as a set (the waves result), this is a material constraint on requote
frequency, not a detail.

Caveat worth respecting: this is documented in the API docs but **not** in the
filed rulebook, whose Rule 5.4(d) says a modify instruction causes the system to
"withdraw the Order from the order book" — which reads the opposite way. Two API
calls settle it empirically once an account exists. Do that before relying on it.

**(b) `count` on amend is cumulative, not remaining.** It is "already filled count
plus desired resting remaining count." Treating it as remaining size silently
*increases* size — and therefore silently forfeits queue position.

**(c) The tick is not globally 1 cent any more — but it is on our series.**
`tick_size` has been removed from market payloads; the grid is per-market via
`price_ranges`. Many live markets now quote `$0.001` in the body and `$0.0001` in
the tails, and an Aug 2025 changelog claiming "the minimum allowable tick size for
orders is still 1c" is now false in general.

**Checked directly on our universe:** `KXWTI`, `KXWTIW`, `KXNATGASD`, `KXGOLDD`,
`KXSILVERD`, `KXBRENTD`, `KXCOPPERD`, `KXAAAGASM`, `KXWTIMAX` all return
`price_level_structure: linear_cent`, `price_ranges: [0.0000 → 1.0000 step 0.0100]`.

So the 1c tick holds for the commodity ladders, and every tick-floor conclusion in
the prior studies remains valid **for now**. But Kalshi is visibly migrating series
to sub-cent grids, and a migration would silently invalidate the tick-floor
analysis, the "one tick inside" quoting rule, and the favourite–longshot
explanation in one move. **The quoter must read `price_ranges` per market per
cycle, and the daily report must alarm on any change.** This is a standing
monitor, not a one-time check.

---

## 3. Maker rebate, volume tier, or market-maker programme?

**Answered — and this is the most consequential section of phase 0.**

### No rebate

The fee engine cannot pay you to trade:

> Net fee = trade fee + rounding fee - rebate (always >= $0.00)

Kalshi's docs do use the word "Rebate", but only for rounding refunds. A reduced
maker fee is not a rebate. **No volume tiers exist for event contracts** — the
10-tier maker/taker schedule applies to perpetual futures only (though prediction
volume counts toward those tiers).

### A subsidised designated competitor — in our series

**Liquidity Provider Program** (CFTC-filed, May 4 2026). Eligibility: *"all Kalshi
members who have executed a Market Maker Agreement."* Requirements are
*"Maximum Spread … Minimum Size within Spread … Minimum Uptime … Market Coverage
(all markets in the Designated Series)."* Reward cap: *"shall not exceed $50,000
USD per week"* per series. Allocation is a **reverse auction** — providers bid the
lowest reward they will accept.

The ~21 currently Incentivized Series include: **WTI** (2 providers), **Primary
Daily/Weekly Commodities — Brent, Corn, Gold, Silver, Copper** (1), **Hourly
Commodities** (1), **Diesel** (1), **Gas Daily & Weekly** (1), Crypto 15min/Hourly/
Daily, Hourly Weather, and others. All terminate 2026-12-31.

**What this does to the thesis.** The brief's §7 names "your fair value is worse
than theirs" as a failure mode and leaves it hypothetical. It is not hypothetical.
There is a specific, identifiable, Kalshi-paid participant in our target ladders,
obligated by contract to post tight two-sided size with high uptime, and
compensated enough that it need not profit on the spread alone.

Three consequences, in order of how much they should change behaviour:

- **The 5.17c mean spread and the 1.83c of room were measured in this
  participant's presence.** They are not evidence of an unattended book. They are
  the equilibrium a subsidised quoter leaves behind.
- **Being "on the right side of the fit 58% of the time" may describe being
  *adversely selected by* the designated provider**, not outcompeting it. A paid
  provider with an uptime mandate must quote through conditions where an
  unsubsidised quoter should stand aside — so the fills we win may concentrate
  exactly where it is widening deliberately.
- **Series selection becomes a first-class decision, not an afterthought.** The
  brief's "1,859 ladder series" generalisation argument is now sharper: prefer
  ladders that are *not* on the Incentivized list. The LP list is public and the
  ladder universe is 52 series; the intersection is small and known.

### But Kalshi will also pay us

**Liquidity Incentive Program** — retail-open, **no opt-in, no agreement**:

> The Liquidity Incentive Program rewards you for placing resting orders that
> improve market liquidity. This program pays you for maintaining orders on the
> books that help other traders get better prices, **even if your orders don't get
> filled.**

Mechanics: order book snapshotted once per second at a random moment; score =
order size × distance multiplier, relative to a reference price derived from where
cumulative depth reaches one fifth of target size; requires **two-sided** resting
depth meeting target size on both sides or the snapshot is excluded. Rewards
$1–$1,000 per market per day, $1.00 minimum payout. Ineligible: Kalshi affiliates,
IBs/FCMs and their customers, non-U.S. users. Programme runs to 2027-01-01.

Keyless and machine-readable: `GET /incentive_programs` returns live
`target_size_fp`, `period_reward`, `discount_factor_bps`, per market ticker. A
real sample returned `target_size_fp: "1000.00"` on a `KXAAAGASM` market.

**Why this matters more than it looks.** It is a revenue term that is *independent
of fills and therefore independent of adverse selection* — structurally the one
income source a naive maker cannot be picked off on. If it is material relative to
spread capture, it changes the gate arithmetic in phase 2. If `target_size_fp` is
1,000 contracts per side, it may also be far beyond the size this project should
be resting, in which case it is worth exactly zero. **Both are plausible and the
difference is decisive, so phase 1 must measure it rather than assume it.**

⚠️ `period_reward` units are undocumented (observed `3000000`; $300 in centi-cents
is consistent with the published $1–$1,000/day range, $30,000 in cents is not).
**Do not model this number until the unit is confirmed.**

---

## 4. What determines queue position, and can you observe it?

**Answered. Strict price-time FIFO, and — unusually — queue position is directly
queryable.**

Rulebook Rule 5.9, *Priority of Orders*:

> Kalshi's trading algorithms execute all trades by matching orders according
> first by price and then time priority… Orders and quotes placed on the Platform
> at the same price will be executed in order of time, from oldest to most recent.

No pro-rata. No size weighting. And notably, Rule 4.3's enumeration of market-maker
benefits — *"financial benefits, reduced fees, differing Position Limits and
Position Accountability Levels, and enhanced access"* — **does not include any
queue or allocation advantage.** The designated provider competes for queue on the
same terms we do. That is a meaningful limit on how bad finding (3) is.

**Observability:**
- `GET /portfolio/orders/{order_id}/queue_position` → `queue_position_fp`,
  *"the number of preceding shares before the order in the queue."*
- `GET /portfolio/orders/queue_positions` → bulk, filterable by `market_tickers` /
  `event_ticker`. One call covers a whole quote book.

This is a genuine gift. The brief's §7 lists queue position as a failure mode we
would have to infer; instead it is an exact, pollable number. **Phase 1 can
measure realised queue position directly rather than modelling it, and phase 2's
"assume last in queue" conservatism can be validated against truth instead of
merely assumed.**

The public orderbook gives aggregate size per price level only — no order counts,
no timestamps, no IDs. (A docs prose line claiming "order counts" is contradicted
by both the schema and live data; schema and live data win.) Others' queue can
only be reconstructed from `orderbook_delta` sequencing; our own is exact.

---

## 5. Settlement and collateral — does Kalshi net across brackets?

**Answered: yes, netting exists — but it is opt-in, off by default, and not freely
reversible.**

Short collateral is **maximum loss**, i.e. `(100 − price)` per contract, not the
full 100. Rulebook Rule 6.1(b): *"All Trader positions are fully cash
collateralized."*

**Collateral return** is the netting feature:

> This feature can be enabled and is **disabled by default for new users.** To opt
> in … go to your account settings and turn on Collateral return

Kalshi's own example nets two NO legs costing $1.30 down to **$0.30** of held
collateral.

### The field to branch on

The event object carries **both** `mutually_exclusive` and `collateral_return_type`
∈ {`MECNET`, `DIRECNET`, `""`}. Kalshi's spec states plainly:

> A false value does not mean collateral-return netting is unavailable. Use
> `collateral_return_type` to distinguish these cases.

Across all 2,400 open events: 410 `MECNET`, 1,364 `DIRECNET`, 626 none. **Every one
of the 1,364 DIRECNET events reports `mutually_exclusive: false` while still
netting.** Branching on `mutually_exclusive` would be a silent, systematic capital
error. Branch on `collateral_return_type`, every event, every time.

Our two ladder shapes map cleanly onto this: cumulative threshold ladders
(`strike_type: greater`, "Above $88.49") are `DIRECNET`; true bracket ladders with
both floor and cap are `MECNET`. Verified live: `KXWTI-26OCT1914` → `DIRECNET`,
30 markets, all `greater`, `cap_strike: None`.

This also settles the flag left open in `FINDINGS_LADDER_DYNAMICS.md` §1 — the
KXWTIW sum-constraint trade's capital objection. Netting is real and would apply.
Whether it applies *enough*, and whether it applies to resting orders, is below.

### Three hazards for a market maker

⚠️ **Unwinding a netted leg can consume funds rather than release them.** Kalshi's
own worked example: selling one leg you would expect to return 90c instead
*decreases* available funds by 10c, because returned collateral must be given back
when the hedge breaks. Capital efficiency here is not freely reversible — size on
the assumption that unwinding may require re-posting collateral.

⚠️ **Enabling the feature can make positions unsellable:** *"Enabling this feature
may make you unable to sell positions for which you've already had collateral
returned."*

⚠️ **Netting is per sub-account** and must be enabled on each.

**Upside:** collateral earns **3.50% APY**, *including* collateral behind open
positions. Carry cost is (cost of capital − 3.5%), not the full cost of capital.

---

## 6. Rate limits for a continuously-quoting account

**Answered.** Two independent token buckets — **Read** (market data) and **Write**
(orders, amends, cancels). Seven tiers: Basic 200/100 tokens per second through
Prestige 12,000/9,600.

Costs: create 10 tokens, cancel 2, get-order 2. Amend cost is **undocumented**
(default 10 implied). Batches bill per item — *"Batch endpoints don't save tokens"*
— so batching buys atomicity and one round-trip, not throughput.

On breach: `429 {"error":"too many requests"}`, **no `Retry-After` header**, no
cooldown, no penalty. Apply exponential backoff. At Basic tier the write bucket
holds only one second of budget — **10 orders/sec sustained with no burst** — which
is the binding constraint on how many ladders can be quoted as a set.

Two hazards:

⚠️ **Post-only quoters that repeatedly cross may be throttled:** *"quoters with
post-only set to true may be temporarily rate limited if they cross several times
in short succession."* A naive reprice loop firing into a moving book can throttle
itself. Back off on `post only cross` rather than retrying.

⚠️ **`cancel-all` is a kill switch, not a requote primitive:** *"Newly placed
orders may also be cancelled during the minute after the request."* Using it in a
quote cycle would silently eat the orders just placed. Wire it to the kill switch
and nowhere else.

Note for later: explicitly setting `exchange_index` scopes the write budget to one
shard and multiplies effective throughput; auto-routing (`-1`) debits *every*
shard's bucket. Our ladders live on shard 2, "Crypto & Commodities".

---

## What this does not say

- **It does not say the strategy works.** It removes a cost term and confirms the
  mechanics are available. Adverse selection — the thing that actually kills
  makers — is untouched by everything above and is phase 2's job.
- **It does not validate the 58% figure.** That number is still measured against
  the ladder's own smoothed mids, which §5 itself calls "a weak fair value". Phase
  0 only establishes that the fee no longer erodes it, and the recompute only
  establishes which population it describes — not that the room is capturable.
- **The subsidy is evidence against the opportunity, and it belongs here, not only
  in the competitive section.** Kalshi paying up to $50,000 per week per series for
  passive provision is a revealed-preference statement that **passive provision in
  these series is not naturally profitable** — an exchange does not subsidise
  behaviour that participants would supply unpaid. That most Incentivized series
  carry *exactly one* provider says the slot is uncontested, which is what a thin
  or negative unsubsidised return looks like from the outside. The brief treats
  the measured 1.83c of room as the opportunity; this finding says that room may
  be the *cost of the subsidy*, visible precisely because someone is being paid to
  leave it there.
- **The competitive problem is cost basis, not queue priority.** Rule 5.9's strict
  price-time FIFO means a designated provider gets no allocation advantage, so the
  queue is fair. That is not the binding constraint. A subsidised quoter can post
  inside fair value and still profit, because the subsidy covers the gap. An
  unsubsidised quoter cannot match that price and make money — leaving two
  outcomes, standing aside, or getting filled when the subsidised quoter widens on
  purpose. Both are bad, and the second is adverse selection by construction: a
  provider bound to an **uptime mandate must keep quoting through conditions where
  an unsubsidised maker should walk away**, so the fills we win concentrate in
  exactly those conditions.
- **It does not establish that there is room beside the designated provider.** It
  establishes that the provider exists and is paid. Whether the measured 1.83c of
  room survives contact with a subsidised, uptime-mandated quoter is unknown and
  is now the first thing phase 1 must look at.
- **No authenticated endpoint was called.** Everything account-shaped —
  queue position, netting behaviour, actual fee charged, LIP accrual — is
  documentation, not observation.

---

## Open items, flagged rather than guessed

| # | Item | Why it matters | How to close |
|---|---|---|---|
| 1 | **Does netting apply to resting orders or only filled positions?** | Decisive for quoting capital. `resting_margin_reservation` defaults to `sum` (un-netted), but that governs shard rebalancing, not clearly the engine check. | Empirical, funded account |
| 2 | **Exact netting algorithm for N>2 legs / partial ladder coverage** | `Σnᵢ − (N−1)` follows from Kalshi's two-leg examples but is **not** a quoted rule | Empirical |
| 3 | ~~**`period_reward` units**~~ **CLOSED** | Resolved: **centi-cents** ($0.0001), per the live OpenAPI `IncentiveProgram` schema. LIP is **meaningful but secondary**, and absent from `KXWTI`/`KXWTIW` entirely. See `FINDINGS_LIP.md` | Done |
| 4 | **Does a size-decrease amendment really retain queue position?** | API docs say yes; rulebook Rule 5.4(d) reads the other way | Two API calls, funded account |
| 5 | **Amend token cost** | Sets the requote budget | `GET /account/endpoint_costs` (auth) |
| 6 | **Minimum resting time** | Not documented anywhere; grepped the full 550KB corpus and both specs. Best indication: none exists | Empirical |
| 7 | **Are fractional contract sizes live?** | Spec says 0.01 granularity; Feb 2026 changelog says not enabled | Authenticated test order |
| 8 | **Post-Feb-2026 fee schedule revision** | `kalshi.com` is bot-blocked; every IA capture since Feb 2026 is also 429 | Open in a real browser, or read `fee_type` live (preferred — it is authoritative and current) |
| 9 | **Rulebook currency** | Copy used is v1.18; 2026 CFTC filings cite "Rule 3.13(c)" for text v1.18 numbers as 3.10, so numbering **has** shifted | Cite rule text, not numbers; re-pull current rulebook |

Items 1 and 2 are the two that most threaten a capital model. Neither is resolvable
without a funded account, and **neither blocks phases 1 or 2**, which place no
orders and therefore post no collateral.

---

## Recommendation for phase 1

The brief's phase-1 gate is "a documented, repeatable population of brackets where
edge exceeds band plus fee." That gate is now easier on one axis — the fee term is
zero on 51 of 52 series — and it is incomplete on another. Phase 1 should add
three measurements, none of which require placing an order:

1. **Designated-provider overlap.** Tag every candidate series with whether it is
   on the LP Incentivized list. Report the edge population split by that tag. If
   the population lives entirely inside subsidised series, that is a finding about
   who we would be trading against, and it should be reported before any gate is
   argued.
2. **LIP accrual, modelled from the live book.** We can compute what a given
   resting posture would have scored, from `/incentive_programs` parameters plus
   the book we are already collecting. This is a fill-independent revenue term and
   it belongs in the phase-2 P&L decomposition as a fifth line, not as a footnote.
   **Now measured (`FINDINGS_LIP.md`), and it demotes itself:** `KXWTI` and
   `KXWTIW` carry no LIP at all; `KXWTIMAX`/`KXWTIMIN` pay $60 per market per
   period. A 100-lot posture across ten markets accrues on the order of $60 per
   period — real, but not a business, and not the adverse-selection-immune
   revenue line it was hoped to be. The allocation formula is unpublished, so
   model it as a bounded upside, never as a baseline.
3. **Tick-grid monitor.** Assert `linear_cent` per target market per cycle, and
   alarm on change. A silent migration to a sub-cent grid invalidates the
   tick-floor work, the "one tick inside" rule and the favourite–longshot
   explanation simultaneously.

I would also propose one change to the brief's own discipline, for the operator to
accept or reject rather than for me to adopt: **§5's phase-1 report should be
per-series throughout, never pooled.** `KXAAAGASM` demonstrates why — it is
simultaneously the largest sample in §5 and the only series where makers pay.
Pooling hides exactly the heterogeneity that decides where to quote.

---

## Status

Phase 0 complete. Nothing built. No orders ever placed. Order manager does not
exist and will not until phase 3 is approved.

**Blocked on the operator for:**
- Which tree is canonical (see `STATE.md`) — the git repo lacks `ladder/`,
  `waves/` and `wti_arb/`, which the fitter and collector are told to reuse.
- Nothing else. Phase 1 needs only keyless public market data.
