# COVERAGE — which ladders nobody is paid to quote

**Inputs are dated snapshots, and every claim below is relative to them.**
Professional list: `lpp/lpp_2026-10-18.json` (scraped 2026-10-18 from
help.kalshi.com/en/articles/15410219, 52 rows, 167 named tickers). Retail list:
`coverage/lip_2026-10-18.json` (`/incentive_programs`, same date). Market
statistics: `data/_import/waves_data_discovery_*.parquet`, a point-in-time
snapshot taken **2026-10-06**. The LPP list changes — daily temperature was on
the June version and is not on this one — so "uncovered" without a snapshot date
is a meaningless statement.

Reconciliation: 801,032 events → 87,457 ladder events → **1,859 ladder series in,
1,859 out**. 4,511,998 ladder markets, 58,322 active, 43,858 active and quoted.

| status | series | tight-spread volume |
|---|---|---|
| uncovered | 1,266 | $3.048B |
| covered | 565 | $0.597B |
| unknown | 28 | $2.582B |

---

## 1. The headline is not the recommendation

Ranked by tight-spread volume, the uncovered set is **92.5% sports**:

| # | series | cat | active | vol 365d | tight-spread vol | snap spread | tight≤2c |
|---|---|---|---|---|---|---|---|
| 1 | KXMLBTOTAL | Sports | 32 | $1.050B | $853.0M | 1.5c | 81% |
| 2 | KXMLBSPREAD | Sports | 27 | $573.1M | $541.2M | 1.0c | 94% |
| 3 | KXNFLSPREAD | Sports | 385 | $447.3M | $351.6M | 2.0c | 79% |
| 4 | KXNFLTOTAL | Sports | 273 | $265.5M | $186.2M | 2.0c | 70% |
| 5 | KXNCAAFSPREAD | Sports | 1686 | $577.9M | $155.3M | 4.0c | 27% |
| 6 | KXWNBATOTAL | Sports | 18 | $129.8M | $122.6M | 1.0c | 94% |
| 7 | KXWNBASPREAD | Sports | 18 | $103.3M | $103.3M | 1.0c | 100% |
| 8 | KXNCAAFTOTAL | Sports | 1102 | $308.4M | $76.7M | 4.0c | 25% |
| 9 | KXEPLTOTAL | Sports | 60 | $46.8M | $46.8M | 1.0c | 100% |
| 10 | KXLALIGATOTAL | Sports | 60 | $61.0M | $46.8M | 2.0c | 77% |
| 11 | KXBTCY | Crypto | 28 | $40.0M | $40.0M | 0.1c | 100% |
| 12 | **KXHIGHLAX** | **Weather** | 12 | $39.4M | $39.4M | 1.0c | 100% |
| 13 | KXUEFANLTOTAL | Sports | 60 | $34.7M | $34.7M | 1.0c | 100% |
| 14 | KXMLBKS | Sports | 48 | $43.4M | $26.6M | 2.0c | 61% |
| 15 | KXMLSTOTAL | Sports | 96 | $53.6M | $20.1M | 3.0c | 38% |

Uncovered tight-spread volume by category: Sports $2.818B (92.5%), Weather
$124.0M (4.1%), Crypto $72.8M (2.4%), Economics $14.4M (0.5%), Financials
$11.0M (0.4%).

Sports clears every bar in `PROTOCOL.md` §1A by a wide margin — 55× the
commodity comparison group. **It is still the wrong universe, for a reason the
bars did not encode.** See §4.

---

## 2. Lead A — daily city temperature: CONFIRMED, and it is the real result

The June LPP list carried daily city high/low temperature. The 2026-10-18
snapshot carries **only hourly** temperature: `KXTEMPMIAH`, `KXTEMPNYCH`,
`KXTEMPLAH`, `KXTEMPCHIH`. The daily ladders are gone from it.

They did not lose volume when they lost the provider. They carry **more** than
the hourly ladders that kept it:

| series | active | vol 365d | tight-spread vol | snap spread | tight≤2c | LPP | LIP |
|---|---|---|---|---|---|---|---|
| KXHIGHLAX | 12 | $39.4M | $39.4M | 1.0c | 100% | no | no |
| KXHIGHNY | 12 | $11.8M | $11.8M | 1.0c | 100% | no | no |
| KXHIGHMIA | 12 | $11.7M | $11.7M | 1.0c | 100% | no | no |
| KXHIGHCHI | 12 | $7.1M | $7.1M | 1.0c | 100% | no | no |
| KXHIGHAUS | 12 | $4.9M | $4.9M | 1.0c | 100% | no | no |
| KXHIGHTSFO | 12 | $4.6M | $4.6M | 1.0c | 100% | no | no |
| KXHIGHTSEA | 12 | $4.2M | $4.2M | 1.0c | 100% | no | no |
| KXHIGHTDAL | 12 | $3.9M | $3.9M | 1.0c | 100% | no | no |
| KXHIGHTATL | 12 | $3.7M | $3.7M | 1.0c | 100% | no | no |
| KXHIGHTPHX | 12 | $5.3M | $3.5M | 1.5c | 67% | no | no |
| *(hourly, for contrast)* | | | | | | | |
| KXTEMPMIAH | 10 | $12.3M | $12.3M | 2.0c | 100% | **yes** | **yes, $5,990/period** |

**51 live uncovered daily-temperature series, $136.5M traded in 365 days,
$123.7M of it at a snapshot spread ≤2c.** Against the pre-registered bars:
breadth 51 (bar ≥8), depth 2.42× the commodity comparison group (bar ≥0.50),
top-series concentration 31.9% (bar ≤40%). All three pass.

This is the configuration the project has been looking for: established retail
volume, a tight book, a vacated professional quote, and no retail subsidy either.

## 3. Lead B — economic data: the premise is wrong, and the lead is a bust

Economic ladders are **not** absent from coverage. Of 282 economics series with
volume, **158 are covered** — including the headline inflation ladders:

| series | active | vol 365d | tight-spread vol | snap spread | status |
|---|---|---|---|---|---|
| KXCPIYOY | 63 | $3.77M | $2.20M | 2.0c | **covered** |
| KXCPI | 44 | $2.48M | $1.10M | 3.0c | **covered** |
| KXRATECUTCOUNT | 21 | $10.3M | $10.3M | 0.2c | uncovered (single-shot) |
| KXU3 | 28 | $1.91M | $1.03M | 2.0c | uncovered |
| KXFED | 247 | $3.85M | $0.30M | **96.0c** | uncovered |

All uncovered economics together is **$14.4M of tight-spread volume — 0.5% of
the uncovered set**, against $123.7M for daily temperature. It is an order of
magnitude too small to be a universe.

`KXFED` is the instructive one: 247 active markets, and a **96c median spread**
with 7.9% of markets inside 2c. That is what an uncovered economic ladder
actually looks like, and it is the structural point. These resolve on scheduled
discrete releases. Between releases there is **no continuously-traded underlying
for a density fitter to fit against** — the information arrives in a step at a
pre-announced timestamp, and the rest of the time the ladder is a static bet. The
`wti_arb` extractor needs a continuous reference process; here there is none.
Uncovered, and correctly so. **Recommend dropping economics entirely.**

*Classification bug, flagged not fixed:* `KXGOVBAL` and `KXGDPNOM` (category
Economics) were matched to the prose row "Commodities 15min markets" and tagged
`unknown`. That match is wrong. It errs conservative so it changes no
conclusion, but the prose matcher needs a category guard before reuse.

---

## 4. Why sports wins the table and should still lose the decision

**`PROTOCOL.md` §1A pre-registered three bars — breadth, depth, concentration —
before this table existed. Sports passes all three. I am adding a fourth
criterion after seeing the data, and saying so plainly rather than quietly
rewriting the bar.**

The addition is legitimate under the selection rule only because of what it is
*not*: it uses no fit residual, no improvable fraction, no edge, no simulated
fill, no P&L. It is a structural fact about where a price comes from, knowable
without running the fitter at all. Under the rule in §1A — coverage, volume,
spread and structure may inform selection; outcomes may not — it is admissible.
It is still a post-hoc addition and the reader should discount it accordingly.

**The criterion: is there a thicker external venue that already sets this price?**

This is the generalised lesson from the NightKing autopsy (`_audit/NIGHTKING_AUTOPSY.md`,
2026-10-04), written two weeks before this table: *ask who sets the price on the
thinner venue, and whether they are looking at the thicker one.* Cross-venue
NightKing died because Kalshi's commodity ladder was not an independent venue —
it was derived from the CME chain by makers who quoted both.

Sports ladders are the same shape, more so. MLB and NFL spreads and totals are
quoted continuously by a global sportsbook market with vastly more capital,
better data and a decades-old pricing infrastructure. The most likely reason
Kalshi pays nobody to quote `KXMLBTOTAL` is **not** that the book is unattended —
it is that the price is free to obtain elsewhere, so arbitrageurs quote it
unpaid. On that reading, uncovered-and-tight is evidence of *maximum* competition,
not absence of it. We would be the least-informed participant in the book.

Daily temperature has no such venue. CME weather futures exist but are
monthly-aggregate HDD/CDD contracts, illiquid, and not a price for "LA high
tomorrow". The price-setting input is public NWS/NOAA forecast output, and
turning an ensemble forecast into a bracket density is modelling work — exactly
the work the extractor does. That is where a fitter can plausibly know something
the quote does not.

**This is a hypothesis, not a measurement, and phase 1 can test it with no
external data.** Decompose bracket repricing into a ladder-wide common-mode shift
(an external line moving) and idiosyncratic per-bracket deviation (the noise the
thesis harvests). If a universe's repricing is almost entirely common-mode, there
is nothing for the fitter to work on regardless of how tight the book looks.
Pre-registered as a phase-1 cut in `PROTOCOL.md`.

---

## 5. Limitations — three of them are serious

**(a) The LIP sweep did not terminate.** `/incentive_programs` ignores series
filters and never returns a terminating cursor. The snapshot behind this document
is 500 pages: 100,000 program records, **0.0% duplicates**, 85,177 distinct
market tickers, 1,135 distinct series — still producing entirely fresh records
when it hit the cap. It is therefore **not exhaustive**, and `lip_active=false`
is an *absence of observation, not an observation of absence*. A 3,000-page
re-sweep is running; until it converges, every "uncovered" tag is provisional on
the retail channel. `KXTEMPMIAH` was found in the sweep and the `KXHIGH*` series
were not, which is weak supporting evidence for lead A, not proof.

**(b) The snapshot spread is biased tight by ~2c.** Validated against measured
minute-grid data (`ladder_results_summary.parquet`, 77–78 comparable series):
Spearman 0.69, Pearson 0.48, **median bias −2.08c**, median absolute error 3.44c.
The one-observation snapshot systematically reports a *tighter* book than minute
sampling measures, so `tight_share_2c` is **inflated** and the "1.0c, 100% tight"
weather rows should be read as "ranks near the top", not "is one cent wide".
Rank order survives; absolute level does not. Worse, the validation set is
commodity-heavy, so the bias is not established to transfer to weather or sports
at all. **Ranking is usable; levels are not. Phase 1 measures the real spread.**

**(c) The `unknown` set is larger than the covered set in volume.** 28 series
hold $2.582B of tight-spread volume, dominated by `KXBTCD` at $2.466B — crypto
daily, matching the prose row "Crypto Hourly & Daily" which names no tickers.
These are deliberately not promoted to uncovered (§1A), and a single unresolvable
help-centre line is therefore sitting on 41% of all tight-spread volume in the
census. If crypto daily ever matters, resolving that row is worth a direct
question to Kalshi.

Lesser: market statistics are a 2026-10-06 point-in-time snapshot; `volume` is
lifetime-per-market; `yes_bid`/`yes_ask` is a single observation, not a series.

---

## 6. Recommendation

**Primary universe: the 51 live uncovered daily city temperature ladders.**
They pass all three pre-registered bars, they are the only category where a
designated provider demonstrably *left* a book that kept its volume, and they
have no thicker external venue setting the price.

**Comparison group: the commodity ladders** (99 census series from the collected
set, $51.2M tight-spread volume, 62 covered) — retained exactly as specified, as
the subsidised-competitor control.

**Sports: collect, do not quote.** 515 series and $2.818B of tight-spread volume
is too much to discard on an untested hypothesis, and it is the ideal negative
control for the common-mode test in §4. Collection is cheap and commits nothing.

**Economics: drop.** Half of it is already covered, the uncovered remainder is
0.5% of the set, and discrete scheduled releases give the fitter no continuous
underlying.

Promotion of the uncovered set to primary is **provisional on the LIP re-sweep**
converging without finding retail programs on the `KXHIGH*` series.
