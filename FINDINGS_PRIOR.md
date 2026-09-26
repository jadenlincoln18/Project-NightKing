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
| `m64` | as `base` with 64 knots (0.22 vol-scales between knots) | +40 coefficients | as `base` |
| `m48x` | `m48` with Part B's exclusion rule applied before the fit (drop strikes with LOO \|z\| > 3, once) | none | as `base` |

**Verdict: the bimodal blind spot is a basis-resolution problem before it is a prior-form problem, and it is now half closed. Every heavy-tailed or local-scale prior on 24 knots leaves it untouched (Student-t ν=3: trough z +6.8 → +6.4, trough coverage 0% → 5%; ν=1 and the horseshoe are rejected on the sampler gate), while the unchanged Gaussian prior on 48 knots takes the trough z from +6.8 to +1.3, trough coverage from 0% to 57%, overall bimodal coverage from 42% to 72% and kinked-peak body coverage from 53% to 89%, with no must-not-regress item failing, every injected fault still caught, and bracket R̂ / ESS on crude chains of 1.020 / 260 against 1.016 / 290. Adding the Student-t tail on top of 48 knots buys nothing and costs sampler health. Recommendation: 48 uniform knots with the current Gaussian prior is the new default; the trough (57% coverage), the overall bimodal (72%) and the spike (59%) are still short of the 80% bar, so the blind spot is narrowed, not closed; 64 knots (§3) is the test of whether more resolution keeps paying: trough z +1.1, trough coverage 75%, overall 74%, spike 59%, at bracket R̂ 1.021 / ESS 217 on crude chains.**

## 1. Checklist, per candidate

Must-not-regress items are judged against the baseline on the same seeds (coverage within 3 points, RMSE within 0.1¢, sampler within the stated gate); must-improve items against the fixed targets (coverage ≥ 80%, trough |z| ≤ 2). Tolerances were fixed before the runs.

| item | baseline | Student-t ν=3, 24 knots | Student-t ν=1, 24 knots | horseshoe, 24 knots | Gaussian, 36 knots | Gaussian, 48 knots | Student-t ν=3, 48 knots | Gaussian, 64 knots | Gaussian, 48 knots + LOO exclusion |
|---|---|---|---|---|---|---|---|---|---|
| A_cov90_all | 92% | 92% ✓ | 91% ✓ | 78% ✗ | 92% ✓ | 92% ✓ | 93% ✓ | 93% ✓ | 92% ✓ |
| A_cov90_body | 95% | 93% ✓ | 94% ✓ | 76% ✗ | 95% ✓ | 95% ✓ | 97% ✓ | 97% ✓ | 95% ✓ |
| A_cov90_tail | 95% | 94% ✓ | 94% ✓ | 80% ✗ | 95% ✓ | 95% ✓ | 96% ✓ | 97% ✓ | 96% ✓ |
| A_rmse_body | 0.57 | 0.64 ✓ | 0.77 ✗ | 0.94 ✗ | 0.64 ✓ | 0.66 ✓ | 0.76 ✗ | 0.77 ✗ | 0.68 ✗ |
| A_rmse_tail | 0.21 | 0.23 ✓ | 0.27 ✓ | 0.31 ✗ | 0.26 ✓ | 0.28 ✓ | 0.30 ✓ | 0.31 ✓ | 0.29 ✓ |
| B_cov90_all | 76% | 78% ✓ | —  | —  | 79% ✓ | 80% ✓ | —  | —  | —  |
| S08_cov90_all | 97% | 96% ✓ | 92% ✗ | 76% ✗ | 98% ✓ | 98% ✓ | 98% ✓ | 99% ✓ | 98% ✓ |
| M_stage14_z | 0.72 | 0.72 ✓ | —  | —  | 0.67 ✓ | 0.67 ✓ | —  | —  | —  |
| X_fwd15_caught_parity | 100% | 100% ✓ | —  | —  | 100% ✓ | 100% ✓ | —  | —  | —  |
| X_stale_caught_resid | 100% | 100% ✓ | —  | —  | 100% ✓ | 100% ✓ | —  | —  | —  |
| X_convexity_caught_resid | 100% | 100% ✓ | —  | —  | 100% ✓ | 100% ✓ | —  | —  | —  |
| X_truncated_caught_edge | 100% | 100% ✓ | —  | —  | 100% ✓ | 100% ✓ | —  | —  | —  |
| X_unconverged_caught | 100% | 100% ✓ | —  | —  | 100% ✓ | 100% ✓ | —  | —  | —  |
| A_bracket_rhat | 1.02 | 1.02 ✓ | 1.05 ✗ | 1.62 ✗ | 1.02 ✓ | 1.02 ✓ | 1.03 ✗ | 1.02 ✓ | 1.02 ✓ |
| A_bracket_ess | 290 | 198 ✓ | 96 ✗ | 27 ✗ | 231 ✓ | 260 ✓ | 169 ✓ | 217 ✓ | 276 ✓ |
| C_trough_cov90 | 0% | 5% ✗ | 10% ✗ | 10% ✗ | 27% ✗ | 57% ✗ | 55% ✗ | 75% ✗ | 55% ✗ |
| C_trough_absz | 6.82 | 6.39 ✗ | 6.73 ✗ | 7.60 ✗ | 2.32 ✗ | 1.30 ✓ | 1.51 ✓ | 1.07 ✓ | 1.47 ✓ |
| C_cov90_all | 42% | 43% ✗ | 42% ✗ | 22% ✗ | 65% ✗ | 72% ✗ | 74% ✗ | 74% ✗ | 73% ✗ |
| G_cov90_all | 46% | 47% ✗ | —  | —  | 57% ✗ | 59% ✗ | 60% ✗ | 59% ✗ | —  |
| E_cov90_body | 53% | 52% ✗ | —  | —  | 82% ✓ | 89% ✓ | 90% ✓ | 90% ✓ | —  |
| **verdict** | | **NO IMPROVEMENT** | **REJECTED (regresses: A_rmse_body, S08_cov90_all, A_bracket_rhat, A_bracket_ess)** | **REJECTED (regresses: A_cov90_all, A_cov90_body, A_cov90_tail, A_rmse_body, A_rmse_tail, S08_cov90_all, A_bracket_rhat, A_bracket_ess)** | **PARTIAL (1 of 5 improve targets met)** | **PARTIAL (2 of 5 improve targets met)** | **REJECTED (regresses: A_rmse_body, A_bracket_rhat)** | **REJECTED (regresses: A_rmse_body)** | **REJECTED (regresses: A_rmse_body)** |

## 2. Bracket coverage and error, by planted density

90% bracket coverage (all / body ≥10¢ / tail 1–10¢), bracket RMSE (¢) body / tail, mean 90% band width (¢) body / tail, bias body (¢).

| config | candidate | n | cov90 all | body | tail | far | RMSE body | tail | width body | tail | bias body |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A_crude_full | Gaussian, 24 knots (current) | 40 | 92% | 95% | 95% | 91% | 0.57 | 0.21 | 1.90 | 0.74 | -0.03 |
| A_crude_full | Student-t ν=3, 24 knots | 40 | 92% | 93% | 94% | 90% | 0.64 | 0.23 | 2.01 | 0.75 | -0.03 |
| A_crude_full | Student-t ν=1, 24 knots | 20 | 91% | 94% | 94% | 89% | 0.77 | 0.27 | 2.19 | 0.78 | -0.04 |
| A_crude_full | horseshoe, 24 knots | 20 | 78% | 76% | 80% | 80% | 0.94 | 0.31 | 1.68 | 0.59 | -0.04 |
| A_crude_full | Gaussian, 36 knots | 30 | 92% | 95% | 95% | 89% | 0.64 | 0.26 | 2.41 | 0.95 | -0.05 |
| A_crude_full | Gaussian, 48 knots | 30 | 92% | 95% | 95% | 89% | 0.66 | 0.28 | 2.70 | 1.05 | -0.06 |
| A_crude_full | Student-t ν=3, 48 knots | 20 | 93% | 97% | 96% | 89% | 0.76 | 0.30 | 3.07 | 1.12 | -0.03 |
| A_crude_full | Gaussian, 64 knots | 20 | 93% | 97% | 97% | 91% | 0.77 | 0.31 | 3.19 | 1.17 | -0.03 |
| A_crude_full | Gaussian, 48 knots + LOO exclusion | 30 | 92% | 95% | 96% | 89% | 0.68 | 0.29 | 2.69 | 1.04 | -0.07 |
| B_lognormal_full | Gaussian, 24 knots (current) | 40 | 76% | 97% | 85% | 66% | 0.65 | 0.34 | 2.41 | 0.88 | -0.05 |
| B_lognormal_full | Student-t ν=3, 24 knots | 40 | 78% | 96% | 86% | 69% | 0.62 | 0.34 | 2.36 | 0.89 | -0.05 |
| B_lognormal_full | Gaussian, 36 knots | 30 | 79% | 97% | 90% | 69% | 0.72 | 0.39 | 2.97 | 1.10 | -0.05 |
| B_lognormal_full | Gaussian, 48 knots | 30 | 80% | 97% | 93% | 70% | 0.78 | 0.41 | 3.34 | 1.24 | -0.06 |
| C_bimodal_full | Gaussian, 24 knots (current) | 40 | 42% | 41% | 29% | 65% | 1.77 | 0.96 | 2.46 | 0.94 | +0.11 |
| C_bimodal_full | Student-t ν=3, 24 knots | 40 | 43% | 40% | 31% | 65% | 1.82 | 0.95 | 2.50 | 0.95 | +0.12 |
| C_bimodal_full | Student-t ν=1, 24 knots | 20 | 42% | 49% | 29% | 63% | 2.04 | 0.95 | 2.85 | 0.98 | +0.16 |
| C_bimodal_full | horseshoe, 24 knots | 20 | 22% | 34% | 18% | 25% | 2.14 | 1.48 | 2.27 | 1.22 | +0.02 |
| C_bimodal_full | Gaussian, 36 knots | 30 | 65% | 70% | 67% | 69% | 1.55 | 0.71 | 3.55 | 1.41 | +0.25 |
| C_bimodal_full | Gaussian, 48 knots | 30 | 72% | 74% | 81% | 72% | 1.58 | 0.70 | 4.09 | 1.73 | +0.25 |
| C_bimodal_full | Student-t ν=3, 48 knots | 20 | 74% | 80% | 79% | 76% | 1.89 | 0.76 | 4.51 | 1.77 | +0.21 |
| C_bimodal_full | Gaussian, 64 knots | 20 | 74% | 81% | 82% | 73% | 1.81 | 0.72 | 4.89 | 1.97 | +0.26 |
| C_bimodal_full | Gaussian, 48 knots + LOO exclusion | 20 | 73% | 78% | 82% | 72% | 1.66 | 0.81 | 4.38 | 1.72 | +0.09 |
| C05_bimodal_halfnoise | Gaussian, 24 knots (current) | 30 | 36% | 30% | 18% | 65% | 1.71 | 0.89 | 1.67 | 0.61 | +0.19 |
| C05_bimodal_halfnoise | Student-t ν=3, 24 knots | 30 | 33% | 30% | 16% | 60% | 1.73 | 0.89 | 1.64 | 0.59 | +0.21 |
| C05_bimodal_halfnoise | Gaussian, 36 knots | 20 | 62% | 73% | 63% | 68% | 1.38 | 0.58 | 2.70 | 0.97 | +0.23 |
| C05_bimodal_halfnoise | Gaussian, 48 knots | 20 | 72% | 78% | 81% | 70% | 1.42 | 0.54 | 3.07 | 1.25 | +0.18 |
| C05_bimodal_halfnoise | Student-t ν=3, 48 knots | 20 | 72% | 80% | 79% | 70% | 1.64 | 0.58 | 3.29 | 1.29 | +0.18 |
| C05_bimodal_halfnoise | Gaussian, 64 knots | 20 | 74% | 78% | 83% | 71% | 1.47 | 0.56 | 3.52 | 1.43 | +0.17 |
| F_bimodal_close | Gaussian, 24 knots (current) | 30 | 62% | 91% | 68% | 56% | 1.02 | 0.54 | 3.00 | 1.16 | +0.05 |
| F_bimodal_close | Student-t ν=3, 24 knots | 30 | 63% | 89% | 68% | 60% | 1.04 | 0.56 | 3.05 | 1.23 | +0.00 |
| F_bimodal_close | Student-t ν=1, 24 knots | 20 | 62% | 87% | 63% | 62% | 1.30 | 0.67 | 3.10 | 1.24 | -0.10 |
| F_bimodal_close | horseshoe, 24 knots | 20 | 34% | 54% | 44% | 24% | 1.60 | 1.87 | 2.76 | 1.55 | -0.30 |
| F_bimodal_close | Gaussian, 36 knots | 20 | 66% | 94% | 79% | 55% | 1.19 | 0.61 | 4.23 | 1.63 | +0.07 |
| F_bimodal_close | Gaussian, 48 knots | 20 | 68% | 96% | 84% | 57% | 1.18 | 0.64 | 4.82 | 1.87 | +0.07 |
| E_sharp_peak | Gaussian, 24 knots (current) | 30 | 74% | 53% | 86% | 76% | 1.88 | 0.43 | 3.06 | 1.09 | -0.12 |
| E_sharp_peak | Student-t ν=3, 24 knots | 30 | 74% | 52% | 87% | 75% | 1.88 | 0.41 | 3.11 | 1.03 | -0.13 |
| E_sharp_peak | Gaussian, 36 knots | 20 | 80% | 82% | 92% | 77% | 1.60 | 0.40 | 3.74 | 1.33 | -0.16 |
| E_sharp_peak | Gaussian, 48 knots | 20 | 82% | 89% | 93% | 78% | 1.54 | 0.40 | 4.09 | 1.43 | -0.15 |
| E_sharp_peak | Student-t ν=3, 48 knots | 20 | 82% | 90% | 95% | 77% | 1.39 | 0.37 | 4.20 | 1.35 | -0.15 |
| E_sharp_peak | Gaussian, 64 knots | 20 | 82% | 90% | 96% | 76% | 1.47 | 0.40 | 4.34 | 1.53 | -0.14 |
| G_spike_outside_prior | Gaussian, 24 knots (current) | 30 | 46% | 37% | 49% | 50% | 5.65 | 2.52 | 3.30 | 1.45 | -2.28 |
| G_spike_outside_prior | Student-t ν=3, 24 knots | 30 | 47% | 33% | 49% | 51% | 5.66 | 2.53 | 3.24 | 1.38 | -2.30 |
| G_spike_outside_prior | Gaussian, 36 knots | 20 | 57% | 52% | 64% | 57% | 4.82 | 2.18 | 4.98 | 2.24 | -1.74 |
| G_spike_outside_prior | Gaussian, 48 knots | 20 | 59% | 55% | 67% | 59% | 4.76 | 2.19 | 5.44 | 2.59 | -1.64 |
| G_spike_outside_prior | Student-t ν=3, 48 knots | 20 | 60% | 60% | 67% | 58% | 4.48 | 2.04 | 5.04 | 2.19 | -1.59 |
| G_spike_outside_prior | Gaussian, 64 knots | 20 | 59% | 55% | 67% | 58% | 4.57 | 2.13 | 5.75 | 2.76 | -1.54 |
| D_heavy_both | Gaussian, 24 knots (current) | 30 | 93% | 95% | 95% | 93% | 0.53 | 0.22 | 2.11 | 0.81 | -0.11 |
| D_heavy_both | Student-t ν=3, 24 knots | 30 | 94% | 96% | 95% | 94% | 0.57 | 0.22 | 2.19 | 0.79 | -0.09 |
| D_heavy_both | Gaussian, 36 knots | 20 | 94% | 98% | 95% | 94% | 0.55 | 0.25 | 2.74 | 1.01 | -0.11 |
| D_heavy_both | Gaussian, 48 knots | 20 | 94% | 98% | 95% | 93% | 0.60 | 0.27 | 2.98 | 1.10 | -0.10 |
| S08_crude | Gaussian, 24 knots (current) | 30 | 97% | 100% | 98% | 96% | 0.67 | 0.37 | 3.29 | 1.41 | -0.05 |
| S08_crude | Student-t ν=3, 24 knots | 30 | 96% | 98% | 96% | 96% | 0.81 | 0.43 | 3.63 | 1.46 | +0.01 |
| S08_crude | Student-t ν=1, 24 knots | 20 | 92% | 89% | 90% | 95% | 1.01 | 0.47 | 3.67 | 1.41 | +0.19 |
| S08_crude | horseshoe, 24 knots | 20 | 76% | 71% | 69% | 84% | 1.20 | 0.52 | 2.76 | 1.01 | +0.18 |
| S08_crude | Gaussian, 36 knots | 20 | 98% | 100% | 99% | 97% | 0.81 | 0.40 | 4.67 | 1.76 | +0.08 |
| S08_crude | Gaussian, 48 knots | 20 | 98% | 100% | 100% | 98% | 0.82 | 0.42 | 4.85 | 1.88 | +0.06 |
| S08_crude | Student-t ν=3, 48 knots | 20 | 98% | 100% | 100% | 98% | 0.89 | 0.45 | 5.27 | 2.00 | +0.04 |
| S08_crude | Gaussian, 64 knots | 20 | 99% | 100% | 100% | 98% | 0.87 | 0.44 | 5.31 | 2.05 | +0.06 |
| S08_crude | Gaussian, 48 knots + LOO exclusion | 20 | 98% | 100% | 100% | 98% | 0.82 | 0.42 | 4.85 | 1.88 | +0.06 |
| M_crude_nomart | Gaussian, 24 knots (current) | 30 | 92% | 98% | 95% | 89% | 0.75 | 0.23 | 2.47 | 0.86 | +0.02 |
| M_crude_nomart | Student-t ν=3, 24 knots | 30 | 92% | 96% | 94% | 89% | 0.79 | 0.25 | 2.57 | 0.87 | +0.05 |
| M_crude_nomart | Gaussian, 36 knots | 20 | 94% | 98% | 96% | 92% | 0.78 | 0.28 | 3.25 | 1.07 | +0.01 |
| M_crude_nomart | Gaussian, 48 knots | 20 | 94% | 98% | 97% | 91% | 0.80 | 0.31 | 3.64 | 1.19 | +0.01 |
| X_fwd15 | Gaussian, 24 knots (current) | 30 | 65% | 26% | 60% | 83% | 3.13 | 0.92 | 2.54 | 1.02 | -0.82 |
| X_fwd15 | Student-t ν=3, 24 knots | 30 | 64% | 26% | 60% | 82% | 3.16 | 0.92 | 2.56 | 1.03 | -0.82 |
| X_fwd15 | Gaussian, 36 knots | 20 | 70% | 29% | 68% | 86% | 3.56 | 1.08 | 3.73 | 1.42 | -0.83 |
| X_fwd15 | Gaussian, 48 knots | 20 | 72% | 30% | 72% | 86% | 3.83 | 1.15 | 4.24 | 1.58 | -0.83 |
| X_stale | Gaussian, 24 knots (current) | 30 | 54% | 38% | 45% | 69% | 11.66 | 3.39 | 2.90 | 1.43 | -0.33 |
| X_stale | Student-t ν=3, 24 knots | 30 | 55% | 39% | 45% | 72% | 11.54 | 4.57 | 3.27 | 1.31 | -0.40 |
| X_stale | Gaussian, 36 knots | 20 | 60% | 44% | 54% | 72% | 12.54 | 4.84 | 4.93 | 1.84 | -0.03 |
| X_stale | Gaussian, 48 knots | 20 | 64% | 49% | 60% | 72% | 11.24 | 5.84 | 6.33 | 2.53 | -0.66 |
| X_stale | Gaussian, 48 knots + LOO exclusion | 20 | 94% | 100% | 97% | 91% | 0.75 | 0.32 | 3.56 | 1.27 | -0.03 |
| X_convexity | Gaussian, 24 knots (current) | 30 | 53% | 35% | 45% | 67% | 6.61 | 2.91 | 2.95 | 1.30 | -0.40 |
| X_convexity | Student-t ν=3, 24 knots | 30 | 52% | 35% | 44% | 66% | 6.61 | 2.92 | 2.99 | 1.31 | -0.39 |
| X_convexity | Gaussian, 36 knots | 20 | 63% | 37% | 56% | 79% | 7.38 | 3.04 | 4.25 | 1.85 | -0.66 |
| X_convexity | Gaussian, 48 knots | 20 | 68% | 41% | 64% | 82% | 7.62 | 3.04 | 4.93 | 2.12 | -0.69 |
| X_convexity | Gaussian, 48 knots + LOO exclusion | 20 | 94% | 98% | 95% | 92% | 0.87 | 0.35 | 3.54 | 1.21 | -0.09 |
| X_truncated_grid | Gaussian, 24 knots (current) | 30 | 15% | 54% | 18% | 0% | 9.15 | 7.88 | 13.31 | 2.62 | -0.14 |
| X_truncated_grid | Student-t ν=3, 24 knots | 30 | 14% | 58% | 16% | 0% | 8.19 | 7.78 | 11.56 | 2.29 | -0.21 |
| X_truncated_grid | Gaussian, 36 knots | 20 | 15% | 62% | 17% | 0% | 9.15 | 7.97 | 13.85 | 3.00 | -0.46 |
| X_truncated_grid | Gaussian, 48 knots | 20 | 17% | 70% | 19% | 0% | 9.18 | 8.00 | 14.79 | 3.17 | -0.42 |
| X_unconverged | Gaussian, 24 knots (current) | 30 | 90% | 94% | 93% | 88% | 0.57 | 0.22 | 1.72 | 0.66 | -0.04 |
| X_unconverged | Student-t ν=3, 24 knots | 30 | 54% | 44% | 47% | 62% | 1.63 | 0.41 | 1.11 | 0.42 | +0.02 |
| X_unconverged | Gaussian, 36 knots | 20 | 93% | 95% | 96% | 91% | 0.61 | 0.22 | 2.10 | 0.79 | -0.03 |
| X_unconverged | Gaussian, 48 knots | 20 | 92% | 94% | 94% | 93% | 0.62 | 0.24 | 2.35 | 0.86 | -0.03 |

## 3. The blind spot: bimodal, spiked and kinked truths

Trough = the bracket between the two humps where the truth is lowest: z of the posterior median against the truth (in units of the 90% band / 3.29), the band's width and whether it contains the truth. Modes = posterior-mean mode count matches the truth.

| config | candidate | n | trough z med | trough 90% width (¢) | trough coverage | cov90 all | cov90 body | modes recovered | posterior modes | density RMSE body (rel. peak) | τ med | χ²/strike med |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_bimodal_full | Gaussian, 24 knots (current) | 40 | +6.8 | 0.69 | 0% | 42% | 41% | 100% | {'2': 40} | 0.088 | 4.95 | 1.08 |
| C_bimodal_full | Student-t ν=3, 24 knots | 40 | +6.4 | 0.68 | 5% | 43% | 40% | 100% | {'2': 40} | 0.088 | 3.43 | 1.10 |
| C_bimodal_full | Student-t ν=1, 24 knots | 20 | +6.7 | 0.70 | 10% | 42% | 49% | 100% | {'2': 20} | 0.092 | 1.79 | 1.12 |
| C_bimodal_full | horseshoe, 24 knots | 20 | +7.6 | 0.61 | 10% | 22% | 34% | 95% | {'2': 19, '3': 1} | 0.102 | 0.33 | 1.15 |
| C_bimodal_full | Gaussian, 36 knots | 30 | +2.3 | 1.22 | 27% | 65% | 70% | 100% | {'2': 30} | 0.065 | 2.23 | 1.05 |
| C_bimodal_full | Gaussian, 48 knots | 30 | +1.3 | 1.55 | 57% | 72% | 74% | 100% | {'2': 30} | 0.063 | 1.33 | 1.05 |
| C_bimodal_full | Student-t ν=3, 48 knots | 20 | +1.5 | 1.75 | 55% | 74% | 80% | 100% | {'2': 20} | 0.069 | 1.00 | 1.02 |
| C_bimodal_full | Gaussian, 64 knots | 20 | +1.1 | 1.93 | 75% | 74% | 81% | 100% | {'2': 20} | 0.067 | 0.89 | 1.03 |
| C_bimodal_full | Gaussian, 48 knots + LOO exclusion | 20 | +1.5 | 1.68 | 55% | 73% | 78% | 100% | {'2': 20} | 0.066 | 1.31 | 0.98 |
| C05_bimodal_halfnoise | Gaussian, 24 knots (current) | 30 | +11.2 | 0.39 | 0% | 36% | 30% | 100% | {'2': 30} | 0.085 | 4.87 | 1.44 |
| C05_bimodal_halfnoise | Student-t ν=3, 24 knots | 30 | +11.3 | 0.41 | 0% | 33% | 30% | 100% | {'2': 30} | 0.085 | 3.38 | 1.48 |
| C05_bimodal_halfnoise | Gaussian, 36 knots | 20 | +3.0 | 0.80 | 5% | 62% | 73% | 100% | {'2': 20} | 0.056 | 2.12 | 1.17 |
| C05_bimodal_halfnoise | Gaussian, 48 knots | 20 | +1.7 | 1.14 | 50% | 72% | 78% | 100% | {'2': 20} | 0.051 | 1.31 | 1.13 |
| C05_bimodal_halfnoise | Student-t ν=3, 48 knots | 20 | +1.8 | 1.13 | 40% | 72% | 80% | 100% | {'2': 20} | 0.055 | 1.05 | 1.12 |
| C05_bimodal_halfnoise | Gaussian, 64 knots | 20 | +1.5 | 1.32 | 60% | 74% | 78% | 100% | {'2': 20} | 0.053 | 0.82 | 1.10 |
| G_spike_outside_prior | Gaussian, 24 knots (current) | 30 | — | — | — | 46% | 37% | 83% | {'1': 5, '2': 25} | 0.135 | 3.43 | 1.25 |
| G_spike_outside_prior | Student-t ν=3, 24 knots | 30 | — | — | — | 47% | 33% | 83% | {'1': 5, '2': 25} | 0.133 | 2.19 | 1.26 |
| G_spike_outside_prior | Gaussian, 36 knots | 20 | — | — | — | 57% | 52% | 85% | {'1': 3, '2': 17} | 0.132 | 2.05 | 1.16 |
| G_spike_outside_prior | Gaussian, 48 knots | 20 | — | — | — | 59% | 55% | 85% | {'1': 3, '2': 17} | 0.139 | 1.26 | 1.12 |
| G_spike_outside_prior | Student-t ν=3, 48 knots | 20 | — | — | — | 60% | 60% | 85% | {'1': 3, '2': 17} | 0.129 | 0.64 | 1.11 |
| G_spike_outside_prior | Gaussian, 64 knots | 20 | — | — | — | 59% | 55% | 85% | {'1': 2, '2': 17, '3': 1} | 0.134 | 0.77 | 1.08 |
| E_sharp_peak | Gaussian, 24 knots (current) | 30 | — | — | — | 74% | 53% | 100% | {'1': 30} | 0.075 | 0.73 | 1.36 |
| E_sharp_peak | Student-t ν=3, 24 knots | 30 | — | — | — | 74% | 52% | 100% | {'1': 30} | 0.075 | 0.48 | 1.38 |
| E_sharp_peak | Gaussian, 36 knots | 20 | — | — | — | 80% | 82% | 100% | {'1': 20} | 0.066 | 0.38 | 1.28 |
| E_sharp_peak | Gaussian, 48 knots | 20 | — | — | — | 82% | 89% | 100% | {'1': 20} | 0.064 | 0.25 | 1.25 |
| E_sharp_peak | Student-t ν=3, 48 knots | 20 | — | — | — | 82% | 90% | 100% | {'1': 20} | 0.058 | 0.16 | 1.24 |
| E_sharp_peak | Gaussian, 64 knots | 20 | — | — | — | 82% | 90% | 100% | {'1': 20} | 0.061 | 0.17 | 1.23 |
| F_bimodal_close | Gaussian, 24 knots (current) | 30 | +0.6 | 1.81 | 90% | 62% | 91% | 90% | {'1': 3, '2': 27} | 0.056 | 2.08 | 1.10 |
| F_bimodal_close | Student-t ν=3, 24 knots | 30 | +0.7 | 1.87 | 87% | 63% | 89% | 70% | {'1': 9, '2': 21} | 0.058 | 1.79 | 1.09 |
| F_bimodal_close | Student-t ν=1, 24 knots | 20 | +0.9 | 1.99 | 85% | 62% | 87% | 55% | {'1': 9, '2': 11} | 0.070 | 1.00 | 1.07 |
| F_bimodal_close | horseshoe, 24 knots | 20 | +1.0 | 1.38 | 55% | 34% | 54% | 55% | {'1': 9, '2': 11} | 0.094 | 0.30 | 1.03 |
| F_bimodal_close | Gaussian, 36 knots | 20 | +0.1 | 3.43 | 100% | 66% | 94% | 75% | {'1': 5, '2': 15} | 0.064 | 1.11 | 1.09 |
| F_bimodal_close | Gaussian, 48 knots | 20 | +0.0 | 4.09 | 100% | 68% | 96% | 85% | {'1': 3, '2': 17} | 0.069 | 0.73 | 1.07 |
| D_heavy_both | Gaussian, 24 knots (current) | 30 | — | — | — | 93% | 95% | 100% | {'1': 30} | 0.025 | 0.69 | 1.08 |
| D_heavy_both | Student-t ν=3, 24 knots | 30 | — | — | — | 94% | 96% | 100% | {'1': 30} | 0.026 | 0.48 | 1.08 |
| D_heavy_both | Gaussian, 36 knots | 20 | — | — | — | 94% | 98% | 100% | {'1': 20} | 0.027 | 0.36 | 0.94 |
| D_heavy_both | Gaussian, 48 knots | 20 | — | — | — | 94% | 98% | 100% | {'1': 20} | 0.029 | 0.24 | 0.94 |

## 4. Sampler health (the acceptance gate)

| config | candidate | n | R̂ max med (p90), raw | min ESS med (p10) | divergences med | bracket R̂ med (p90) | bracket ESS med (p10) | s / run |
|---|---|---|---|---|---|---|---|---|
| A_crude_full | Gaussian, 24 knots (current) | 40 | 1.024 (1.088) | 199 (98) | 23 | 1.016 (1.055) | 290 (119) | 68 |
| A_crude_full | Student-t ν=3, 24 knots | 40 | 1.053 (1.157) | 100 (45) | 26 | 1.023 (1.087) | 198 (77) | 117 |
| A_crude_full | Student-t ν=1, 24 knots | 20 | 1.139 (2.022) | 37 (20) | 26 | 1.051 (1.224) | 96 (33) | 129 |
| A_crude_full | horseshoe, 24 knots | 20 | 4.160 (5.353) | 13 (13) | 6 | 1.623 (2.269) | 27 (20) | 123 |
| A_crude_full | Gaussian, 36 knots | 30 | 1.033 (1.151) | 144 (55) | 27 | 1.021 (1.126) | 231 (58) | 62 |
| A_crude_full | Gaussian, 48 knots | 30 | 1.033 (1.106) | 183 (44) | 31 | 1.020 (1.079) | 260 (67) | 83 |
| A_crude_full | Student-t ν=3, 48 knots | 20 | 1.051 (1.237) | 108 (55) | 33 | 1.030 (1.192) | 169 (77) | 203 |
| A_crude_full | Gaussian, 64 knots | 20 | 1.036 (1.081) | 177 (80) | 51 | 1.021 (1.048) | 217 (127) | 110 |
| A_crude_full | Gaussian, 48 knots + LOO exclusion | 30 | 1.023 (1.072) | 201 (66) | 21 | 1.016 (1.035) | 276 (112) | 77 |
| B_lognormal_full | Gaussian, 24 knots (current) | 40 | 1.027 (1.148) | 215 (53) | 22 | 1.020 (1.094) | 238 (73) | 46 |
| B_lognormal_full | Student-t ν=3, 24 knots | 40 | 1.045 (1.173) | 126 (54) | 20 | 1.027 (1.105) | 202 (64) | 113 |
| B_lognormal_full | Gaussian, 36 knots | 30 | 1.026 (1.115) | 178 (61) | 18 | 1.020 (1.119) | 249 (51) | 50 |
| B_lognormal_full | Gaussian, 48 knots | 30 | 1.044 (1.137) | 135 (47) | 20 | 1.028 (1.129) | 174 (72) | 70 |
| C_bimodal_full | Gaussian, 24 knots (current) | 40 | 1.134 (1.691) | 52 (20) | 16 | 1.044 (1.136) | 147 (74) | 118 |
| C_bimodal_full | Student-t ν=3, 24 knots | 40 | 1.133 (1.451) | 53 (24) | 30 | 1.049 (1.188) | 96 (50) | 208 |
| C_bimodal_full | Student-t ν=1, 24 knots | 20 | 1.452 (2.754) | 25 (15) | 8 | 1.087 (1.213) | 86 (45) | 159 |
| C_bimodal_full | horseshoe, 24 knots | 20 | 4.173 (6.403) | 13 (12) | 4 | 1.477 (1.888) | 31 (18) | 117 |
| C_bimodal_full | Gaussian, 36 knots | 30 | 1.108 (1.480) | 52 (24) | 19 | 1.052 (1.177) | 129 (62) | 107 |
| C_bimodal_full | Gaussian, 48 knots | 30 | 1.107 (1.572) | 58 (19) | 31 | 1.056 (1.240) | 108 (32) | 145 |
| C_bimodal_full | Student-t ν=3, 48 knots | 20 | 1.216 (1.549) | 34 (25) | 22 | 1.076 (1.255) | 88 (40) | 290 |
| C_bimodal_full | Gaussian, 64 knots | 20 | 1.099 (1.391) | 69 (21) | 16 | 1.050 (1.136) | 125 (48) | 162 |
| C_bimodal_full | Gaussian, 48 knots + LOO exclusion | 20 | 1.083 (1.351) | 65 (29) | 26 | 1.044 (1.113) | 142 (47) | 137 |
| C05_bimodal_halfnoise | Gaussian, 24 knots (current) | 30 | 1.171 (1.996) | 41 (16) | 42 | 1.053 (1.189) | 133 (61) | 117 |
| C05_bimodal_halfnoise | Student-t ν=3, 24 knots | 30 | 1.194 (1.591) | 48 (24) | 34 | 1.104 (1.330) | 70 (37) | 211 |
| C05_bimodal_halfnoise | Gaussian, 36 knots | 20 | 1.115 (1.581) | 42 (25) | 79 | 1.038 (1.146) | 122 (55) | 102 |
| C05_bimodal_halfnoise | Gaussian, 48 knots | 20 | 1.083 (1.383) | 64 (27) | 45 | 1.047 (1.134) | 136 (65) | 139 |
| C05_bimodal_halfnoise | Student-t ν=3, 48 knots | 20 | 1.245 (1.850) | 35 (21) | 49 | 1.079 (1.220) | 66 (55) | 281 |
| C05_bimodal_halfnoise | Gaussian, 64 knots | 20 | 1.119 (1.386) | 53 (24) | 68 | 1.046 (1.233) | 95 (47) | 153 |
| F_bimodal_close | Gaussian, 24 knots (current) | 30 | 1.043 (1.215) | 133 (48) | 16 | 1.020 (1.253) | 225 (75) | 80 |
| F_bimodal_close | Student-t ν=3, 24 knots | 30 | 1.067 (1.147) | 99 (46) | 9 | 1.027 (1.101) | 165 (74) | 186 |
| F_bimodal_close | Student-t ν=1, 24 knots | 20 | 1.283 (1.941) | 26 (18) | 4 | 1.073 (1.288) | 85 (30) | 160 |
| F_bimodal_close | horseshoe, 24 knots | 20 | 3.701 (5.809) | 14 (12) | 8 | 1.429 (2.026) | 36 (20) | 116 |
| F_bimodal_close | Gaussian, 36 knots | 20 | 1.049 (1.095) | 105 (60) | 6 | 1.022 (1.054) | 175 (108) | 86 |
| F_bimodal_close | Gaussian, 48 knots | 20 | 1.045 (1.076) | 153 (61) | 13 | 1.018 (1.055) | 273 (109) | 110 |
| E_sharp_peak | Gaussian, 24 knots (current) | 30 | 1.022 (1.093) | 223 (84) | 14 | 1.021 (1.078) | 226 (72) | 49 |
| E_sharp_peak | Student-t ν=3, 24 knots | 30 | 1.041 (1.103) | 145 (58) | 17 | 1.030 (1.065) | 192 (78) | 81 |
| E_sharp_peak | Gaussian, 36 knots | 20 | 1.028 (1.064) | 192 (93) | 10 | 1.021 (1.032) | 209 (153) | 45 |
| E_sharp_peak | Gaussian, 48 knots | 20 | 1.026 (1.063) | 195 (95) | 12 | 1.022 (1.102) | 225 (70) | 62 |
| E_sharp_peak | Student-t ν=3, 48 knots | 20 | 1.037 (1.073) | 134 (74) | 9 | 1.028 (1.066) | 197 (78) | 132 |
| E_sharp_peak | Gaussian, 64 knots | 20 | 1.024 (1.107) | 181 (58) | 9 | 1.019 (1.085) | 200 (71) | 78 |
| G_spike_outside_prior | Gaussian, 24 knots (current) | 30 | 1.146 (1.504) | 47 (24) | 41 | 1.054 (1.257) | 128 (40) | 94 |
| G_spike_outside_prior | Student-t ν=3, 24 knots | 30 | 1.093 (1.456) | 74 (21) | 19 | 1.043 (1.175) | 143 (48) | 148 |
| G_spike_outside_prior | Gaussian, 36 knots | 20 | 1.087 (1.480) | 66 (27) | 20 | 1.050 (1.325) | 88 (55) | 109 |
| G_spike_outside_prior | Gaussian, 48 knots | 20 | 1.103 (1.614) | 51 (30) | 8 | 1.070 (1.226) | 89 (40) | 143 |
| G_spike_outside_prior | Student-t ν=3, 48 knots | 20 | 1.060 (1.271) | 77 (29) | 5 | 1.038 (1.118) | 145 (61) | 254 |
| G_spike_outside_prior | Gaussian, 64 knots | 20 | 1.112 (1.293) | 57 (26) | 23 | 1.066 (1.220) | 101 (32) | 161 |
| D_heavy_both | Gaussian, 24 knots (current) | 30 | 1.021 (1.088) | 231 (84) | 28 | 1.012 (1.063) | 324 (91) | 68 |
| D_heavy_both | Student-t ν=3, 24 knots | 30 | 1.056 (1.198) | 93 (58) | 38 | 1.028 (1.083) | 189 (80) | 111 |
| D_heavy_both | Gaussian, 36 knots | 20 | 1.028 (1.099) | 175 (72) | 22 | 1.021 (1.055) | 260 (104) | 67 |
| D_heavy_both | Gaussian, 48 knots | 20 | 1.025 (1.065) | 168 (81) | 30 | 1.021 (1.065) | 228 (126) | 91 |
| S08_crude | Gaussian, 24 knots (current) | 30 | 1.032 (1.524) | 180 (73) | 53 | 1.029 (1.394) | 168 (63) | 68 |
| S08_crude | Student-t ν=3, 24 knots | 30 | 1.074 (1.675) | 89 (22) | 43 | 1.035 (1.321) | 104 (53) | 104 |
| S08_crude | Student-t ν=1, 24 knots | 20 | 1.139 (1.952) | 43 (20) | 26 | 1.067 (1.451) | 89 (33) | 131 |
| S08_crude | horseshoe, 24 knots | 20 | 3.146 (4.898) | 14 (13) | 18 | 1.422 (1.840) | 35 (27) | 103 |
| S08_crude | Gaussian, 36 knots | 20 | 1.053 (1.134) | 113 (42) | 54 | 1.041 (1.142) | 161 (58) | 62 |
| S08_crude | Gaussian, 48 knots | 20 | 1.042 (1.316) | 126 (44) | 57 | 1.037 (1.300) | 144 (55) | 76 |
| S08_crude | Student-t ν=3, 48 knots | 20 | 1.077 (1.196) | 83 (34) | 55 | 1.064 (1.250) | 95 (37) | 180 |
| S08_crude | Gaussian, 64 knots | 20 | 1.065 (1.253) | 97 (46) | 42 | 1.043 (1.249) | 131 (66) | 88 |
| S08_crude | Gaussian, 48 knots + LOO exclusion | 20 | 1.042 (1.316) | 126 (44) | 57 | 1.037 (1.300) | 144 (55) | 69 |
| M_crude_nomart | Gaussian, 24 knots (current) | 30 | 1.029 (1.085) | 155 (60) | 34 | 1.019 (1.090) | 241 (79) | 57 |
| M_crude_nomart | Student-t ν=3, 24 knots | 30 | 1.040 (1.078) | 136 (75) | 18 | 1.020 (1.067) | 267 (92) | 97 |
| M_crude_nomart | Gaussian, 36 knots | 20 | 1.025 (1.102) | 215 (49) | 43 | 1.020 (1.086) | 249 (75) | 64 |
| M_crude_nomart | Gaussian, 48 knots | 20 | 1.027 (1.084) | 182 (92) | 31 | 1.022 (1.060) | 254 (111) | 88 |
| X_fwd15 | Gaussian, 24 knots (current) | 30 | 1.040 (1.107) | 158 (62) | 32 | 1.026 (1.057) | 199 (97) | 87 |
| X_fwd15 | Student-t ν=3, 24 knots | 30 | 1.048 (1.274) | 116 (34) | 43 | 1.034 (1.209) | 140 (49) | 137 |
| X_fwd15 | Gaussian, 36 knots | 20 | 1.061 (1.124) | 82 (53) | 40 | 1.041 (1.142) | 161 (52) | 97 |
| X_fwd15 | Gaussian, 48 knots | 20 | 1.043 (1.143) | 99 (53) | 48 | 1.042 (1.069) | 125 (74) | 124 |
| X_stale | Gaussian, 24 knots (current) | 30 | 1.281 (2.438) | 39 (18) | 31 | 1.137 (3.018) | 70 (20) | 106 |
| X_stale | Student-t ν=3, 24 knots | 30 | 1.188 (3.342) | 50 (15) | 28 | 1.074 (1.927) | 71 (18) | 159 |
| X_stale | Gaussian, 36 knots | 20 | 1.449 (2.834) | 24 (15) | 38 | 1.139 (1.875) | 60 (19) | 107 |
| X_stale | Gaussian, 48 knots | 20 | 1.319 (2.953) | 30 (14) | 31 | 1.151 (1.925) | 46 (24) | 132 |
| X_stale | Gaussian, 48 knots + LOO exclusion | 20 | 1.028 (1.065) | 167 (65) | 41 | 1.018 (1.048) | 201 (87) | 98 |
| X_convexity | Gaussian, 24 knots (current) | 30 | 1.039 (2.394) | 144 (16) | 30 | 1.056 (1.624) | 98 (35) | 104 |
| X_convexity | Student-t ν=3, 24 knots | 30 | 1.121 (2.337) | 47 (17) | 27 | 1.066 (1.601) | 97 (28) | 143 |
| X_convexity | Gaussian, 36 knots | 20 | 1.184 (2.668) | 37 (17) | 30 | 1.103 (1.314) | 61 (30) | 102 |
| X_convexity | Gaussian, 48 knots | 20 | 1.084 (2.595) | 71 (15) | 28 | 1.075 (1.667) | 99 (26) | 129 |
| X_convexity | Gaussian, 48 knots + LOO exclusion | 20 | 1.024 (1.156) | 162 (55) | 40 | 1.021 (1.079) | 274 (101) | 90 |
| X_truncated_grid | Gaussian, 24 knots (current) | 30 | 1.105 (1.714) | 63 (18) | 1 | 1.049 (1.363) | 119 (33) | 137 |
| X_truncated_grid | Student-t ν=3, 24 knots | 30 | 1.125 (1.555) | 48 (22) | 4 | 1.037 (1.114) | 142 (68) | 168 |
| X_truncated_grid | Gaussian, 36 knots | 20 | 1.103 (1.609) | 67 (17) | 1 | 1.060 (1.250) | 119 (30) | 120 |
| X_truncated_grid | Gaussian, 48 knots | 20 | 1.326 (1.701) | 32 (21) | 1 | 1.090 (1.295) | 69 (32) | 144 |
| X_unconverged | Gaussian, 24 knots (current) | 30 | 1.322 (1.740) | 12 (8) | 8 | 1.135 (1.581) | 22 (11) | 2 |
| X_unconverged | Student-t ν=3, 24 knots | 30 | 2.533 (4.146) | 7 (6) | 6 | 1.817 (2.317) | 10 (7) | 5 |
| X_unconverged | Gaussian, 36 knots | 20 | 1.442 (2.078) | 13 (8) | 12 | 1.266 (1.770) | 15 (10) | 2 |
| X_unconverged | Gaussian, 48 knots | 20 | 1.411 (1.967) | 12 (9) | 10 | 1.246 (2.094) | 16 (12) | 2 |

X_unconverged band width relative to the converged run on the same seeds (median): Gaussian, 24 knots (current) 0.87, Student-t ν=3, 24 knots 0.52, Gaussian, 36 knots 0.80, Gaussian, 48 knots 0.82.


## 5. Stage 14 and the injected faults

| config | candidate | n | Stage 14 bias (¢) | \|z\| vs truth med | E[F] 90% cov | parity flags the forward | z(used) > 3 | injected strike resid > 3 | χ² > 2 | edge-mass fails | sampler flagged |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M_crude_nomart | Gaussian, 24 knots (current) | 30 | -0.68 | 0.72 | 97% | 0% | 3% | — | 3% | 0% | 100% |
| M_crude_nomart | Student-t ν=3, 24 knots | 30 | -0.97 | 0.72 | 90% | 0% | 3% | — | 3% | 0% | 100% |
| M_crude_nomart | Gaussian, 36 knots | 20 | -0.76 | 0.67 | 100% | 0% | 0% | — | 5% | 0% | 100% |
| M_crude_nomart | Gaussian, 48 knots | 20 | -0.63 | 0.67 | 95% | 0% | 0% | — | 5% | 0% | 100% |
| X_fwd15 | Gaussian, 24 knots (current) | 30 | +14.00 | 17.40 | 0% | 100% | 3% | — | 27% | 0% | 100% |
| X_fwd15 | Student-t ν=3, 24 knots | 30 | +14.01 | 17.30 | 0% | 100% | 3% | — | 27% | 0% | 100% |
| X_fwd15 | Gaussian, 36 knots | 20 | +13.84 | 16.36 | 0% | 100% | 5% | — | 35% | 0% | 100% |
| X_fwd15 | Gaussian, 48 knots | 20 | +13.90 | 16.90 | 0% | 100% | 5% | — | 25% | 0% | 100% |
| X_stale | Gaussian, 24 knots (current) | 30 | +24.32 | 1.45 | 57% | 0% | 13% | 100% | 100% | 3% | 100% |
| X_stale | Student-t ν=3, 24 knots | 30 | +0.12 | 1.43 | 57% | 0% | 10% | 100% | 100% | 3% | 100% |
| X_stale | Gaussian, 36 knots | 20 | -0.20 | 1.37 | 55% | 0% | 0% | 100% | 100% | 0% | 100% |
| X_stale | Gaussian, 48 knots | 20 | +6.37 | 1.20 | 55% | 0% | 0% | 100% | 100% | 0% | 100% |
| X_stale | Gaussian, 48 knots + LOO exclusion | 20 | +0.00 | 0.89 | 70% | 0% | 0% | — | 5% | 0% | 100% |
| X_convexity | Gaussian, 24 knots (current) | 30 | +1.42 | 1.39 | 60% | 0% | 17% | 100% | 100% | 0% | 100% |
| X_convexity | Student-t ν=3, 24 knots | 30 | +1.41 | 1.38 | 57% | 0% | 17% | 100% | 100% | 0% | 100% |
| X_convexity | Gaussian, 36 knots | 20 | +1.38 | 1.09 | 55% | 0% | 20% | 100% | 100% | 0% | 100% |
| X_convexity | Gaussian, 48 knots | 20 | +1.35 | 1.08 | 55% | 0% | 25% | 100% | 100% | 0% | 100% |
| X_convexity | Gaussian, 48 knots + LOO exclusion | 20 | +0.04 | 0.91 | 70% | 0% | 0% | — | 5% | 0% | 100% |
| X_truncated_grid | Gaussian, 24 knots (current) | 30 | +0.19 | 0.91 | 83% | 0% | 0% | — | 100% | 100% | 100% |
| X_truncated_grid | Student-t ν=3, 24 knots | 30 | +0.19 | 0.90 | 73% | 0% | 0% | — | 100% | 100% | 100% |
| X_truncated_grid | Gaussian, 36 knots | 20 | -0.00 | 1.05 | 75% | 0% | 0% | — | 100% | 100% | 100% |
| X_truncated_grid | Gaussian, 48 knots | 20 | -0.00 | 1.02 | 75% | 0% | 0% | — | 100% | 100% | 100% |
| X_unconverged | Gaussian, 24 knots (current) | 30 | +0.20 | 0.92 | 83% | 0% | 0% | — | 3% | 0% | 100% |
| X_unconverged | Student-t ν=3, 24 knots | 30 | +0.02 | 0.96 | 73% | 0% | 0% | — | 3% | 0% | 100% |
| X_unconverged | Gaussian, 36 knots | 20 | -0.04 | 0.76 | 65% | 0% | 0% | — | 5% | 0% | 100% |
| X_unconverged | Gaussian, 48 knots | 20 | -0.03 | 1.02 | 70% | 0% | 0% | — | 5% | 0% | 100% |

## 6. Reading


**Why the tail form did nothing at 24 knots.** The brief's diagnosis — one scale for the whole curve, Gaussian tails, so a sharp
feature is astronomically improbable at any τ — is right about the *prior*, but the prior was not the binding constraint. With 24
coefficients over ±7 vol-scales the knots are 0.7 vol-scales apart; the planted humps are 2.6 apart, so the trough between them spans
about two knot intervals, and a cubic B-spline with that spacing cannot represent a trough of that width at all. A heavier-tailed prior
makes large second differences cheaper, but the increments the trough needs cannot be formed in the basis, so the posterior under
Student-t ν=3 is the Gaussian posterior with a smaller τ (3.43 vs 4.95): same trough z, same 0.7¢ band, same 100% two-mode recovery with
the wrong depth. The three hyperpriors of `FINDINGS_SYNTHETIC.md` §9 giving identical answers was the same symptom. Cauchy increments
(ν=1) and explicit local scales (horseshoe) do not change the answer either and mix unusably: R̂ 1.05 / 1.62 on crude chains, ESS 96 / 27 —
the docstring's warning about sampled scales was borne out (a global τ on top of local λ_j ran straight down the flat τ→0, λ→∞ ridge and
had to be removed before the horseshoe would fit at all).

**What resolution does.** 36 knots halve the trough z (+2.3), 48 knots take it to +1.3 with a 1.55¢ band that contains the truth 57% of the
time, and the improvement carries to the shapes the brief listed: kinked peak body coverage 53% → 89%, spike 46% → 59%, half-noise bimodal
trough z +11.2 → +1.7. `F_bimodal_close` stays honest (trough coverage 100%). The price is precision on smooth truths, not calibration: on the
crude-skew chains coverage is unchanged (92% / 95% / 95% all / body / tail against 92% / 95% / 95%) while the body band widens from 1.90¢ to 2.70¢
and the RMSE from 0.57¢ to 0.66¢ — the model is admitting shapes it used to rule out by construction. The eight-strike gate holds (98% vs
97%), Stage 14 is unchanged (|z| 0.67 vs 0.72), and every injected fault is still caught at the same rate.

**Sampler health at 48 knots** is inside the gate on the crude chains (bracket R̂ 1.020 vs 1.016, bracket ESS 260 vs 290, divergences 31 vs
23 per run) and somewhat worse on the bimodal ones (bracket ESS 108 vs 147, p10 32), which is where the posterior is now genuinely
multimodal in shape and the whitening at the MAP is a poorer guide. Run time per chain rises from 68 s to 83 s. Student-t on 48 knots
adds nothing to the blind-spot rows and pushes bracket R̂ to 1.030 and the RMSE past the tolerance, so it is rejected.

**What is still not right.** Trough coverage 57% and overall bimodal coverage 72% at 48 knots are honest by comparison with 0% and 42%,
but they are not 90%: the band at the trough is still too narrow by a factor of about two. Two things are left to try, in order:
(i) more resolution — 64 knots (run: trough z +1.1, trough coverage 75%, overall 74%, spike 59%; bracket R̂ 1.021, ESS 217 on crude chains — REJECTED (regresses: A_rmse_body)); (ii) knots dense where strikes are dense, which the writeup asked for and V2 deferred because a
non-uniform knot vector changes what the second-difference penalty means (the fix is a divided-difference penalty, standard for
unequal P-splines). The learned-prior idea the operator raised stays behind both: calibrating τ's hyperprior from real extractions is
sound and cheap once the basis can express what the data ask for, but it cannot substitute for that.

**Part B on this harness** (`m48x`: 48 knots with the LOO exclusion rule applied before the fit): coverage on the clean chains is
unchanged (92% / 95% / 96%), 0.7% of quotes are removed on them and none on the 8-strike chains, the injected stale and crossed quotes
are removed on 100% of the fault chains, and the bimodal truth is untouched (73% overall). The rule removes noise, not signal; what it
does on the real chains is in `FINDINGS_REALCHAIN_V4.md` §8.

**Recommendation.** Make 48 uniform knots with the Gaussian prior the default (`act3.M_COEF = 48`), re-run the real chains with it
(`FINDINGS_REALCHAIN_V4.md`), and keep the 24-knot model runnable as the baseline. `FINDINGS_SYNTHETIC.md`'s FAIL verdict is
superseded in its diagnosis (form of the prior) but not in its status: the harness still shows a 1.6¢-wide band that misses the
truth by 1.3σ at the trough, so the answer to "is the blind spot closed" is **narrowed, not closed**.

Plots: `synth/plots_prior/` — the planted bimodal, spike and kinked chains under each prior (same seed).

