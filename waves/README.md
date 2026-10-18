# waves — do propagation waves exist? (descriptive census)

Brief: `NightKing/HANDOFF_waves.md`. Report: `FINDINGS_WAVES.md`. Follow-on list: `NEXT_STUDY.md`.
Reuses `ladder.store` (grid builder) on two stores: the commodity store `../data` (read-only) and
the expanded store `../waves_data` (pulled by `wti_arb/collect.py`, same layout).

| file | role |
|---|---|
| `discover.py` | exchange-wide event discovery (all statuses, nested markets) → `waves_data/discovery/`, scale report `SCALE.md` |
| `census.py` | per-bracket normalised events (p90/95/99/99.9 of a bracket's own non-zero mid changes), neighbour response by distance and horizon, first-move timing with the neighbour's baseline rate, initiator persistence |
| `run.py` | runner over a store: per-event checkpoints, resume, `status.jsonl` (ok / skipped / failed), aggregation to `results/events.parquet` + `summary.parquet` |
| `report.py` | `FINDINGS_WAVES.md` + `plots/` |
| `tests/` | synthetic-ladder tests |

```bash
python3 -m unittest discover -s waves/tests -v
python3 -m waves.discover                          # ~15 min; then waves_data/discovery/SCALE.md
# the pull (from wti_arb, the collector is unchanged):
cd wti_arb && python3 collect.py --out ../waves_data --no-probe --yes --pause 0.2 --workers 2 --series <comma list>
python3 -m waves.run --tag commodity               # commodity store
python3 -m waves.run --store waves_data --tag expanded
python3 -m waves.report
```
