# Project-NightKing

Two studies of Kalshi commodity ladders, kept apart so they cannot be confused.
The data stores at the root are shared and read-only.

| folder | what it is | status |
|---|---|---|
| `wti_arb/` | **Previous work (Sep 1 – Oct 4, 2026):** the Kalshi collector, the Databento/CME side, the density extractor (`synth/`), the synthetic validation, real-chain V2–V4, and the Kalshi backtest. Verdict: the WTI option-vs-Kalshi arbitrage is **closed** (`wti_arb/FINDINGS_BACKTEST_V2.md`). Its own `README.md` is the original runbook. | finished, frozen |
| `ladder/` | **Current work (from Oct 5, 2026):** the Kalshi ladder against itself — monotonicity and sum violations, their duration, propagation between neighbouring brackets, tradeability net of fees, live depth at the touch. No CME data, no extractor. Report: `ladder/FINDINGS_LADDER_DYNAMICS.md`. | active |
| `waves/` | **Current work (from Oct 5, 2026, evening):** do propagation waves exist? Per-bracket-normalised event census across the commodity store and an expanded exchange-wide ladder store (`waves_data/`, pulled with the unchanged collector). Report: `waves/FINDINGS_WAVES.md`. | active |
| `waves_data/` | Expanded Kalshi ladder store for the waves study (discovery tables kept; parquet gitignored). | written by the pull |
| `data/` | Kalshi store: 162 series, 56,167 markets, 58.9M 1-minute candles with bid and ask separate (built by `wti_arb/collect.py`; parquet gitignored). | read-only |
| `data_cme/` | Databento store for the previous study (parquet gitignored). | read-only |
| `NightKing/` | Obsidian vault: briefs (`HANDOFF_*.md`), pipeline notes, writeups. Not in git. | — |

`wti_arb/` runs unchanged from inside its folder: it reaches the stores through the
symlinks `wti_arb/data -> ../data`, `wti_arb/data_cme -> ../data_cme` and
`wti_arb/.env -> ../.env`.

```bash
# previous study, unchanged
cd wti_arb && python3 -m unittest discover -s tests        # 140 tests, ~90 s
cd wti_arb && python3 -m synth.realchain --help

# ladder study
python3 -m unittest discover -s ladder/tests               # 13 tests, < 1 s
python3 -m ladder.run --live                               # whole store, ~1 min on 6 cores, resumable
python3 -m ladder.report                                   # FINDINGS_LADDER_DYNAMICS.md + plots
python3 -m ladder.collect_books --books                    # live depth collector (keyless, free)

# waves study
python3 -m unittest discover -s waves/tests
python3 -m waves.discover && python3 -m waves.run && python3 -m waves.run --store waves_data --tag expanded && python3 -m waves.report
```
