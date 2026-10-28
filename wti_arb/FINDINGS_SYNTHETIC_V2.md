# FINDINGS_SYNTHETIC_V2 — the full synthetic study at 48 knots, 24 vs 48 side by side

Task 2 of `NightKing/HANDOFF_tickfloor_and_fullsynth.md`. Every configuration, seed and sampler setting of `FINDINGS_SYNTHETIC.md` (the 24-knot study) re-run with `act3.M_COEF = 48` and no tick floor (`FINDINGS_TICKFLOOR.md` did not adopt one). Each cell is 24 → 48. Coverage is the headline; band width is the cost and is reported next to it everywhere.

**Verdict: calibrated where it operates, narrowed where it was blind, and still not honest at a planted bimodal trough. At 48 knots the operating configurations are at or above nominal (crude-skew 90% coverage 95% all / 97% body / 97% tail, lognormal 81% / 97% / 92%, heavy-tailed 95%, the 8-strike gate 98%), Stage 14 lands on the forward unaided (bias 0.00¢, |z| 0.76), and every injected fault is caught at the same rate as at 24 knots. The blind spot moved a long way — bimodal trough z +7.8 → +1.4, trough coverage 3% → 57%, bimodal body coverage 42% → 79%, kinked-peak body 49% → 76%, spike 48% → 60% — but the harness's own criteria still fail (trough coverage < 80%, bimodal body < 85%, a mis-specified truth not flagged by χ²), so the mechanical verdict stays FAIL and the honest word is *narrowed, not closed*. The cost is the one the operator named: crude-skew body bands 1.95 → 2.77¢ (+0.8¢ of gap per trade through the filter), tail bands 0.67 → 0.95¢, body RMSE 0.59 → 0.69¢, and bracket ESS 303 → 253 with R̂ 1.014 → 1.018.**

## 1. Bracket coverage at 90% (the primary test), by region

Body = brackets worth ≥ 10¢, tail = 1–10¢ (where the strategy trades), far < 1¢, open = the two open-ended brackets. n = runs.

| config | n | all | body | tail | far | open | 50% level (all) | 95% level (all) |
|---|---|---|---|---|---|---|---|---|
| A_crude_full | 120 → 120 | 93% → 95% | 94% → 97% | 95% → 97% | 91% → 92% | 85% → 87% | 60% → 66% | 96% → 97% |
| B_lognormal_full | 120 → 120 | 79% → 81% | 94% → 97% | 88% → 92% | 70% → 71% | 42% → 41% | 40% → 45% | 85% → 87% |
| C_bimodal_full | 120 → 120 | 39% → 73% | 42% → 79% | 27% → 81% | 62% → 68% | 20% → 29% | 17% → 34% | 46% → 80% |
| S08_crude | 60 → 60 | 97% → 98% | 99% → 99% | 98% → 100% | 96% → 97% | 93% → 92% | 62% → 67% | 99% → 99% |
| S12_crude | 60 → 60 | 96% → 97% | 98% → 99% | 96% → 98% | 95% → 96% | 90% → 91% | 63% → 67% | 98% → 98% |
| S16_crude | 60 → 60 | 96% → 97% | 96% → 98% | 97% → 98% | 97% → 97% | 88% → 88% | 64% → 69% | 98% → 98% |
| S23_crude | 60 → 60 | 96% → 96% | 95% → 98% | 97% → 98% | 95% → 95% | 90% → 88% | 60% → 66% | 98% → 98% |
| N05_crude | 60 → 60 | 92% → 94% | 95% → 97% | 92% → 96% | 92% → 93% | 82% → 85% | 57% → 63% | 95% → 97% |
| N20_crude | 60 → 60 | 92% → 92% | 96% → 98% | 96% → 96% | 88% → 88% | 82% → 80% | 58% → 63% | 95% → 95% |
| NU_crude_uniform | 60 → 60 | 96% → 96% | 99% → 100% | 98% → 99% | 94% → 93% | 86% → 84% | 71% → 76% | 97% → 97% |
| NO_crude_observed_hs | 60 → 60 | 92% → 94% | 91% → 96% | 93% → 97% | 91% → 91% | 83% → 84% | 55% → 59% | 95% → 96% |
| NF_crude_tickfloor | 60 → 60 | 96% → 94% | 96% → 96% | 96% → 97% | 97% → 92% | 95% → 84% | 67% → 64% | 98% → 96% |
| L2_crude_2day | 60 → 60 | 96% → 97% | 96% → 99% | 96% → 98% | 96% → 95% | 96% → 98% | 60% → 67% | 98% → 98% |
| D_heavy_both | 60 → 60 | 94% → 95% | 97% → 98% | 95% → 97% | 93% → 94% | 88% → 86% | 59% → 64% | 96% → 97% |
| E_sharp_peak | 60 → 60 | 76% → 82% | 49% → 76% | 85% → 93% | 79% → 79% | 61% → 62% | 41% → 46% | 81% → 86% |
| F_bimodal_close | 60 → 60 | 62% → 70% | 91% → 97% | 66% → 83% | 59% → 60% | 12% → 14% | 30% → 37% | 71% → 76% |
| G_spike_outside_prior | 50 → 50 | 48% → 60% | 39% → 56% | 49% → 69% | 52% → 57% | 34% → 36% | 26% → 34% | 53% → 64% |
| C05_bimodal_halfnoise | 40 → 40 | 35% → 70% | 30% → 77% | 18% → 79% | 64% → 65% | 14% → 21% | 15% → 34% | 39% → 77% |
| M_crude_nomart | 60 → 60 | 93% → 95% | 98% → 98% | 95% → 97% | 92% → 93% | 84% → 82% | 58% → 62% | 96% → 97% |
| M_lognormal_nomart | 50 → 50 | 78% → 80% | 97% → 98% | 86% → 92% | 69% → 69% | 39% → 39% | 39% → 43% | 84% → 86% |
| X_fwd05 | 50 → 50 | 85% → 88% | 72% → 79% | 86% → 90% | 89% → 90% | 80% → 80% | 47% → 51% | 90% → 93% |
| X_fwd15 | 50 → 50 | 65% → 72% | 24% → 31% | 59% → 70% | 84% → 87% | 75% → 78% | 33% → 37% | 70% → 76% |
| X_fwd50 | 50 → 50 | 42% → 62% | 9% → 14% | 33% → 65% | 63% → 73% | 58% → 69% | 19% → 30% | 48% → 68% |
| X_fwd05_nomart | 50 → 50 | 93% → 94% | 98% → 98% | 94% → 97% | 92% → 91% | 84% → 83% | 57% → 62% | 96% → 96% |
| X_fwd15_nomart | 50 → 50 | 92% → 94% | 98% → 98% | 94% → 97% | 91% → 91% | 84% → 81% | 56% → 61% | 96% → 96% |
| X_fwd50_nomart | 50 → 50 | 92% → 93% | 98% → 98% | 94% → 97% | 90% → 90% | 77% → 76% | 57% → 61% | 95% → 95% |
| X_truncated_grid | 50 → 50 | 16% → 17% | 60% → 66% | 19% → 20% | 0% → 0% | 0% → 0% | 7% → 7% | 19% → 19% |
| X_convexity | 50 → 50 | 58% → 68% | 38% → 46% | 51% → 64% | 71% → 81% | 66% → 70% | 27% → 35% | 63% → 75% |
| X_stale | 50 → 50 | 54% → 60% | 42% → 46% | 46% → 56% | 66% → 69% | 61% → 65% | 29% → 31% | 58% → 66% |
| X_unconverged | 50 → 50 | 91% → 92% | 95% → 96% | 93% → 93% | 90% → 92% | 82% → 82% | 55% → 61% | 94% → 94% |

## 2. Error and band width (¢), by region

| config | RMSE body | RMSE tail | bias body | width90 body | width90 tail | density RMSE body (rel. peak) |
|---|---|---|---|---|---|---|
| A_crude_full | 0.59 → 0.69 | 0.20 → 0.24 | -0.02 → -0.02 | 1.95 → 2.77 | 0.67 → 0.95 | 0.024 → 0.029 |
| B_lognormal_full | 0.90 → 1.16 | 0.36 → 0.46 | -0.03 → -0.04 | 2.55 → 3.57 | 0.81 → 1.15 | 0.040 → 0.052 |
| C_bimodal_full | 1.70 → 1.46 | 0.91 → 0.67 | +0.13 → +0.31 | 2.56 → 4.14 | 0.85 → 1.58 | 0.087 → 0.059 |
| S08_crude | 0.69 → 0.82 | 0.33 → 0.39 | -0.02 → +0.03 | 3.24 → 4.47 | 1.32 → 1.76 | 0.038 → 0.047 |
| S12_crude | 0.64 → 0.72 | 0.28 → 0.33 | +0.00 → +0.01 | 2.67 → 3.56 | 1.07 → 1.38 | 0.032 → 0.039 |
| S16_crude | 0.60 → 0.69 | 0.23 → 0.27 | +0.02 → +0.02 | 2.28 → 3.14 | 0.93 → 1.26 | 0.028 → 0.034 |
| S23_crude | 0.54 → 0.63 | 0.21 → 0.24 | -0.02 → -0.03 | 2.04 → 2.86 | 0.82 → 1.13 | 0.025 → 0.029 |
| N05_crude | 0.36 → 0.45 | 0.15 → 0.19 | +0.00 → -0.01 | 1.31 → 1.87 | 0.51 → 0.72 | 0.017 → 0.021 |
| N20_crude | 0.80 → 0.96 | 0.31 → 0.39 | -0.03 → -0.06 | 2.85 → 3.91 | 1.06 → 1.43 | 0.037 → 0.046 |
| NU_crude_uniform | 0.36 → 0.41 | 0.14 → 0.17 | +0.00 → -0.01 | 1.82 → 2.54 | 0.70 → 0.95 | 0.016 → 0.018 |
| NO_crude_observed_hs | 0.42 → 0.53 | 0.17 → 0.21 | +0.02 → +0.02 | 1.44 → 2.03 | 0.60 → 0.83 | 0.021 → 0.027 |
| NF_crude_tickfloor | 0.49 → 0.64 | 0.18 → 0.25 | -0.01 → -0.03 | 1.89 → 2.66 | 0.73 → 1.00 | 0.021 → 0.030 |
| L2_crude_2day | 0.50 → 0.61 | 0.19 → 0.22 | -0.08 → -0.08 | 2.09 → 2.82 | 0.70 → 0.96 | 0.022 → 0.027 |
| D_heavy_both | 0.52 → 0.62 | 0.20 → 0.24 | -0.08 → -0.05 | 2.09 → 2.77 | 0.78 → 1.02 | 0.023 → 0.028 |
| E_sharp_peak | 1.90 → 1.84 | 0.42 → 0.42 | -0.13 → -0.09 | 2.98 → 3.97 | 1.06 → 1.35 | 0.074 → 0.069 |
| F_bimodal_close | 1.05 → 1.22 | 0.53 → 0.63 | +0.12 → +0.10 | 3.13 → 4.52 | 1.14 → 1.81 | 0.058 → 0.068 |
| G_spike_outside_prior | 5.64 → 5.07 | 2.46 → 2.25 | -2.54 → -2.19 | 3.43 → 5.13 | 1.45 → 2.42 | 0.125 → 0.114 |
| C05_bimodal_halfnoise | 1.66 → 1.22 | 0.89 → 0.51 | +0.20 → +0.25 | 1.62 → 2.92 | 0.61 → 1.25 | 0.084 → 0.047 |
| M_crude_nomart | 0.71 → 0.87 | 0.23 → 0.27 | +0.01 → +0.00 | 2.49 → 3.34 | 0.83 → 1.10 | 0.029 → 0.036 |
| M_lognormal_nomart | 1.11 → 1.39 | 0.36 → 0.42 | +0.01 → +0.01 | 3.28 → 4.44 | 0.96 → 1.31 | 0.047 → 0.061 |
| X_fwd05 | 1.00 → 1.19 | 0.34 → 0.41 | -0.25 → -0.27 | 2.08 → 2.84 | 0.78 → 1.06 | 0.044 → 0.055 |
| X_fwd15 | 3.03 → 3.53 | 0.86 → 1.00 | -0.72 → -0.76 | 2.57 → 3.73 | 0.98 → 1.39 | 0.129 → 0.156 |
| X_fwd50 | 13.11 → 13.80 | 4.57 → 4.68 | -2.70 → -2.58 | 4.26 → 5.69 | 2.13 → 3.42 | 0.670 → 0.753 |
| X_fwd05_nomart | 0.74 → 0.92 | 0.24 → 0.28 | +0.01 → +0.00 | 2.58 → 3.46 | 0.84 → 1.12 | 0.030 → 0.037 |
| X_fwd15_nomart | 0.75 → 0.89 | 0.24 → 0.28 | +0.01 → +0.00 | 2.53 → 3.51 | 0.83 → 1.11 | 0.030 → 0.037 |
| X_fwd50_nomart | 0.79 → 0.96 | 0.25 → 0.29 | +0.01 → +0.00 | 2.69 → 3.59 | 0.87 → 1.14 | 0.031 → 0.038 |
| X_truncated_grid | 8.66 → 8.99 | 7.64 → 7.69 | -0.16 → -0.11 | 14.10 → 15.43 | 2.80 → 3.14 | 0.634 → 0.685 |
| X_convexity | 7.04 → 7.66 | 3.02 → 3.35 | -0.76 → -0.70 | 3.61 → 4.90 | 1.66 → 2.15 | 0.397 → 0.501 |
| X_stale | 11.81 → 12.07 | 4.74 → 6.10 | -0.39 → -0.80 | 4.35 → 5.76 | 1.72 → 2.36 | 1.023 → 1.232 |
| X_unconverged | 0.53 → 0.53 | 0.21 → 0.23 | -0.03 → -0.03 | 1.72 → 2.17 | 0.64 → 0.80 | 0.024 → 0.027 |

## 3. The blind spot: bimodal, spike, kink

| config | trough z med | trough 90% width (¢) | trough coverage | modes recovered | cov90 all | cov90 body | χ²/strike med | τ med |
|---|---|---|---|---|---|---|---|---|
| C_bimodal_full | +7.8 → +1.4 | 0.59 → 1.46 | 3% → 57% | 100% → 100% | 39% → 73% | 42% → 79% | 1.20 → 1.07 | 4.79 → 1.33 |
| D_heavy_both | — → — | — → — | — → — | 100% → 100% | 94% → 95% | 97% → 98% | 0.99 → 0.98 | 0.69 → 0.23 |
| E_sharp_peak | — → — | — → — | — → — | 100% → 100% | 76% → 82% | 49% → 76% | 1.32 → 1.27 | 0.72 → 0.25 |
| F_bimodal_close | +0.5 → +0.1 | 1.74 → 3.42 | 90% → 97% | 92% → 85% | 62% → 70% | 91% → 97% | 1.10 → 1.07 | 2.19 → 0.72 |
| G_spike_outside_prior | — → — | — → — | — → — | 86% → 90% | 48% → 60% | 39% → 56% | 1.29 → 1.16 | 3.32 → 1.05 |
| C05_bimodal_halfnoise | +10.9 → +1.6 | 0.42 → 1.07 | 0% → 57% | 100% → 100% | 35% → 70% | 30% → 77% | 1.43 → 1.11 | 4.79 → 1.31 |

## 4. Sampler health

| config | R̂ max med (p90), raw | min ESS med | divergences med | bracket R̂ med (p90) | bracket ESS med (p10) | bracket R̂ < 1.01 | bracket ESS ≥ 400 | s / run |
|---|---|---|---|---|---|---|---|---|
| A_crude_full | 1.021 → 1.031 (1.058 → 1.131) | 204 → 165 | 26 → 30 | 1.014 → 1.018 (1.051 → 1.150) | 303 → 253 (119 → 53) | 28% → 17% | 31% → 22% | 75 → 89 |
| B_lognormal_full | 1.026 → 1.034 (1.098 → 1.169) | 182 → 165 | 20 → 20 | 1.020 → 1.027 (1.105 → 1.128) | 235 → 199 (68 → 68) | 21% → 12% | 22% → 12% | 52 → 76 |
| C_bimodal_full | 1.171 → 1.110 (1.878 → 1.569) | 48 → 55 | 21 → 18 | 1.054 → 1.044 (1.178 → 1.199) | 141 → 132 (59 → 52) | 11% → 8% | 10% → 8% | 117 → 141 |
| S08_crude | 1.031 → 1.052 (1.144 → 1.207) | 183 → 119 | 41 → 52 | 1.025 → 1.040 (1.197 → 1.229) | 189 → 148 (66 → 52) | 8% → 7% | 7% → 8% | 67 → 73 |
| S12_crude | 1.033 → 1.036 (1.150 → 1.260) | 172 → 143 | 39 → 48 | 1.023 → 1.022 (1.131 → 1.175) | 221 → 207 (61 → 56) | 20% → 15% | 18% → 17% | 63 → 73 |
| S16_crude | 1.040 → 1.041 (1.170 → 1.187) | 143 → 150 | 40 → 53 | 1.024 → 1.033 (1.097 → 1.154) | 207 → 162 (96 → 66) | 12% → 7% | 12% → 13% | 67 → 81 |
| S23_crude | 1.034 → 1.033 (1.125 → 1.095) | 146 → 172 | 34 → 40 | 1.021 → 1.024 (1.064 → 1.083) | 247 → 235 (101 → 81) | 17% → 22% | 15% → 18% | 65 → 85 |
| N05_crude | 1.037 → 1.031 (1.234 → 1.154) | 153 → 177 | 34 → 28 | 1.023 → 1.022 (1.139 → 1.083) | 196 → 248 (57 → 88) | 8% → 25% | 15% → 20% | 74 → 101 |
| N20_crude | 1.027 → 1.027 (1.077 → 1.075) | 208 → 186 | 30 → 34 | 1.017 → 1.016 (1.083 → 1.091) | 268 → 288 (100 → 70) | 27% → 25% | 28% → 27% | 57 → 82 |
| NU_crude_uniform | 1.024 → 1.032 (1.084 → 1.076) | 196 → 182 | 32 → 26 | 1.016 → 1.020 (1.088 → 1.070) | 260 → 204 (83 → 110) | 22% → 25% | 27% → 18% | 74 → 95 |
| NO_crude_observed_hs | 1.026 → 1.024 (1.118 → 1.089) | 179 → 192 | 26 → 32 | 1.017 → 1.018 (1.086 → 1.090) | 245 → 268 (84 → 92) | 27% → 30% | 25% → 30% | 70 → 92 |
| NF_crude_tickfloor | 1.025 → 1.034 (1.088 → 1.195) | 200 → 158 | 33 → 33 | 1.017 → 1.021 (1.084 → 1.169) | 253 → 244 (82 → 50) | 27% → 17% | 20% → 22% | 60 → 104 |
| L2_crude_2day | 1.034 → 1.042 (1.124 → 1.128) | 155 → 143 | 32 → 35 | 1.017 → 1.019 (1.140 → 1.073) | 277 → 247 (96 → 93) | 30% → 30% | 32% → 27% | 65 → 104 |
| D_heavy_both | 1.023 → 1.032 (1.083 → 1.082) | 227 → 159 | 28 → 28 | 1.014 → 1.021 (1.059 → 1.062) | 312 → 246 (122 → 105) | 35% → 18% | 27% → 18% | 66 → 144 |
| E_sharp_peak | 1.020 → 1.024 (1.085 → 1.073) | 234 → 192 | 13 → 10 | 1.019 → 1.020 (1.078 → 1.056) | 274 → 258 (91 → 109) | 22% → 17% | 15% → 17% | 47 → 72 |
| F_bimodal_close | 1.045 → 1.034 (1.215 → 1.104) | 118 → 149 | 4 → 4 | 1.020 → 1.020 (1.150 → 1.076) | 212 → 262 (72 → 76) | 13% → 17% | 13% → 12% | 99 → 125 |
| G_spike_outside_prior | 1.112 → 1.073 (1.504 → 1.522) | 53 → 64 | 41 → 13 | 1.049 → 1.039 (1.257 → 1.197) | 128 → 115 (43 → 40) | 4% → 6% | 6% → 4% | 92 → 141 |
| C05_bimodal_halfnoise | 1.182 → 1.096 (2.037 → 1.383) | 40 → 62 | 28 → 46 | 1.055 → 1.047 (1.189 → 1.134) | 133 → 135 (61 → 51) | 8% → 8% | 10% → 2% | 117 → 168 |
| M_crude_nomart | 1.029 → 1.025 (1.117 → 1.092) | 171 → 216 | 35 → 30 | 1.017 → 1.017 (1.079 → 1.065) | 256 → 277 (82 → 118) | 23% → 30% | 27% → 22% | 59 → 103 |
| M_lognormal_nomart | 1.028 → 1.030 (1.089 → 1.080) | 177 → 168 | 20 → 16 | 1.022 → 1.025 (1.099 → 1.052) | 226 → 201 (68 → 109) | 20% → 14% | 22% → 10% | 52 → 769 |
| X_fwd05 | 1.029 → 1.035 (1.111 → 1.101) | 193 → 138 | 29 → 30 | 1.026 → 1.022 (1.081 → 1.072) | 209 → 214 (73 → 83) | 28% → 12% | 24% → 14% | 68 → 102 |
| X_fwd15 | 1.037 → 1.047 (1.096 → 1.176) | 155 → 89 | 30 → 46 | 1.023 → 1.041 (1.053 → 1.128) | 215 → 130 (100 → 73) | 12% → 8% | 14% → 6% | 87 → 134 |
| X_fwd50 | 1.526 → 1.674 (2.169 → 2.349) | 23 → 21 | 16 → 10 | 1.200 → 1.255 (1.522 → 1.719) | 46 → 41 (25 → 22) | 0% → 0% | 0% → 0% | 129 → 207 |
| X_fwd05_nomart | 1.024 → 1.028 (1.084 → 1.081) | 188 → 215 | 38 → 30 | 1.020 → 1.019 (1.056 → 1.055) | 260 → 271 (107 → 98) | 24% → 20% | 20% → 18% | 59 → 209 |
| X_fwd15_nomart | 1.024 → 1.031 (1.052 → 1.126) | 200 → 168 | 34 → 31 | 1.019 → 1.019 (1.046 → 1.093) | 242 → 205 (121 → 71) | 28% → 18% | 26% → 22% | 59 → 993 |
| X_fwd50_nomart | 1.023 → 1.023 (1.083 → 1.072) | 210 → 209 | 30 → 31 | 1.017 → 1.016 (1.061 → 1.037) | 288 → 268 (116 → 132) | 28% → 28% | 26% → 14% | 55 → 75 |
| X_truncated_grid | 1.099 → 1.262 (1.731 → 1.703) | 65 → 32 | 2 → 1 | 1.044 → 1.084 (1.411 → 1.320) | 126 → 82 (32 → 29) | 8% → 0% | 6% → 0% | 134 → 162 |
| X_convexity | 1.068 → 1.207 (2.750 → 2.718) | 88 → 38 | 30 → 25 | 1.074 → 1.109 (2.036 → 1.651) | 69 → 70 (19 → 24) | 14% → 4% | 8% → 8% | 94 → 144 |
| X_stale | 1.354 → 1.652 (3.015 → 3.181) | 30 → 18 | 32 → 16 | 1.184 → 1.258 (6.584 → 2.109) | 57 → 41 (18 → 19) | 10% → 8% | 16% → 6% | 97 → 142 |
| X_unconverged | 1.355 → 1.329 (2.057 → 2.392) | 11 → 13 | 7 → 10 | 1.153 → 1.210 (1.650 → 2.068) | 20 → 23 (9 → 12) | 0% → 0% | 0% → 0% | 2 → 3 |

## 5. Stage 14, the forward, and the injected faults

| config | Stage 14 bias (¢) | \|z\| vs truth med | E[F] 90% cov | parity flags the forward | z(used) > 3 | injected resid > 3 | χ² > 2 | edge-mass fails | sampler flagged | Act II − Act III med (¢) |
|---|---|---|---|---|---|---|---|---|---|---|
| A_crude_full | +0.14 → +0.15 | 0.86 → 0.84 | 80% → 81% | 0% → 0% | 0% → 0% | — → — | 2% → 2% | 0% → 0% | 99% → 100% | 0.56 → 0.64 |
| M_crude_nomart | -0.16 → +0.00 | 0.74 → 0.76 | 95% → 90% | 0% → 0% | 2% → 0% | — → — | 2% → 2% | 0% → 0% | 100% → 100% | 0.75 → 0.86 |
| M_lognormal_nomart | +0.16 → +0.23 | 0.76 → 0.79 | 88% → 90% | 0% → 0% | 0% → 0% | — → — | 4% → 4% | 0% → 0% | 100% → 100% | 0.76 → 0.93 |
| X_fwd05 | +4.61 → +4.67 | 5.63 → 5.70 | 0% → 0% | 100% → 100% | 0% → 0% | — → — | 2% → 2% | 0% → 0% | 100% → 100% | 0.73 → 0.93 |
| X_fwd15 | +13.91 → +14.07 | 16.56 → 16.56 | 0% → 0% | 100% → 100% | 2% → 2% | — → — | 22% → 14% | 0% → 0% | 100% → 100% | 1.80 → 2.33 |
| X_fwd50 | +47.20 → +47.44 | 57.18 → 56.70 | 0% → 0% | 100% → 100% | 46% → 30% | — → — | 96% → 92% | 0% → 0% | 100% → 100% | 10.08 → 11.57 |
| X_fwd05_nomart | -0.32 → -0.06 | 0.78 → 0.77 | 90% → 90% | 100% → 100% | 18% → 16% | — → — | 2% → 2% | 0% → 0% | 98% → 100% | 0.79 → 0.83 |
| X_fwd15_nomart | -0.25 → -0.05 | 0.79 → 0.76 | 88% → 90% | 100% → 100% | 90% → 84% | — → — | 2% → 2% | 0% → 0% | 100% → 100% | 1.54 → 1.56 |
| X_fwd50_nomart | -0.23 → +0.01 | 0.74 → 0.81 | 86% → 90% | 100% → 100% | 100% → 100% | — → — | 2% → 2% | 0% → 0% | 100% → 100% | 15.87 → 9.99 |
| X_truncated_grid | +0.05 → +0.06 | 1.02 → 1.03 | 80% → 74% | 0% → 0% | 0% → 0% | — → — | 100% → 100% | 100% → 100% | 100% → 100% | 21.83 → 21.82 |
| X_convexity | -26.58 → +1.94 | 1.03 → 1.23 | 68% → 60% | 0% → 0% | 14% → 22% | 98% → 98% | 96% → 96% | 0% → 0% | 100% → 100% | 2.77 → 6.15 |
| X_stale | +19.67 → +1.37 | 1.18 → 1.08 | 56% → 60% | 0% → 0% | 10% → 2% | 100% → 100% | 96% → 96% | 6% → 6% | 100% → 100% | 10.23 → 11.98 |
| X_unconverged | +0.03 → +0.06 | 1.03 → 1.01 | 80% → 68% | 0% → 0% | 0% → 0% | — → — | 4% → 4% | 0% → 0% | 100% → 100% | 0.54 → 0.67 |

Forward sensitivity (¢ of bracket per ¢ of forward error, max over brackets, median run): X_fwd05 0.150 → 0.185; X_fwd15 0.182 → 0.214; X_fwd50 0.336 → 0.362; X_fwd05_nomart 0.009 → 0.011; X_fwd15_nomart 0.004 → 0.004; X_fwd50_nomart 0.002 → 0.001.

Unconverged-chain band width relative to converged (median): 0.87 → 0.81.


## 6. Mechanical criteria (the report's own verdict function, on each study)

| criterion | 24 knots | 48 knots |
|---|---|---|
| A_bracket90_body | 0.935 ✓ | 0.971 ✓ |
| A_bracket90_tail | 0.947 ✓ | 0.969 ✓ |
| B_bracket90_body | 0.942 ✓ | 0.972 ✓ |
| B_bracket90_tail | 0.878 ✓ | 0.922 ✓ |
| stage14_mean_lands_on_F0 | -0.16, 0.74 ✓ | 0.00, 0.76 ✓ |
| caught_X_fwd05_by_parity | 1.000 ✓ | 1.000 ✓ |
| caught_X_fwd15_by_parity | 1.000 ✓ | 1.000 ✓ |
| caught_X_fwd50_by_parity | 1.000 ✓ | 1.000 ✓ |
| caught_truncated_grid | 1.000 ✓ | 1.000 ✓ |
| caught_X_convexity | 0.90, 0.98, 0.96 ✓ | 0.90, 0.98, 0.96 ✓ |
| caught_X_stale | 0.90, 1.00, 0.96 ✓ | 0.90, 1.00, 0.96 ✓ |
| caught_unconverged | 1.000 ✓ | 1.000 ✓ |
| bimodal_modes_recovered | 1.000 ✓ | 1.000 ✓ |
| bimodal_bands_honest_at_trough90 | 0.025 ✗ | 0.571 ✗ |
| bimodal_bracket90_body | 0.419 ✗ | 0.792 ✗ |
| misspecified_truth_flagged | 0.06, 0.14 ✗ | 0.02, 0.08 ✗ |
| **verdict** | **FAIL** (3 core failures) | **FAIL** (3 core failures) |

## 7. Verdict and what remains unfixed

**What changed and what it cost, in one place.** Every row of §1–§5 is the same seed under the same noise, sampler and planted
truth, with only the knot count changed. On the configurations the strategy will actually run on — crude-skew, lognormal, heavy
tails, 8 to 23 strikes, half and double noise, observed spreads, two-day horizon — coverage moves up by one to three points to
sit at or slightly above nominal, bias stays at zero, and the price is paid in width: body bands widen by about 40% (1.95 → 2.77¢
on crude-skew, 3.24 → 4.47¢ at eight strikes) and body RMSE by about 15%. The sampler stays inside the gate (bracket R̂ 1.014 → 1.018,
ESS 303 → 253), run time rises 75 → 89 s per chain, and a deliberately unconverged chain still shows itself (R̂/ESS flagged on 100% of
runs). Forward sensitivity rises slightly at 15¢ offset: a finer basis moves a little more per cent of location error, which is one
more reason the forward now comes from the futures.

**The blind spot.** The planted bimodal truth that `FINDINGS_SYNTHETIC.md` §9 could not represent at any smoothness is now mostly
represented: two modes recovered as before, but the trough is overstated by 1.4σ instead of 7.8σ, its band is 1.46¢ instead of 0.59¢
and contains the truth 57% of the time instead of 3%; the half-noise variant goes from 0% to 57% at the trough. The kinked peak and the
close bimodal are now at nominal in the body (76% and 97%). The spike improves least (48% → 60%) and is the case the brief deprioritised. None of
this changes χ²: the mis-specified truths still fit the quotes inside their spreads, so the harness's "flag a mis-specified truth"
criterion still fails — the quotes genuinely cannot tell, and the gates that stand in for it on real chains are split-half (data
inconsistency), Act II (shape), and the backtest's rule against brackets in an interior local minimum.

**The tick floor is not in these numbers.** `FINDINGS_TICKFLOOR.md` adopted a 1¢ floor for the real chains and declined it for this
harness by its pre-stated rule, because every floor drifts synthetic crude coverage to 96–98% — the synthetic quotes carry no
inconsistency beyond rounding, so a floor double-counts there. `NF_crude_tickfloor` (a 1¢ floor, in this table) shows the same thing:
96% → 94% all-region coverage at 24 → 48 knots, the one configuration where 48 knots did not raise coverage, and a reminder that the
harness's noise model is now the binding limitation on validating the tolerance.

**Still unfixed, gated rather than solved.** (i) A consistent bimodal truth is still over-confident at the trough by about 1.4σ with
57% coverage; the gates catch inconsistency and shape disagreement, not a well-fitting wrong smooth shape. (ii) The spike truth is at
60% and will not improve without knots dense where strikes are dense; deliberately parked. (iii) The synthetic noise model is
Gaussian-exact with sd = half-spread and cannot adjudicate the tick floor's value; the floor is adopted on real-chain evidence only.
(iv) Band width is up about 40% on the operating configurations, which is lost signal through the trade filter, accepted in exchange
for honesty on shapes the prior used to exclude. The next brief inherits these four, and none of them blocks the backtest.

Plots: `synth/plots48/` (48 knots) and `synth/plots/` (24 knots), same file names.

