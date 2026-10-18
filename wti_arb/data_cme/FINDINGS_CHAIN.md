# FINDINGS_CHAIN - which CME WTI option root, and is TBBO dense enough

Generated 2026-09-10T23:28:16+00:00. Cost of the pulls behind this file: $0.01 futures_stats_c0, $0.49 futures_stats_clfut, $5.89 definition_LO, $0.08 definition_LO1, $0.11 definition_LO2, $0.09 definition_LO3, $0.12 definition_LO4, $0.04 definition_LO5, $0.10 definition_ML1, $0.11 definition_ML2, $0.09 definition_ML3, $0.10 definition_ML4, $0.04 definition_ML5, $0.09 definition_WL1, $0.09 definition_WL2, $0.09 definition_WL3, $0.09 definition_WL4, $0.02 definition_WL5, $1.66 definition_MCO, $0.02 tbbo_BTC, $0.11 tbbo_LO1, $0.13 tbbo_LO2, $0.10 tbbo_LO3, $0.12 tbbo_LO4, $0.05 tbbo_LO5, $0.26 tbbo_MCO, $0.08 tbbo_ML1, $0.09 tbbo_ML2, $0.05 tbbo_ML3, $0.07 tbbo_ML4, $0.03 tbbo_ML5, $0.07 tbbo_WL1, $0.07 tbbo_WL2, $0.05 tbbo_WL3, $0.05 tbbo_WL4, $0.02 tbbo_WL5, $0.00 tbbo_XPT4, $0.50 tbbo_LO_2026-01, $0.43 tbbo_LO_2026-02, $0.97 tbbo_LO_2026-03, $0.76 tbbo_LO_2026-04, $0.62 tbbo_LO_2026-05, $0.69 tbbo_LO_2026-06, $0.73 tbbo_LO_2026-07, $0.53 tbbo_LO_2026-08, $0.22 tbbo_LO_2026-09.

## Symbology (UNVERIFIED item 3, resolved)

`symbology.resolve(stype_in='parent')` puts child instruments in the response's `partial` list, not in `result`; counting `result` reads as 0 mappings. Children per root in the window: LO 188138 (3232 options, rest UD spreads), LO1 9651 (2162 options, rest UD spreads), LO2 13437 (3224 options, rest UD spreads), LO3 10268 (2524 options, rest UD spreads), LO4 13496 (3046 options, rest UD spreads), LO5 4400 (950 options, rest UD spreads), ML1 9030 (2456 options, rest UD spreads), ML2 9704 (2770 options, rest UD spreads), ML3 7594 (2790 options, rest UD spreads), ML4 8809 (2802 options, rest UD spreads), ML5 3728 (1254 options, rest UD spreads), WL1 8377 (2896 options, rest UD spreads), WL2 8845 (3174 options, rest UD spreads), WL3 7753 (3030 options, rest UD spreads), WL4 7618 (2774 options, rest UD spreads), WL5 2268 (964 options, rest UD spreads), MCO 44614 (2754 options, rest UD spreads)

## Root selection (UNVERIFIED item 1)

Expiries listed per root inside the Kalshi window:

| root | expiries | first | last | strikes per expiry (median) | strike range |
|---|---:|---|---|---:|---|
| LO | 23 | 2026-01-14 | 2031-11-17 | 271 | 0.50 - 500.00 |
| LO1 | 8 | 2026-01-02 | 2026-10-02 | 157 | 22.50 - 225.00 |
| LO2 | 9 | 2026-01-09 | 2026-09-11 | 169 | 22.50 - 250.00 |
| LO3 | 8 | 2026-01-16 | 2026-09-18 | 151 | 22.50 - 250.00 |
| LO4 | 9 | 2026-01-23 | 2026-09-25 | 153 | 22.50 - 250.00 |
| LO5 | 3 | 2026-01-30 | 2026-07-31 | 157 | 22.50 - 225.00 |
| MCO | 12 | 2026-01-14 | 2026-12-16 | 392 | 5.00 - 210.00 |
| ML1 | 9 | 2026-01-05 | 2026-10-05 | 168 | 22.50 - 225.00 |
| ML2 | 9 | 2026-01-12 | 2026-09-14 | 163 | 22.50 - 230.00 |
| ML3 | 7 | 2026-03-16 | 2026-09-21 | 165 | 27.50 - 250.00 |
| ML4 | 8 | 2026-01-26 | 2026-09-28 | 152 | 22.50 - 250.00 |
| ML5 | 4 | 2025-12-29 | 2026-08-31 | 173 | 22.50 - 220.00 |
| WL1 | 10 | 2026-01-07 | 2026-10-07 | 164 | 22.50 - 225.00 |
| WL2 | 9 | 2026-01-14 | 2026-09-09 | 169 | 22.50 - 250.00 |
| WL3 | 9 | 2026-01-21 | 2026-09-16 | 156 | 22.50 - 250.00 |
| WL4 | 9 | 2026-01-28 | 2026-09-23 | 153 | 22.50 - 225.00 |
| WL5 | 4 | 2025-12-31 | 2026-09-30 | 143 | 22.50 - 225.00 |

**KXWTI**: 134 settlement dates, 83 have an option expiring that day.

| weekday | dates | with an expiry |
|---|---:|---:|
| Monday | 26 | 26 |
| Tuesday | 28 | 2 |
| Wednesday | 27 | 27 |
| Thursday | 27 | 3 |
| Friday | 26 | 25 |

dates covered per root: LO2 7, WL2 7, LO 6, ML3 6, WL4 6, WL3 6, WL1 6, ML2 6, ML1 6, MCO 6, LO4 6, LO1 5, ML4 5, LO3 5, ML5 3, LO5 2, WL5 2

**KXWTIW**: 37 settlement dates, 34 have an option expiring that day.

| weekday | dates | with an expiry |
|---|---:|---:|
| Thursday | 2 | 0 |
| Friday | 35 | 34 |

dates covered per root: LO2 9, LO4 8, LO1 7, LO3 7, LO5 3

**Roots to use: LO, LO1, LO2, LO3, LO4, LO5, MCO, ML1, ML2, ML3, ML4, ML5, WL1, WL2, WL3, WL4, WL5.** CME lists WTI weeklies expiring Monday (ML1-5), Wednesday (WL1-5) and Friday (LO1-5); there are no Tuesday or Thursday weeklies, so a Kalshi daily (KXWTI) settling on those days can only match the monthly LO on its own expiry day.

## TBBO quote density (UNVERIFIED item 2)

Per Kalshi settlement date and root: strikes (calls and puts pooled) whose last TBBO quote before 14:30 ET was within 30 / 60 / 120 minutes; wings counted against the NYMEX settlement of the day (fallback: median quoted strike). `clears` = at least 8 strikes within 60 minutes with at least 3 on each side.

**KXWTI**: 83 dates with a matching expiry, **79 clear** the 8-strike / both-wings threshold (95%).

| date | root | listed strikes | quoted (any) | 30m | 60m (below/above) | 120m | median age (min) | clears |
|---|---|---:|---:|---:|---|---:|---:|:---:|
| 2026-03-02 | ML1 | 108 | 55 | 13 | 17 (10/7) | 29 | 116 | yes |
| 2026-03-06 | LO1 | 157 | 81 | 27 | 31 (28/3) | 43 | 111 | yes |
| 2026-03-09 | ML2 | 239 | 92 | 44 | 52 (34/18) | 65 | 32 | yes |
| 2026-03-11 | WL2 | 432 | 108 | 41 | 50 (25/24) | 65 | 79 | yes |
| 2026-03-13 | LO2 | 432 | 119 | 47 | 56 (39/17) | 62 | 76 | yes |
| 2026-03-16 | ML3 | 433 | 102 | 37 | 51 (15/36) | 62 | 59 | yes |
| 2026-03-17 | LO | 320 | 89 | 25 | 33 (21/12) | 50 | 102 | yes |
| 2026-03-17 | MCO | 406 | 54 | 6 | 12 (8/4) | 17 | 153 | yes |
| 2026-03-18 | WL3 | 422 | 87 | 43 | 57 (23/34) | 64 | 31 | yes |
| 2026-03-20 | LO3 | 347 | 91 | 44 | 48 (25/23) | 57 | 43 | yes |
| 2026-03-23 | ML4 | 422 | 113 | 64 | 74 (18/56) | 78 | 27 | yes |
| 2026-03-25 | WL4 | 304 | 71 | 31 | 36 (22/14) | 51 | 57 | yes |
| 2026-03-27 | LO4 | 414 | 83 | 40 | 46 (32/14) | 51 | 40 | yes |
| 2026-03-30 | ML5 | 281 | 75 | 38 | 42 (22/20) | 48 | 30 | yes |
| 2026-04-01 | WL1 | 199 | 73 | 32 | 40 (21/19) | 49 | 54 | yes |
| 2026-04-06 | ML1 | 205 | 104 | 30 | 48 (25/23) | 58 | 85 | yes |
| 2026-04-08 | WL2 | 194 | 101 | 37 | 43 (13/30) | 53 | 80 | yes |
| 2026-04-10 | LO2 | 205 | 77 | 33 | 42 (13/29) | 56 | 48 | yes |
| 2026-04-13 | ML2 | 186 | 82 | 34 | 42 (17/25) | 54 | 50 | yes |
| 2026-04-15 | WL3 | 181 | 78 | 29 | 38 (16/22) | 49 | 71 | yes |
| 2026-04-16 | LO | 475 | 77 | 29 | 37 (12/25) | 49 | 70 | yes |
| 2026-04-16 | MCO | 463 | 55 | 9 | 16 (2/14) | 34 | 94 |  |
| 2026-04-17 | LO3 | 139 | 92 | 34 | 38 (15/23) | 45 | 172 | yes |
| 2026-04-20 | ML3 | 149 | 69 | 22 | 34 (16/18) | 44 | 67 | yes |
| 2026-04-22 | WL4 | 149 | 78 | 23 | 30 (18/12) | 49 | 88 | yes |
| 2026-04-24 | LO4 | 150 | 88 | 37 | 47 (28/19) | 54 | 54 | yes |
| 2026-04-27 | ML4 | 150 | 76 | 31 | 41 (22/19) | 49 | 56 | yes |
| 2026-04-29 | WL5 | 166 | 53 | 19 | 25 (21/4) | 35 | 63 | yes |
| 2026-05-01 | LO1 | 191 | 85 | 26 | 30 (14/16) | 47 | 105 | yes |
| 2026-05-04 | ML1 | 195 | 83 | 28 | 38 (27/11) | 52 | 69 | yes |
| 2026-05-06 | WL1 | 192 | 90 | 33 | 40 (14/26) | 48 | 106 | yes |
| 2026-05-08 | LO2 | 192 | 77 | 34 | 42 (21/21) | 53 | 52 | yes |
| 2026-05-11 | ML2 | 198 | 69 | 40 | 42 (18/24) | 49 | 30 | yes |
| 2026-05-13 | WL2 | 191 | 51 | 19 | 20 (8/12) | 31 | 83 | yes |
| 2026-05-14 | LO | 476 | 70 | 24 | 31 (18/13) | 38 | 101 | yes |
| 2026-05-14 | MCO | 439 | 45 | 11 | 17 (9/8) | 23 | 117 | yes |
| 2026-05-15 | LO3 | 179 | 56 | 21 | 23 (22/1) | 32 | 95 |  |
| 2026-05-18 | ML3 | 169 | 75 | 24 | 30 (21/9) | 37 | 122 | yes |
| 2026-05-20 | WL3 | 161 | 72 | 28 | 33 (15/18) | 49 | 80 | yes |
| 2026-05-22 | LO4 | 154 | 79 | 32 | 45 (26/19) | 54 | 48 | yes |
| 2026-05-27 | WL4 | 164 | 57 | 21 | 30 (4/26) | 37 | 54 | yes |
| 2026-05-29 | LO5 | 157 | 65 | 19 | 31 (16/15) | 43 | 66 | yes |
| 2026-06-01 | ML1 | 168 | 67 | 16 | 23 (13/10) | 35 | 83 | yes |
| 2026-06-03 | WL1 | 163 | 56 | 17 | 24 (15/9) | 29 | 92 | yes |
| 2026-06-05 | LO1 | 163 | 55 | 26 | 27 (11/16) | 36 | 62 | yes |
| 2026-06-08 | ML2 | 163 | 58 | 22 | 25 (11/14) | 26 | 178 | yes |
| 2026-06-10 | WL2 | 150 | 59 | 23 | 26 (7/19) | 35 | 78 | yes |
| 2026-06-12 | LO2 | 150 | 55 | 22 | 26 (9/17) | 32 | 88 | yes |
| 2026-06-15 | ML3 | 177 | 46 | 21 | 22 (8/13) | 24 | 99 | yes |
| 2026-06-16 | LO | 461 | 69 | 23 | 31 (10/21) | 45 | 96 | yes |
| 2026-06-16 | MCO | 428 | 42 | 2 | 4 (1/3) | 16 | 146 |  |
| 2026-06-17 | WL3 | 174 | 41 | 13 | 19 (9/10) | 24 | 81 | yes |
| 2026-06-22 | ML4 | 197 | 48 | 21 | 23 (11/12) | 23 | 129 | yes |
| 2026-06-24 | WL4 | 178 | 43 | 16 | 17 (5/12) | 23 | 87 | yes |
| 2026-06-26 | LO4 | 190 | 44 | 14 | 15 (5/10) | 22 | 111 | yes |
| 2026-06-29 | ML5 | 193 | 37 | 13 | 15 (8/6) | 22 | 84 | yes |
| 2026-07-01 | WL1 | 193 | 32 | 14 | 16 (5/11) | 17 | 76 | yes |
| 2026-07-06 | ML1 | 183 | 27 | 9 | 13 (8/5) | 15 | 62 | yes |
| 2026-07-08 | WL2 | 179 | 53 | 27 | 33 (15/18) | 37 | 30 | yes |
| 2026-07-10 | LO2 | 196 | 41 | 18 | 19 (8/11) | 21 | 79 | yes |
| 2026-07-13 | ML2 | 145 | 56 | 35 | 46 (28/18) | 50 | 17 | yes |
| 2026-07-15 | WL3 | 145 | 42 | 16 | 18 (11/7) | 28 | 93 | yes |
| 2026-07-16 | LO | 457 | 54 | 17 | 18 (9/9) | 27 | 119 | yes |
| 2026-07-16 | MCO | 408 | 36 | 5 | 8 (3/5) | 13 | 165 | yes |
| 2026-07-17 | LO3 | 174 | 51 | 17 | 21 (14/7) | 25 | 122 | yes |
| 2026-07-20 | ML3 | 165 | 59 | 19 | 23 (12/11) | 29 | 121 | yes |
| 2026-07-22 | WL4 | 164 | 54 | 15 | 17 (12/5) | 26 | 137 | yes |
| 2026-07-24 | LO4 | 198 | 69 | 20 | 22 (11/11) | 32 | 137 | yes |
| 2026-07-27 | ML4 | 202 | 58 | 24 | 26 (8/18) | 37 | 79 | yes |
| 2026-07-29 | WL5 | 196 | 56 | 20 | 25 (12/13) | 26 | 148 | yes |
| 2026-07-31 | LO5 | 196 | 58 | 16 | 27 (15/12) | 30 | 84 | yes |
| 2026-08-03 | ML1 | 197 | 45 | 17 | 26 (11/15) | 31 | 44 | yes |
| 2026-08-05 | WL1 | 185 | 52 | 9 | 16 (7/9) | 30 | 113 | yes |
| 2026-08-07 | LO1 | 185 | 48 | 22 | 25 (12/13) | 27 | 53 | yes |
| 2026-08-10 | ML2 | 169 | 47 | 13 | 20 (15/5) | 21 | 148 | yes |
| 2026-08-12 | WL2 | 169 | 45 | 15 | 20 (13/7) | 22 | 136 | yes |
| 2026-08-14 | LO2 | 169 | 42 | 11 | 11 (9/2) | 17 | 186 |  |
| 2026-08-17 | LO | 451 | 58 | 24 | 28 (17/11) | 29 | 106 | yes |
| 2026-08-17 | MCO | 389 | 35 | 6 | 13 (7/6) | 19 | 65 | yes |
| 2026-08-17 | ML3 | 153 | 24 | 5 | 11 (7/4) | 15 | 80 | yes |
| 2026-08-19 | WL3 | 155 | 31 | 11 | 16 (7/9) | 18 | 54 | yes |
| 2026-08-21 | LO3 | 153 | 42 | 16 | 21 (14/7) | 24 | 59 | yes |
| 2026-08-24 | ML4 | 153 | 40 | 13 | 16 (6/10) | 21 | 91 | yes |
| 2026-08-26 | WL4 | 153 | 41 | 13 | 14 (6/8) | 20 | 125 | yes |
| 2026-08-28 | LO4 | 153 | 38 | 13 | 16 (11/5) | 19 | 116 | yes |
| 2026-08-31 | ML5 | 153 | 40 | 12 | 13 (12/1) | 19 | 158 |  |
| 2026-09-02 | WL1 | 166 | 47 | 18 | 20 (16/4) | 26 | 95 | yes |
| 2026-09-04 | LO1 | 157 | 43 | 16 | 17 (9/8) | 23 | 92 | yes |
| 2026-09-09 | WL2 | 154 | 45 | 17 | 20 (13/7) | 28 | 77 | yes |
| 2026-09-11 | LO2 | 159 | 0 | 0 | 0 (0/0) | 0 | - |  |

**KXWTIW**: 34 dates with a matching expiry, **30 clear** the 8-strike / both-wings threshold (88%).

| date | root | listed strikes | quoted (any) | 30m | 60m (below/above) | 120m | median age (min) | clears |
|---|---|---:|---:|---:|---|---:|---:|:---:|
| 2026-01-02 | LO1 | 99 | 23 | 7 | 7 (5/2) | 11 | 131 |  |
| 2026-01-09 | LO2 | 94 | 32 | 12 | 13 (7/6) | 16 | 121 | yes |
| 2026-01-16 | LO3 | 105 | 29 | 9 | 13 (5/8) | 15 | 113 | yes |
| 2026-01-23 | LO4 | 105 | 31 | 14 | 16 (12/4) | 19 | 53 | yes |
| 2026-01-30 | LO5 | 122 | 47 | 17 | 19 (11/8) | 23 | 126 | yes |
| 2026-02-06 | LO1 | 110 | 52 | 14 | 15 (5/10) | 23 | 163 | yes |
| 2026-02-13 | LO2 | 109 | 31 | 8 | 12 (4/8) | 17 | 82 | yes |
| 2026-02-20 | LO3 | 105 | 38 | 14 | 16 (10/6) | 23 | 83 | yes |
| 2026-02-27 | LO4 | 100 | 55 | 11 | 17 (11/6) | 21 | 212 | yes |
| 2026-03-06 | LO1 | 157 | 81 | 27 | 31 (28/3) | 43 | 111 | yes |
| 2026-03-13 | LO2 | 432 | 119 | 47 | 56 (39/17) | 62 | 76 | yes |
| 2026-03-20 | LO3 | 347 | 91 | 44 | 48 (25/23) | 57 | 43 | yes |
| 2026-03-27 | LO4 | 414 | 83 | 40 | 46 (32/14) | 51 | 40 | yes |
| 2026-04-10 | LO2 | 205 | 77 | 33 | 42 (13/29) | 56 | 48 | yes |
| 2026-04-17 | LO3 | 139 | 92 | 34 | 38 (15/23) | 45 | 172 | yes |
| 2026-04-24 | LO4 | 150 | 88 | 37 | 47 (28/19) | 54 | 54 | yes |
| 2026-05-01 | LO1 | 191 | 85 | 26 | 30 (14/16) | 47 | 105 | yes |
| 2026-05-08 | LO2 | 192 | 77 | 34 | 42 (21/21) | 53 | 52 | yes |
| 2026-05-15 | LO3 | 179 | 56 | 21 | 23 (22/1) | 32 | 95 |  |
| 2026-05-22 | LO4 | 154 | 79 | 32 | 45 (26/19) | 54 | 48 | yes |
| 2026-05-29 | LO5 | 157 | 65 | 19 | 31 (16/15) | 43 | 66 | yes |
| 2026-06-05 | LO1 | 163 | 55 | 26 | 27 (11/16) | 36 | 62 | yes |
| 2026-06-12 | LO2 | 150 | 55 | 22 | 26 (9/17) | 32 | 88 | yes |
| 2026-06-26 | LO4 | 190 | 44 | 14 | 15 (5/10) | 22 | 111 | yes |
| 2026-07-10 | LO2 | 196 | 41 | 18 | 19 (8/11) | 21 | 79 | yes |
| 2026-07-17 | LO3 | 174 | 51 | 17 | 21 (14/7) | 25 | 122 | yes |
| 2026-07-24 | LO4 | 198 | 69 | 20 | 22 (11/11) | 32 | 137 | yes |
| 2026-07-31 | LO5 | 196 | 58 | 16 | 27 (15/12) | 30 | 84 | yes |
| 2026-08-07 | LO1 | 185 | 48 | 22 | 25 (12/13) | 27 | 53 | yes |
| 2026-08-14 | LO2 | 169 | 42 | 11 | 11 (9/2) | 17 | 186 |  |
| 2026-08-21 | LO3 | 153 | 42 | 16 | 21 (14/7) | 24 | 59 | yes |
| 2026-08-28 | LO4 | 153 | 38 | 13 | 16 (11/5) | 19 | 116 | yes |
| 2026-09-04 | LO1 | 157 | 43 | 16 | 17 (9/8) | 23 | 92 | yes |
| 2026-09-11 | LO2 | 159 | 0 | 0 | 0 (0/0) | 0 | - |  |

## Verdict on TBBO

**TBBO is sufficient**: 109 of 117 dates clear the threshold. No bbo-1m upgrade needed.

## Store notes

`parquet/options_tbbo/root=R/` holds every record the parent request returned, including user-defined spread instruments (`UD:...`) that trade at net credits, so negative prices appear there. `parquet/options_tbbo_by_expiry/root=R/expiry=D/` is the outright-only view, joined to the definitions, which is what the smile fit should read. Bid and ask are `bid_px_00` / `ask_px_00` with sizes `bid_sz_00` / `ask_sz_00`; no mid is stored.

## Timestamp alignment (UNVERIFIED item 4)

Databento TBBO rows carry `ts_event` (matching-engine time) and `ts_recv` (capture time). `ts_event` is used. Kalshi 1-minute candles are keyed by `end_period_ts`, the END of the bar, so a Databento event at time t belongs to the Kalshi bar ending at ceil_minute(t); `db_common.kalshi_bar_end()` implements that. Kalshi settles at 14:30 ET (18:30 UTC in summer, 19:30 in winter) - the Kalshi close_time is used per event rather than a fixed UTC offset.
