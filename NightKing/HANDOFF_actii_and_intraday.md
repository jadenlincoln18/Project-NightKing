# Act II firing rate, intraday futures, and a V3 re-run

V2 worked (`FINDINGS_REALCHAIN_V2.md`): futures-anchored forward plus quote
synchronisation took Act III χ²/strike from 8.1 to 1.6 on all 30 dates,
multimodality 43% → 0% at T-1d, Stage 14 pass 36% → 70%, forward RMSE 37.7¢ →
10.8¢. The split-half gate fires 17% on synchronised chains against 68% for the
old Act II gate on raw ones.

This is three tasks, cheapest first. **Task 1 may make Task 2 unnecessary — do
them in order and report Task 1 before spending anything.**

**Read first:** `FINDINGS_REALCHAIN_V2.md` (especially §8, the still-not-right
list, and the Gate 4 calibration note), then
`NightKing/HANDOFF_forward_and_sync_fix.md` for what V2 was asked to do.

**Nothing in this brief touches Kalshi prices or evaluates a trade.** Still
descriptive. The backtest is a separate piece of work and is explicitly out of
scope.

---

## Task 1 — Act II's V2 firing rate (free, the number already exists)

### Why this matters

V2's Gate 4 calibration note says: **split-half never fires on planted bimodal
truth, while Act II fires every time.** So the two detectors catch different
things:

| detector | catches | blind to |
|---|---|---|
| split-half | inconsistent data | a mis-specified prior |
| Act II vs Act III | a mis-specified prior | — (but was swamped by noise on raw chains) |

Act II fired 64–77% in V1, but Act II differentiates and therefore amplifies the
very asynchronicity V2 removed. **On synchronised chains that confound is gone,
so its firing rate is now interpretable** — and it is the only detector we have
for the bimodal blind spot documented in `FINDINGS_SYNTHETIC.md`.

### What to report

From the V2 run already on disk, no re-running:

- Act II firing rate on **synchronised** chains, by snapshot and window, against
  the V1 raw-chain baseline
- The distribution of max |Act II − Act III| on synchronised chains: median,
  p90, max — the V1 numbers were median 3.36–5.81¢, p90 up to 26¢, max 36.76¢
- **Do Act II and split-half fire on the same chains or different ones?** A
  confusion matrix. Overlapping means they are seeing one phenomenon;
  disjoint means they cover two, which is the hoped-for result.
- Act II fit health on synchronised chains: g(k) ≥ 0 rate, density mean vs
  forward. V1 had 96–100% butterfly-free but a ~$0.50 mean drift on synthetic;
  a comparison arm that is itself broken makes its firing rate hard to read.
- The chains where Act II fires but split-half does not — what do they look
  like? Multimodal posterior? High τ? Wide bands? Few strikes?

### The question this answers

**If Act II is now quiet on synchronised chains** (roughly the calibrated
false-positive rate rather than 68%), then split-half and Act II between them
gate both failure modes, and the prior can stay untouched for now.

**If Act II still fires on most synchronised chains**, either real WTI densities
genuinely sit outside the prior's comfort zone, or Act II is too fragile to use
as a gate at all. Say which, with evidence. That moves the prior's form to the
front of the queue.

State the answer plainly in one sentence at the top of the findings.

---

## Task 2 — intraday CL futures (small spend, only if Task 1 warrants continuing)

### Why

V2's synchronisation is the fix that worked, and it depends on a **reconstructed**
intraday price path — estimated from the option trade stream and anchored to the
settlement at 14:29, because `data_cme/` holds only settlements and session
extremes. It validates well (3¢ median against settlement) but it is an estimate
carrying the load-bearing fix.

Two things it plausibly explains:

- **χ² sits at 1.6–1.9 rather than ~1.1.** Residual asynchronicity from an
  imperfect path is the obvious candidate.
- **T-4h/60 keeps 23% multimodal runs** while every other snapshot went to 0%.
  T-4h is 10:30 ET, the furthest point from the 14:29 anchor — where the
  reconstruction is weakest. Real data separates "reconstruction artifact" from
  "the market really is bimodal that morning," and that matters because **T-4h
  is the snapshot closest to decision time.**

### Scope and spend

Futures are one instrument per contract, not hundreds of strikes, so this should
be cheap — `CL.FUT statistics` was $0.49 for six months.

- **Cost-preflight with `metadata.get_cost()` before every billable call**, log
  the quote, and abort if the total exceeds **$25**. Same discipline as
  `NightKing/HANDOFF_databento_pull.md`.
- **Dry-run by default**; `--execute` required to spend.
- Scope to the CL contracts each date's option actually exercises into. V1 §7
  verified `options_definition.underlying` maps correctly on 100% of dates —
  use it rather than assuming front month. Kalshi rolls its referenced month on
  the 16th, independent of either exchange's expiry.
- Schema is your call. `ohlcv-1m` is likely cheapest and sufficient since only
  the level is needed, not the spread; `bbo-1m` gives bid/ask if that is worth
  the difference. Price both and pick.
- Only the 30 dates in the study, and only the hours the snapshots need
  (T-2d/T-1d at 14:30 ET, T-4h from 10:30, plus enough margin for the windows).

**Report the quoted cost and wait for approval before executing.**

### Validation

Compare the real path against V2's reconstruction on the same dates and minutes.
Report the distribution of the difference — mean, median, MAD, RMSE, p10–p90 —
and whether the error grows with distance from the 14:29 anchor. That last one
is the direct test of the T-4h hypothesis, and it is worth reporting even if the
answer is "the reconstruction was fine."

---

## Task 3 — V3 re-run

Same 30 dates, same snapshots, same sampler settings, same before/after
discipline. **Only the price path changes**: real intraday futures in place of
the reconstruction. Everything else identical to V2.

`FINDINGS_REALCHAIN_V3.md` with V1 / V2 / V3 side by side on every table.

### Stated in advance, so it is not decided after seeing the numbers

- **Works:** χ² moves meaningfully toward 1.1 **and** T-4h multimodality drops
  substantially below 23%
- **Partial:** one improves and not the other — say which and hypothesise why
- **Does not:** neither moves materially. Then the reconstruction was adequate,
  the residual is model rather than data, and **the prior's form is the next
  thing to fix.** That is a useful answer, not a failure.

---

## Long-run resilience — required

The operator will start this and walk between buildings. **Network will drop for
minutes at a time. The run must survive that without losing work.**

- **Retry with exponential backoff** on every network call, and treat a
  connection failure as retryable rather than fatal. Distinguish a network
  failure from a 4xx: the first waits and retries, the second is a real error.
- **Pause-and-resume rather than fail.** On repeated connection failures, sleep
  and keep retrying — do not exit. A twenty-minute walk should look like a
  twenty-minute pause, not a crash.
- **Checkpoint continuously, not at the end.** One line per completed job, so a
  kill at any point loses at most the job in flight. V2's study log already does
  something like this; extend it.
- **Resume is the default.** Re-running the same command picks up where it
  stopped and re-does only genuinely failed jobs. Re-doing completed work
  requires an explicit flag.
- **Distinguish "failed" from "not attempted" in the checkpoint.** A manifest
  that records both as absent cannot retry correctly — that exact bug cost four
  runs on the Kalshi collector.
- **Log with timestamps**, including pauses and resumes, so a gap in the log is
  explicable afterwards.
- Nothing in Task 1 or Task 3 needs the network at all — only Task 2's Databento
  pull does. Structure it so a network outage during Task 2 cannot corrupt a
  partial download: **verify by record count and reject partials**, as V1's
  Databento work already does.

Practical note for the operator: run it under `nohup` with `caffeinate -is` so a
closed lid or a dropped SSH session does not kill it.

---

## Foundational

- **Still descriptive.** No Kalshi price read, no gap computed, no trade
  evaluated, and none of that code written. The backtest is the next piece of
  work, not this one.
- **χ²/strike stays the headline metric.** Act III's own fit against the
  market's own spreads, independent of any cross-check.
- **Before/after on the same dates**, every table. A number without a baseline
  cannot be attributed.
- **Do not tune the prior in this pass.** Task 1 decides whether it needs
  touching at all; tuning before that answer would be tuning against a question
  not yet asked.
- **Do not add quote-level exclusion.** V2 §8 already identified this as the
  obvious next step and correctly declined it as tuning against known-bad data.
  Task 2 either removes the need or proves it is warranted.
- **Say plainly when something does not work.** "χ² went 1.6 → 1.55, the real
  path was not the constraint" is more useful than a tuned number.

## Your judgement

- How to structure the Act II / split-half comparison and what statistic best
  captures whether they are disjoint
- Databento schema and exact scoping for Task 2
- How to splice the real path into the existing synchronisation code — and
  whether to keep the reconstruction as a fallback for gaps in the real data
- Whether T-2d is worth keeping now that it extracts on 26 of 30 dates
- Checkpoint format and retry policy specifics

**If a foundational item looks wrong, say so rather than working around it.**
The Stage 6 decision was overturned exactly that way.

## Deliverables

1. `FINDINGS_ACTII_V2.md` — Task 1, with the one-sentence verdict at the top
2. A cost-preflighted, dry-run-default puller for Task 2 (only if Task 1
   warrants it), with the quote reported before execution
3. `FINDINGS_REALCHAIN_V3.md` — V1 / V2 / V3 side by side, with the
   stated-in-advance verdict
4. Doc updates if any conclusion changes `NightKing/PIPELINE_CHOICES.md`,
   `PIPELINE_MAP.md`, `Pipeline.canvas`, or the root writeup

## Environment

macOS, Python 3.9-compatible. `data/` (Kalshi) and `data_cme/` (CME) read-only
except for Task 2's new pull. Both test suites must stay green. API key in
`.env` as `DATABENTO_API_KEY`; `.env` stays gitignored.
