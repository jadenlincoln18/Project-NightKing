# Tick-floor test, full synthetic re-run at 48 knots, then stop

`FINDINGS_PRIOR.md` overturned the brief's diagnosis, correctly: the bimodal
blind spot was basis resolution, not the prior's tail form. 48 knots with the
unchanged Gaussian prior took the trough from 6.8σ to 1.3σ where no heavy-tail
or local-scale form moved it at all.

Two items remain before the backtest. **Both are validation of what already
exists, not new capability.** When they are done, stop.

**Read first:**

1. `FINDINGS_PRIOR.md` — §1 checklist, and the Part B section on exclusion
2. `FINDINGS_REALCHAIN_V4.md` — the two watch chains and the consistency finding
3. `synth/act3.py` — the `Model` constructor's `hs_floor` parameter and its comment

---

## A note on scope, before the tasks

This project has a genuine tendency to chase theoretical perfection past the
point of practical return, and the operator has called it. Read this as context
for judgement calls, **not as licence to cut corners on the two tasks below** —
those are both necessary.

The evidence for the operator's position:

- Across 30 real dates, **no chain is both internally consistent and bimodal.**
  2026-05-01 is multimodal under every prior but fails every consistency check
  (χ² 4.1, eight LOO flags, split-half fires) — bad data, not bimodal evidence.
  2026-03-06 is unimodal under the real path.
- The bimodal, spike and kinked-peak configs are **stress tests**, deliberately
  chosen to sit outside the prior's comfort zone. They are not the operating
  environment. `A_crude_full`, `B_lognormal_full`, `D_heavy_both` and `S08_crude`
  are.
- Every increment of robustness on the exotic cases has been bought with **band
  width**: crude body bands 1.90¢ → 2.70¢ going from 24 to 48 knots. Since the
  trade filter is `|gap| > band + friction`, that is 0.8¢ more gap required per
  trade. Not inaccuracy — **lost signal.**

So: **the spike configuration is explicitly deprioritised.** It does not improve
at any knot count (46% → 59% and flat), it is the least realistic planted shape,
and non-uniform knots are now a drawing-board item rather than a blocker. Do not
build non-uniform knots in this pass. If you believe that is wrong, say so with
evidence rather than doing it.

The standing position on the blind spot: **narrowed and gated, not closed.**
Split-half catches inconsistent data; Act II is reported as the shape signal;
the backtest will carry a rule against trading brackets that sit in an interior
local minimum of the extracted density. That is sufficient coverage to proceed.
If the backtest surfaces a case where it bites, it comes back to the board then.

**When in doubt, prefer the change that is measurable in the backtest over the
change that is defensible in theory.**

---

## Task 1 — tick-floored likelihood, tested against LOO exclusion

### The question

`FINDINGS_PRIOR.md` Part B found the exclusion rule works — on real chains it
takes T-1d χ² 1.8 → 1.3 and Gate 4 27% → 0% — but flagged the tell: **the
removed quotes are tighter than average, not staler.**

That is the signature of an error-model problem rather than bad data. The
likelihood sets its tolerance at one half-spread. But options trade in 1¢ ticks,
so a 1¢-wide quote does not locate the true price to 0.5¢ — it locates it
somewhere inside a penny. Demanding sub-tick accuracy on tight quotes produces
large residuals on the *best* quotes, which then look like the worst ones.

Deleting them hides that. Widening the tolerance addresses it.

### What to build

`act3.py`'s `Model.__init__` already takes `hs_floor`, currently 0, commented
*"a quote cannot locate a price more precisely than the tick."* Someone
anticipated this. Use it.

Run three arms on the same chains and seeds:

| arm | description |
|---|---|
| `base48` | 48 knots, `hs_floor = 0`, no exclusion — the V4 default |
| `floor48` | 48 knots, `hs_floor` set, no exclusion |
| `excl48` | 48 knots, `hs_floor = 0`, Part B's exclusion rule — already run |

The floor value is your judgement. Half a tick (0.5¢) is the natural first
choice; justify whatever you pick, and if the result is sensitive to it, say so
and report a small sweep rather than one value.

### What to report

**Synthetic first.** The floor widens the assumed noise, so coverage could
over-widen. Check that crude coverage stays near 90% rather than drifting to
97%, and that the injected faults are still caught — a looser tolerance could
blunt the stale-quote and convexity detectors, which would be a genuine cost.

**Then real chains**, all 30 dates, all snapshots:

- χ²/strike, Gate 4 firing, Stage 14, band widths, sampler health
- **How many quotes each approach removes** — exclusion drops 7.7%, the floor
  drops none
- Whether the floor makes the exclusion rule redundant, i.e. whether LOO still
  flags strikes at the same rate once the tolerance is honest
- The chains where the two disagree, and what they look like

### The decision

- **Floor works and exclusion is redundant** → adopt the floor, drop the
  exclusion rule. Preferred outcome: it keeps every quote and fixes the cause.
- **Both are needed** → say so, and say why deleting good-looking quotes is
  still justified after the tolerance is corrected.
- **Neither works** → report it. `FINDINGS_REALCHAIN_V4.md` already shows real
  χ² at V3 levels, which is usable; this is an improvement, not a blocker.

**Do not adopt the exclusion rule as the default without the floor comparison.**
47% of T-1d chains losing more than a tenth of their quotes is a large
intervention to make on a symptom.

---

## Task 2 — full synthetic study at 48 knots

`FINDINGS_PRIOR.md` states the limitation plainly: the prior study used **20–40
seeds per configuration**, not the full 1,840-run study behind
`FINDINGS_SYNTHETIC.md`. 48 knots is now `act3.M_COEF`'s default, so the headline
numbers in the project's main synthetic document describe a configuration that is
no longer in use.

Re-run the full study at 48 knots (plus the tick floor if Task 1 adopts it) and
produce the definitive numbers.

- Same configurations, same seeds, same sampler settings as
  `FINDINGS_SYNTHETIC.md`
- Report **24-knot vs 48-knot side by side** on every table, so the cost of the
  change is visible in one place rather than inferred across documents
- **Coverage is the headline**, as before
- Revise `FINDINGS_SYNTHETIC.md`'s verdict. It currently reads FAIL with a
  superseded-in-part note at the top. With the blind spot narrowed to 1.3σ and
  57% trough coverage, and no consistent real chain showing bimodality, state
  the honest verdict — and say plainly what remains unfixed rather than
  declaring victory.

This is the one place where thoroughness is worth the compute: it is the
document everything else cites.

---

## What not to do in this pass

- **No non-uniform knots.** Drawing-board item.
- **No further work on the spike configuration.**
- **No further prior forms.** Student-t, horseshoe and local scales were tested
  and lost to knot count. That question is settled.
- **No touching the data pipeline.** Forward, synchronisation and the real path
  are settled.
- **No backtest code.** Still descriptive: no Kalshi price read, no gap
  computed, no trade evaluated. The backtest is the next brief.

## Foundational

- **Synthetic is the arbiter**, real chains are the check. A change that
  improves real χ² while degrading synthetic coverage is worse.
- **Sampler health gates acceptance**: R̂, ESS and divergences on every arm.
  Current real-chain baseline is R̂ 1.016–1.021, ESS 202–246, divergences 0.
- **Before/after on the same seeds**, every table.
- **Band width is a reported cost, not a footnote.** It converts directly into
  lost trades through the filter. Report it alongside coverage everywhere.
- **Say plainly when something does not work.** "The floor moved χ² 1.8 → 1.75,
  the exclusion rule is doing something the error model is not" is a useful
  result.

## Your judgement

- The `hs_floor` value and whether a sweep is warranted
- Whether the floor belongs on the half-spread or on the price directly
- How to present the 24-vs-48 comparison so the trade-off is legible
- Whether any configuration in the full study is no longer worth running at full
  seed count

**If a foundational item looks wrong, say so rather than working around it.**
The Stage 6 forward decision and this brief's own predecessor were both
overturned that way, and both times the correction was right.

## Deliverables

1. `FINDINGS_TICKFLOOR.md` — three arms, synthetic and real, with a clear
   recommendation on floor vs exclusion vs both
2. `FINDINGS_SYNTHETIC_V2.md` (or a revision of `FINDINGS_SYNTHETIC.md`) — the
   full study at 48 knots, 24-vs-48 side by side, honest verdict
3. Doc updates where conclusions change: `NightKing/PIPELINE_CHOICES.md`,
   `PIPELINE_MAP.md`, `Pipeline.canvas`, the root writeup
4. A one-paragraph statement of **what is still unfixed and gated rather than
   solved**, for the next brief to inherit

## Long runs

The operator starts these and walks away. Retry with backoff, pause and resume
rather than exit, checkpoint per completed job, resume as the default,
distinguish "failed" from "not attempted". Timestamped logs including pauses.
Nothing here needs the network — no new data, no spend.

## Environment

macOS, Python 3.9-compatible, numpy/scipy only. `data/` and `data_cme/`
read-only. Both test suites stay green.
