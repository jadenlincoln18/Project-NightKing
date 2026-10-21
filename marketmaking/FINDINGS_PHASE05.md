# FINDINGS — Phase 0.5 (PROTOCOL §1B)

**Date:** 2026-10-20 (supersedes the 2026-10-18 BLOCKED verdict)
**Branch:** `claude/gracious-edison-s2s7t5`
**Protocol:** `marketmaking/PROTOCOL.md` §1B, committed `132ce8c` before any phase 0.5 data was read. **Not modified by this run.**

---

## Verdict

> ### Test A: **NOT RUN.** The blocker has changed, and the new one is not a data problem.
> ### Test B: **not reached** (§1B gates it on Test A passing).

**This is still not a FAIL.** A FAIL is a measurement: the fit was scored against
the quote and lost. Nothing has been scored. No inference about the fit —
favourable or unfavourable — is licensed by this document.

What changed since 2026-10-18:

| | 2026-10-18 | 2026-10-20 |
|---|---|---|
| One-minute candle store staged | ❌ no | ✅ **yes** — `stores.check_staging()` passes |
| Quote time series at minute *t* | ❌ absent | ✅ **built** — `phase05/panel.py` |
| Settlement outcomes joined | ❌ snapshot only | ✅ from the store's own markets table |
| **Fair value + credible band at *t*** | assumed available | ❌ **does not exist for the §1A universe** |

The 2026-10-18 blocker was *"the data is one copy away."* That was correct, and
this run made the copy. Underneath it was a second blocker that the staging gap
had been hiding: **§1B scores an object that this repository cannot construct
for the universe §1A fixes.** That is a defect in the pre-registration, not in
the data, and per the run's constraints it is reported here rather than patched.

---

## 1. Resolved this run — the staging gap is closed

The §1A primary universe plus the commodity comparison group were materialised
out of iCloud Drive and staged into `marketmaking/data/_import/waves_data/`, in
exactly the layout `ladder/store.py::paths()` expects:

```
<root>/parquet/kalshi_candles/period=1/series=*/event=*/part.parquet
<root>/parquet/kalshi_markets/series=*/part.parquet
```

| | |
|---|---|
| Series staged | **53** — 48 `KXHIGH*`/`KXLOW*` + `KXWTI`, `KXWTIW`, `KXBRENTD`, `KXGOLDD`, `KXNATGASD` |
| Files | 12,914 parquet parts, **1.18 GB** logical |
| Source | `~/Library/Mobile Documents/com~apple~CloudDocs/.../waves_data/parquet` (read-only; never written) |
| Gate | `phase05/stores.py::check_staging()` **passes**; `assert_not_live()` clean |

The data stays out of git by design (`.gitignore:38 marketmaking/data/`). Only
code and this document are committed.

### Two operational facts worth not re-deriving

**`brctl download` silently no-ops on a relative path.** It returns `rc=0`,
prints nothing, and the file stays `dataless`. Only an **absolute** path
actually queues the fetch. This cost the first two full passes over all 12,914
files — the known "`brctl download <dir>` does not recurse" gotcha in `STATE.md`
has a second half, and this is it.

**Request and copy must be decoupled.** Materialisation is asynchronous and the
daemon re-evicts. A loop that requests a batch, sleeps, then copies, misses
every file that lands mid-sleep and re-requests files already in flight —
throughput decayed to ~0.7 files/s. Two independent loops (one requesting in
bounded chunks, one continuously copying anything readable to local disk) hold
~45–75 files/min against a measured 573 KB/s of actual iCloud throughput.
**Copy out the instant a file is readable**; bytes on local disk cannot be
evicted.

The Trash copy at `~/.Trash/Project-Nightking/data/` was checked as instructed
and **declined**: it carries the five commodity series' candles but **no
`kalshi_markets` table at all**, and those five series are only **98 of the
12,914 target files**. It could not satisfy staging and was not worth the
verification cost.

---

## 2. The blocker that replaced it: §1B's fit has no implementation for §1A's universe

§1B's unit of observation needs ten columns. The staged store now supplies
seven of them. The remaining three are `fit_mean`, `fit_lo`, `fit_hi` — the
fitter's fair value and **its own credible band**, as of minute *t*.

§1B is explicit that the band is not phase 0.5's to construct:

> "the fit's fair value lies **outside the fit's own credible band** relative to
> the quote midpoint. The band is the fitter's existing interval; **phase 0.5
> does not invent a new one**."

and that the extractor is not phase 0.5's to change:

> "It … may not change the universe fixed in §1A, **may not alter the density
> extractor in `wti_arb/synth/`**, and may not modify `ladder/` or `waves/`."

**There are exactly two fair-value producers in this repository. Neither can
satisfy both sentences on the §1A universe.**

### 2.1 Act III (`wti_arb/synth/act3.py`) — has a band, cannot read a ladder

Act III is the only object in the repo that emits a per-bracket credible
interval (`summarise()` returns posterior bracket-probability draws; the
backtest CSVs carry them as `pq_mean`, `pq_q05`, `pq_q95`). It is also
**irreducibly an options-chain model**. From `Model.__init__`:

```python
pay_c = np.maximum(self.s[None, :] - self.K[:, None], 0.0)
pay_p = np.maximum(self.K[:, None] - self.s[None, :], 0.0)
self.G = D * np.where(self.is_call[:, None], pay_c, pay_p)
```

`G` is a **vanilla call/put payoff matrix** and the likelihood is
`Chat = G @ p` against `mid`, the option mid prices, scaled by half-spread. The
constructor signature is `Model(K, right, mid, hs, F0, D, T, atm_sigma, …)`.

For a daily city-temperature ladder there is:

- **no option chain** — `mid`, `right` and `hs` have no referent;
- **no forward `F0` and no `atm_sigma`** — temperature is not a traded asset, so
  there is no forward price and no implied volatility;
- **no valid coordinate system** — the grid is built in log-moneyness
  `x = log(s/F0)` over `±extent_sd·σ√T`, which presupposes a positive,
  lognormal-ish support. Daily lows in °F go to zero and below.

A Kalshi bracket is a **digital** on an interval, not a vanilla. Feeding one to
Act III means replacing `G` with an indicator matrix and replacing the
log-moneyness grid with a linear one — i.e. **altering the density extractor**,
which §1B forbids in the same sentence that names it.

> `BRIEF.md` §3 asserts the opposite — *"the extractor does not care where the
> prices came from … feed it Kalshi bracket quotes instead of CME option prices
> and it works on every ladder series."* **That is an architectural aspiration,
> not a property of the code as written.** The conversion is real and standard
> (a cumulative ladder is a CDF; `C(K) = ∫_K^∞ P(S>u)du` recovers vanillas), but
> it is unwritten, and §1A's ladders are `range`-kind — measured: **301 of 301
> `KXLOWTAUS` events classify as `range`**, not `cumul` — so even the CDF route
> needs a construction that does not exist.

### 2.2 `ladder/maker.py` — reads a ladder, has no band

The PAVA monotone least-squares fair value is the ladder's *own* coherent shape,
computed from Kalshi mids alone. It works on the staged store today and needs no
external venue. It produces **a point estimate and nothing else** — there is no
interval anywhere in `ladder/`, and `FINDINGS_LADDER_DYNAMICS.md` §"Fair value"
confirms it is a least-squares fit, not a posterior.

Giving it a band (bootstrap, residual-scaled, anything) is **inventing a new
one**, which §1B forbids — and the band is not a detail here. It is the
threshold that defines the disagreement set, so whoever picks it picks the test.

### 2.3 The three escape routes are each closed by §1B itself

| Route | Blocked by |
|---|---|
| Give Act III a digital likelihood | "may not alter the density extractor in `wti_arb/synth/`" |
| Give the PAVA fit a credible band | "phase 0.5 does not invent a new one" |
| Run Test A on the commodity series, where chains exist | "may not change the universe fixed in §1A" — and `wti_arb/data_cme/parquet/` is **absent from this clone** (64 KB total), so the chains are not staged either |

**This is a genuine pre-registration defect.** §1B was committed before its data
was read, which is exactly the property that makes it worth something — and the
cost of that ordering is that it could presume an object that turns out not to
exist. It presumed a fitter that produces a fair value **with a credible band**
on daily temperature ladders. `BRIEF.md` §4 describes that fitter in the future
tense ("**Fitter.** Per ladder, per update: … produce a fair value **with a
credible band** per bracket"). It is phase-1 work that has not been built.

**Per the run's constraints, §1B is left exactly as committed.** The protocol is
not wrong about what it wants to measure; it is ahead of the stack.
