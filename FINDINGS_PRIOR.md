# FINDINGS_PRIOR — locally adaptive priors on the log-density's second differences

Part A of `NightKing/HANDOFF_prior_fix.md`. Every candidate runs through the synthetic harness (`synth/prior_study.py`) on the same planted densities, real strike grids, noise model and seeds as `FINDINGS_SYNTHETIC.md`; the baseline row is the current Gaussian prior's runs on disk restricted to the same seeds, so every comparison is paired. Sampler: 4 × (400 + 400) NUTS, unchanged.

| candidate | prior on d = D2·θ | extra parameters | how τ is handled |
|---|---|---|---|
| `base` | d_j ~ N(0, τ²) | none | integrated out (1-d quadrature) |
| `t3` | d_j ~ τ·t₃ (Gaussian with inverse-gamma local scale, integrated per increment) | none | integrated out (quadrature over a product of t densities) |
| `t1` | d_j ~ τ·t₁ (Cauchy increments) | none | as `t3` |
| `hs` | d_j = λ_j z_j, z_j ~ N(0,1), λ_j ~ C⁺(0, 0.5), non-centred | 22 log-scales | none (a global τ with local λ_j ran down the flat τ→0, λ→∞ ridge) |
| `m36` / `m48` | as `base` with 36 / 48 knots (0.47 / 0.35 vol-scales between knots instead of 0.7) | +12 / +24 coefficients | as `base` |
| `m48t3` | Student-t ν=3 increments on 48 knots | +24 coefficients | as `t3` |

**VERDICT_PLACEHOLDER**

## 1. Checklist, per candidate

Must-not-regress items are judged against the baseline on the same seeds (coverage within 3 points, RMSE within 0.1¢, sampler within the stated gate); must-improve items against the fixed targets (coverage ≥ 80%, trough |z| ≤ 2). Tolerances were fixed before the runs.

| item | baseline | Student-t ν=3, 24 knots | Student-t ν=1, 24 knots | horseshoe, 24 knots |
|---|---|---|---|---|
| A_cov90_all | 92% | 92% ✓ | 91% ✓ | 78% ✗ |
| A_cov90_body | 95% | 93% ✓ | 94% ✓ | 76% ✗ |
| A_cov90_tail | 95% | 94% ✓ | 94% ✓ | 80% ✗ |
| A_rmse_body | 0.57 | 0.64 ✓ | 0.77 ✗ | 0.94 ✗ |
| A_rmse_tail | 0.21 | 0.23 ✓ | 0.27 ✓ | 0.31 ✗ |
| B_cov90_all | 76% | 78% ✓ | —  | —  |
| S08_cov90_all | 97% | 96% ✓ | 92% ✗ | 76% ✗ |
| M_stage14_z | 0.72 | 0.72 ✓ | —  | —  |
| X_fwd15_caught_parity | 100% | 100% ✓ | —  | —  |
| X_stale_caught_resid | 100% | 100% ✓ | —  | —  |
| X_convexity_caught_resid | 100% | 100% ✓ | —  | —  |
| X_truncated_caught_edge | 100% | 100% ✓ | —  | —  |
| X_unconverged_caught | 100% | 100% ✓ | —  | —  |
| A_bracket_rhat | 1.02 | 1.02 ✓ | 1.05 ✗ | 1.62 ✗ |
| A_bracket_ess | 290 | 198 ✓ | 96 ✗ | 27 ✗ |
| C_trough_cov90 | 0% | 5% ✗ | 10% ✗ | 10% ✗ |
| C_trough_absz | 6.82 | 6.39 ✗ | 6.73 ✗ | 7.60 ✗ |
| C_cov90_all | 42% | 43% ✗ | 42% ✗ | 22% ✗ |
| G_cov90_all | 46% | 47% ✗ | —  | —  |
| E_cov90_body | 53% | 52% ✗ | —  | —  |
| **verdict** | | **NO IMPROVEMENT** | **REJECTED (regresses: A_rmse_body, S08_cov90_all, A_bracket_rhat, A_bracket_ess)** | **REJECTED (regresses: A_cov90_all, A_cov90_body, A_cov90_tail, A_rmse_body, A_rmse_tail, S08_cov90_all, A_bracket_rhat, A_bracket_ess)** |

## 2. Bracket coverage and error, by planted density

90% bracket coverage (all / body ≥10¢ / tail 1–10¢), bracket RMSE (¢) body / tail, mean 90% band width (¢) body / tail, bias body (¢).

| config | candidate | n | cov90 all | body | tail | far | RMSE body | tail | width body | tail | bias body |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A_crude_full | Gaussian, 24 knots (current) | 40 | 92% | 95% | 95% | 91% | 0.57 | 0.21 | 1.90 | 0.74 | -0.03 |
| A_crude_full | Student-t ν=3, 24 knots | 40 | 92% | 93% | 94% | 90% | 0.64 | 0.23 | 2.01 | 0.75 | -0.03 |
| A_crude_full | Student-t ν=1, 24 knots | 20 | 91% | 94% | 94% | 89% | 0.77 | 0.27 | 2.19 | 0.78 | -0.04 |
| A_crude_full | horseshoe, 24 knots | 20 | 78% | 76% | 80% | 80% | 0.94 | 0.31 | 1.68 | 0.59 | -0.04 |
| B_lognormal_full | Gaussian, 24 knots (current) | 40 | 76% | 97% | 85% | 66% | 0.65 | 0.34 | 2.41 | 0.88 | -0.05 |
| B_lognormal_full | Student-t ν=3, 24 knots | 40 | 78% | 96% | 86% | 69% | 0.62 | 0.34 | 2.36 | 0.89 | -0.05 |
| C_bimodal_full | Gaussian, 24 knots (current) | 40 | 42% | 41% | 29% | 65% | 1.77 | 0.96 | 2.46 | 0.94 | +0.11 |
| C_bimodal_full | Student-t ν=3, 24 knots | 40 | 43% | 40% | 31% | 65% | 1.82 | 0.95 | 2.50 | 0.95 | +0.12 |
| C_bimodal_full | Student-t ν=1, 24 knots | 20 | 42% | 49% | 29% | 63% | 2.04 | 0.95 | 2.85 | 0.98 | +0.16 |
| C_bimodal_full | horseshoe, 24 knots | 20 | 22% | 34% | 18% | 25% | 2.14 | 1.48 | 2.27 | 1.22 | +0.02 |
| C05_bimodal_halfnoise | Gaussian, 24 knots (current) | 30 | 36% | 30% | 18% | 65% | 1.71 | 0.89 | 1.67 | 0.61 | +0.19 |
| C05_bimodal_halfnoise | Student-t ν=3, 24 knots | 30 | 33% | 30% | 16% | 60% | 1.73 | 0.89 | 1.64 | 0.59 | +0.21 |
| F_bimodal_close | Gaussian, 24 knots (current) | 30 | 62% | 91% | 68% | 56% | 1.02 | 0.54 | 3.00 | 1.16 | +0.05 |
| F_bimodal_close | Student-t ν=3, 24 knots | 30 | 63% | 89% | 68% | 60% | 1.04 | 0.56 | 3.05 | 1.23 | +0.00 |
| F_bimodal_close | Student-t ν=1, 24 knots | 20 | 62% | 87% | 63% | 62% | 1.30 | 0.67 | 3.10 | 1.24 | -0.10 |
| F_bimodal_close | horseshoe, 24 knots | 20 | 34% | 54% | 44% | 24% | 1.60 | 1.87 | 2.76 | 1.55 | -0.30 |
| E_sharp_peak | Gaussian, 24 knots (current) | 30 | 74% | 53% | 86% | 76% | 1.88 | 0.43 | 3.06 | 1.09 | -0.12 |
| E_sharp_peak | Student-t ν=3, 24 knots | 30 | 74% | 52% | 87% | 75% | 1.88 | 0.41 | 3.11 | 1.03 | -0.13 |
| G_spike_outside_prior | Gaussian, 24 knots (current) | 30 | 46% | 37% | 49% | 50% | 5.65 | 2.52 | 3.30 | 1.45 | -2.28 |
| G_spike_outside_prior | Student-t ν=3, 24 knots | 30 | 47% | 33% | 49% | 51% | 5.66 | 2.53 | 3.24 | 1.38 | -2.30 |
| D_heavy_both | Gaussian, 24 knots (current) | 30 | 93% | 95% | 95% | 93% | 0.53 | 0.22 | 2.11 | 0.81 | -0.11 |
| D_heavy_both | Student-t ν=3, 24 knots | 30 | 94% | 96% | 95% | 94% | 0.57 | 0.22 | 2.19 | 0.79 | -0.09 |
| S08_crude | Gaussian, 24 knots (current) | 30 | 97% | 100% | 98% | 96% | 0.67 | 0.37 | 3.29 | 1.41 | -0.05 |
| S08_crude | Student-t ν=3, 24 knots | 30 | 96% | 98% | 96% | 96% | 0.81 | 0.43 | 3.63 | 1.46 | +0.01 |
| S08_crude | Student-t ν=1, 24 knots | 20 | 92% | 89% | 90% | 95% | 1.01 | 0.47 | 3.67 | 1.41 | +0.19 |
| S08_crude | horseshoe, 24 knots | 20 | 76% | 71% | 69% | 84% | 1.20 | 0.52 | 2.76 | 1.01 | +0.18 |
| M_crude_nomart | Gaussian, 24 knots (current) | 30 | 92% | 98% | 95% | 89% | 0.75 | 0.23 | 2.47 | 0.86 | +0.02 |
| M_crude_nomart | Student-t ν=3, 24 knots | 30 | 92% | 96% | 94% | 89% | 0.79 | 0.25 | 2.57 | 0.87 | +0.05 |
| X_fwd15 | Gaussian, 24 knots (current) | 30 | 65% | 26% | 60% | 83% | 3.13 | 0.92 | 2.54 | 1.02 | -0.82 |
| X_fwd15 | Student-t ν=3, 24 knots | 30 | 64% | 26% | 60% | 82% | 3.16 | 0.92 | 2.56 | 1.03 | -0.82 |
| X_stale | Gaussian, 24 knots (current) | 30 | 54% | 38% | 45% | 69% | 11.66 | 3.39 | 2.90 | 1.43 | -0.33 |
| X_stale | Student-t ν=3, 24 knots | 30 | 55% | 39% | 45% | 72% | 11.54 | 4.57 | 3.27 | 1.31 | -0.40 |
| X_convexity | Gaussian, 24 knots (current) | 30 | 53% | 35% | 45% | 67% | 6.61 | 2.91 | 2.95 | 1.30 | -0.40 |
| X_convexity | Student-t ν=3, 24 knots | 30 | 52% | 35% | 44% | 66% | 6.61 | 2.92 | 2.99 | 1.31 | -0.39 |
| X_truncated_grid | Gaussian, 24 knots (current) | 30 | 15% | 54% | 18% | 0% | 9.15 | 7.88 | 13.31 | 2.62 | -0.14 |
| X_truncated_grid | Student-t ν=3, 24 knots | 30 | 14% | 58% | 16% | 0% | 8.19 | 7.78 | 11.56 | 2.29 | -0.21 |
| X_unconverged | Gaussian, 24 knots (current) | 30 | 90% | 94% | 93% | 88% | 0.57 | 0.22 | 1.72 | 0.66 | -0.04 |
| X_unconverged | Student-t ν=3, 24 knots | 30 | 54% | 44% | 47% | 62% | 1.63 | 0.41 | 1.11 | 0.42 | +0.02 |

## 3. The blind spot: bimodal, spiked and kinked truths

Trough = the bracket between the two humps where the truth is lowest: z of the posterior median against the truth (in units of the 90% band / 3.29), the band's width and whether it contains the truth. Modes = posterior-mean mode count matches the truth.

| config | candidate | n | trough z med | trough 90% width (¢) | trough coverage | cov90 all | cov90 body | modes recovered | posterior modes | density RMSE body (rel. peak) | τ med | χ²/strike med |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_bimodal_full | Gaussian, 24 knots (current) | 40 | +6.8 | 0.69 | 0% | 42% | 41% | 100% | {'2': 40} | 0.088 | 4.95 | 1.08 |
| C_bimodal_full | Student-t ν=3, 24 knots | 40 | +6.4 | 0.68 | 5% | 43% | 40% | 100% | {'2': 40} | 0.088 | 3.43 | 1.10 |
| C_bimodal_full | Student-t ν=1, 24 knots | 20 | +6.7 | 0.70 | 10% | 42% | 49% | 100% | {'2': 20} | 0.092 | 1.79 | 1.12 |
| C_bimodal_full | horseshoe, 24 knots | 20 | +7.6 | 0.61 | 10% | 22% | 34% | 95% | {'2': 19, '3': 1} | 0.102 | 0.33 | 1.15 |
| C05_bimodal_halfnoise | Gaussian, 24 knots (current) | 30 | +11.2 | 0.39 | 0% | 36% | 30% | 100% | {'2': 30} | 0.085 | 4.87 | 1.44 |
| C05_bimodal_halfnoise | Student-t ν=3, 24 knots | 30 | +11.3 | 0.41 | 0% | 33% | 30% | 100% | {'2': 30} | 0.085 | 3.38 | 1.48 |
| G_spike_outside_prior | Gaussian, 24 knots (current) | 30 | — | — | — | 46% | 37% | 83% | {'1': 5, '2': 25} | 0.135 | 3.43 | 1.25 |
| G_spike_outside_prior | Student-t ν=3, 24 knots | 30 | — | — | — | 47% | 33% | 83% | {'1': 5, '2': 25} | 0.133 | 2.19 | 1.26 |
| E_sharp_peak | Gaussian, 24 knots (current) | 30 | — | — | — | 74% | 53% | 100% | {'1': 30} | 0.075 | 0.73 | 1.36 |
| E_sharp_peak | Student-t ν=3, 24 knots | 30 | — | — | — | 74% | 52% | 100% | {'1': 30} | 0.075 | 0.48 | 1.38 |
| F_bimodal_close | Gaussian, 24 knots (current) | 30 | +0.6 | 1.81 | 90% | 62% | 91% | 90% | {'1': 3, '2': 27} | 0.056 | 2.08 | 1.10 |
| F_bimodal_close | Student-t ν=3, 24 knots | 30 | +0.7 | 1.87 | 87% | 63% | 89% | 70% | {'1': 9, '2': 21} | 0.058 | 1.79 | 1.09 |
| F_bimodal_close | Student-t ν=1, 24 knots | 20 | +0.9 | 1.99 | 85% | 62% | 87% | 55% | {'1': 9, '2': 11} | 0.070 | 1.00 | 1.07 |
| F_bimodal_close | horseshoe, 24 knots | 20 | +1.0 | 1.38 | 55% | 34% | 54% | 55% | {'1': 9, '2': 11} | 0.094 | 0.30 | 1.03 |
| D_heavy_both | Gaussian, 24 knots (current) | 30 | — | — | — | 93% | 95% | 100% | {'1': 30} | 0.025 | 0.69 | 1.08 |
| D_heavy_both | Student-t ν=3, 24 knots | 30 | — | — | — | 94% | 96% | 100% | {'1': 30} | 0.026 | 0.48 | 1.08 |

## 4. Sampler health (the acceptance gate)

| config | candidate | n | R̂ max med (p90), raw | min ESS med (p10) | divergences med | bracket R̂ med (p90) | bracket ESS med (p10) | s / run |
|---|---|---|---|---|---|---|---|---|
| A_crude_full | Gaussian, 24 knots (current) | 40 | 1.024 (1.088) | 199 (98) | 23 | 1.016 (1.055) | 290 (119) | 68 |
| A_crude_full | Student-t ν=3, 24 knots | 40 | 1.053 (1.157) | 100 (45) | 26 | 1.023 (1.087) | 198 (77) | 117 |
| A_crude_full | Student-t ν=1, 24 knots | 20 | 1.139 (2.022) | 37 (20) | 26 | 1.051 (1.224) | 96 (33) | 129 |
| A_crude_full | horseshoe, 24 knots | 20 | 4.160 (5.353) | 13 (13) | 6 | 1.623 (2.269) | 27 (20) | 123 |
| B_lognormal_full | Gaussian, 24 knots (current) | 40 | 1.027 (1.148) | 215 (53) | 22 | 1.020 (1.094) | 238 (73) | 46 |
| B_lognormal_full | Student-t ν=3, 24 knots | 40 | 1.045 (1.173) | 126 (54) | 20 | 1.027 (1.105) | 202 (64) | 113 |
| C_bimodal_full | Gaussian, 24 knots (current) | 40 | 1.134 (1.691) | 52 (20) | 16 | 1.044 (1.136) | 147 (74) | 118 |
| C_bimodal_full | Student-t ν=3, 24 knots | 40 | 1.133 (1.451) | 53 (24) | 30 | 1.049 (1.188) | 96 (50) | 208 |
| C_bimodal_full | Student-t ν=1, 24 knots | 20 | 1.452 (2.754) | 25 (15) | 8 | 1.087 (1.213) | 86 (45) | 159 |
| C_bimodal_full | horseshoe, 24 knots | 20 | 4.173 (6.403) | 13 (12) | 4 | 1.477 (1.888) | 31 (18) | 117 |
| C05_bimodal_halfnoise | Gaussian, 24 knots (current) | 30 | 1.171 (1.996) | 41 (16) | 42 | 1.053 (1.189) | 133 (61) | 117 |
| C05_bimodal_halfnoise | Student-t ν=3, 24 knots | 30 | 1.194 (1.591) | 48 (24) | 34 | 1.104 (1.330) | 70 (37) | 211 |
| F_bimodal_close | Gaussian, 24 knots (current) | 30 | 1.043 (1.215) | 133 (48) | 16 | 1.020 (1.253) | 225 (75) | 80 |
| F_bimodal_close | Student-t ν=3, 24 knots | 30 | 1.067 (1.147) | 99 (46) | 9 | 1.027 (1.101) | 165 (74) | 186 |
| F_bimodal_close | Student-t ν=1, 24 knots | 20 | 1.283 (1.941) | 26 (18) | 4 | 1.073 (1.288) | 85 (30) | 160 |
| F_bimodal_close | horseshoe, 24 knots | 20 | 3.701 (5.809) | 14 (12) | 8 | 1.429 (2.026) | 36 (20) | 116 |
| E_sharp_peak | Gaussian, 24 knots (current) | 30 | 1.022 (1.093) | 223 (84) | 14 | 1.021 (1.078) | 226 (72) | 49 |
| E_sharp_peak | Student-t ν=3, 24 knots | 30 | 1.041 (1.103) | 145 (58) | 17 | 1.030 (1.065) | 192 (78) | 81 |
| G_spike_outside_prior | Gaussian, 24 knots (current) | 30 | 1.146 (1.504) | 47 (24) | 41 | 1.054 (1.257) | 128 (40) | 94 |
| G_spike_outside_prior | Student-t ν=3, 24 knots | 30 | 1.093 (1.456) | 74 (21) | 19 | 1.043 (1.175) | 143 (48) | 148 |
| D_heavy_both | Gaussian, 24 knots (current) | 30 | 1.021 (1.088) | 231 (84) | 28 | 1.012 (1.063) | 324 (91) | 68 |
| D_heavy_both | Student-t ν=3, 24 knots | 30 | 1.056 (1.198) | 93 (58) | 38 | 1.028 (1.083) | 189 (80) | 111 |
| S08_crude | Gaussian, 24 knots (current) | 30 | 1.032 (1.524) | 180 (73) | 53 | 1.029 (1.394) | 168 (63) | 68 |
| S08_crude | Student-t ν=3, 24 knots | 30 | 1.074 (1.675) | 89 (22) | 43 | 1.035 (1.321) | 104 (53) | 104 |
| S08_crude | Student-t ν=1, 24 knots | 20 | 1.139 (1.952) | 43 (20) | 26 | 1.067 (1.451) | 89 (33) | 131 |
| S08_crude | horseshoe, 24 knots | 20 | 3.146 (4.898) | 14 (13) | 18 | 1.422 (1.840) | 35 (27) | 103 |
| M_crude_nomart | Gaussian, 24 knots (current) | 30 | 1.029 (1.085) | 155 (60) | 34 | 1.019 (1.090) | 241 (79) | 57 |
| M_crude_nomart | Student-t ν=3, 24 knots | 30 | 1.040 (1.078) | 136 (75) | 18 | 1.020 (1.067) | 267 (92) | 97 |
| X_fwd15 | Gaussian, 24 knots (current) | 30 | 1.040 (1.107) | 158 (62) | 32 | 1.026 (1.057) | 199 (97) | 87 |
| X_fwd15 | Student-t ν=3, 24 knots | 30 | 1.048 (1.274) | 116 (34) | 43 | 1.034 (1.209) | 140 (49) | 137 |
| X_stale | Gaussian, 24 knots (current) | 30 | 1.281 (2.438) | 39 (18) | 31 | 1.137 (3.018) | 70 (20) | 106 |
| X_stale | Student-t ν=3, 24 knots | 30 | 1.188 (3.342) | 50 (15) | 28 | 1.074 (1.927) | 71 (18) | 159 |
| X_convexity | Gaussian, 24 knots (current) | 30 | 1.039 (2.394) | 144 (16) | 30 | 1.056 (1.624) | 98 (35) | 104 |
| X_convexity | Student-t ν=3, 24 knots | 30 | 1.121 (2.337) | 47 (17) | 27 | 1.066 (1.601) | 97 (28) | 143 |
| X_truncated_grid | Gaussian, 24 knots (current) | 30 | 1.105 (1.714) | 63 (18) | 1 | 1.049 (1.363) | 119 (33) | 137 |
| X_truncated_grid | Student-t ν=3, 24 knots | 30 | 1.125 (1.555) | 48 (22) | 4 | 1.037 (1.114) | 142 (68) | 168 |
| X_unconverged | Gaussian, 24 knots (current) | 30 | 1.322 (1.740) | 12 (8) | 8 | 1.135 (1.581) | 22 (11) | 2 |
| X_unconverged | Student-t ν=3, 24 knots | 30 | 2.533 (4.146) | 7 (6) | 6 | 1.817 (2.317) | 10 (7) | 5 |

X_unconverged band width relative to the converged run on the same seeds (median): Gaussian, 24 knots (current) 0.87, Student-t ν=3, 24 knots 0.52.


## 5. Stage 14 and the injected faults

| config | candidate | n | Stage 14 bias (¢) | \|z\| vs truth med | E[F] 90% cov | parity flags the forward | z(used) > 3 | injected strike resid > 3 | χ² > 2 | edge-mass fails | sampler flagged |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M_crude_nomart | Gaussian, 24 knots (current) | 30 | -0.68 | 0.72 | 97% | 0% | 3% | — | 3% | 0% | 100% |
| M_crude_nomart | Student-t ν=3, 24 knots | 30 | -0.97 | 0.72 | 90% | 0% | 3% | — | 3% | 0% | 100% |
| X_fwd15 | Gaussian, 24 knots (current) | 30 | +14.00 | 17.40 | 0% | 100% | 3% | — | 27% | 0% | 100% |
| X_fwd15 | Student-t ν=3, 24 knots | 30 | +14.01 | 17.30 | 0% | 100% | 3% | — | 27% | 0% | 100% |
| X_stale | Gaussian, 24 knots (current) | 30 | +24.32 | 1.45 | 57% | 0% | 13% | 100% | 100% | 3% | 100% |
| X_stale | Student-t ν=3, 24 knots | 30 | +0.12 | 1.43 | 57% | 0% | 10% | 100% | 100% | 3% | 100% |
| X_convexity | Gaussian, 24 knots (current) | 30 | +1.42 | 1.39 | 60% | 0% | 17% | 100% | 100% | 0% | 100% |
| X_convexity | Student-t ν=3, 24 knots | 30 | +1.41 | 1.38 | 57% | 0% | 17% | 100% | 100% | 0% | 100% |
| X_truncated_grid | Gaussian, 24 knots (current) | 30 | +0.19 | 0.91 | 83% | 0% | 0% | — | 100% | 100% | 100% |
| X_truncated_grid | Student-t ν=3, 24 knots | 30 | +0.19 | 0.90 | 73% | 0% | 0% | — | 100% | 100% | 100% |
| X_unconverged | Gaussian, 24 knots (current) | 30 | +0.20 | 0.92 | 83% | 0% | 0% | — | 3% | 0% | 100% |
| X_unconverged | Student-t ν=3, 24 knots | 30 | +0.02 | 0.96 | 73% | 0% | 0% | — | 3% | 0% | 100% |

## 6. Reading

READING_PLACEHOLDER

Plots: `synth/plots_prior/` — the planted bimodal, spike and kinked chains under each prior (same seed).

