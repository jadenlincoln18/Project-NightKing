# marketmaking — state

**Phase: 0 complete. Phase 1 not started.**

Nothing built, nothing running, no orders ever placed. The order manager does not
exist and will not until phase 3 is explicitly approved.

## Next action

Operator review of `FINDINGS_PHASE0.md`, then phase 1 (shadow mode) —
full stack, order manager disabled, two weeks minimum, weekdays and weekends.

Before writing phase-1 code, the canonical-tree question below must be answered.

## Blocked on

1. **WHICH TREE IS CANONICAL — needs the operator.** The git repo
   (`~/.openclaw/workspace/Project-NightKing`, branch
   `claude/gracious-edison-s2s7t5`) contains `marketmaking/` but does **not**
   contain `ladder/`, `waves/` or `wti_arb/` in any branch or anywhere in
   history. A fuller tree exists at
   `~/Library/Mobile Documents/com~apple~CloudDocs/Desktop/Project-NightKing/`
   with all of them — but it is **not a git repo**.
   The brief instructs reuse of `wti_arb/synth/act3.py`, `ladder/store.py`,
   `ladder/kapi.py`, `ladder/fees.py`, `ladder/collect_books.py`. Those exist only
   in the iCloud copy. Phase 0 read its evidence from there; phase 1 cannot import
   code across that boundary cleanly, and iCloud sync under a live collector is a
   bad idea besides.
   *Note:* the iCloud copy dematerialises files (`EDEADLK` on read until
   downloaded); staged read-only copies are in `/tmp/nk_ro/`.

2. **Kalshi API key for trading** (operator supplies). Phases 0–2 need only
   keyless public market data. Not blocking yet.

## Learned so far

**Phase 0 — the six unknowns are answered in `FINDINGS_PHASE0.md`.** Headlines:

- **Maker fee is ZERO on 51 of 52 ladder series** (`fee_type: quadratic`). Only
  `KXAAAGASM` charges (0.0175). So §5's **58%** branch applies, not 38% — and
  `KXAAAGASM`, the one maker-fee series, is the top row of §5's table.
- **`post_only` exists** and is cancel-on-cross. With a zero maker coefficient a
  quoter on our series can be structurally incapable of paying a fee.
- **Kalshi pays a designated market maker in our exact series.** Liquidity
  Provider Program, ≤$50k/week/series, mandated max spread + min size + min
  uptime. Incentivized list includes WTI, Brent, Gold, Silver, Copper, Diesel,
  gas daily/weekly. The 5.17c spread and 1.83c of room were measured in this
  participant's presence. **Biggest finding of phase 0.**
- **Kalshi also pays retail to rest orders** — Liquidity Incentive Program, no
  opt-in, $1–$1,000/market/day, paid *even if orders never fill*. Keyless via
  `GET /incentive_programs`. A fill-independent revenue term, so structurally
  immune to adverse selection. Units of `period_reward` unconfirmed — do not
  model until resolved.
- **Queue position is directly queryable** —
  `GET /portfolio/orders/queue_positions`. Strict price-time FIFO (Rule 5.9), and
  designated MMs get **no** queue advantage. Phase 2's "assume last in queue" can
  be validated against truth rather than assumed.
- **Amend does NOT preserve queue priority on a reprice** — only size-decrease and
  expiry-extend do. And `count` on amend is *cumulative*, not remaining; getting
  that wrong silently forfeits queue position.
- **Netting is real but opt-in and OFF by default** (`collateral_return_type` ∈
  `MECNET`/`DIRECNET`/`""`). **Never branch on `mutually_exclusive`** — all 1,364
  live DIRECNET events report it `false` while still netting. Unwinding one leg of
  a netted set can *consume* available funds. Collateral earns 3.50% APY.
- **Tick is still 1c on our ladders** (`linear_cent`, step 0.0100 — verified on 9
  target series), but `tick_size` is gone from the API and other Kalshi markets
  now quote $0.001/$0.0001. A silent migration would invalidate the tick-floor
  work, the "one tick inside" rule and the favourite–longshot explanation at once.
  **Read `price_ranges` per market per cycle and alarm on change.**
- **Rate limits:** separate Read/Write token buckets. Basic tier = 10 orders/sec,
  no burst. 429 carries no `Retry-After`. `cancel-all` eats orders placed in the
  following minute — kill switch only, never a requote primitive.

**Open items deliberately left unresolved rather than guessed** — full table in
`FINDINGS_PHASE0.md`. The two that most threaten a capital model, both needing a
funded account, neither blocking phases 1–2:
- Does netting apply to **resting orders** or only filled positions?
- Exact netting algorithm for N>2 legs and partial ladder coverage.

**Method note for the next session.** `kalshi.com` (fee schedule, rulebook) is
behind a Vercel bot checkpoint returning 429 to every non-browser client — this is
what defeated `FINDINGS_LADDER_DYNAMICS.md` §8. Two routes around it that worked:
the Internet Archive capture of the exact PDF URL, and — better — the **live
keyless series API**, which exposes `fee_type`/`fee_multiplier` per series and is
both authoritative and current. Prefer the API over the PDF.
