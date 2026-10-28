# FINDINGS_TICKFLOOR — a tick floor on the likelihood tolerance, against the LOO exclusion rule

Task 1 of `NightKing/HANDOFF_tickfloor_and_fullsynth.md`. The likelihood's tolerance is the quote's half-spread; options trade in 1¢ ticks, so a 1¢-wide market (half-spread 0.5¢) does not locate the price to 0.5¢, and `FINDINGS_PRIOR.md` Part B found that the exclusion rule was removing exactly those quotes (57% of removed quotes had a 0.5¢ half-spread). On the real chains 26–32% of quotes are 1¢ wide and a further 20–23% are 2¢ wide. A half-tick floor taken as a maximum is a no-op (no half-spread is below 0.5¢), so the sweep is 0.5¢ added in quadrature, 1¢, 1¢ in quadrature, and 2¢. Every arm is 48 knots with the Gaussian prior; the exclusion rule is Part B's (LOO |z| > 3, once, Gate 0 preserved).

**Verdict: the floor works on the real chains and the exclusion rule is mostly, not entirely, redundant with it — adopt the 1¢ floor for the real chains, keep the exclusion rule as a diagnostic, and do not adopt it as a default. With a 1¢ floor and no quote removed, T-1d/60 χ²/strike goes 1.8 → 1.4 (T-4h 1.5 → 1.1, T-2d 1.5 → 1.2), Gate 4 fires on 3% instead of 27% of T-1d chains, Stage 14 passes on 93% instead of 87%, bands narrow slightly (3.8 → 3.2¢) and the sampler is unchanged; the exclusion rule gets χ² to 1.3 and Gate 4 to 0% but by deleting 8–10% of quotes. Leave-one-out still flags strikes on 87% of floored chains, so a residual of genuinely inconsistent quotes remains that the tolerance does not explain (the combined arm removes 6.7% of quotes on top of the floor, 26% of chains marked suspect, and reaches χ² 1.1, Gate 4 0%). The synthetic harness could not admit any floor: every variant kept coverage on the fault, 8-strike and bimodal chains and improved RMSE, but drifted crude-skew coverage to 96%–98% because its noise model is Gaussian-exact with sd = half-spread and has no tick-level inconsistency to absorb — so, by the rule fixed in advance, the full synthetic study (`FINDINGS_SYNTHETIC_V2.md`) ran without a floor. That is a limitation of the harness, not evidence against the floor, and it is the one place this document departs from "synthetic is the arbiter": the floor exists for a feature of real quotes the synthetic quotes do not have.**

Decision rule fixed before the runs (`synth/tickfloor_decide.py`): a floor is admissible if crude-skew 90% coverage stays in [88%, 95%] and within 3 points of base48, the stale and crossed injected quotes are still caught on ≥ 90% of chains, bimodal coverage is within 5 points of base48, and bracket R̂ ≤ 1.03; the smallest admissible floor is adopted. Outcome: **no floor admissible**.

| candidate | admissible | crude cov90 in [88, 95]% | not 3 pts below base48 | stale caught | crossed caught | bimodal within 5 pts | bracket R̂ ≤ 1.03 |
|---|---|---|---|---|---|---|---|
| floor48: 0.5¢ (quadrature) | no | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| floor48: 1¢ (max) | no | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| floor48: 1¢ (quadrature) | no | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| floor48: 2¢ (max) | no | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |

## 1. Synthetic harness (paired seeds, 48 knots throughout)

| config | arm | n | cov90 all | body | tail | RMSE body (¢) | tail | width body (¢) | tail | χ²/strike med | bracket R̂ med | bracket ESS med | quotes removed / chain | injected strike removed | injected resid > 3 | Stage 14 \|z\| |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_crude_full | base48: 48 knots, no floor, no exclusion | 30 | 92% | 95% | 95% | 0.66 | 0.28 | 2.70 | 1.05 | 1.02 | 1.020 | 260 | 0 | — | — | 0.95 |
| A_crude_full | floor48: 0.5¢ (quadrature) | 30 | 96% | 96% | 98% | 0.59 | 0.24 | 2.66 | 1.04 | 0.94 | 1.021 | 220 | 0 | — | — | 1.00 |
| A_crude_full | floor48: 1¢ (max) | 30 | 97% | 97% | 97% | 0.59 | 0.24 | 2.64 | 1.02 | 0.92 | 1.018 | 249 | 0 | — | — | 0.94 |
| A_crude_full | floor48: 1¢ (quadrature) | 30 | 98% | 98% | 98% | 0.52 | 0.22 | 2.83 | 1.09 | 0.80 | 1.018 | 244 | 0 | — | — | 0.97 |
| A_crude_full | floor48: 2¢ (max) | 30 | 98% | 99% | 98% | 0.54 | 0.22 | 2.99 | 1.15 | 0.72 | 1.021 | 232 | 0 | — | — | 0.95 |
| A_crude_full | excl48: LOO exclusion, no floor | 30 | 92% | 95% | 96% | 0.68 | 0.29 | 2.69 | 1.04 | 1.01 | 1.016 | 276 | 0.27 | — | — | 0.95 |
| A_crude_full | both: 1¢ floor + exclusion | 30 | 97% | 97% | 98% | 0.62 | 0.25 | 2.63 | 1.02 | 0.90 | 1.017 | 249 | 0.20 | — | — | 0.94 |
| B_lognormal_full | base48: 48 knots, no floor, no exclusion | 30 | 80% | 97% | 93% | 0.78 | 0.41 | 3.34 | 1.24 | 1.16 | 1.028 | 174 | 0 | — | — | 0.72 |
| B_lognormal_full | floor48: 0.5¢ (quadrature) | 30 | 88% | 98% | 96% | 0.64 | 0.32 | 3.14 | 1.17 | 1.05 | 1.025 | 276 | 0 | — | — | 0.69 |
| B_lognormal_full | floor48: 1¢ (max) | 30 | 94% | 98% | 97% | 0.61 | 0.29 | 2.96 | 1.11 | 0.90 | 1.019 | 246 | 0 | — | — | 0.75 |
| B_lognormal_full | floor48: 1¢ (quadrature) | 30 | 95% | 99% | 98% | 0.53 | 0.26 | 3.13 | 1.16 | 0.75 | 1.018 | 256 | 0 | — | — | 0.77 |
| B_lognormal_full | floor48: 2¢ (max) | 30 | 96% | 99% | 97% | 0.55 | 0.25 | 3.45 | 1.25 | 0.60 | 1.017 | 267 | 0 | — | — | 0.80 |
| B_lognormal_full | both: 1¢ floor + exclusion | 30 | 94% | 98% | 97% | 0.59 | 0.28 | 2.96 | 1.10 | 0.89 | 1.019 | 238 | 0.20 | — | — | 0.72 |
| S08_crude | base48: 48 knots, no floor, no exclusion | 20 | 98% | 100% | 100% | 0.82 | 0.42 | 4.85 | 1.88 | 1.02 | 1.037 | 144 | 0 | — | — | 0.99 |
| S08_crude | floor48: 0.5¢ (quadrature) | 20 | 99% | 100% | 100% | 0.78 | 0.39 | 4.85 | 1.86 | 0.97 | 1.039 | 140 | 0 | — | — | 1.07 |
| S08_crude | floor48: 1¢ (max) | 20 | 99% | 100% | 100% | 0.81 | 0.40 | 5.07 | 1.93 | 0.95 | 1.032 | 139 | 0 | — | — | 1.01 |
| S08_crude | floor48: 1¢ (quadrature) | 20 | 99% | 100% | 100% | 0.77 | 0.40 | 5.05 | 1.99 | 0.82 | 1.045 | 141 | 0 | — | — | 1.05 |
| S08_crude | floor48: 2¢ (max) | 20 | 99% | 100% | 100% | 0.78 | 0.40 | 5.39 | 2.05 | 0.77 | 1.033 | 162 | 0 | — | — | 1.07 |
| S08_crude | excl48: LOO exclusion, no floor | 20 | 98% | 100% | 100% | 0.82 | 0.42 | 4.85 | 1.88 | 1.02 | 1.037 | 144 | 0.00 | — | — | 0.99 |
| S08_crude | both: 1¢ floor + exclusion | 20 | 99% | 100% | 100% | 0.81 | 0.40 | 5.07 | 1.93 | 0.95 | 1.032 | 139 | 0.00 | — | — | 1.01 |
| C_bimodal_full | base48: 48 knots, no floor, no exclusion | 30 | 72% | 74% | 81% | 1.58 | 0.70 | 4.09 | 1.73 | 1.05 | 1.056 | 108 | 0 | — | — | 0.66 |
| C_bimodal_full | floor48: 0.5¢ (quadrature) | 20 | 82% | 85% | 89% | 1.42 | 0.65 | 4.37 | 1.73 | 0.99 | 1.031 | 179 | 0 | — | — | 0.71 |
| C_bimodal_full | floor48: 1¢ (max) | 20 | 85% | 88% | 89% | 1.33 | 0.62 | 4.21 | 1.70 | 0.90 | 1.026 | 165 | 0 | — | — | 0.74 |
| C_bimodal_full | floor48: 1¢ (quadrature) | 20 | 88% | 93% | 91% | 1.25 | 0.63 | 4.59 | 1.84 | 0.81 | 1.032 | 189 | 0 | — | — | 0.74 |
| C_bimodal_full | floor48: 2¢ (max) | 20 | 92% | 95% | 93% | 1.18 | 0.63 | 5.14 | 1.98 | 0.70 | 1.023 | 228 | 0 | — | — | 0.74 |
| C_bimodal_full | excl48: LOO exclusion, no floor | 20 | 73% | 78% | 82% | 1.66 | 0.81 | 4.38 | 1.72 | 0.98 | 1.044 | 142 | 0.60 | — | — | 0.72 |
| C_bimodal_full | both: 1¢ floor + exclusion | 20 | 85% | 90% | 89% | 1.52 | 0.78 | 4.55 | 1.74 | 0.92 | 1.028 | 142 | 0.75 | — | — | 0.73 |
| X_stale | base48: 48 knots, no floor, no exclusion | 20 | 64% | 49% | 60% | 11.24 | 5.84 | 6.33 | 2.53 | 11.24 | 1.151 | 46 | 0 | — | 100% | 1.20 |
| X_stale | floor48: 0.5¢ (quadrature) | 20 | 66% | 48% | 60% | 11.19 | 5.26 | 6.49 | 2.64 | 10.75 | 1.128 | 54 | 0 | — | 100% | 1.13 |
| X_stale | floor48: 1¢ (max) | 20 | 70% | 54% | 62% | 12.65 | 5.06 | 6.54 | 2.19 | 11.11 | 1.158 | 45 | 0 | — | 100% | 1.25 |
| X_stale | floor48: 1¢ (quadrature) | 20 | 70% | 51% | 64% | 11.85 | 5.13 | 7.14 | 2.42 | 9.80 | 1.164 | 54 | 0 | — | 100% | 1.10 |
| X_stale | floor48: 2¢ (max) | 20 | 70% | 49% | 59% | 11.99 | 5.54 | 6.61 | 2.54 | 9.82 | 1.243 | 45 | 0 | — | 100% | 1.29 |
| X_stale | excl48: LOO exclusion, no floor | 20 | 94% | 100% | 97% | 0.75 | 0.32 | 3.56 | 1.27 | 0.94 | 1.018 | 201 | 3.90 | 100% | — | 0.89 |
| X_stale | both: 1¢ floor + exclusion | 20 | 97% | 100% | 99% | 0.55 | 0.24 | 3.23 | 1.15 | 0.86 | 1.015 | 304 | 4.00 | 100% | — | 0.91 |
| X_convexity | base48: 48 knots, no floor, no exclusion | 20 | 68% | 41% | 64% | 7.62 | 3.04 | 4.93 | 2.12 | 12.21 | 1.075 | 99 | 0 | — | 100% | 1.08 |
| X_convexity | floor48: 0.5¢ (quadrature) | 20 | 69% | 46% | 62% | 7.43 | 3.05 | 5.11 | 2.18 | 11.68 | 1.187 | 46 | 0 | — | 100% | 1.04 |
| X_convexity | floor48: 1¢ (max) | 20 | 73% | 49% | 64% | 7.62 | 3.07 | 5.17 | 2.21 | 12.07 | 1.067 | 84 | 0 | — | 100% | 1.07 |
| X_convexity | floor48: 1¢ (quadrature) | 20 | 75% | 43% | 68% | 6.87 | 2.83 | 5.47 | 2.33 | 10.59 | 1.092 | 74 | 0 | — | 100% | 0.90 |
| X_convexity | floor48: 2¢ (max) | 20 | 75% | 44% | 68% | 6.72 | 2.84 | 5.65 | 2.45 | 10.89 | 1.107 | 77 | 0 | — | 100% | 0.93 |
| X_convexity | excl48: LOO exclusion, no floor | 20 | 94% | 98% | 95% | 0.87 | 0.35 | 3.54 | 1.21 | 0.93 | 1.021 | 274 | 3.90 | 100% | — | 0.91 |
| X_convexity | both: 1¢ floor + exclusion | 20 | 94% | 97% | 93% | 0.78 | 0.31 | 3.41 | 1.18 | 0.80 | 1.022 | 244 | 3.90 | 100% | — | 0.92 |

## 2. Real chains (30 dates, every snapshot; 48 knots throughout)

| snapshot | window | arm | n | χ²/strike med (p90) | χ² < 2 | max resid < 3 | Gate 4 fired | LOO flags / chain | chains with a LOO flag | quotes removed / chain | share removed | Stage 14 pass | \|z\| med | multimodal majority | 90% body width (¢) | bracket R̂ med | bracket ESS med | divergences med |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T-2d | 60 | base48 | 26 | 1.5 (2.1) | 85% | 65% | 23% | 1.8 | 77% | 0.0 | 0% | 96% | 1.1 | 8% | 2.7 | 1.021 | 227 | 21 |
| T-2d | 60 | floor48 1¢ | 26 | 1.2 (1.7) | 100% | 85% | 12% | 1.7 | 77% | 0.0 | 0% | 96% | 1.0 | 0% | 2.6 | 1.016 | 269 | 20 |
| T-2d | 60 | excl48 | 26 | 1.3 (1.5) | 100% | 92% | 0% | 0.2 | 19% | 1.7 | 9% | 96% | 0.9 | 0% | 2.1 | 1.014 | 295 | 26 |
| T-2d | 60 | both (1¢ + excl) | 26 | 0.9 (1.4) | 100% | 100% | 0% | 0.3 | 31% | 1.6 | 8% | 96% | 0.9 | 0% | 2.1 | 1.015 | 281 | 21 |
| T-2d | 10 | base48 | 8 | 1.1 (1.9) | 88% | 100% | 0% | 0.6 | 62% | 0.0 | 0% | 100% | 0.8 | 0% | 4.5 | 1.024 | 259 | 31 |
| T-2d | 10 | floor48 1¢ | 8 | 1.1 (1.2) | 100% | 100% | 0% | 0.8 | 62% | 0.0 | 0% | 100% | 1.0 | 0% | 4.5 | 1.016 | 277 | 23 |
| T-2d | 10 | excl48 | 8 | 1.1 (1.9) | 88% | 100% | 0% | 0.2 | 25% | 0.4 | 3% | 100% | 1.1 | 0% | 4.5 | 1.024 | 201 | 44 |
| T-2d | 10 | both (1¢ + excl) | 8 | 1.1 (1.2) | 100% | 100% | 0% | 0.5 | 38% | 0.4 | 4% | 100% | 1.0 | 0% | 4.3 | 1.028 | 194 | 41 |
| T-1d | 60 | base48 | 30 | 1.8 (3.2) | 53% | 53% | 27% | 2.9 | 87% | 0.0 | 0% | 87% | 1.3 | 10% | 3.8 | 1.017 | 159 | 20 |
| T-1d | 60 | floor48 1¢ | 30 | 1.4 (3.1) | 70% | 67% | 3% | 2.6 | 87% | 0.0 | 0% | 93% | 1.2 | 3% | 3.2 | 1.021 | 213 | 14 |
| T-1d | 60 | excl48 | 30 | 1.3 (1.8) | 97% | 100% | 0% | 0.2 | 20% | 2.9 | 10% | 100% | 0.9 | 0% | 3.3 | 1.021 | 258 | 15 |
| T-1d | 60 | both (1¢ + excl) | 30 | 1.1 (1.6) | 97% | 100% | 0% | 0.2 | 20% | 2.6 | 9% | 100% | 0.8 | 0% | 2.9 | 1.022 | 277 | 28 |
| T-1d | 10 | base48 | 21 | 1.2 (2.4) | 81% | 90% | 0% | 0.8 | 33% | 0.0 | 0% | 90% | 0.9 | 0% | 3.5 | 1.024 | 185 | 32 |
| T-1d | 10 | floor48 1¢ | 21 | 1.1 (1.7) | 90% | 95% | 5% | 0.8 | 43% | 0.0 | 0% | 90% | 0.9 | 0% | 3.9 | 1.027 | 181 | 33 |
| T-1d | 10 | excl48 | 21 | 1.2 (1.7) | 95% | 100% | 0% | 0.1 | 10% | 0.8 | 5% | 95% | 0.9 | 0% | 3.3 | 1.024 | 224 | 26 |
| T-1d | 10 | both (1¢ + excl) | 21 | 1.0 (1.5) | 100% | 100% | 0% | 0.1 | 14% | 0.7 | 5% | 95% | 0.9 | 0% | 3.7 | 1.027 | 185 | 33 |
| T-4h | 60 | base48 | 30 | 1.5 (3.1) | 70% | 53% | 13% | 1.8 | 77% | 0.0 | 0% | 90% | 1.0 | 10% | 7.2 | 1.023 | 231 | 12 |
| T-4h | 60 | floor48 1¢ | 30 | 1.1 (2.0) | 90% | 77% | 7% | 1.5 | 77% | 0.0 | 0% | 97% | 1.0 | 7% | 7.1 | 1.022 | 185 | 15 |
| T-4h | 60 | excl48 | 30 | 1.2 (1.8) | 97% | 77% | 3% | 0.2 | 17% | 1.8 | 7% | 97% | 1.1 | 3% | 7.0 | 1.021 | 229 | 9 |
| T-4h | 60 | both (1¢ + excl) | 30 | 0.9 (1.4) | 100% | 100% | 3% | 0.3 | 23% | 1.5 | 5% | 100% | 0.9 | 0% | 7.1 | 1.024 | 228 | 12 |
| T-4h | 10 | base48 | 9 | 1.5 (2.5) | 78% | 78% | 11% | 0.8 | 44% | 0.0 | 0% | 100% | 1.3 | 0% | 8.0 | 1.019 | 170 | 15 |
| T-4h | 10 | floor48 1¢ | 9 | 1.3 (1.7) | 100% | 89% | 0% | 1.0 | 44% | 0.0 | 0% | 100% | 1.0 | 0% | 7.1 | 1.023 | 255 | 28 |
| T-4h | 10 | excl48 | 9 | 1.3 (1.7) | 89% | 89% | 0% | 0.3 | 22% | 0.7 | 5% | 100% | 0.9 | 0% | 8.0 | 1.031 | 132 | 15 |
| T-4h | 10 | both (1¢ + excl) | 9 | 1.2 (1.6) | 100% | 100% | 0% | 0.4 | 22% | 0.8 | 5% | 100% | 0.8 | 0% | 7.1 | 1.025 | 255 | 28 |

## 3. Where the floor and the exclusion rule disagree (60-minute windows, floor48 1¢ vs excl48)

Gate 4 (split-half) and the LOO flag count per chain under each treatment; a chain is listed if Gate 4's answer differs or the χ²/strike differs by more than 0.5.

| date | snap | strikes | χ²: base48 / floor / excl | Gate 4: base48 / floor / excl | LOO flags: base48 / floor / excl | quotes removed by excl | modes: floor / excl | width (¢): floor / excl |
|---|---|---|---|---|---|---|---|---|
| 2026-01-09 | T-2d | 12 | 1.3 / 0.7 / 1.3 | quiet / quiet / quiet | 1 / 3 / 0 | 1 | 1 / 1 | 11.2 / 9.3 |
| 2026-01-09 | T-4h | 14 | 1.3 / 0.8 / 1.3 | quiet / quiet / quiet | 0 / 0 / 0 | 0 | 1 / 1 | 8.0 / 7.2 |
| 2026-01-16 | T-4h | 18 | 1.5 / 0.9 / 1.5 | quiet / quiet / quiet | 0 / 0 / 0 | 0 | 1 / 1 | 8.4 / 5.6 |
| 2026-01-30 | T-4h | 17 | 3.3 / 2.1 / 1.0 | quiet / quiet / quiet | 4 / 4 / 0 | 4 | 1 / 1 | 8.0 / 9.8 |
| 2026-02-13 | T-2d | 24 | 2.8 / 1.8 / 1.3 | quiet / quiet / quiet | 5 / 5 / 0 | 5 | 1 / 1 | 7.1 / 5.6 |
| 2026-02-13 | T-4h | 14 | 1.7 / 0.8 / 1.4 | quiet / quiet / quiet | 1 / 1 / 0 | 1 | 1 / 1 | 10.2 / 9.9 |
| 2026-02-27 | T-1d | 34 | 8.0 / 5.9 / 1.8 | fired / quiet / quiet | 9 / 8 / 1 | 9 | 1 / 1 | 3.7 / 3.9 |
| 2026-02-27 | T-2d | 16 | 2.1 / 1.2 / 1.8 | quiet / quiet / quiet | 1 / 1 / 0 | 1 | 1 / 1 | 4.6 / 4.1 |
| 2026-02-27 | T-4h | 26 | 1.3 / 0.7 / 1.2 | quiet / quiet / quiet | 2 / 1 / 0 | 2 | 1 / 1 | 9.4 / 9.1 |
| 2026-03-06 | T-4h | 41 | 4.3 / 2.8 / 1.9 | fired / fired / quiet | 6 / 5 / 0 | 6 | 1 / 1 | 2.2 / 3.1 |
| 2026-03-20 | T-1d | 46 | 3.3 / 3.1 / 1.5 | quiet / quiet / quiet | 5 / 5 / 0 | 5 | 1 / 1 | 1.4 / 1.4 |
| 2026-03-20 | T-2d | 28 | 2.2 / 2.0 / 1.0 | fired / fired / quiet | 4 / 4 / 0 | 4 | 1 / 1 | 1.5 / 1.2 |
| 2026-04-10 | T-1d | 48 | 2.4 / 2.3 / 1.3 | fired / fired / quiet | 7 / 6 / 0 | 7 | 3 / 1 | 6.3 / 1.5 |
| 2026-04-10 | T-2d | 25 | 1.5 / 1.5 / 1.0 | fired / fired / quiet | 2 / 2 / 0 | 2 | 1 / 1 | 1.3 / 1.4 |
| 2026-05-01 | T-2d | 19 | 1.5 / 1.5 / 0.9 | quiet / quiet / quiet | 2 / 2 / 0 | 2 | 1 / 1 | 1.8 / 1.7 |
| 2026-05-01 | T-4h | 48 | 4.1 / 2.2 / 1.4 | fired / quiet / quiet | 8 / 7 / 0 | 8 | 2 / 1 | 19.9 / 7.1 |
| 2026-05-08 | T-2d | 13 | 1.6 / 1.6 / 1.7 | fired / fired / quiet | 2 / 2 / 0 | 2 | 1 / 1 | 4.7 / 1.9 |
| 2026-05-22 | T-1d | 56 | 3.1 / 3.1 / 1.6 | fired / quiet / quiet | 8 / 7 / 1 | 8 | 1 / 1 | 1.6 / 1.5 |
| 2026-06-05 | T-1d | 22 | 3.2 / 2.5 / 1.6 | fired / quiet / quiet | 6 / 4 / 0 | 6 | 1 / 1 | 3.0 / 3.4 |
| 2026-06-12 | T-4h | 32 | 2.9 / 1.8 / 2.7 | quiet / quiet / quiet | 1 / 1 / 0 | 1 | 1 / 1 | 4.7 / 4.9 |
| 2026-07-10 | T-1d | 25 | 5.7 / 3.2 / 2.3 | fired / quiet / quiet | 5 / 5 / 0 | 5 | 1 / 1 | 4.3 / 3.8 |
| 2026-07-24 | T-1d | 21 | 2.8 / 2.6 / 1.9 | quiet / quiet / quiet | 3 / 2 / 0 | 3 | 1 / 1 | 2.1 / 2.0 |
| 2026-09-04 | T-1d | 31 | 2.3 / 1.2 / 1.8 | quiet / quiet / quiet | 1 / 1 / 0 | 1 | 1 / 1 | 2.7 / 3.1 |
| 2026-09-04 | T-2d | 30 | 1.4 / 0.9 / 1.4 | quiet / quiet / quiet | 0 / 0 / 0 | 0 | 1 / 1 | 2.0 / 2.1 |

24 chains listed.


## 4. Reading

**Why the floor is right on real chains and wrong on the harness.** A 1¢-wide market says the fair price is somewhere inside a
penny; the writeup's tolerance (sd = half-spread = 0.5¢) says it is known to half a penny at one sigma, so two adjacent tight quotes
that disagree by 2¢ — ordinary on a one-cent grid — are a 4σ event and the fit is pulled toward whichever one it can satisfy. On the
real chains the floor takes T-1d χ²/strike from 1.8 to 1.4 and T-4h to 1.1, the p90 from 3.2 to 3.1 at T-1d, the split-half gate from 27%
to 3%, and it does so with every quote in place and bands 3.2¢ rather than 3.8¢ (the tight quotes lose some pull, so the posterior
moves less between neighbours). On the synthetic harness the quotes are generated as the true price plus Gaussian noise with exactly
the half-spread as its scale, then rounded; there is no inconsistency between neighbours beyond that rounding, so any floor makes the
assumed noise larger than the real noise and coverage rises above nominal (92% → 96% for 0.5¢ in quadrature, 97% for 1¢) while width and
RMSE improve. The decision rule was fixed to reject exactly that drift, and it did. The harness would need a tick-inconsistency
component in its noise model to arbitrate the floor's *value*; what it can say is that a 1¢ floor costs nothing on calibration of the
fault detectors (stale and crossed quotes caught on 100% of chains), on the 8-strike gate or on the bimodal shapes.

**Is the exclusion rule redundant?** Mostly. Under the floor the rule's own criterion (LOO |z| > 3) still fires on 87% of T-1d chains
against 87% without it, because a subset of quotes disagree with their neighbours by more than a tick — 2026-02-27, 2026-03-06,
2026-04-10, 2026-05-22 and 2026-07-10 in §3 keep 4–8 flags under the floor and only the rule clears them. Those are the chains where
the two treatments disagree; on the other 19 chains listed the floor alone brings χ² to ≈ 1 and Gate 4 is quiet either way. The rule
therefore adds a second, smaller effect, and it buys it by deleting a tenth of the quotes on half the T-1d chains. The brief's
question — is deleting good-looking quotes still justified after the tolerance is corrected — has the answer: only as a diagnostic
that names the chains the backtest should distrust, not as a default that edits every chain.

**Recommendation.** For the real chains, `hs_floor = 0.01` (max) is the tolerance; the exclusion rule stays available (`--arms *x`) and
its flag count is reported per chain but nothing is removed by default. The full synthetic numbers in `FINDINGS_SYNTHETIC_V2.md` are
without the floor, per the rule; re-running the harness with a tick-inconsistency noise term and the floor is the natural next
validation, and it is small.

