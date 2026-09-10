# Project-NightKing — Kalshi historical collection

A one-shot, comprehensive collector of Kalshi commodity-ladder history: 1-minute
candlesticks with **bid and ask stored separately**, plus market, event and
settlement metadata, in Parquet. Its output (`FINDINGS.md`) decides which CME
options history to buy from Databento.

Four earlier attempts failed silently. Each failure is now a test:

| failure | where it is caught |
|---|---|
| 10,000-candle chunks; the real cap is 5,000 and every request 400'd | `candle_windows`, adaptive cap from the 400 body (`tests/test_chunking.py`) |
| read `close`, the API sends `close_dollars`; stored all-null bid/ask | `ohlc()` (`tests/test_parse.py`), `verify.py` fails on an all-null column |
| 40-page cursor cap truncated KXWTI at exactly 8,000 | `Client.page` has no cap; exact multiples are flagged (`tests/test_client.py`) |
| network failure and "never traded" both stored as `rows: 0` | manifest `status` + `fetch_ok` + HTTP codes; resume retries only errors (`tests/test_store.py`) |

## Files

| file | role |
|---|---|
| `probe.py` | asks the API every UNVERIFIED question from the brief; writes `data/probe.json` |
| `collect.py` | the collector: discovery → metadata tables → candles; resumable; `--smoke` |
| `verify.py` | validates the stored parquet and manifest; exit 1 on FAIL |
| `findings.py` | writes `FINDINGS.md` (also run at the end of `collect.py`) |
| `kalshi_common.py` | shared client, parsing, chunking, merge policy, store |
| `tests/` | unit tests on captured fixtures + a fake Kalshi server for end-to-end runs |
| `venue_scan.py`, `Diagnose.py` | the live orderbook scanner and the network diagnostic (unchanged tools) |

## Runbook (macOS)

```bash
pip3 install -r requirements.txt            # or: conda install pandas pyarrow
python3 -m unittest discover -s tests -v    # must be green before anything else (~1-2 min)

python3 probe.py                            # ~5-10 min; read the report, then data/probe.json
python3 collect.py --smoke                  # ~20 markets, both hosts, then verify.py; exit 0 required

python3 collect.py                          # prints the estimate by cadence group, asks y/N
# for the real thing, survive a closed lid / dropped SSH:
nohup caffeinate -is python3 collect.py --yes --workers 3 > collect.log 2>&1 &
tail -f collect.log

python3 verify.py                           # exit 0 required before using the data
python3 verify.py --crosscheck data/wtiw    # optional: compare with an old-collector pull
open FINDINGS.md
```

`collect.py` refuses to start without `data/probe.json`. Every script checks the
Python version, that pandas and pyarrow import, and that the SSL certificate
store is not empty (the python.org build on macOS ships an empty one; the
script prints the fix). If `exchange/status` is unreachable it stops with the
HTTP status rather than degrading.

Any interpreter ≥ 3.9 works (system 3.9 on the Mac Mini, conda 3.12 on the
laptop).

## What gets stored (`data/`)

```
data/
  probe.json                                   what the API said (cap, field style, hosts, cadence, estimate)
  manifest.jsonl                               one line per market fetch - THE checkpoint (append-only)
  manifest.json                                human-readable snapshot (counts per series, runs)
  summary.csv                                  one row per series
  FINDINGS.md                                  per-series usable window, settlement source, Databento shortlist
  collect.log
  parquet/kalshi_candles/period=1/series=S/event=E/part.parquet
  parquet/kalshi_markets/series=S/part.parquet one row per market, every API field
  parquet/kalshi_events/series=S/part.parquet
  raw/kalshi/events/S.json.gz                  exact API responses, gzipped
  raw/kalshi/markets/S.live.json.gz  S.hist.json.gz
  raw/kalshi/candles/S/E/TICKER.p1.json.gz     per market: every chunk response, with the HTTP status
```

Candle columns: `ts, dt, series, event, ticker, bracket, ladder_kind, period_min,
volume, open_interest, yes_bid_{open,high,low,close}, yes_ask_{...},
price_{...}, spread, half_spread, source`. Prices are cents (float64), parsed
from the `*_dollars` strings. `spread`/`half_spread` are **derived**; bid and ask
are the source of truth. `price_*` is null when nothing traded in that minute.

Market columns include `settlement_sources`, `settlement_source_name`,
`mutually_exclusive` → `ladder_kind` (RANGE / CUMUL), `expiration_value` (+
`_num`), `result`, `settlement_ts`, `occurrence_datetime`,
`settlement_timer_seconds`, `custom_strike.front_month_contract`,
`custom_strike.strike_date`, `rules_primary`, `strike_type`, `floor_strike`,
`cap_strike`, every timestamp as `<name>_epoch`, and **every other scalar field
the API returned** as a string column. Nothing needs a re-pull because a field
was not anticipated.

## Manifest statuses and resume

Each `manifest.jsonl` line is one market at one period (`key = TICKER@1`):

| status | meaning | resume |
|---|---|---|
| `ok` | candles stored (`rows` > 0) | skipped |
| `empty` | request succeeded, zero candles | skipped |
| `not_found` | HTTP 404 on **both** hosts (never-traded 2024-25 markets do this) | skipped; `--retry-not-found` retries |
| `error` | network failure, 429 exhausted, 5xx, or any other 4xx (`fetch_ok: false`) | **retried** |

`http_live` / `http_hist` record what each host answered and `source` which one
delivered. Resume is the default: re-running `collect.py` does only what is
missing. `--repull` ignores the manifest. A run that ends with `error` entries
exits 1 and says so; run it again.

## Scope and the confirmation gate

The probe classifies every series by cadence from the spacing of its events.
`collect.py` excludes the **intraday** group (15-minute and hourly ladders,
roughly 180,000 markets, none hedgeable with a CME option) unless you pass
`--include-intraday` or `--cadence hourly,daily,...`. Before a full run it
prints markets, requests and hours per cadence group and per series and waits
for `y`; `--yes` pre-confirms (needed under `nohup`). Adding the intraday series
later is `python3 collect.py --yes --include-intraday`: it resumes into the same
store.

Other filters: `--series KXWTIW,KXWTI`, `--exclude 'KXAAAGAS*'`,
`--since 2026-01-01`, `--min-volume 1`, `--period 60`.

## Live vs historical hosts

Every series is discovered on both hosts and every market's candles are tried
on the live host first, then the historical one. When the same market comes
back from both, the record with more settlement information (settlement_ts,
result, expiration_value, status) is primary and fills in the other's gaps.
Non-volatile fields that disagree are listed in `merge_conflicts` and logged.

## Old data in `data/`

The collector only touches the paths listed above. Pulls made by the previous
collector into `data/wtiw`, `data/wti`, … are neither read nor written nor
deleted, whether or not those runs are still going. A v1 `data/manifest.json`
is renamed `manifest.v1.json` on first write, never overwritten. Use
`verify.py --crosscheck data/wtiw` to compare an old pull with the new store on
overlapping `(ticker, ts)` rows.

## Tests

```bash
python3 -m unittest discover -s tests -v                 # everything, including end-to-end
python3 -m unittest discover -s tests -p 'test_[a-df-z]*.py'   # unit tests only (fast)
python3 tests/fake_kalshi.py --port 8765                 # run the fake server by hand, then:
python3 probe.py --out /tmp/x --live-base http://127.0.0.1:8765/trade-api/v2 \
                 --hist-base http://127.0.0.1:8765/trade-api/v2/historical
```

The fake server reproduces the verified API quirks (dollar-string OHLC, the
5,000 cap and its 400 message, bids-only books, cursor paging, live/historical
routing including an archived market served only by live, never-traded 404s)
and an outage switch used to test resume.
