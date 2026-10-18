# marketmaking — state

**Phase: 0 complete, plus two operator-requested follow-ups. Phase 1 not started.**

Nothing built, nothing running, no orders ever placed. The order manager does not
exist and will not until phase 3 is explicitly approved.

## Next action

Phase 1 (shadow mode) — full stack, order manager disabled, two weeks minimum,
weekdays and weekends. Start it in a **fresh session**; this document is written
to be read cold.

Read in this order: `BRIEF.md` → `FINDINGS_PHASE0.md` → `FINDINGS_PHASE0_S5_RECOMPUTE.md`
→ `FINDINGS_LIP.md`.

## Blocked on

1. **`git push` has no credentials.** Two commits sit unpushed on
   `claude/gracious-edison-s2s7t5` (`14ca080`, `0eb56f1`). `github_identity_status`
   reports `credentialState: unavailable`. Operator action: connect GitHub under
   Settings → Agents → Tools, or push manually. **The work is committed locally
   and safe; only publication is blocked.**
2. **Kalshi API key for trading** (operator supplies). Phases 0–2 need only
   keyless public market data. Not blocking yet.

## Repo layout — resolved 2026-10-18

The canonical tree is now **this git repo**, at a non-iCloud path:
`~/.openclaw/workspace/Project-NightKing`. Work here. Do not work in the iCloud
copy.

Commit `0eb56f1` consolidated it:
- Root python/docs → `wti_arb/` via `git mv` (78 renames, all R100 — this
  completed the rename that was staged but never committed).
- `ladder/` (16 files) and `waves/` (12 files) added from the iCloud copy.
- `NightKing/` strategy writeups and HANDOFF docs added.
- `.gitignore` rewritten: `data/`, `waves_data/`, `ladder/data/`, `results/`,
  `plots/`, `*.pkl`, `*.png` stay out. Code only, 13.7 MB.

**Historical data stores were deliberately not committed** (tens of GB). They
remain read-only in the iCloud copy at
`~/Library/Mobile Documents/com~apple~CloudDocs/Desktop/Project-NightKing/`.
Phases 1–2 collect fresh data, so this is not blocking. If the fitter needs the
historical stores, that is a separate direct transfer — not a git problem.

**iCloud gotchas, both hit during consolidation — do not re-derive:**
- Files are *dataless*: reads fail with `Resource deadlock avoided` (EDEADLK)
  until materialised. **`brctl download <dir>` does not recurse** — it must be
  called per file:
  `find <dir> -type f | xargs -P 8 -I{} brctl download "{}"` then wait ~15s.
- The iCloud `.git` is **unusable**: EDEADLK on `HEAD`, `config` and
  `packed-refs` that no amount of `brctl download` fixes, plus stale lock files
  in `.git/_stale` dated to the failed push. It was not needed — the code
  directories had never been committed there anyway.
- This is exactly why a live collector must never point at an iCloud directory.

## Learned so far

**Phase 0 — the six unknowns are answered in `FINDINGS_PHASE0.md`.** Headlines:

- **Maker fee is ZERO on 51 of 52 ladder series** (`fee_type: quadratic`). Only
  `KXAAAGASM` charges (0.0175). So §5's **58%** branch applies, not 38%.
- **`post_only` exists** and is cancel-on-cross. With a zero maker coefficient a
  quoter on our series can be structurally incapable of paying a fee.
- **Kalshi pays a designated market maker in our exact series.** Liquidity
  Provider Program, ≤$50k/week/series, mandated max spread + min size + min
  uptime. Includes WTI, Brent, Gold, Silver, Copper, Diesel, gas daily/weekly.
  The 5.17c spread and 1.83c of room were measured in this participant's presence.
  **Biggest finding of phase 0.**
- **Queue position is directly queryable** —
  `GET /portfolio/orders/queue_positions`. Strict price-time FIFO (Rule 5.9), and
  designated MMs get **no** queue advantage. The competitive problem is therefore
  **cost basis, not queue priority**: a subsidised quoter can post inside fair
  value and still profit; we cannot match that price and make money.
- **Amend does NOT preserve queue priority on a reprice** — only size-decrease and
  expiry-extend do. And `count` on amend is *cumulative*, not remaining.
- **Netting is real but opt-in and OFF by default** (`collateral_return_type`).
  **Never branch on `mutually_exclusive`** — all 1,364 live DIRECNET events report
  it `false` while still netting. Collateral earns 3.50% APY.
- **Tick is still 1c on our ladders** (`linear_cent`, verified on 9 target
  series), but `tick_size` is gone from the API and other Kalshi markets now quote
  $0.001/$0.0001. **Read `price_ranges` per market per cycle and alarm on change.**
- **Rate limits:** separate Read/Write buckets. Basic = 10 orders/sec, no burst.
  429 carries no `Retry-After`. `cancel-all` eats orders placed in the following
  minute — kill switch only, never a requote primitive.

**§5 recompute (`FINDINGS_PHASE0_S5_RECOMPUTE.md`) — operator-requested.**
Exact subtraction on `ladder/results/maker.pkl`; the accumulators are additive
counts, so no reimplementation was needed.
- Excluding `KXAAAGASM`: **57.79% → 58.50%** improvable. **The 58% headline is
  robust.** `KXAAAGASM` heads §5's table by *ladder*-minutes (6.37%) but is only
  **4.63% of bracket-minutes**, which is what the headline is computed over — it
  never dominated it. Its ladders are short (8.06 brackets/min vs 11.28).
- **The 38% branch should be retired, not recomputed** — it describes every series
  paying a fee when exactly one does. Phase 1's gate should be stated against
  **58.50% on the maker-free series**, with `KXAAAGASM` excluded from the quoting
  universe.

**LIP (`FINDINGS_LIP.md`) — operator-requested.**
- **`period_reward` is in centi-cents** ($0.0001), per the live OpenAPI
  `IncentiveProgram` schema. `3000000` = **$300.00** per period. Spec-defined,
  high confidence. Closes phase-0 open item #3.
- **Coverage demotes it:** `KXWTI` and `KXWTIW` carry **no LIP at all**.
  `KXWTIMAX`/`KXWTIMIN` pay $60/market/period (40 markets each). A 100-lot posture
  across ten markets accrues ~$60/period — real, but not a business.
- **Verdict: meaningful but secondary**, not the adverse-selection-immune revenue
  line we hoped for.
- **Allocation formula and qualification rules are unpublished.** Model LIP as
  bounded upside, never as a baseline.
- The LIP money concentrates on `KXAAAGASM` ($39k/period) — the same series that
  is the only maker-fee payer and the worst microstructure in §5. **Kalshi pays
  most where quoting is least attractive.**

### The through-line, and the thing phase 1 must attack

Three independent observations — the designated-provider subsidy, the
single-provider structure, and the LIP concentration — all say the same thing:
**passive provision in these series is not naturally profitable.** An exchange
does not pay for behaviour participants would supply unpaid, and an uncontested
subsidised slot is what a thin or negative unsubsidised return looks like from
outside. The measured 1.83c of room may be *the cost of the subsidy*, visible
precisely because someone is paid to leave it there.

This is the NightKing lesson restated: challenge the premise before admiring the
pipeline. Phase 1's first job is not the edge population — it is **whether there
is room beside a subsidised, uptime-mandated quoter at all.**

## Open items deliberately left unresolved

Full table in `FINDINGS_PHASE0.md`. The two that most threaten a capital model,
both needing a funded account, neither blocking phases 1–2:
- Does netting apply to **resting orders** or only filled positions?
- Exact netting algorithm for N>2 legs and partial ladder coverage.

Plus, from the LIP work: the **allocation formula** and **qualification rules**
are unpublished, and the `/incentive_programs` endpoint **ignores its
`series_ticker`/`market_ticker` filters** and never returns a terminating cursor —
so LIP *absence* on a given series is a large-sample observation, not proof.

## Method note for the next session

`kalshi.com` (fee schedule, rulebook, LIP terms) is behind a Vercel bot checkpoint
returning 429 to every non-browser client — this is what defeated
`FINDINGS_LADDER_DYNAMICS.md` §8. Two routes around it work: the Internet Archive
capture of an exact PDF URL, and — better — the **live keyless API**
(`api.elections.kalshi.com/trade-api/v2`) plus `docs.kalshi.com/openapi.yaml`,
which are authoritative, current, and not blocked. Prefer the API over the PDF.
