"""Density fit for a Kalshi *range* ladder — the PROTOCOL §8.5 specification.

A bracket quote is **already a probability**: the mass of the outcome density
over an interval. So the forward operator is an *indicator integral*

    Chat_i = sum_k G[i, k] p_k ,   G[i, k] = fraction of cell k inside bracket i

not the vanilla call/put payoff `(s - K)^+` the WTI extractor uses. Everything
else about the inference is the WTI extractor's, reproduced here rather than
imported, because `wti_arb/synth/` may not be modified and its `Model` is
irreducibly an options-chain object (log-moneyness grid around a forward `F0`,
grid half-width set by an implied volatility — none of which a temperature has).

What is reproduced
------------------
  grid      s_k **linear in degrees Fahrenheit** on [lo, hi]  <- the one structural change
  basis     cubic B-splines in s, m coefficients, uniform clamped knots
  density   p_k = w_k exp(phi_k) / Z,  phi = B theta
  gauge     theta = Q eta, Q an orthonormal basis of the sum-zero subspace
  prior     second-difference (P-spline) penalty; in the eigenbasis of Q'D2'D2 Q the
            coordinates are a priori independent, u_j ~ N(0, tau^2 / e_j); the single
            e_j = 0 direction (the exponential tilt) gets N(0, 30^2)
  tau       integrated out exactly by 1-d quadrature over log tau, so the sampler sees
            m-1 coordinates and no funnel
  lik       Gaussian, sd = half-spread, against the bracket's quote midpoint
  metric    dense Gauss-Newton Hessian at the MAP, NUTS in whitened coordinates

What is deliberately absent
---------------------------
**No martingale constraint and no forward.** The WTI model can pin the density's
mean to `F0` because a futures price exists and no-arbitrage ties the two. A
daily temperature has neither.

On the prior scale not being retuned
------------------------------------
`TAU_LN_MED = 0.5` is the extractor's own value. It is *not* adjusted for the
change of coordinate, and it does not need to be: at m = 24 over a 48 degF grid
the knot spacing is ~2.3 degF, and the second difference of a Gaussian
log-density with sigma = 3 degF across that spacing is ~ h^2/sigma^2 = 0.6 — the
same order as the ~0.4 the WTI body produces at its own knot spacing. Retuning it
to flatter the fit is exactly the move PROTOCOL §8.5 forbids.
"""
from __future__ import annotations

import time

import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import minimize

from fit import nuts as _nuts

# --- hyperparameters, taken from the WTI extractor unchanged ----------------
TILT_SD = 30.0
TAU_LN_MED = 0.5
TAU_LN_SD = 1.0

# --- PROTOCOL §8.5 fixed settings -------------------------------------------
M_COEF = 24
N_GRID = 400
PAD_DEGF = 20.0
HS_FLOOR = 0.005
BAND_LEVEL = 90.0


def bspline_basis(x: np.ndarray, m: int, x_lo: float, x_hi: float, degree: int = 3) -> np.ndarray:
    n_inner = m - degree - 1
    inner = np.linspace(x_lo, x_hi, n_inner + 2)[1:-1]
    t = np.concatenate([[x_lo] * (degree + 1), inner, [x_hi] * (degree + 1)])
    return BSpline.design_matrix(np.clip(x, x_lo, x_hi), t, degree).toarray()


def bracket_operator(s: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """G[i, k] = share of grid cell k lying inside bracket i. Columns sum to 1.

    Cells are the Voronoi intervals of the grid points. A cell straddling an
    edge is split in proportion to the overlap rather than assigned whole, so a
    bracket boundary between grid points does not quantise the likelihood.
    """
    n_br = len(edges) + 1
    cell = np.concatenate([[s[0]], 0.5 * (s[1:] + s[:-1]), [s[-1]]])
    lo, hi = cell[:-1], cell[1:]
    width = np.maximum(hi - lo, 1e-12)
    bounds = np.concatenate([[-np.inf], np.asarray(edges, float), [np.inf]])
    G = np.empty((n_br, len(s)))
    for i in range(n_br):
        a, b = bounds[i], bounds[i + 1]
        G[i] = np.clip(np.minimum(hi, b) - np.maximum(lo, a), 0.0, None) / width
    return G


class LadderModel:
    """Posterior over a log-density on a linear degF grid, given bracket quotes."""

    def __init__(self, edges, probs, half_spreads, s_lo, s_hi,
                 m: int = M_COEF, n_grid: int = N_GRID, hs_floor: float = HS_FLOOR):
        self.edges = np.asarray(edges, float)
        self.mid = np.asarray(probs, float)
        self.hs = np.maximum(np.asarray(half_spreads, float), hs_floor)
        n_br = len(self.mid)
        if len(self.edges) != n_br - 1:
            raise ValueError("need %d interior edges for %d brackets, got %d"
                             % (n_br - 1, n_br, len(self.edges)))
        self.n_br = n_br

        self.s_lo, self.s_hi = float(s_lo), float(s_hi)
        self.s = np.linspace(self.s_lo, self.s_hi, n_grid)
        h = np.diff(self.s)
        w = np.zeros(n_grid)
        w[:-1] += 0.5 * h
        w[1:] += 0.5 * h
        self.w = w
        self.logw = np.log(w)
        self.m = m
        self.B = bspline_basis(self.s, m, self.s_lo, self.s_hi)
        self.G = bracket_operator(self.s, self.edges)

        ones = np.ones((m, 1)) / np.sqrt(m)
        Qfull, _ = np.linalg.qr(np.hstack([ones, np.eye(m)[:, :-1]]))
        self.Q = Qfull[:, 1:]
        D2 = np.zeros((m - 2, m))
        for i in range(m - 2):
            D2[i, i:i + 3] = [1.0, -2.0, 1.0]
        e, V = np.linalg.eigh(self.Q.T @ D2.T @ D2 @ self.Q)
        self.eig = np.maximum(e, 0.0)
        self.penalised = self.eig > 1e-8
        self.q_pen = int(self.penalised.sum())
        self.QV = self.Q @ V
        self.dim = m - 1
        self.nll_scale = 1.0 / np.maximum(self.hs, 1e-4)

        self.logtau_grid = np.linspace(-7.0, 5.0, 361)
        tau_g = np.exp(self.logtau_grid)
        self.inv_tau2 = 1.0 / tau_g ** 2
        log_p_tau = -0.5 * ((self.logtau_grid - np.log(TAU_LN_MED)) / TAU_LN_SD) ** 2
        self.prior_const = (-self.q_pen * self.logtau_grid + log_p_tau
                            + 0.5 * float(np.sum(np.log(self.eig[self.penalised]))))

    # --- prior ---------------------------------------------------------------
    def _marginal_prior(self, S: float):
        a = self.prior_const - 0.5 * S * self.inv_tau2
        mx = a.max()
        ex = np.exp(a - mx)
        Z = ex.sum()
        wq = ex / Z
        return mx + np.log(Z), -0.5 * float(wq @ self.inv_tau2), wq

    def tau_draw(self, psi, rng) -> float:
        u = np.asarray(psi, float)
        S = float(np.sum(self.eig[self.penalised] * u[self.penalised] ** 2))
        _, _, wq = self._marginal_prior(S)
        return float(np.exp(self.logtau_grid[rng.choice(len(wq), p=wq / wq.sum())]))

    # --- density -------------------------------------------------------------
    def density(self, theta):
        lg = self.B @ theta + self.logw
        lg -= lg.max()
        p = np.exp(lg)
        p /= p.sum()
        return p, p / self.w

    def _lik_terms(self, theta):
        p, _ = self.density(theta)
        Chat = self.G @ p
        r = (self.mid - Chat) * self.nll_scale
        bbar = p @ self.B
        J = self.G @ (p[:, None] * self.B) - np.outer(Chat, bbar)
        return p, r, J

    def logpost(self, psi, with_grad: bool = True):
        u = np.asarray(psi, float)
        if not np.all(np.isfinite(u)) or np.max(np.abs(u)) > 1e4:
            return -np.inf if not with_grad else (-np.inf, np.zeros(self.dim))
        theta = self.QV @ u
        if with_grad:
            p, r, J = self._lik_terms(theta)
            g_theta = J.T @ (r * self.nll_scale)
        else:
            p, _ = self.density(theta)
            r = (self.mid - self.G @ p) * self.nll_scale
        lp = -0.5 * float(r @ r)
        pen = self.penalised
        S = float(np.sum(self.eig[pen] * u[pen] ** 2))
        lse, dlse_dS, _ = self._marginal_prior(S)
        lp += lse
        tilt = ~pen
        lp += -0.5 * float(u[tilt] @ u[tilt]) / TILT_SD ** 2
        if not with_grad:
            return lp
        g_u = self.QV.T @ g_theta
        g_u[pen] += dlse_dS * 2.0 * self.eig[pen] * u[pen]
        g_u[tilt] += -u[tilt] / TILT_SD ** 2
        return lp, g_u

    def gauss_newton(self, psi):
        u = np.asarray(psi, float)
        theta = self.QV @ u
        _, _, J = self._lik_terms(theta)
        Ju = J @ self.QV
        H = (Ju * self.nll_scale[:, None] ** 2).T @ Ju
        pen = self.penalised
        S = float(np.sum(self.eig[pen] * u[pen] ** 2))
        _, dlse_dS, _ = self._marginal_prior(S)
        prior = np.full(self.dim, 1.0 / TILT_SD ** 2)
        prior[pen] = -2.0 * dlse_dS * self.eig[pen]
        return H + np.diag(prior)

    # --- summaries -----------------------------------------------------------
    def bracket_draws(self, thetas) -> np.ndarray:
        """(M, n_br) posterior draws of the bracket probabilities."""
        out = np.empty((thetas.shape[0], self.n_br))
        for i in range(thetas.shape[0]):
            p, _ = self.density(thetas[i])
            out[i] = self.G @ p
        return out


def map_estimate(model: LadderModel, maxiter: int = 3000) -> np.ndarray:
    def f(p):
        lp, g = model.logpost(p)
        return -lp, -g
    return minimize(f, np.zeros(model.dim), jac=True, method="L-BFGS-B",
                    options={"maxiter": maxiter, "maxcor": 30}).x


def prepare(model: LadderModel):
    psi = map_estimate(model)
    H = 0.5 * (model.gauss_newton(psi) + model.gauss_newton(psi).T)
    w, V = np.linalg.eigh(H)
    return psi, V @ np.diag(1.0 / np.sqrt(np.maximum(w, 1e-8)))


def sample(model: LadderModel, rng, sampler: str = "nuts", n_chains: int = 4,
           n_warmup: int = 500, n_samples: int = 500, max_depth: int = 8,
           target_accept: float = 0.8) -> dict:
    """Posterior draws of theta. Mirrors `act3.sample`, martingale parts removed."""
    t0 = time.time()
    psi_map, L = prepare(model)
    d = model.dim
    if sampler == "laplace":
        M = n_chains * n_samples
        psi = psi_map[None, :] + (L @ rng.standard_normal((d, M))).T
        return {"thetas": psi @ model.QV.T, "rhat_max": 1.0, "ess_min": float(M),
                "divergences": 0, "converged": True, "sampler": "laplace",
                "seconds": time.time() - t0}

    centre, Lcur = psi_map, L
    states = [0.5 * rng.standard_normal(d) for _ in range(n_chains)]
    n_final_warm = n_warmup
    if n_warmup >= 150:
        for frac in (0.3, 0.3):
            wn = int(frac * n_warmup)
            n_final_warm -= wn
            pooled, ends = [], []
            for c in range(n_chains):
                s = _nuts.NUTS(_nuts.Whitened(model, centre, Lcur), rng,
                               max_depth=max_depth, target_accept=target_accept)
                res = s.run(states[c], wn, 0, keep_warmup=True)
                pooled.append(res["warm_draws"][wn // 2:])
                ends.append(res["last"])
            arr = np.concatenate(pooled)
            n_pool = arr.shape[0]
            mu = arr.mean(axis=0)
            S = np.cov(arr, rowvar=False) if n_pool > d + 2 else np.eye(d)
            S = (n_pool / (n_pool + 5.0)) * S + (5.0 / (n_pool + 5.0)) * np.eye(d)
            A = np.linalg.cholesky(0.5 * (S + S.T) + 1e-9 * np.eye(d))
            centre = centre + Lcur @ mu
            Lcur = Lcur @ A
            states = [np.linalg.solve(A, e - mu) for e in ends]

    white = _nuts.Whitened(model, centre, Lcur)
    chains, divs = [], 0
    for c in range(n_chains):
        s = _nuts.NUTS(white, rng, max_depth=max_depth, target_accept=target_accept)
        res = s.run(states[c], n_final_warm, n_samples)
        chains.append(res["draws"])
        divs += res["divergences"]
    ch = np.array(chains)
    rhat = _nuts.split_rhat(ch) if n_chains > 1 and n_samples >= 4 else np.ones(d)
    es = _nuts.ess(ch)
    psi = white.psi(ch.reshape(-1, d))
    rhat_max, ess_min = float(np.nanmax(rhat)), float(np.nanmin(es))
    return {"thetas": psi @ model.QV.T, "rhat_max": rhat_max, "ess_min": ess_min,
            "divergences": int(divs),
            "converged": bool(rhat_max < 1.01 and ess_min >= 400 and divs == 0),
            "sampler": "nuts", "seconds": time.time() - t0}


def fit_ladder(edges, probs, half_spreads, rng, pad: float = PAD_DEGF,
               level: float = BAND_LEVEL, sampler: str = "nuts",
               n_chains: int = 4, n_samples: int = 500, n_warmup: int = 500,
               target_accept: float = 0.8) -> dict:
    """Fit one ladder; return the posterior mean and **band90** per bracket.

    The quantiles are returned exactly as the sampler produced them —
    asymmetric — per PROTOCOL §1B's band ruling. Nothing is symmetrised.
    """
    edges = np.asarray(edges, float)
    model = LadderModel(edges, probs, half_spreads,
                        s_lo=edges.min() - pad, s_hi=edges.max() + pad)
    res = sample(model, rng, sampler=sampler, n_chains=n_chains,
                 n_samples=n_samples, n_warmup=n_warmup, target_accept=target_accept)
    br = model.bracket_draws(res["thetas"])
    lo_q = (100.0 - level) / 2.0
    return {
        "fit_mean": br.mean(axis=0),
        "fit_lo": np.percentile(br, lo_q, axis=0),
        "fit_hi": np.percentile(br, 100.0 - lo_q, axis=0),
        "converged": res["converged"], "rhat_max": res["rhat_max"],
        "ess_min": res["ess_min"], "divergences": res["divergences"],
        "seconds": res["seconds"], "sampler": res["sampler"],
    }
