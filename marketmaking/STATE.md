# marketmaking — state

**Phase: 0 complete. Phase 0.5 gate built and staged; BLOCKED on a protocol
ruling. Phase 1 not started.**

Nothing built for trading, no orders ever placed. The order manager does not
exist and will not until phase 3 is explicitly approved. `ORDERS_ENABLED` is
`False`. A live collector runs under launchd; phase 0.5 never touched it.

## Next action

**An operator ruling on `FINDINGS_PHASE05.md` §6 — three questions, in order.**
Phase 0.5 cannot proceed without the first one, and phase 1 is gated on phase
0.5 by §1B. Do not start phase 1 analysis until Test A has actually run.

Read in this order: `FINDINGS_PHASE05.md` (§2 is the blocker) → `PROTOCOL.md`
§1B → `BRIEF.md` §3–§4.

## Blocked on

1. **§1B scores a fit that does not exist for the §1A universe.** (2026-10-20,
   the live blocker.) §1B needs a fair value **with a credible band** per
   bracket-minute on daily city-temperature ladders. `wti_arb/synth/act3.py` is
   the only band-producing fitter and its likelihood is a vanilla call/put
   payoff matrix on a log-moneyness grid around a forward — temperature has no
   chain, no forward, no implied vol. `ladder/maker.py` reads the ladder but is
   a point estimate with no interval. Altering either, or changing the universe,
   is forbidden by §1B's own text. **This needs a protocol amendment, not a code
   change.** `python -m phase05.run --band-rule …` reproduces the full diagnosis
   and exits 2. Details and the four options: `FINDINGS_PHASE05.md` §2, §6.
2. **Kalshi API key for trading** (operator supplies). Phases 0–2 need only
   keyless public market data. Not blocking yet.

## Resolved since 2026-10-18

- **`git push` works.** The credential blocker recorded here is stale; the
  branch publishes normally to `origin`.
- **The historical one-minute store is staged — COMPLETE IN SCOPE.**
  `phase05/stores.py::check_staging()` passes.

  **This is the single authoritative staging number. Two earlier figures
  (552 MB / 32 of 48 series, and 1.18 GB / 53 series) were snapshots of a run
  still in progress and are superseded. Do not cite them.**

  Measured directly 2026-10-20 22:20 CDT, source vs destination, per series:

  | quantity | value |
  |---|---|
  | series staged | **53 of 53 in scope** (0 short of source) |
  | temperature series | **48** (`KXHIGH*` / `KXLOW*`) |
  | commodity series | **5** (KXWTI, KXWTIW, KXBRENTD, KXGOLDD, KXNATGASD) |
  | events staged | **12,860 of 12,860 in scope** (0 short) |
  | parquet files | **12,914** (12,860 candles + 54 markets tables) |
  | true byte total | **1.15 GB** |
  | `.icloud` dataless placeholders remaining | **0** |
  | zero-byte parquet | **0** |

  **"In scope" is the point.** `ops/stage_icloud_store.sh` deliberately targets
  the PROTOCOL §1A primary universe plus the commodity comparison group — 53
  series — and **not** all **422** series present in the iCloud store. So 369
  unstaged series is the intended design, not a shortfall. Completeness must be
  judged per-series against source, which is how the numbers above were taken.

  Gitignored by design. Staging is idempotent and resumable:
  `sh marketmaking/ops/stage_icloud_store.sh`. The earlier stall was iCloud
  refusing to serve (server-side, verified), never a local failure.

  Measurement caveat worth keeping: `du` reports ~1.2 GB physical against a
  1.15 GB byte total, and a naive `find | xargs du` undercounts badly because
  `xargs` batches and only the last batch's total is read. Sum file sizes with
  `-exec stat -f%z {} +` instead. The candle tree is partitioned
  `period=1/series=X/event=Y`, so counting series at depth 1 returns `1`
  (`period=1`), not 53 — count at the `series=` level.

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

**iCloud gotchas, all hit during consolidation or staging — do not re-derive:**
- Files are *dataless*: reads fail with `Resource deadlock avoided` (EDEADLK)
  until materialised. **`brctl download <dir>` does not recurse** — it must be
  called per file:
  `find <dir> -type f | xargs -P 8 -I{} brctl download "{}"` then wait ~15s.
- **`brctl download` silently no-ops on a RELATIVE path** (2026-10-20). It
  returns `rc=0`, prints nothing, and the file stays `dataless`. Only an
  **absolute** path queues the fetch. This is the second half of the gotcha
  above and it cost two full passes over 12,914 files.
- **Decouple request from copy.** Materialisation is async and the daemon
  re-evicts; a request-sleep-copy loop misses everything that lands mid-sleep.
  Copy to local disk the instant a file reads — staged bytes cannot be evicted.
- **iCloud throttles to a stop.** After ~1 h at ~600 KB/s it stopped honouring
  requests entirely, including single explicit absolute-path calls with all
  local loops stopped. Server-side; wait and resume.
- All of this is encoded in `marketmaking/ops/stage_icloud_store.sh`.
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

## Parked idea: NWS probabilistic forecast as a second, independent fair value (2026-10-20)

**Not now. After phase 0.5 resolves.** Recorded because it names a real gap in
the current thesis rather than an enhancement to it.

**The gap:** the self-fit smooths Kalshi's own quotes. Smoothing can remove
noise; it cannot add information. Every input is a price set by the same
participants, so the fit can only ever say "this bracket disagrees with its six
neighbours" — never "this ladder disagrees with the weather."

**The idea:** the National Weather Service publishes free probabilistic
forecasts giving percentiles for daily high temperatures. That is to temperature
what the CME options chain was to WTI — a second fair value carrying information
the market's own prices do not contain, from a source with no position.

**Why it matters either way phase 0.5 goes:**
- If the self-fit PASSES Test A, the forecast is the natural next layer.
- If the self-fit FAILS, the forecast may be the edge on its own — and a failure
  of the self-fit would NOT kill that, because it tests a different claim.

**Caveat to check before building:** the NightKing autopsy lesson applies
directly. Ask first *who sets the price on the thinner venue, and are they
looking at the same forecast?* If Kalshi's temperature makers already quote
straight off NWS/NBM guidance, this is fedarb again with extra steps. That
question is answerable cheaply from the data already staged, and must be
answered before any forecast adapter is written.
