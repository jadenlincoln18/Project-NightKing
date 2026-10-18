# Re-examine the backtest: threshold markets, leg count, and the friction measurement

`FINDINGS_BACKTEST.md` returned STRUCTURE, NOT AN EDGE. Two specific things in
it need checking before that verdict stands, and one of them traces to an error
in a previous brief.

**This is error-correction, not result-shopping.** If both checks come back
clean, the null stands and we write it up as final. Do not tune thresholds, do
not relax gates, do not revisit the extractor. The protocol in
`BACKTEST_PROTOCOL.md` is still binding — any amendment is a documented
amendment with its reason, committed before the re-run.

**Read first:** `FINDINGS_BACKTEST.md`, `BACKTEST_PROTOCOL.md` §4 (friction),
and the backtest implementation's replication construction.

---

## The correction that prompts this

A previous brief stated that Kalshi's "Above $X" threshold markets are either
hourly or Pyth-settled, and therefore unhedgeable. **That is wrong.**

`KXWTI` — the daily series, 46 cleared dates at T-4h in the backtest — is a
threshold ladder, ICE-settled. Its market rules read:

> Resolves Yes if the daily settlement price for WTI crude oil (November 2026
> contract) on October 05, 2026 is above 90.99 USD/Bbl. **Outcome verified from ICE.**

Two consequences.

**Leg count.** A *bracket* digital ("between $87 and $88") is
$D(a) - D(b)$ — **four** option legs. A *threshold* digital ("above $87") is
$D(a)$ alone — **two** legs. Friction scales directly with leg count, so a
threshold market should cost roughly half what a bracket market costs.

**Roll rule.** The same rules page says settlement rolls to the next contract
*"2 business days before the current contract's last trading day."* Project docs
record this as "the 16th of the month." Check which the backtest's contract
matching actually used, and correct the docs either way.

---

## Task A — leg-count audit (free, do first)

**Read the backtest's replication construction and establish, for each series,
how many legs it priced.**

- Did `KXWTI` get a two-leg threshold replication, or a four-leg bracket one?
- Did the friction calculation in `BACKTEST_PROTOCOL.md` §4 distinguish the two
  market types at all?
- If the daily arm was charged four legs, **its friction is double what it
  should be and those 46 dates were never properly tested.**

Report what you find plainly, including "it was handled correctly" if that is
the answer.

If it was wrong: re-run the daily arm with the correct construction, before/after
on every table. Treat it as a bug fix, not a new experiment — same protocol, same
thresholds, same gates.

---

## Task B — the friction measurement

`FINDINGS_BACKTEST.md` reports CME legs at **4–5¢/bbl half-spread**, and notes
that **only two brackets in the entire sample had every leg quoted within five
minutes of the snapshot.** 201 brackets at T-1d died on `cme_leg_unquoted`.

That is a very thin basis for the number that decided the verdict.

**Why it is likely biased.** TBBO samples in *trade* space — a strike gets a
recorded quote only when it trades. So the measured spreads come from whichever
legs happened to print, and strikes with a live two-sided market that simply
did not trade contribute nothing. The full book is not in the data.

**Scale check.** CL options tick at $0.01/bbl, so a 4–5¢ half-spread is an
**8–10 tick wide market**. For liquid near-ATM strikes on a front weekly, that
is implausibly wide — 1–2 ticks is the usual order. The number should be
treated as suspect until measured properly.

**What it does to the arithmetic:**

$$\text{friction per Kalshi dollar} = \frac{n_{\text{legs}} \times \text{half-spread}}{h}$$

| legs | half-spread | ramp $h$ | friction |
|---|---|---|---|
| 4 (bracket) | 4.5¢ | $0.50 | **36¢** |
| 2 (threshold) | 4.5¢ | $0.50 | 18¢ |
| 2 (threshold) | 1.0¢ | $0.50 | **4¢** |

Nine-fold between the first and last row, from two inputs that are both in
question. Against measured per-bracket gap standard deviations of 0.9–5.0¢,
4¢ friction and 36¢ friction are different worlds.

### How to measure it properly

**Option 1 — `bbo-1m` on the option chain, scoped.** The actual quote every
minute rather than trade-sampled. `db_scope.py` priced `bbo-1m` at **$11.11 per
trading day** for the whole parent chain; scoped to the relevant expiry and the
hour around each snapshot it should be far less.

**Cost-preflight with `metadata.get_cost()` before any billable call, report
the quote, and wait for approval.** Cap $50. Dry-run by default.

**Option 2 — operator-measured, free.** The operator has a tastytrade account
and can read the live CL options chain directly. If you can specify exactly what
to record — which strikes, which expiry, which fields — he can collect it by
hand. Say what you need.

Do whichever gives a defensible number. **Report the measured half-spread
distribution by strike moneyness**, since the legs you actually trade are not
the ones that trade most.

---

## Task C — restate the comparison in probability space

The method already compares probabilities — a Kalshi contract at 11¢ *is* an
11% implied probability, and the density integrates to 0.109. But
`FINDINGS_BACKTEST.md` writes everything in cents, which reads as a price
comparison and obscures what is being done.

Restate it so the chain of reasoning is visible per bracket:

1. **Kalshi implied probability** (executable, on the side the trade would hit)
2. **Density implied probability** (posterior mean, with the band)
3. **Disagreement in probability points**
4. **The hedge**: which legs, what ratio, how exposure cancels — with the
   derivation shown
5. **Friction in probability points**, so it is commensurate with step 3
6. **Net**, and whether it is positive

Same numbers, but the pricing becomes a consequence of the probability
disagreement rather than the thing being compared. Add it to the findings as its
own table.

---

## What would and would not change the verdict

**Would:** the daily arm was charged four legs when it should have been two,
*and* real half-spreads come in near 1¢/bbl. Then threshold markets have ~4¢
friction against gaps with a 0.9–5.0¢ spread, and some brackets clear. That
would mean **the threshold strategy was never actually tested**, which is a gap
in the work rather than a reason to doubt the result.

**Would not:** better friction data on the *bracket* arm. Four legs at even 1¢
is 8¢ against a 1.1¢ mean gap. The KXWTIW result is robust.

**Also would not:** the body agreement. Both venues anchor to the same futures
settlement, so tight agreement near the money is what efficiency predicts, and
Kalshi never enters the extractor so there is no path for contamination. The
deviation lives in the tails and Stage 18 already measured it at b = 0.69.

---

## Foundational

- **No tuning.** Thresholds, gates, extractor, prior — all frozen. If something
  looks like it needs changing, write it down and report the unchanged result.
- **Protocol amendments are documented and committed before the re-run**, with
  the reason, as the existing amendments were.
- **Report the denominator** again. If the leg-count fix changes which brackets
  clear, show what changed and why.
- **If the checks come back clean, say so and let the null stand.** "The daily
  arm was handled correctly and spreads really are 4¢" is the most useful
  possible answer if it is true.

## Your judgement

- Whether the `bbo-1m` pull is worth its cost given what Task A finds — if the
  leg count was already right, the friction measurement matters less
- Scoping for that pull
- How to present the probability-space table
- Whether any other series in the store is an ICE-settled threshold ladder that
  was wrongly excluded on the same bad assumption — worth a sweep of
  `settlement_sources` and ladder type together

## Deliverables

1. `FINDINGS_LEGCOUNT.md` — what the backtest actually priced, per series, and
   the corrected daily-arm results if it was wrong
2. A friction measurement with a stated basis, replacing the two-bracket estimate
3. `FINDINGS_BACKTEST_V2.md` — only if something changed; otherwise an amendment
   note to V1 saying the checks were run and the verdict stands
4. Doc corrections: the threshold-markets error and the roll rule, in
   `NightKing/PIPELINE_CHOICES.md`, `PIPELINE_MAP.md` and the root writeup

## Environment

macOS, Python 3.9-compatible. `data/` and `data_cme/` read-only except a scoped
Databento pull if approved. Both test suites stay green. 48 knots, 1¢ tick
floor, extractor frozen.
