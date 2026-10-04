# BACKTEST_PROTOCOL — fixed before any Kalshi price is read

Written and committed 2026-10-03 (see the commit timestamp) before `synth/backtest.py` existed and before any
file under `data/parquet/kalshi_candles` or `kalshi_markets` was opened for a price. The only Kalshi fields the
project has read so far are event metadata (`close_time`, `expiration_value`, `rules_primary`,
`custom_strike.front_month_contract`) for Gate 0 and the basis study; no bid, ask, price or volume. Everything
below is a commitment. Whatever the gaps look like, the extractor, the gates and these thresholds do not move in
this pass; anything that looks like it needs tuning is written to the "next pass" list, not applied.

Brief: `NightKing/HANDOFF_backtest.md`. Inputs: `nightking-strategy-writeup.md` Act IV / Part 5, `PIPELINE_CHOICES.md`
Stage 18 and the two sizing rules, `FINDINGS_TICKFLOOR.md` §2, `FINDINGS_REALCHAIN_V4.md`, `data_cme/FINDINGS_BASIS.md`,
`data/FINDINGS.md`.

---

## 1. What is being tested, and on what

**The object.** For each hedgeable Kalshi settlement date, each snapshot and each bracket of the KXWTIW RANGE ladder:
the gap between Kalshi's executable bracket price and the posterior mean of the Act III risk-neutral probability of
that bracket, with the posterior band, the Stage 18 decomposition and the Stage 19 filter.

**The extractor is frozen** at the configuration the real-chain studies ended on: 48 uniform knots, Gaussian
roughness prior with τ integrated out, forward from the intraday NYMEX futures bars at the snapshot instant with the
quotes synchronised along the real path (sticky-strike), likelihood tolerance max(half-spread, 1¢), NUTS 4 × 400/400,
martingale constraint on. In code that is `synth.realchain` arm `real_m48_f1`. No other arm is run against Kalshi.

**Series.** KXWTIW (weekly, Friday 14:30 ET settlement) is the study. KXWTI (daily, Mon/Wed/Fri hedgeable dates) is a
*secondary* arm: it runs after KXWTIW if its chains are on disk, is reported in its own section with its own
denominator, and never pools into the KXWTIW bar. Reason: short-dated extraction is harder (`PIPELINE_MAP.md`), and
the writeup's own ordering is weeklies first.

**Snapshots.** Two, both already defined in `synth.realchain`:

| snapshot | instant (ET) | role |
|---|---|---|
| T-1d | 14:30 one business day before settlement | **lead** — the better-conditioned extraction (χ²/strike 1.4, Gate 4 3%) |
| T-4h | 10:30 on settlement day | reported alongside — closest to decision time, worse conditioned (χ² 1.1 but 7¢ bands) |

Lead is T-1d, decided now. If the two snapshots disagree in sign on the same bracket, that is reported as an artifact
signal (§7), not resolved by picking one.

**Window.** 60 minutes, Gate 0's own window. The 10-minute window is not run.

---

## 2. The evidentiary bar

Effective sample: ~34 KXWTIW dates (Kalshi events with a settlement value since 2026-01-01; `FINDINGS_BASIS.md`), of
which the real-chain studies found 30 clearing Gate 0 at the 60-minute window. Brackets within a date share a density
and consecutive weeks share a regime, so **effective n is ~30, not ~800 bracket-comparisons**. Every claim below is
made at the date level.

Three conditions, all fixed now, each answerable yes/no from the tables in `FINDINGS_BACKTEST.md`:

**B1 — structure exists.** In the pooled Stage 18 regression at the lead snapshot (per-date intercepts, one slope
$b$ and one tilt $c$ across dates, run per posterior draw), the 90% credible interval of $b$ lies entirely below 1,
**or** the 90% interval of $c$ excludes 0; **and** the same interval statement holds at T-4h with the same sign.
A structure that appears at one snapshot only is treated as an artifact candidate, not a finding.

**B2 — a tradeable edge exists.** Brackets that clear the Stage 19 filter (§5) come from **at least 8 distinct
KXWTIW dates** spread over **at least 3 calendar months**, and the sign of the gap on those brackets agrees with the
direction B1 implies (longshots rich if $b<1$; the sign of $c$ in the state) on **at least 75%** of them. Fewer dates,
or concentration in one month, is reported as a regime observation.

**B3 — it survives friction, held to settlement, at the size the hedge actually requires.** Net P&L per Kalshi
contract across all filtered brackets, at the applicable size (§6) and with the full friction stack (§4), is
positive; **positive on at least 60% of the dates traded**; and **still positive with the three best dates removed**.

Verdict vocabulary, fixed:

- **EDGE** — B1, B2 and B3 all hold.
- **STRUCTURE, NOT AN EDGE** — B1 holds, B2 or B3 fails. The venues disagree systematically but not by more than
  band plus friction, or not consistently enough to trade.
- **NULL** — B1 fails. The gaps are indistinguishable from zero at this sample size. This is a result.

A magnitude is also stated for the record, not as a criterion: the mean |gap| on filtered brackets and the median
|gap| by moneyness band, against the measured friction. If the only brackets clearing the filter have a mean |gap|
below twice the friction, the report says so in the verdict sentence.

**No other bar is introduced after the numbers are seen.** If a result is interesting under a different cut, that cut
is listed in the "next pass" section and not claimed.

---

## 3. Gates, in order, per date and snapshot

| # | gate | rule | source |
|---|---|---|---|
| G0a | same-day CME weekly expiry | a TBBO partition `options_tbbo_by_expiry/root=*/expiry=<settle_date>` exists for the Kalshi settlement date | `PIPELINE_CHOICES.md` Gate 0 |
| G0b | contract month | the option's underlying (from the CME definitions) equals the contract Kalshi names in `rules_primary` (fallbacks: `custom_strike.front_month_contract`, then Kalshi's 16th-of-month calendar); the source of the match is logged | `db_common.kalshi_settlements` |
| G0c | strikes | ≥ 8 OTM strikes with a two-sided quote in the 60 minutes before the snapshot, ≥ 3 per wing of the forward | `synth.realchain.run_one` |
| G0d | forward | intraday CL bars exist for the underlying around the snapshot (the `real` path); a date without them is **not attempted**, not failed, and is logged as such | `FINDINGS_REALCHAIN_V3.md` |
| G4 | split-half | the odd/even-strike posteriors agree on every bracket of the ladder, max\|z\| ≤ calibrated cutoff (2.65) | `synth.detector.split_half` |
| — | Act II | **reported, not gating**: max \|Act II − Act III\| over the ladder in cents, flag at 2.5¢ | `FINDINGS_ACTII_V2.md` |
| — | sampler | **reported, not gating**: bracket R̂ < 1.05 and bracket ESS ≥ 100; a chain failing this is marked and its brackets are excluded from the filter (§5) but kept in the gap tables | `FINDINGS_REALCHAIN_V4.md` §7 |

Per bracket, after the date clears:

**Interior-local-minimum rule (new, pre-stated).** On the posterior-mean density $\bar f(s)$ over the Act III grid,
an *interior local minimum* is a grid point $s^*$ that is a local minimum of $\bar f$ with a local maximum on each
side whose height is at least $0.02\,\max\bar f$, and with $\bar f(s^*) \le 0.98 \times \min(\text{peak}_L,\text{peak}_R)$
(a 2% dip, to ignore grid ripple). Its *trough region* is the contiguous interval around $s^*$ on which $\bar f$ lies
in the **lower half of the dip**, $\bar f < \bar f(s^*) + \tfrac12\,[\min(\text{peak}_L,\text{peak}_R) - \bar f(s^*)]$
(amended from "below 98% of the lower peak" before the first run, commit 2, because that version declared the
shoulders of both humps a trough on the unit test's planted bimodal; the blind spot is at the bottom of the dip).
**A bracket whose edges overlap any trough region is not traded.**
It stays in the gap tables, marked. The count removed is reported per snapshot. Rationale: the residual bimodal blind
spot has trough coverage 57% (`FINDINGS_SYNTHETIC_V2.md`), so a mid-density dip is wrong roughly two times in five.

**LOO proximity (reported risk factor, not a gate).** A strike flagged by leave-one-out (|r| > 3) that lies within
**$1.00** of either bracket edge — the two replicating strikes of that edge and their nearest neighbours — is
reported against the candidate trade as `loo_near_edge`. The count of filtered brackets carrying the flag is reported
and their P&L is shown separately. The $1.00 distance is fixed now.

---

## 4. The friction stack, per Kalshi contract ($1 notional), with the arithmetic

The filter and the P&L use **measured** CME half-spreads per trade; the fee parameters below are assumptions, named
so the operator can check them. The writeup's working figure of ~5¢ per contract round trip is **not** inherited;
the derivation is here and it comes out higher.

**Hedge structure (needed to put CME costs in Kalshi units).** A Kalshi bracket $[X, X+1)$ (Kalshi's
"$X.00 to $X.99", edges at $X-0.005$ and $X+0.995$) is replicated with CL weekly options on the $0.50 strike grid by
the *outer condor*

$$\Pi = C(X-0.5) - C(X) \;-\; C(X+1) + C(X+1.5),$$

which pays $0.50/bbl for $S_T \in [X, X+1]$, zero outside $[X-0.5, X+1.5]$, and ramps linearly on $[X-0.5, X]$ and
$[X+1, X+1.5]$. The ramps lie **outside** the bracket, so inside it the two legs cancel exactly and the gap is locked;
the residual is confined to the two half-dollar ramps, where the structure pays up to $0.50/bbl while Kalshi pays 0.
Per standard CL contract (1,000 bbl) the structure's maximum payoff is $500, so **one structure hedges 500 Kalshi
contracts**; on Micro WTI (100 bbl) it would hedge 50. The hedge ratio is therefore

$$n_{\text{structures}} = \frac{N_{\text{Kalshi}} \times \$1}{0.50\ \$/\text{bbl} \times \text{bbl per contract}}
= \frac{N_{\text{Kalshi}}}{500}\ (\text{CL}),\quad \frac{N_{\text{Kalshi}}}{50}\ (\text{MCO}),$$

one contract per leg per structure, four legs. This is the backtest's derivation; the operator intends to derive his
own, and the gap analysis of §5 does not depend on it. Alternatives considered and not used: centred $1-wide spreads
(a butterfly for a $1 bracket — no flat top, mismatch up to 0.5 *inside* the bracket); inner condor
$C(X)-C(X+0.5)-C(X+1)+C(X+1.5)$ (ramps inside the bracket, mismatch up to 1.0 at the lower edge). If a replicating
strike is not listed or not quoted two-sided in the window, the next listed strike outward is used and the wider ramp
is logged; if none is, the trade is **unavailable** and logged.

**Legs crossed.** Buying Kalshi (gap < 0) means selling $\Pi$: sell $C(X-0.5)$ at bid, buy $C(X)$ at ask, buy
$C(X+1)$ at ask, sell $C(X+1.5)$ at bid. Selling Kalshi (gap > 0) is the mirror. Four half-spreads are crossed either way.

**Stack, in Kalshi probability units (¢ per $1 contract):**

| component | formula | assumption / source | worked example |
|---|---|---|---|
| Kalshi fee (taker) | $0.07 \cdot P(1-P)$ per contract, $P$ = executable price; maker 0 | Kalshi's published general fee schedule (0.07 coefficient, rounded up to the cent per order) — **verify on the live schedule before trading** | $P=0.10$: 0.63¢; $P=0.50$: 1.75¢ |
| Kalshi spread | **0** in the stack: the gap is computed on the executable side, so the spread is already inside it | §5 | typical 1¢ wide on the moderate tail → 0.5¢ vs mid, reported |
| CME spread, 4 legs | $\sum_{\text{legs}} h_\ell / 0.50$, $h_\ell$ = measured half-spread ($/bbl) of leg $\ell$ at the snapshot | TBBO last quote in the window; measured per trade | $h=\$0.01$ each: $4 \times 0.01/0.5 = $ **8.0¢**; $h=\$0.005$: 4.0¢ |
| CME fees, entry | $4 \times f_{\text{leg}} / 500$ | $f_{\text{leg}} = \$1.50$ exchange+clearing (NYMEX, non-member, Globex) $+ \$0.02$ NFA $+ \$0.85$ commission $= \$2.37$ — **assumption** | $4 \times 2.37 / 500 = $ **1.90¢** |
| CME fees, exit | $x_{\text{exit}} \times 4 \times f_{\text{leg}} / 500$, legs exercised/assigned at expiry; $x_{\text{exit}} = 0.5$ (on average half the legs finish in the money) | same $f_{\text{leg}}$; CME has no separate exercise fee, brokers may — **assumption** | 0.95¢ |
| **total** | | | **$P=0.10$, $h=1$¢: 11.5¢; $h=0.5$¢: 7.5¢** |

So the honest working figure for a standard-CL hedge is **7–12¢ per Kalshi contract**, dominated by the CME spread
expressed in digital units (a 1¢/bbl half-spread on a $0.50-wide spread is 2% of the digital per leg). On Micro
(if a weekly existed) the fee term would be $4 \times \$0.77 / 50 = 6.2¢$ before spreads. **This is a foundational
item that looks wrong in the writeup**: the ~5¢ figure appears unreachable with four option legs on a $0.50 grid.
The filter uses the measured number per trade, so the result is not hostage to this paragraph, but the magnitude
of edge needed is roughly double what the writeup implies.

Parameters, so they can be changed by the operator and the whole report re-rendered without touching logic:
`KALSHI_FEE_COEF = 0.07`, `CME_FEE_PER_LEG = 2.37`, `CME_EXIT_FRACTION = 0.5`, `SPREAD_WIDTH = 0.50`,
`BBL_PER_CONTRACT = {CL: 1000, MCO: 100}`.

---

## 5. The comparison and the filter

**Kalshi price at the snapshot.** The stored 1-minute candle whose `end_period_ts` equals the snapshot minute (a bar
ending at $T$ covers $(T-60s, T]$; `db_common.kalshi_bar_end`). If that bar is absent, the latest bar ending within
the preceding **10 minutes**; otherwise the bracket has **no executable price** at that snapshot and is logged.
Executable: **buy at `yes_ask_close`, sell at `yes_bid_close`**, in probability units. Never the `price` field, never a
mid, for any gap or P&L. A side that is missing or at 0¢/100¢ is unavailable; the trade in that direction is logged
as unavailable, not priced.

**Model probability.** For each posterior draw $\theta^{(m)}$ (all 1,600 NUTS draws of the martingale-constrained
fit), $p^{(m)}_j = \int_{a_j}^{b_j} f(s;\theta^{(m)})\,ds$ over the bracket's **exact** edges taken from the Kalshi
market record: lower edge `floor_strike` − 0.005, upper edge `cap_strike` + 0.005 for "between" brackets; the open
tails use one edge and $\pm\infty$ (the Act III grid edge; edge mass is checked). The edge convention is verified
against `yes_sub_title` at run time and any disagreement is logged and resolved in favour of the sub-title text, with
the rule recorded.

**Gap.** $g_j = p^{\text{mkt}}_j - \bar p^{\mathbb{Q}}_j$ where $p^{\text{mkt}}_j$ is the executable price on the side
the trade would hit, chosen by the sign of the *mid-based* gap first (so the side is determined before the gap is
computed, not after), and $\bar p^{\mathbb{Q}}_j$ the posterior mean. **Band** $w_j$ = width of the 90% posterior
interval of $p^{(m)}_j$. Both are reported for every bracket with a two-sided Kalshi quote, filtered or not.

**Stage 18.** Per draw $m$, per date and snapshot, OLS of $\text{logit}(p^{\text{mkt,mid}}_j)$ on
$\text{logit}(p^{(m)}_j)$ and $m_j = (\text{bracket midpoint} - F_0)$ in dollars, over brackets with a two-sided
Kalshi quote whose mid lies in $[1¢, 99¢]$; $p^{(m)}_j$ clipped at $10^{-3}$. Pooled version: per-date intercepts,
common $b$ and $c$. Reported: posterior 5/50/95% of $(a, b, c)$ per date and pooled. Kalshi's **mid** is used here
and only here, because Stage 18 characterises the venue's pricing, not a trade; stated so it is not mistaken for a
mid-based edge.

**Stage 19 filter.** Bracket $j$ at (date, snapshot) is a *candidate trade* iff all of:

1. the date/snapshot clears G0a–G0d and G4, and its sampler check (bracket R̂ < 1.05, ESS ≥ 100) passes;
2. $|g_j| > w_j + \text{friction}_j$, friction measured as in §4;
3. the executable Kalshi price on the needed side is in **[2¢, 98¢]**;
4. $w_j \le 20¢$ (a wider band is an uninformative extraction, not a trade);
5. the bracket does not overlap an interior trough region (§3);
6. all four replicating legs have a two-sided TBBO quote in the 60-minute window.

No depth threshold: the stored data (1-minute candles with per-minute volume and open interest) cannot establish
resting depth, so feasibility at size is reported as **unknown from stored data** with the bar's volume and the
market's open interest as context, never assumed. Brackets failing 2–6 are logged with the failing condition, so the
signal record accumulates whether or not the trade would have been taken.

---

## 6. Sizing and P&L

**Size.** For every KXWTIW date the same-day expiry is a standard CL weekly (ML/WL/LO); MCO expires monthly only. So
the **applicable size is 500 Kalshi contracts per structure** on every weekly date; 50 is reported as the size the
depth scan cleared but is **not available** on these dates. Both are tabulated; the shortfall is the headline of the
sizing section. A date on which the Kalshi settlement coincides with an MCO monthly expiry would be the exception
and is flagged if it occurs.

**P&L per candidate, held to settlement (Rule 1), per Kalshi contract:**

- Kalshi leg: $\pm(\mathbb{1}\{\text{settled yes}\} - P_{\text{exec}})$ from the market's `result` (cross-checked
  against `expiration_value` and the edges; a disagreement is logged and the market excluded);
- CME leg: $\mp(\Pi_{\text{settle}} - \Pi_{\text{exec}})/0.50$ with $\Pi_{\text{settle}}$ the structure's intrinsic
  value at the **NYMEX** settlement of the underlying on the settlement date (`futures_stats`, stat_type 3), and
  $\Pi_{\text{exec}}$ the executable structure price from the four crossed legs;
- minus the friction fees of §4 (spreads are already inside the executable prices).

The ICE/NYMEX basis enters through the two settlements being different numbers; on KXWTIW it is zero to the cent on
33 of 34 dates (`FINDINGS_BASIS.md`). **Ramp residual (Rule 2):** for each candidate the posterior probability that
settlement lands in a ramp and the posterior expected ramp loss are reported next to the locked gap, and the
worst case (settlement at the inner end of a ramp: $1 per Kalshi contract against the position) is stated. Realised
P&L is reported in dollars at 500 and 50 contracts and per contract, by date, with the three best dates removed.

---

## 7. Exclusions and the denominator

Every (date, snapshot) gets exactly one row in `synth/results_backtest/denominator.csv` with one of these outcomes,
and every bracket of a cleared date gets a row in `brackets.csv` with its own status. No date is dropped for any
reason not in this list.

| outcome | meaning |
|---|---|
| `no_kalshi_event` | no KXWTIW event with a settlement value for the date |
| `g0a_no_same_day_expiry` | no CME weekly option expiring that day on disk |
| `g0b_contract_mismatch` | option underlying ≠ Kalshi's named contract |
| `g0c_too_few_strikes` | < 8 OTM strikes or < 3 per wing in the window |
| `g0d_no_intraday_bars` | **not attempted**: the real path is unavailable |
| `extraction_error` | **failed**: the job raised; traceback kept |
| `g4_split_half_fired` | the chain is internally inconsistent; brackets kept in gap tables, none traded |
| `sampler_fail` | bracket R̂/ESS outside the check; brackets kept in gap tables, none traded |
| `no_kalshi_candles` | the event has no candle within 10 minutes of the snapshot on any bracket |
| `cleared` | enters §5 |

Bracket statuses: `traded`, `no_two_sided_kalshi_quote`, `date_gated` (the date's split-half or sampler check
failed; the bracket is in the gap tables, not tradeable), `price_out_of_range` (covers a missing or 0¢/100¢ side),
`band_too_wide`, `interior_minimum`, `cme_leg_unquoted`, `below_threshold` (|g| ≤ band + friction, the logged signal).
A bracket with no `result` settles by `expiration_value` against its edges and says so.

**Artifact checks (§6 of the brief), all reported before the verdict:** (i) gap vs residual forward error — the
posterior mean of $F$ minus the futures level, and the correlation of per-date mean gap with it; (ii) asynchronicity —
gaps at T-1d vs T-4h on the same bracket, and gaps on dates where the real path was reconstructed from fewer bars;
(iii) one-snapshot systematic error — $(a,b,c)$ by snapshot; (iv) extractor-independence — the chain's own
condor-implied digital (mid) against $\bar p^{\mathbb{Q}}$ and against Kalshi, so a Kalshi-vs-CME disagreement that
survives without the extractor is separated from one that needs it. June 15 (−$4.70, a KXWTI date) is not a KXWTIW
date; if the KXWTI arm runs, that date's rows are flagged `basis_anomaly`.

---

## 8. Run discipline

Resumable: one checkpoint per completed (date, snapshot) job, atomic write, `failed` distinguished from
`not_attempted`; a re-run redoes failed jobs and skips completed ones. Timestamped log. BLAS pinned to one thread
per worker. No network, no spend: every input is on disk. Both test suites stay green; the new code gets its own
tests on synthetic inputs (edge parsing, condor payoff and hedge ratio, the interior-minimum rule, the fee
arithmetic, the filter) that never touch the Kalshi store.

**Order of operations, verifiable from git:** this file is committed first; `synth/backtest.py` is committed
after it; the first Kalshi price is read by that module's first run, logged with a timestamp in
`synth/results_backtest/backtest.log`.
