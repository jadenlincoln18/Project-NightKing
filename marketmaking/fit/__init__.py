"""Fair-value fitting for Kalshi *range* ladders — PROTOCOL §1B Gate 0.

Everything in this package is new code living inside `marketmaking/`. It never
imports, modifies, subclasses or monkey-patches `wti_arb/synth/`, `ladder/` or
`waves/`; `ladder.store` is read read-only for staged historical data only.

Why a new module rather than a call into the existing extractor
---------------------------------------------------------------
`wti_arb/synth/act3.py` infers a density from how **option prices curve across
strikes**: its payoff matrix is vanilla call/put payoffs on a **log-moneyness**
grid centred on a forward `F0`, with the grid half-width set by an implied
volatility. A daily city-temperature ladder has no forward, no implied
volatility, and a support that reaches 0 °F and below, where `log(s/F0)` is not
defined. A Kalshi bracket is also not a vanilla: it is a **digital on an
interval**, so its payoff row is an indicator integral, not `(s-K)^+`.

What is reused is the *structure*, copied here rather than imported:
B-spline-parameterised log-density, second-difference roughness prior with a
sampled smoothing scale, Gaussian likelihood with sd = half-spread, posterior
draws, and a 90% credible band taken as posterior quantiles (`band90`).
"""
