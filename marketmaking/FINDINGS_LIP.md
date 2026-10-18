# FINDINGS_LIP — the Liquidity Incentive Program, measured

**Verdict: `period_reward` is in centi-cents, and the money is real but small and
pointed at the wrong series. On the WTI ladders this project targets it is
meaningful-but-secondary at best; on most of them it does not exist at all. The
one ladder series where LIP pays serious money is `KXAAAGASM` — which is also the
only series that charges a maker fee and has the worst microstructure in §5.**

Keyless public API only. No authenticated call, no order, no trading endpoint.

---

## 1. The unit — resolved, authoritative

`https://docs.kalshi.com/openapi.yaml`, schema `IncentiveProgram`:

```yaml
period_reward:
  type: integer
  format: int64
  description: Total reward for the period in centi-cents
```

**1 centi-cent = $0.0001.** So `period_reward: 3000000` = **$300.00** for the period.

This is a primary-source definition in the live spec, not an inference.
Confidence: **high.** It also settles open item #3 in `FINDINGS_PHASE0.md`.

The practical range observed live is **$10 to $600 per market per period**, modal
**$50–$100**. The brief's remembered "$1–$1,000 per market per day" was the right
order of magnitude but wrong on the period: most programs are **not** daily.

## 2. The full record shape

`GET https://api.elections.kalshi.com/trade-api/v2/incentive_programs` (keyless, HTTP 200):

```json
{"discount_factor_bps":5000, "end_date":"2026-12-07T15:00:00Z",
 "incentive_description":"series_lip", "incentive_type":"liquidity",
 "market_ticker":"KXAAAGASM-26DEC31-2.90", "paid_out":false,
 "period_reward":3000000, "start_date":"2026-11-30T15:00:00Z",
 "target_size_fp":"1000.00"}
```

| field | observed | reading |
|---|---|---|
| `incentive_type` | `liquidity` (enum also has `volume`, `margin_maker_volume`, `margin_taker_volume`) | LIP is the liquidity variant |
| `incentive_description` | `series_lip` on essentially all rows | confirms "series LIP" |
| `period_reward` | $10–$600, modal $50–$100 | **centi-cents**, per market, per period |
| `target_size_fp` | `"1000.00"` on **every** row sampled | the size the reward is scaled against |
| `discount_factor_bps` | `5000` on **every** row sampled | 50% |
| `max_reward_per_account` | `null` on every row sampled | no per-account cap published |
| period length | mostly 0-day (intraday) and 7-day | **not** uniformly daily |

## 3. Coverage — this is the finding that matters

200,000 unique programs retrieved (zero duplicate `id`s), spanning **1,970
distinct series**. Against §5's target ladders:

| series | LIP markets | $/period | modal $/market |
|---|---|---|---|
| `KXAAAGASM` | 138 | **$39,000.00** | $300.00 |
| `KXAAAGASW` | 291 | **$29,100.00** | $100.00 |
| `KXWTIMAX` | 40 | $3,200.00 | $60.00 |
| `KXWTIMIN` | 40 | $3,200.00 | $60.00 |
| `KXNGASMAX` | 7 | $1,050.00 | $150.00 |
| `KXWTI` | 0 | — | not found |
| `KXWTIW` | 0 | — | not found |
| `KXBRENTD` | 0 | — | not found |
| `KXGOLDD` / `KXGOLDMON` / `KXRHGOLD` | 0 | — | not found |
| `KXSILVERD` | 0 | — | not found |
| `KXSOLAR` / `KXOILRIGS` / `KXBARRELS` | 0 | — | not found |

**`KXWTI` and `KXWTIW` — the core WTI ladders — carry no LIP in the sample.** The
WTI exposure that does exist is on the MAX/MIN variants at $60 per market.

### The irony worth naming

The LIP money concentrates on `KXAAAGASM` and `KXAAAGASW`. `KXAAAGASM` is
simultaneously:

- the **only one of 52 ladder series that charges a maker fee** (0.0175),
- the **worst maker microstructure in §5** (43.06% improvable vs 58.50% elsewhere,
  4.02c spread vs 5.23c),
- and the **largest LIP payer** among the ladders at $39,000/period.

That is a coherent, consistent picture rather than three coincidences: **Kalshi
pays most where quoting is least attractive.** It is the same revealed-preference
argument as the designated-provider subsidy, visible a second time in independent
data. The size of the inducement is a measure of how unattractive the book is.

## 4. Worked magnitude — a retail quoter on a WTI ladder

Assumptions, all stated because several are unverified:

- Target series `KXWTIMAX`: 40 incentivised markets, `period_reward` $60 each.
- `target_size_fp` = 1000 contracts is the size the pool is scaled against.
- Reward is split **pro-rata by qualifying resting size** (see §5 — *not confirmed*).
- We rest 100 contracts per market — 10% of target size — across 10 markets.

```
per market : $60 × (100 / 1000)            = $6.00  per period
10 markets : $6.00 × 10                    = $60.00 per period
```

Against the project's own §5 numbers: a 5.23c mean spread with 1.86c of room. One
round-trip on a single 100-lot at 1c captured is $1.00. **The entire LIP accrual
across ten markets is worth roughly 60 such round-trips per period** — real, but
not a business.

On `KXAAAGASM` the same posture scores $300 × 0.1 × 138 markets ≈ $4,140/period —
which *is* material. But that is the fee-paying, worst-microstructure series, and
the one I recommend excluding from the quoting universe.

## 5. Verdict per question

| # | Question | Answer | Confidence |
|---|---|---|---|
| 1 | Unit of `period_reward` | **Centi-cents** ($0.0001). Spec-defined | High |
| 2 | Allocation formula | **Not published.** `target_size_fp` + `discount_factor_bps: 5000` imply pro-rata scaling against a 1,000-contract target with a 50% factor, but the arithmetic is not stated anywhere public | **Low — do not model** |
| 3 | Qualification requirements | **Not published** in the API or OpenAPI spec. No minimum spread, uptime or resting-time field exists on the record | Low |
| 4 | Live values on commodity ladders | Measured, §3 above | High |
| 5 | Retail eligible without agreement | `incentive_description: series_lip` and no agreement field; consistent with no opt-in, **but not positively confirmed** | Medium |
| 6 | Cash vs trading credit | Not determinable from public sources | None |

**Verdict line: (b) meaningful but secondary — and on `KXWTI`/`KXWTIW`
specifically, (a) non-existent.** It is not the adverse-selection-immune revenue
line we hoped for, because it is largely absent from the books we want to quote.

## 6. What I could not determine

1. **The allocation formula.** Decisive for any P&L line. The $6.00 figure above
   assumes linear pro-rata against `target_size_fp` and **ignores**
   `discount_factor_bps` because its role is unstated. If the 50% factor applies
   to the payout, halve every number. *Resolves by:* observing one settled
   accrual on a funded account, or a Kalshi LIP terms page read in a real browser.
2. **Qualification rules.** No minimum spread/uptime/resting-time is exposed. It
   is implausible that none exists — an exchange paying for depth does not pay for
   a 1-lot parked at 1c. *Resolves by:* the LIP terms document (`kalshi.com`, bot-blocked).
3. **Whether the list is complete.** Every request returned exactly `limit` rows
   (1,000 → 1,000; 200,000 → 200,000) with `cursor: null` and no duplicates, so
   **I never reached the end of the set.** The "not found" rows in §3 are therefore
   *absence in a 200k-program sample, not proven absence.* The endpoint also
   **ignores the `series_ticker` and `market_ticker` filters** — both return the
   same unfiltered head — so targeted confirmation is not currently possible.
   *Resolves by:* a working server-side filter, or paging to genuine exhaustion.
4. **Payment form and tax treatment.** Not public.

**Caveat on item 3, stated plainly:** the headline coverage claim is the weakest
part of this document. The unit (§1) is solid; the coverage table is a large
sample that the API will not let me verify as exhaustive.

---

*Method note: `kalshi.com` remains behind a Vercel bot checkpoint returning 429 to
every non-browser client, which is why the terms documents above are unresolved.
`docs.kalshi.com` and the keyless API are unaffected and were used throughout.*
