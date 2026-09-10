# FINDINGS_BASIS - ICE (Kalshi settlement) vs NYMEX (CL) daily settlement

Generated 2026-09-10T21:25:54+00:00. Kalshi `expiration_value` is the realised ICE daily settlement per event; NYMEX settlements come from Databento `GLBX.MDP3` `statistics` records with `stat_type = 3` (SETTLEMENT_PRICE). Both settle at 14:30 ET.

Cost of this test: $0.01 futures_stats_c0, $0.49 futures_stats_clfut.

Kalshi events with a settlement value: 166 (KXWTI 131, KXWTIW 35). Joined to a NYMEX c.0 settlement: 164; to the reference contract: 164. Reference contract source: rules 95, calendar 71. Kalshi's calendar convention (next month from the 16th) reproduces the stated contract on 99 of 99 events where one is stated.

## Distribution of ICE - NYMEX ($/bbl), by series

| series | basis | n | mean | median | sd | min | p5 | p95 | max | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| KXWTI | vs reference contract (contract stated by Kalshi) | 79 | -0.059 | +0.000 | 0.529 | -4.70 | +0.000 | +0.000 | +0.00 | too wide |
| KXWTI | vs reference contract (all events) | 130 | +0.010 | +0.000 | 0.537 | -4.70 | +0.000 | +0.000 | +3.52 | too wide |
| KXWTI | vs reference contract, roll-boundary assignments excluded | 127 | -0.035 | +0.000 | 0.418 | -4.70 | +0.000 | +0.000 | +0.20 | too wide |
| KXWTI | vs CL.c.0 (contaminated by rolls) | 130 | -0.226 | +0.000 | 0.728 | -4.70 | -0.982 | +0.000 | +0.20 | too wide |
| KXWTIW | vs reference contract (contract stated by Kalshi) | 16 | +0.000 | +0.000 | 0.000 | +0.00 | +0.000 | +0.000 | +0.00 | tight |
| KXWTIW | vs reference contract (all events) | 34 | +0.003 | +0.000 | 0.017 | +0.00 | +0.000 | +0.000 | +0.10 | tight |
| KXWTIW | vs reference contract, roll-boundary assignments excluded | 33 | +0.000 | +0.000 | 0.000 | +0.00 | +0.000 | +0.000 | +0.00 | tight |
| KXWTIW | vs CL.c.0 (contaminated by rolls) | 34 | -0.043 | +0.000 | 0.176 | -0.75 | -0.307 | +0.000 | +0.09 | meaningful-but-stable |

Events where ICE and NYMEX settled within $0.005 of each other: **158 of 164** (96%); within $0.05: 158.

Verdict thresholds against a $1-wide bracket: **tight** = |mean| < 0.05, sd < 0.10, 95th pct of |basis| < 0.25; **meaningful-but-stable** = |mean| < 0.15, sd < 0.30, 95th pct < 0.60; else **too wide**.

## Verdict: **tight in the body, with a real tail**

On 98% of events (158 of 162, roll-boundary assignments excluded) Kalshi's ICE settlement equals the NYMEX settlement to the cent: no persistent offset, no noise. The mechanical threshold verdict on the same events is 'too wide' because of 2 unexplained events, 1 of which exceed a full $1 bracket width. That is the tail the brief warned about: rare, unhedgeable by construction, and it must be understood (Kalshi settlement anomaly, or a genuine ICE dislocation) before position size is chosen. Sizing rule of thumb from this sample: one event per ~162 settlements where the ICE-NYMEX difference reaches $4.70.

Every event where ICE and NYMEX did NOT settle within half a cent, with that day's NYMEX settlements of the adjacent contract months. A `roll-boundary assignment` is an event in the early 'front-month' era (no contract named in the rules) where Kalshi's value equals the adjacent month to the cent: the calendar fallback assigned the wrong month, the exchanges agreed. `UNEXPLAINED` matches no contract that day.

| date | series | Kalshi (ICE) | reference | source | NYMEX | basis | Kalshi value matches | kind | adjacent NYMEX settlements |
|---|---|---:|---|---|---:|---:|---|---|---|
| 2026-03-16 | KXWTI | 93.50 | CLK6 | calendar | 92.46 | +1.04 | CLJ6 | roll-boundary assignment | CLJ6 93.50, CLK6 92.46, CLM6 88.54, CLN6 84.99 |
| 2026-04-06 | KXWTI | 112.61 | CLK6 | calendar | 112.41 | +0.20 | none | UNEXPLAINED | CLK6 112.41, CLM6 98.47, CLN6 90.24 |
| 2026-04-16 | KXWTI | 94.69 | CLM6 | calendar | 91.17 | +3.52 | CLK6 | roll-boundary assignment | CLK6 94.69, CLM6 91.17, CLN6 86.98, CLQ6 83.50 |
| 2026-04-17 | KXWTI | 83.85 | CLM6 | calendar | 82.59 | +1.26 | CLK6 | roll-boundary assignment | CLK6 83.85, CLM6 82.59, CLN6 80.22, CLQ6 78.00 |
| 2026-06-15 | KXWTI | 76.05 | CLN6 | rules | 80.75 | -4.70 | none | UNEXPLAINED | CLN6 80.75, CLQ6 79.44, CLU6 78.17 |
| 2026-01-16 | KXWTIW | 59.44 | CLH6 | calendar | 59.34 | +0.10 | CLG6 | roll-boundary assignment | CLG6 59.44, CLH6 59.34, CLJ6 59.20, CLK6 59.06 |

4 roll-boundary assignments, 2 unexplained.

A NYMEX CL option is an adequate hedge for a Kalshi ICE-settled bracket on the current account in the body of the distribution; no ICE licence is needed for the basis. The tail events above are the residual risk to size against.

## Roll dates

Dates where Databento's continuous CL.c.0 was on a different contract than Kalshi's reference contract: **28 of 164** comparable dates. Kalshi moves to the next delivery month on the 16th of each month, weeks before the NYMEX last trade; c.0 rolls the session after the last trade. Between those two dates the c.0 basis is the calendar spread, not an exchange difference. NYMEX last trade dates read from the data: CLG6 2026-01-20, CLH6 2026-02-20, CLJ6 2026-03-20, CLK6 2026-04-21, CLM6 2026-05-19, CLN6 2026-06-22, CLQ6 2026-07-21, CLU6 2026-08-20.

| date | series | Kalshi front month | CL.c.0 contract | basis vs c.0 | basis vs front month |
|---|---|---|---|---:|---:|
| 2026-03-16 | KXWTI | CLK6 (c) | CLJ6 | +0.000 | +1.040 |
| 2026-03-17 | KXWTI | CLK6 (c) | CLJ6 | -0.680 | +0.000 |
| 2026-03-18 | KXWTI | CLK6 (c) | CLJ6 | -0.860 | +0.000 |
| 2026-03-19 | KXWTI | CLK6 (c) | CLJ6 | -0.590 | +0.000 |
| 2026-03-20 | KXWTI | CLK6 (c) | CLJ6 | -0.090 | +0.000 |
| 2026-04-16 | KXWTI | CLM6 (c) | CLK6 | +0.000 | +3.520 |
| 2026-04-17 | KXWTI | CLM6 (c) | CLK6 | +0.000 | +1.260 |
| 2026-04-20 | KXWTI | CLM6 (c) | CLK6 | -2.190 | +0.000 |
| 2026-04-21 | KXWTI | CLM6 (c) | CLK6 | -2.460 | +0.000 |
| 2026-05-18 | KXWTI | CLN6 (r) | CLM6 | -4.280 | +0.000 |
| 2026-05-19 | KXWTI | CLN6 (r) | CLM6 | -3.620 | +0.000 |
| 2026-06-16 | KXWTI | CLQ6 (r) | CLN6 | -0.780 | +0.000 |
| 2026-06-17 | KXWTI | CLQ6 (r) | CLN6 | -0.780 | +0.000 |
| 2026-06-18 | KXWTI | CLQ6 (r) | CLN6 | -0.750 | +0.000 |
| 2026-06-22 | KXWTI | CLQ6 (r) | CLN6 | -0.960 | +0.000 |
| 2026-07-16 | KXWTI | CLU6 (r) | CLQ6 | -0.670 | +0.000 |
| 2026-07-17 | KXWTI | CLU6 (r) | CLQ6 | -0.710 | +0.000 |
| 2026-07-20 | KXWTI | CLU6 (r) | CLQ6 | -0.750 | +0.000 |
| 2026-07-21 | KXWTI | CLU6 (r) | CLQ6 | -0.570 | +0.000 |
| 2026-08-17 | KXWTI | CLV6 (r) | CLU6 | -0.760 | +0.000 |
| 2026-08-18 | KXWTI | CLV6 (r) | CLU6 | -0.880 | +0.000 |
| 2026-08-19 | KXWTI | CLV6 (r) | CLU6 | -1.440 | +0.000 |
| 2026-08-20 | KXWTI | CLV6 (r) | CLU6 | -1.000 | +0.000 |
| 2026-01-16 | KXWTIW | CLH6 (c) | CLG6 | +0.000 | +0.100 |
| 2026-02-20 | KXWTIW | CLJ6 (c) | CLH6 | +0.090 | +0.000 |
| 2026-03-20 | KXWTIW | CLK6 (c) | CLJ6 | -0.090 | +0.000 |
| 2026-06-18 | KXWTIW | CLQ6 (r) | CLN6 | -0.750 | +0.000 |
| 2026-07-17 | KXWTIW | CLU6 (r) | CLQ6 | -0.710 | +0.000 |

On these dates the c.0 basis is contaminated by the calendar spread between two contract months; the named-front-month basis is the one that measures the exchange difference.

### Contract in use by date

| contract | CL.c.0 first..last date | Kalshi front month first..last date |
|---|---|---|
| CLG6 | 2026-01-02..2026-01-16 | 2026-01-02..2026-01-09 |
| CLH6 | 2026-01-23..2026-02-20 | 2026-01-16..2026-02-13 |
| CLJ6 | 2026-02-27..2026-03-20 | 2026-02-20..2026-03-13 |
| CLK6 | 2026-03-23..2026-04-21 | 2026-03-16..2026-04-15 |
| CLM6 | 2026-04-22..2026-05-19 | 2026-04-16..2026-05-15 |
| CLN6 | 2026-05-20..2026-06-22 | 2026-05-18..2026-06-15 |
| CLQ6 | 2026-06-23..2026-07-21 | 2026-06-16..2026-07-15 |
| CLU6 | 2026-07-22..2026-08-20 | 2026-07-16..2026-08-14 |
| CLV6 | 2026-08-21..2026-09-09 | 2026-08-17..2026-09-09 |

## Largest |basis| days (named front month)

| date | series | ICE (Kalshi) | NYMEX | basis |
|---|---|---:|---:|---:|
| 2026-06-15 | KXWTI | 76.05 | 80.75 | -4.700 |
| 2026-04-16 | KXWTI | 94.69 | 91.17 | +3.520 |
| 2026-04-17 | KXWTI | 83.85 | 82.59 | +1.260 |
| 2026-03-16 | KXWTI | 93.50 | 92.46 | +1.040 |
| 2026-04-06 | KXWTI | 112.61 | 112.41 | +0.200 |
| 2026-01-16 | KXWTIW | 59.44 | 59.34 | +0.100 |
| 2026-03-02 | KXWTI | 71.23 | 71.23 | +0.000 |
| 2026-08-14 | KXWTI | 82.40 | 82.40 | +0.000 |
| 2026-08-10 | KXWTI | 82.13 | 82.13 | +0.000 |
| 2026-08-11 | KXWTI | 83.20 | 83.20 | +0.000 |

## Time series

| date | series | ICE (Kalshi) | front month | NYMEX | basis | c.0 contract | NYMEX c.0 | basis c.0 |
|---|---|---:|---|---:|---:|---|---:|---:|
| 2026-01-02 | KXWTIW | 57.32 | CLG6 (c) | 57.32 | +0.000 | CLG6 | 57.32 | +0.000 |
| 2026-01-09 | KXWTIW | 59.12 | CLG6 (c) | 59.12 | +0.000 | CLG6 | 59.12 | +0.000 |
| 2026-01-16 | KXWTIW | 59.44 | CLH6 (c) | 59.34 | +0.100 | CLG6 | 59.44 | +0.000 |
| 2026-01-23 | KXWTIW | 61.07 | CLH6 (c) | 61.07 | +0.000 | CLH6 | 61.07 | +0.000 |
| 2026-01-30 | KXWTIW | 65.21 | CLH6 (c) | 65.21 | +0.000 | CLH6 | 65.21 | +0.000 |
| 2026-02-06 | KXWTIW | 63.55 | CLH6 (c) | 63.55 | +0.000 | CLH6 | 63.55 | +0.000 |
| 2026-02-13 | KXWTIW | 62.89 | CLH6 (c) | 62.89 | +0.000 | CLH6 | 62.89 | +0.000 |
| 2026-02-20 | KXWTIW | 66.48 | CLJ6 (c) | 66.48 | +0.000 | CLH6 | 66.39 | +0.090 |
| 2026-02-27 | KXWTIW | 67.02 | CLJ6 (c) | 67.02 | +0.000 | CLJ6 | 67.02 | +0.000 |
| 2026-03-02 | KXWTI | 71.23 | CLJ6 (c) | 71.23 | +0.000 | CLJ6 | 71.23 | +0.000 |
| 2026-03-06 | KXWTIW | 90.90 | CLJ6 (c) | 90.90 | +0.000 | CLJ6 | 90.90 | +0.000 |
| 2026-03-06 | KXWTI | 90.90 | CLJ6 (c) | 90.90 | +0.000 | CLJ6 | 90.90 | +0.000 |
| 2026-03-09 | KXWTI | 94.77 | CLJ6 (c) | 94.77 | +0.000 | CLJ6 | 94.77 | +0.000 |
| 2026-03-10 | KXWTI | 83.45 | CLJ6 (c) | 83.45 | +0.000 | CLJ6 | 83.45 | +0.000 |
| 2026-03-11 | KXWTI | 87.25 | CLJ6 (c) | 87.25 | +0.000 | CLJ6 | 87.25 | +0.000 |
| 2026-03-12 | KXWTI | 95.73 | CLJ6 (c) | 95.73 | +0.000 | CLJ6 | 95.73 | +0.000 |
| 2026-03-13 | KXWTI | 98.71 | CLJ6 (c) | 98.71 | +0.000 | CLJ6 | 98.71 | +0.000 |
| 2026-03-13 | KXWTIW | 98.71 | CLJ6 (c) | 98.71 | +0.000 | CLJ6 | 98.71 | +0.000 |
| 2026-03-16 | KXWTI | 93.50 | CLK6 (c) | 92.46 | +1.040 | CLJ6 | 93.50 | +0.000 |
| 2026-03-17 | KXWTI | 95.53 | CLK6 (c) | 95.53 | +0.000 | CLJ6 | 96.21 | -0.680 |
| 2026-03-18 | KXWTI | 95.46 | CLK6 (c) | 95.46 | +0.000 | CLJ6 | 96.32 | -0.860 |
| 2026-03-19 | KXWTI | 95.55 | CLK6 (c) | 95.55 | +0.000 | CLJ6 | 96.14 | -0.590 |
| 2026-03-20 | KXWTIW | 98.23 | CLK6 (c) | 98.23 | +0.000 | CLJ6 | 98.32 | -0.090 |
| 2026-03-20 | KXWTI | 98.23 | CLK6 (c) | 98.23 | +0.000 | CLJ6 | 98.32 | -0.090 |
| 2026-03-23 | KXWTI | 88.13 | CLK6 (c) | 88.13 | +0.000 | CLK6 | 88.13 | +0.000 |
| 2026-03-24 | KXWTI | 92.35 | CLK6 (c) | 92.35 | +0.000 | CLK6 | 92.35 | +0.000 |
| 2026-03-25 | KXWTI | 90.32 | CLK6 (c) | 90.32 | +0.000 | CLK6 | 90.32 | +0.000 |
| 2026-03-26 | KXWTI | 94.48 | CLK6 (c) | 94.48 | +0.000 | CLK6 | 94.48 | +0.000 |
| 2026-03-27 | KXWTIW | 99.64 | CLK6 (c) | 99.64 | +0.000 | CLK6 | 99.64 | +0.000 |
| 2026-03-27 | KXWTI | 99.64 | CLK6 (c) | 99.64 | +0.000 | CLK6 | 99.64 | +0.000 |
| 2026-03-30 | KXWTI | 102.88 | CLK6 (c) | 102.88 | +0.000 | CLK6 | 102.88 | +0.000 |
| 2026-03-31 | KXWTI | 101.38 | CLK6 (c) | 101.38 | +0.000 | CLK6 | 101.38 | +0.000 |
| 2026-04-01 | KXWTI | 100.12 | CLK6 (c) | 100.12 | +0.000 | CLK6 | 100.12 | +0.000 |
| 2026-04-02 | KXWTI | 111.54 | CLK6 (c) | 111.54 | +0.000 | CLK6 | 111.54 | +0.000 |
| 2026-04-03 | KXWTI | 111.54 | CLK6 (c) | - | - | - | - | - |
| 2026-04-03 | KXWTIW | 111.54 | CLK6 (c) | - | - | - | - | - |
| 2026-04-06 | KXWTI | 112.61 | CLK6 (c) | 112.41 | +0.200 | CLK6 | 112.41 | +0.200 |
| 2026-04-07 | KXWTI | 112.95 | CLK6 (c) | 112.95 | +0.000 | CLK6 | 112.95 | +0.000 |
| 2026-04-08 | KXWTI | 94.41 | CLK6 (c) | 94.41 | +0.000 | CLK6 | 94.41 | +0.000 |
| 2026-04-09 | KXWTI | 97.87 | CLK6 (c) | 97.87 | +0.000 | CLK6 | 97.87 | +0.000 |
| 2026-04-10 | KXWTI | 96.57 | CLK6 (c) | 96.57 | +0.000 | CLK6 | 96.57 | +0.000 |
| 2026-04-10 | KXWTIW | 96.57 | CLK6 (c) | 96.57 | +0.000 | CLK6 | 96.57 | +0.000 |
| 2026-04-13 | KXWTI | 99.08 | CLK6 (c) | 99.08 | +0.000 | CLK6 | 99.08 | +0.000 |
| 2026-04-14 | KXWTI | 91.28 | CLK6 (c) | 91.28 | +0.000 | CLK6 | 91.28 | +0.000 |
| 2026-04-15 | KXWTI | 91.29 | CLK6 (c) | 91.29 | +0.000 | CLK6 | 91.29 | +0.000 |
| 2026-04-16 | KXWTI | 94.69 | CLM6 (c) | 91.17 | +3.520 | CLK6 | 94.69 | +0.000 |
| 2026-04-17 | KXWTI | 83.85 | CLM6 (c) | 82.59 | +1.260 | CLK6 | 83.85 | +0.000 |
| 2026-04-20 | KXWTI | 87.42 | CLM6 (c) | 87.42 | +0.000 | CLK6 | 89.61 | -2.190 |
| 2026-04-21 | KXWTI | 89.67 | CLM6 (c) | 89.67 | +0.000 | CLK6 | 92.13 | -2.460 |
| 2026-04-22 | KXWTI | 92.96 | CLM6 (c) | 92.96 | +0.000 | CLM6 | 92.96 | +0.000 |
| 2026-04-23 | KXWTI | 95.85 | CLM6 (c) | 95.85 | +0.000 | CLM6 | 95.85 | +0.000 |
| 2026-04-24 | KXWTI | 94.40 | CLM6 (c) | 94.40 | +0.000 | CLM6 | 94.40 | +0.000 |
| 2026-04-24 | KXWTIW | 94.40 | CLM6 (c) | 94.40 | +0.000 | CLM6 | 94.40 | +0.000 |
| 2026-04-27 | KXWTI | 96.37 | CLM6 (c) | 96.37 | +0.000 | CLM6 | 96.37 | +0.000 |
| 2026-04-28 | KXWTI | 99.93 | CLM6 (c) | 99.93 | +0.000 | CLM6 | 99.93 | +0.000 |
| 2026-04-29 | KXWTI | 106.88 | CLM6 (c) | 106.88 | +0.000 | CLM6 | 106.88 | +0.000 |
| 2026-04-30 | KXWTI | 105.07 | CLM6 (c) | 105.07 | +0.000 | CLM6 | 105.07 | +0.000 |
| 2026-05-01 | KXWTI | 101.94 | CLM6 (c) | 101.94 | +0.000 | CLM6 | 101.94 | +0.000 |
| 2026-05-01 | KXWTIW | 101.94 | CLM6 (c) | 101.94 | +0.000 | CLM6 | 101.94 | +0.000 |
| 2026-05-04 | KXWTI | 106.42 | CLM6 (c) | 106.42 | +0.000 | CLM6 | 106.42 | +0.000 |
| 2026-05-05 | KXWTI | 102.27 | CLM6 (c) | 102.27 | +0.000 | CLM6 | 102.27 | +0.000 |
| 2026-05-06 | KXWTI | 95.08 | CLM6 (c) | 95.08 | +0.000 | CLM6 | 95.08 | +0.000 |
| 2026-05-07 | KXWTI | 94.81 | CLM6 (c) | 94.81 | +0.000 | CLM6 | 94.81 | +0.000 |
| 2026-05-08 | KXWTI | 95.42 | CLM6 (c) | 95.42 | +0.000 | CLM6 | 95.42 | +0.000 |
| 2026-05-08 | KXWTIW | 95.42 | CLM6 (c) | 95.42 | +0.000 | CLM6 | 95.42 | +0.000 |
| 2026-05-11 | KXWTI | 98.07 | CLM6 (c) | 98.07 | +0.000 | CLM6 | 98.07 | +0.000 |
| 2026-05-12 | KXWTI | 102.18 | CLM6 (c) | 102.18 | +0.000 | CLM6 | 102.18 | +0.000 |
| 2026-05-13 | KXWTI | 101.02 | CLM6 (c) | 101.02 | +0.000 | CLM6 | 101.02 | +0.000 |
| 2026-05-14 | KXWTI | 101.17 | CLM6 (c) | 101.17 | +0.000 | CLM6 | 101.17 | +0.000 |
| 2026-05-15 | KXWTI | 105.42 | CLM6 (c) | 105.42 | +0.000 | CLM6 | 105.42 | +0.000 |
| 2026-05-15 | KXWTIW | 105.42 | CLM6 (c) | 105.42 | +0.000 | CLM6 | 105.42 | +0.000 |
| 2026-05-18 | KXWTI | 104.38 | CLN6 (r) | 104.38 | +0.000 | CLM6 | 108.66 | -4.280 |
| 2026-05-19 | KXWTI | 104.15 | CLN6 (r) | 104.15 | +0.000 | CLM6 | 107.77 | -3.620 |
| 2026-05-20 | KXWTI | 98.26 | CLN6 (r) | 98.26 | +0.000 | CLN6 | 98.26 | +0.000 |
| 2026-05-21 | KXWTI | 96.35 | CLN6 (r) | 96.35 | +0.000 | CLN6 | 96.35 | +0.000 |
| 2026-05-22 | KXWTI | 96.60 | CLN6 (r) | 96.60 | +0.000 | CLN6 | 96.60 | +0.000 |
| 2026-05-22 | KXWTIW | 96.60 | CLN6 (r) | 96.60 | +0.000 | CLN6 | 96.60 | +0.000 |
| 2026-05-26 | KXWTI | 93.89 | CLN6 (r) | 93.89 | +0.000 | CLN6 | 93.89 | +0.000 |
| 2026-05-27 | KXWTI | 88.68 | CLN6 (r) | 88.68 | +0.000 | CLN6 | 88.68 | +0.000 |
| 2026-05-28 | KXWTI | 88.90 | CLN6 (r) | 88.90 | +0.000 | CLN6 | 88.90 | +0.000 |
| 2026-05-29 | KXWTI | 87.36 | CLN6 (r) | 87.36 | +0.000 | CLN6 | 87.36 | +0.000 |
| 2026-05-29 | KXWTIW | 87.36 | CLN6 (r) | 87.36 | +0.000 | CLN6 | 87.36 | +0.000 |
| 2026-06-01 | KXWTI | 92.16 | CLN6 (r) | 92.16 | +0.000 | CLN6 | 92.16 | +0.000 |
| 2026-06-02 | KXWTI | 93.76 | CLN6 (r) | 93.76 | +0.000 | CLN6 | 93.76 | +0.000 |
| 2026-06-03 | KXWTI | 96.02 | CLN6 (r) | 96.02 | +0.000 | CLN6 | 96.02 | +0.000 |
| 2026-06-04 | KXWTI | 93.04 | CLN6 (r) | 93.04 | +0.000 | CLN6 | 93.04 | +0.000 |
| 2026-06-05 | KXWTIW | 90.54 | CLN6 (r) | 90.54 | +0.000 | CLN6 | 90.54 | +0.000 |
| 2026-06-05 | KXWTI | 90.54 | CLN6 (r) | 90.54 | +0.000 | CLN6 | 90.54 | +0.000 |
| 2026-06-08 | KXWTI | 91.30 | CLN6 (r) | 91.30 | +0.000 | CLN6 | 91.30 | +0.000 |
| 2026-06-09 | KXWTI | 88.20 | CLN6 (r) | 88.20 | +0.000 | CLN6 | 88.20 | +0.000 |
| 2026-06-10 | KXWTI | 90.03 | CLN6 (r) | 90.03 | +0.000 | CLN6 | 90.03 | +0.000 |
| 2026-06-11 | KXWTI | 87.71 | CLN6 (r) | 87.71 | +0.000 | CLN6 | 87.71 | +0.000 |
| 2026-06-12 | KXWTI | 84.88 | CLN6 (r) | 84.88 | +0.000 | CLN6 | 84.88 | +0.000 |
| 2026-06-12 | KXWTIW | 84.88 | CLN6 (r) | 84.88 | +0.000 | CLN6 | 84.88 | +0.000 |
| 2026-06-15 | KXWTI | 76.05 | CLN6 (r) | 80.75 | -4.700 | CLN6 | 80.75 | -4.700 |
| 2026-06-16 | KXWTI | 75.27 | CLQ6 (r) | 75.27 | +0.000 | CLN6 | 76.05 | -0.780 |
| 2026-06-17 | KXWTI | 76.01 | CLQ6 (r) | 76.01 | +0.000 | CLN6 | 76.79 | -0.780 |
| 2026-06-18 | KXWTIW | 75.85 | CLQ6 (r) | 75.85 | +0.000 | CLN6 | 76.60 | -0.750 |
| 2026-06-18 | KXWTI | 75.85 | CLQ6 (r) | 75.85 | +0.000 | CLN6 | 76.60 | -0.750 |
| 2026-06-22 | KXWTI | 73.86 | CLQ6 (r) | 73.86 | +0.000 | CLN6 | 74.82 | -0.960 |
| 2026-06-23 | KXWTI | 73.21 | CLQ6 (r) | 73.21 | +0.000 | CLQ6 | 73.21 | +0.000 |
| 2026-06-24 | KXWTI | 70.34 | CLQ6 (r) | 70.34 | +0.000 | CLQ6 | 70.34 | +0.000 |
| 2026-06-25 | KXWTI | 71.92 | CLQ6 (r) | 71.92 | +0.000 | CLQ6 | 71.92 | +0.000 |
| 2026-06-26 | KXWTIW | 69.23 | CLQ6 (r) | 69.23 | +0.000 | CLQ6 | 69.23 | +0.000 |
| 2026-06-26 | KXWTI | 69.23 | CLQ6 (r) | 69.23 | +0.000 | CLQ6 | 69.23 | +0.000 |
| 2026-06-29 | KXWTI | 70.75 | CLQ6 (r) | 70.75 | +0.000 | CLQ6 | 70.75 | +0.000 |
| 2026-06-30 | KXWTI | 69.50 | CLQ6 (r) | 69.50 | +0.000 | CLQ6 | 69.50 | +0.000 |
| 2026-07-01 | KXWTI | 68.58 | CLQ6 (r) | 68.58 | +0.000 | CLQ6 | 68.58 | +0.000 |
| 2026-07-02 | KXWTIW | 68.69 | CLQ6 (r) | 68.69 | +0.000 | CLQ6 | 68.69 | +0.000 |
| 2026-07-02 | KXWTI | 68.69 | CLQ6 (r) | 68.69 | +0.000 | CLQ6 | 68.69 | +0.000 |
| 2026-07-06 | KXWTI | 68.55 | CLQ6 (r) | 68.55 | +0.000 | CLQ6 | 68.55 | +0.000 |
| 2026-07-07 | KXWTI | 70.44 | CLQ6 (r) | 70.44 | +0.000 | CLQ6 | 70.44 | +0.000 |
| 2026-07-08 | KXWTI | 73.52 | CLQ6 (r) | 73.52 | +0.000 | CLQ6 | 73.52 | +0.000 |
| 2026-07-09 | KXWTI | 72.08 | CLQ6 (r) | 72.08 | +0.000 | CLQ6 | 72.08 | +0.000 |
| 2026-07-10 | KXWTI | 71.41 | CLQ6 (r) | 71.41 | +0.000 | CLQ6 | 71.41 | +0.000 |
| 2026-07-10 | KXWTIW | 71.41 | CLQ6 (r) | 71.41 | +0.000 | CLQ6 | 71.41 | +0.000 |
| 2026-07-13 | KXWTI | 78.14 | CLQ6 (r) | 78.14 | +0.000 | CLQ6 | 78.14 | +0.000 |
| 2026-07-14 | KXWTI | 79.34 | CLQ6 (r) | 79.34 | +0.000 | CLQ6 | 79.34 | +0.000 |
| 2026-07-15 | KXWTI | 79.60 | CLQ6 (r) | 79.60 | +0.000 | CLQ6 | 79.60 | +0.000 |
| 2026-07-16 | KXWTI | 78.28 | CLU6 (r) | 78.28 | +0.000 | CLQ6 | 78.95 | -0.670 |
| 2026-07-17 | KXWTIW | 81.78 | CLU6 (r) | 81.78 | +0.000 | CLQ6 | 82.49 | -0.710 |
| 2026-07-17 | KXWTI | 81.78 | CLU6 (r) | 81.78 | +0.000 | CLQ6 | 82.49 | -0.710 |
| 2026-07-20 | KXWTI | 82.48 | CLU6 (r) | 82.48 | +0.000 | CLQ6 | 83.23 | -0.750 |
| 2026-07-21 | KXWTI | 84.34 | CLU6 (r) | 84.34 | +0.000 | CLQ6 | 84.91 | -0.570 |
| 2026-07-22 | KXWTI | 86.83 | CLU6 (r) | 86.83 | +0.000 | CLU6 | 86.83 | +0.000 |
| 2026-07-23 | KXWTI | 92.19 | CLU6 (r) | 92.19 | +0.000 | CLU6 | 92.19 | +0.000 |
| 2026-07-24 | KXWTIW | 89.31 | CLU6 (r) | 89.31 | +0.000 | CLU6 | 89.31 | +0.000 |
| 2026-07-24 | KXWTI | 89.31 | CLU6 (r) | 89.31 | +0.000 | CLU6 | 89.31 | +0.000 |
| 2026-07-27 | KXWTI | 82.61 | CLU6 (r) | 82.61 | +0.000 | CLU6 | 82.61 | +0.000 |
| 2026-07-28 | KXWTI | 79.26 | CLU6 (r) | 79.26 | +0.000 | CLU6 | 79.26 | +0.000 |
| 2026-07-29 | KXWTI | 84.46 | CLU6 (r) | 84.46 | +0.000 | CLU6 | 84.46 | +0.000 |
| 2026-07-30 | KXWTI | 83.59 | CLU6 (r) | 83.59 | +0.000 | CLU6 | 83.59 | +0.000 |
| 2026-07-31 | KXWTIW | 84.67 | CLU6 (r) | 84.67 | +0.000 | CLU6 | 84.67 | +0.000 |
| 2026-07-31 | KXWTI | 84.67 | CLU6 (r) | 84.67 | +0.000 | CLU6 | 84.67 | +0.000 |
| 2026-08-03 | KXWTI | 80.34 | CLU6 (r) | 80.34 | +0.000 | CLU6 | 80.34 | +0.000 |
| 2026-08-04 | KXWTI | 75.77 | CLU6 (r) | 75.77 | +0.000 | CLU6 | 75.77 | +0.000 |
| 2026-08-05 | KXWTI | 75.22 | CLU6 (r) | 75.22 | +0.000 | CLU6 | 75.22 | +0.000 |
| 2026-08-06 | KXWTI | 77.29 | CLU6 (r) | 77.29 | +0.000 | CLU6 | 77.29 | +0.000 |
| 2026-08-07 | KXWTIW | 78.18 | CLU6 (r) | 78.18 | +0.000 | CLU6 | 78.18 | +0.000 |
| 2026-08-07 | KXWTI | 78.18 | CLU6 (r) | 78.18 | +0.000 | CLU6 | 78.18 | +0.000 |
| 2026-08-10 | KXWTI | 82.13 | CLU6 (r) | 82.13 | +0.000 | CLU6 | 82.13 | +0.000 |
| 2026-08-11 | KXWTI | 83.20 | CLU6 (r) | 83.20 | +0.000 | CLU6 | 83.20 | +0.000 |
| 2026-08-12 | KXWTI | 83.27 | CLU6 (r) | 83.27 | +0.000 | CLU6 | 83.27 | +0.000 |
| 2026-08-13 | KXWTI | 81.25 | CLU6 (r) | 81.25 | +0.000 | CLU6 | 81.25 | +0.000 |
| 2026-08-14 | KXWTI | 82.40 | CLU6 (r) | 82.40 | +0.000 | CLU6 | 82.40 | +0.000 |
| 2026-08-14 | KXWTIW | 82.40 | CLU6 (r) | 82.40 | +0.000 | CLU6 | 82.40 | +0.000 |
| 2026-08-17 | KXWTI | 83.74 | CLV6 (r) | 83.74 | +0.000 | CLU6 | 84.50 | -0.760 |
| 2026-08-18 | KXWTI | 84.06 | CLV6 (r) | 84.06 | +0.000 | CLU6 | 84.94 | -0.880 |
| 2026-08-19 | KXWTI | 84.39 | CLV6 (r) | 84.39 | +0.000 | CLU6 | 85.83 | -1.440 |
| 2026-08-20 | KXWTI | 86.83 | CLV6 (r) | 86.83 | +0.000 | CLU6 | 87.83 | -1.000 |
| 2026-08-21 | KXWTI | 87.06 | CLV6 (r) | 87.06 | +0.000 | CLV6 | 87.06 | +0.000 |
| 2026-08-21 | KXWTIW | 87.06 | CLV6 (r) | 87.06 | +0.000 | CLV6 | 87.06 | +0.000 |
| 2026-08-24 | KXWTI | 85.01 | CLV6 (r) | 85.01 | +0.000 | CLV6 | 85.01 | +0.000 |
| 2026-08-25 | KXWTI | 82.36 | CLV6 (r) | 82.36 | +0.000 | CLV6 | 82.36 | +0.000 |
| 2026-08-26 | KXWTI | 82.23 | CLV6 (r) | 82.23 | +0.000 | CLV6 | 82.23 | +0.000 |
| 2026-08-27 | KXWTI | 83.53 | CLV6 (r) | 83.53 | +0.000 | CLV6 | 83.53 | +0.000 |
| 2026-08-28 | KXWTI | 83.40 | CLV6 (r) | 83.40 | +0.000 | CLV6 | 83.40 | +0.000 |
| 2026-08-28 | KXWTIW | 83.40 | CLV6 (r) | 83.40 | +0.000 | CLV6 | 83.40 | +0.000 |
| 2026-08-31 | KXWTI | 85.76 | CLV6 (r) | 85.76 | +0.000 | CLV6 | 85.76 | +0.000 |
| 2026-09-01 | KXWTI | 90.22 | CLV6 (r) | 90.22 | +0.000 | CLV6 | 90.22 | +0.000 |
| 2026-09-02 | KXWTI | 91.01 | CLV6 (r) | 91.01 | +0.000 | CLV6 | 91.01 | +0.000 |
| 2026-09-03 | KXWTI | 91.30 | CLV6 (r) | 91.30 | +0.000 | CLV6 | 91.30 | +0.000 |
| 2026-09-04 | KXWTIW | 91.48 | CLV6 (r) | 91.48 | +0.000 | CLV6 | 91.48 | +0.000 |
| 2026-09-04 | KXWTI | 91.48 | CLV6 (r) | 91.48 | +0.000 | CLV6 | 91.48 | +0.000 |
| 2026-09-08 | KXWTI | 93.03 | CLV6 (r) | 93.03 | +0.000 | CLV6 | 93.03 | +0.000 |
| 2026-09-09 | KXWTI | 96.05 | CLV6 (r) | 96.05 | +0.000 | CLV6 | 96.05 | +0.000 |

## statistics schema contents (UNVERIFIED item 5, now measured)

stat_type values seen on CL.c.0: {"1": 168, "2": 20275, "3": 552, "4": 19455, "5": 22817, "6": 354, "7": 31168, "8": 32649, "9": 354, "17": 762, "18": 762}. SETTLEMENT_PRICE = 3 carries the daily settlement, published about 14:30:50 ET and repeated (same price) at ~17:40 ET and again the next morning with stat_flags=3. `ts_ref` is midnight UTC of the trade date (20:00 ET the evening before): use its UTC date, never its ET date. The continuous symbol's `symbol` column is 'CL.c.0'; the contract is recovered from instrument_id via the CL.FUT records.

![basis](basis.png)
