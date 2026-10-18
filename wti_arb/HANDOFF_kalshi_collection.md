# Kalshi historical data collection — handoff brief

You are building a **one-shot, comprehensive** data collector. It runs, it stores
everything needed, and we do not come back to it. Previous attempts failed four
separate times on details that looked right and were not. Those failures are
documented below so you do not repeat them.

**Read the whole brief before writing code.** In particular the two sections
marked VERIFIED and UNVERIFIED. Everything under UNVERIFIED must be resolved by
querying the API, never by assuming.

---

## 1. What this is for

We are testing a statistical arbitrage strategy between Kalshi prediction
markets and CME options on futures.

The mechanism: Kalshi lists ladders of price brackets on commodities (e.g. "WTI
between $87.00 and $87.99"). Each bracket is a digital option. Separately, an
options chain on the corresponding futures contract implies a full risk-neutral
probability density (Breeden–Litzenberger). If we extract that density and
integrate it over Kalshi's bracket edges, we get a model probability for each
bracket that we can compare against Kalshi's quoted price. Where the gap exceeds
both our estimation uncertainty and transaction costs, there may be a trade.

**Why the data must be exactly right:**

- We need **bid and ask separately**, never a mid. The half-spread drives the
  weighting in the density fit and the likelihood in the Bayesian extraction.
  A stored mid destroys that information permanently.
- We need **settlement metadata** to determine whether a CME option is even a
  valid hedge (this turned out to be the critical question — see §5).
- We need **realized settlement values** as backtest ground truth.

This collection step gates a paid Databento purchase of CME options data. We
want to know exactly which dates and which series are worth buying before
spending money.

---

## 2. What to collect

For every Kalshi commodity series that has usable history:

1. **Candlestick history** at 1-minute resolution, with bid and ask OHLC stored
   as separate columns.
2. **Market metadata** — settlement source, referenced futures contract,
   realized settlement value, result, strike type, open/close times.
3. **Event metadata** — whether the ladder is mutually exclusive, settlement
   sources.
4. **Raw API responses** persisted alongside every derived row, so parsing bugs
   can be fixed without re-pulling.

Storage: **Parquet, not CSV.** CSV loses types — we previously had the same
column inferred as Integer in one file and Float in another. Partition by
series and event. Write a manifest for resumability and a small summary CSV.

---

## 3. VERIFIED facts — these are confirmed by direct API observation

Do not re-derive these, but do assert them in tests so a change breaks loudly.

### Endpoints and auth

- Live/recent: `https://api.elections.kalshi.com/trade-api/v2`
- Archived: `https://external-api.kalshi.com/trade-api/v2/historical`
- **No authentication required** for market data (series, events, markets,
  orderbook, candlesticks). No API key needed.
- Public market data rate limit is roughly 30 requests/second. We use ~0.25s
  between requests when running several processes in parallel.

### Candlesticks

- Path (live): `/series/{series_ticker}/markets/{market_ticker}/candlesticks`
- Path (archived): `/historical/markets/{market_ticker}/candlesticks`
- Required params: `start_ts`, `end_ts`, `period_interval`
- `period_interval` accepts 1, 60, 1440 (minutes)
- **HARD CAP: 5,000 candlesticks per request.** Not 10,000. Exceeding it returns
  HTTP 400 with `"max candlesticks: 5000"`. We lost an entire overnight run to
  this — every 1-minute request for a week-long market returned 400 and the
  collector stored zero rows while logging success. **Chunk the time range.**
- Response key is `candlesticks` (a list).

### Field names — this is where the second silent failure happened

OHLC values come back **suffixed with `_dollars`, as decimal strings**:

```json
{
  "end_period_ts": 1787961600,
  "yes_bid": {"open_dollars":"0.0100","high_dollars":"0.0300",
              "low_dollars":"0.0000","close_dollars":"0.0200"},
  "yes_ask": {"open_dollars":"0.9700","high_dollars":"0.9700",
              "low_dollars":"0.0400","close_dollars":"0.0400"},
  "price": {},
  "volume_fp": "0.00",
  "open_interest_fp": "0.00"
}
```

Reading `block["close"]` returns `None` for every row. The collector "worked",
logged happy output, and stored a table where every bid and ask was null.
**Parse `*_dollars` and multiply by 100 to get cents. Also `volume_fp` and
`open_interest_fp`, not `volume`/`open_interest`.**

### Orderbook (if you collect live snapshots)

- Path: `/markets/{ticker}/orderbook`, param `depth` (0–100)
- **Kalshi returns BIDS ONLY, on both sides.** There is no ask array. A YES bid
  at 7c is identical to a NO ask at 93c. So:
  `yes_ask = 100 - best_no_bid`, same size.
  Treating the raw book as yes-bid/yes-ask produces garbage spreads.
- Bulk endpoint `/markets/orderbooks` takes param `market_tickers` (NOT
  `tickers`), up to 100 comma-separated.

### Event object fields (authoritative — use these, do not infer)

- `mutually_exclusive` (bool) — **definitive** RANGE vs CUMULATIVE ladder type.
  RANGE = exclusive brackets that sum to 100c ("$87.00 to $87.99").
  CUMULATIVE = nested thresholds that do NOT sum to 100 ("Above $89.99").
  We previously inferred this from label text and produced 47 false-positive
  "arbitrage" signals by summing cumulative ladders.
- `settlement_sources` — what the exchange settles against. Observed values:
  `name=ICE | url=https://www.theice.com/products/213/WTI-Crude-Futures`
  `name=Pyth - Brent | url=https://app.pyth.com/...`

### Market object fields

- `ticker`, `event_ticker`, `yes_sub_title` (the bracket label),
  `open_time`, `close_time`, `status`, `strike_type`,
  `floor_strike` / `cap_strike`
- `expiration_value` — **realized settlement price**. Empty string on unsettled
  markets. This is our backtest ground truth.
- `result` — "yes"/"no"/empty
- `custom_strike.front_month_contract` — e.g. `"WBS 26V-ICE"`, naming the
  futures contract referenced
- `rules_primary` — plain-English settlement rule
- `volume_fp` — total volume, decimal string

### Paging

Events and historical markets both use a `cursor`. **Page until the cursor is
empty.** An earlier version capped at 40 pages × 200 = 8,000 and silently
truncated: KXWTI reported exactly 8,000 archived markets, and raising the cap
revealed 10,813. Any count landing exactly on a round multiple of your page
size is a truncation warning.

### Host routing — counterintuitive, verify it yourself

A **finalized** market from July 2026 (`KXWTIW-26JUL2414-B79.50`) is served by
the **live** host and returns 404 on the historical host. So "archived markets
are on the historical host" is not reliably true. Try both, record which
worked. Do not assume.

---

## 4. UNVERIFIED — you must resolve these by querying, not guessing

**Do not hardcode any of this. Build discovery into the script.**

1. **Series tickers.** We know `KXWTIW`, `KXWTI`, `KXBRENTD`, `KXGOLDD`,
   `KXNATGASD` exist. Do not hardcode a list — query `/series?category=...` and
   discover them. An earlier attempt hardcoded 13 guessed tickers and 11 were
   wrong, reported misleadingly as "no open markets".

2. **Which categories exist.** We used "Commodities". There may be relevant
   series under Economics or Financials. Query and see.

3. **Ticker format changed over time.** Old: `KXWTIW-24DEC06-T74.99`.
   New: `KXWTIW-26JUL2414-B79.50` (8-char date with a time suffix). We do not
   know when or why it changed, or whether old-format tickers are still
   resolvable. Handle both; do not assume a single regex works.

4. **There is a data gap between 2025-11 and 2026-05** in KXWTIW with no events
   at all. Cause unknown — possible delisting and relaunch. Determine whether
   those events exist under a different ticker convention.

5. **Whether `period_interval` accepts values beyond 1/60/1440.** Probe it.

6. **Whether the historical host is needed at all**, given the finding in §3.
   Test both hosts on a known-archived market and a known-live one.

7. **Rate limit behaviour under parallelism.** We have not measured where 429s
   actually begin. Probe conservatively.

**How to resolve these:** write a `probe` mode that runs first, queries the API
for each unknown, prints what it found, and writes the findings to a file the
main collector reads. Do not proceed to a full pull until probe output is
reviewed.

---

## 5. Critical finding that shapes what matters

Settlement source determines whether this strategy is possible at all:

| series | settles on | implication |
|---|---|---|
| KXWTIW, KXWTI | **ICE** WTI Crude Futures | hedgeable with a CME/NYMEX option, but cross-exchange basis exists and must be measured |
| KXBRENTD, KXGOLDD, KXNATGASD | **Pyth** (aggregated oracle index) | an aggregated 24/7 index is not a specific contract's settlement; basis is likely larger and less stable |

So `settlement_sources`, `front_month_contract`, and `rules_primary` are not
nice-to-haves. **Capture them for every market.** Emit a summary grouping series
by settlement source at the end of the run.

### The other critical finding: most historical data is worthless

KXWTIW has 201 events going back to Dec 2024, but coverage collapses before
2026:

```
month      brackets  zero-candle  %live   total candles
2025-09          45           42     7%               8
2025-10          45           35    22%              20
...
2026-05          49            0   100%         207,491
2026-06          60            0   100%         113,632
2026-07          99            0   100%         281,973
```

Investigated: those 2024–25 markets have **total volume of 5.00 contracts** over
their entire life and return 404 on candlesticks. They existed and never traded.

**Implication:** the usable backtest window starts around 2026-03 to 2026-05.
Do not treat a zero-candle market as a failure — but DO distinguish, in the
manifest, between:

- request succeeded, market genuinely has no candles
- request failed (network, 4xx, 5xx)

The previous manifest recorded both as `rows: 0`, so a resume could not retry
genuine failures. **Store the HTTP status and an explicit `fetch_ok` flag.**
This matters: a network outage would otherwise be indistinguishable from "this
market never traded", and would silently bias any analysis of market activity.

---

## 6. Requirements

**Verify before pulling.** Probe mode first (§4). Print findings. Only then
collect.

**Test before running.** Unit tests against captured response fixtures for:
`*_dollars` parsing, the 5000-candle chunking, cents normalisation, the
orderbook ask derivation, ticker date parsing in both formats, parquet
round-trip preserving dtypes. Then a smoke run on ~20 markets that exercises
**both** live and archived paths, validated by a checker that reads the stored
parquet (not the logs) and asserts bid/ask are populated, prices are 0–100, and
spreads are non-negative.

A previous smoke test passed while storing all-null bid/ask because it only
checked row counts. **Check column population, not row count.**

**Resumable.** Manifest checkpointed during the run, not only at the end. Resume
should be the default; make re-pulling an explicit opt-in flag. Resume must
retry markets where `fetch_ok` was false and skip ones that genuinely had no
data.

**Store raw responses** gzipped alongside derived parquet.

**Never store a mid as the source of truth.** Bid and ask as separate columns.
Derived spread/half-spread are fine if clearly marked derived.

**Log honestly.** If a request fails, say so with the status code. Silent
degradation caused three of the four previous failures.

---

## 7. Deliverables

1. `probe.py` — resolves everything in §4, writes findings to JSON
2. `collect.py` — the collector, resumable, tested
3. `verify.py` — validates the stored parquet, exits nonzero on failure
4. `tests/` — unit tests with captured fixtures
5. A short `FINDINGS.md` written at the end of the run: per series, the usable
   date window, event count, settlement source, ladder type, and total candles.
   This is what we use to decide the Databento purchase.

## 8. Environment

macOS. Python 3.12 (conda) on the laptop, 3.9 system Python on a Mac Mini —
**do not assume a specific interpreter**; check that pandas and pyarrow import
and that `ssl.create_default_context().cert_store_stats()["x509_ca"] > 0`
before doing anything else. A missing cert store makes every HTTPS call fail
with an opaque URLError, which cost us an hour.

Long runs should survive a dropped SSH session: `nohup` plus `caffeinate -is`,
or tmux.
