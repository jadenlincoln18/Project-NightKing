# ladder — the Kalshi ladder against itself

Brief: `NightKing/HANDOFF_ladder_dynamics.md`. Report: `FINDINGS_LADDER_DYNAMICS.md`.
Next pass: `NEXT_PASS.md`. Reads `../data/parquet` (read-only); never touches
`../wti_arb` or `../data_cme`.

| file | role |
|---|---|
| `store.py` | markets table → ladder classification (cumul / range, 'less' ladders flipped to P(>X) form; title parser for 2022-24 markets); candles → forward-filled minute grid with empty sides as NaN and intra-minute extremes kept |
| `fees.py` | Kalshi fee: taker 0.07·P(1−P), maker 0.0175, per-order round-up |
| `census.py` | executable monotonicity violations (adjacent, any-pair, intra-minute upper bound, mid-shape), episodes with duration / net / depth proxies; range-ladder sum constraint |
| `propagation.py` | impulse response of neighbours at distance ±1..3 and horizons 0..30 min; stale-neighbour trade net of fees |
| `maker.py` | monotone (PAVA) fair value from the ladder's own mids; how often a maker could post inside the spread |
| `run.py` | runner over all series, one job per event, atomic per-event checkpoints, resume by default, `status.jsonl`, timestamped log, aggregation |
| `report.py` | renders the findings and `plots/` |
| `collect_books.py` | live collector: size at the touch for every open market every minute, full books for the focus series every 5 min; resumable, backoff, never exits on a transient |
| `pull_event.py` | pull a recent event's candles into `data/live_candles/` (used for KXAAAGASDCA-26OCT04/05) |
| `kapi.py` | keyless client with retry/backoff |
| `tests/` | synthetic-ladder unit tests |

```bash
python3 -m unittest discover -s ladder/tests -v
python3 -m ladder.run --live                 # ~1 min; results/parts/<series>/<event>.pkl, summary.parquet, episodes.parquet, ...
python3 -m ladder.run --aggregate            # rebuild aggregates only
python3 -m ladder.report                     # FINDINGS_LADDER_DYNAMICS.md, plots/
nohup python3 -m ladder.collect_books --books > /dev/null 2>&1 &     # data/books/date=*/touch-*.parquet, depth-*.parquet, collect.log
```

Definitions fixed before the run (see the report, section 0): violation = executable
edge ≥ 1c (sensitivity 2/3/5c); move = mid change ≥ 2c on a two-sided bracket with
spread ≤ 10c (sensitivity 1/5c); body = mid in [10, 90]c; duration in grid minutes.
