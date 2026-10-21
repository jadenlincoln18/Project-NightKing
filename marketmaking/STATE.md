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

## Ops: watchdog proven under a deliberate wedge (2026-10-20)

**Why this section exists.** On 2026-10-20 the watchdog was reported as broken
on the evidence that `watchdog.log` held two entries across two days. That
reading was wrong, and the way it was wrong is the lesson: the watchdog had run
**633 times** (`launchctl print` run count), exiting 0 each time, and the
collector *was* writing `logs/collector.heartbeat.json` every cycle. The old
watchdog simply returned silently on the healthy path. **A monitor that is
silent when healthy cannot be distinguished from a monitor that is dead.**

Fixed in `ops/watchdog.py`:
- Every check logs, including `CHECK: OK ...` with age, sweeps, depth passes.
- A missing / unreadable / stale heartbeat now **alerts the operator** over the
  configured channel, de-duplicated to once per `MM_ALERT_REPEAT_S` (30 min),
  with an explicit RECOVERED notice when the heartbeat returns.
  "No heartbeat yet" can no longer persist unnoticed for two days.
- `MM_STALE_S` / `MM_GRACE_S` are env-overridable so the drill below runs in
  seconds. Production defaults are unchanged (600 s / 20 s).

### The drill: SIGSTOP, the alive-but-wedged case

`kill -STOP` pauses a process without killing it — precisely the failure launchd
`KeepAlive` cannot see, and the one this watchdog exists for.

| Time (UTC) | Event |
|---|---|
| 02:42:43 | last healthy beat, sweep 631, pid 45417 |
| 02:46:04 | `kill -STOP 45417` — process state `T`, heartbeat frozen |
| 02:46:51 | watchdog `CHECK: STALE age=249s` (drill limit 30 s) |
| 02:46:55 | **operator alert delivered** (4 s end-to-end) |
| 02:46:55 | SIGTERM to wedged pid |
| 02:47:00 | still alive after 5 s grace → SIGKILL |
| 02:47:30 | `launchctl kickstart` issued |
| 02:47:36 | collector restarts (launchd run #5, pid 33488) |
| 02:52:36 | first post-restart beat, `sweeps=1`, pid 33488 |

**Restart gap: 9 min 53 s** of heartbeat silence end to end (02:42:43 →
02:52:36); roughly two touch cycles of data lost. Detection-to-kickstart was
86 s of that. The remainder is collector startup plus one full 300 s cycle.

### Second defect, found only because the drill was run

For ~5 minutes after any restart the heartbeat still named the **previous pid**,
because `_heartbeat()` was called only at the *end* of a cycle. A watchdog
firing in that window sees a dead pid, concludes "collector not running", and
kickstarts a collector that is in fact healthy — a restart loop. Production
`STALE_S=600` left only ~2× margin over the ~300 s blind window.

Fixed: `mm/collect.py::run()` now beats once immediately at startup, before the
first cycle. The blind window is gone and the pid in the heartbeat is correct
from the first second.

### Market rollover verified by content, not row count

A collector polling a stale market list keeps returning healthy row counts while
collecting nothing current. Checked by ticker content in the live touch store:
2,433 distinct tickers, 605 temperature tickers, of which **288 carry today's
date tag `26OCT20`** and **zero** carry `26OCT19` or `26OCT18`. The universe is
rolling over daily as intended.
