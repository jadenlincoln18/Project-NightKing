"""The PROTOCOL §9.2 fitter: T ~ SkewNormal(xi, omega, alpha) on a range ladder.

Three parameters against six prices, in place of §8.5's twenty-four spline
coefficients. Everything numeric below is fixed by PROTOCOL §9.3-§9.7 and was
committed (`3ecbc62`) before a single skew-normal fit was run.

Why the CDF and not a grid
--------------------------
A range bracket's probability is a CDF difference, so with a parametric family
it is **exact and analytic**, including the two unbounded wings (§9.4):

    p_1 = F(e_1)            lower wing, (-inf, e_1)   -- no truncation
    p_k = F(e_k) - F(e_k-1) interior
    p_K = 1 - F(e_K-1)      upper wing, [e_K-1, inf)  -- no truncation

The §8.5 spline cannot do this: it lives on a finite grid and truncates both
wings at a hand-chosen pad. `check_against_indicator_operator` cross-checks the
analytic probabilities against the existing indicator-integral construction
(`fitter.density.bracket_operator`), which is reused, not reimplemented.

Skew-normal CDF via Owen's T, F(x) = Phi(z) - 2 T(z, alpha), z = (x - xi)/omega.
`scipy.special.owens_t` is vectorised and broadcasts, which is what makes both
the 20,000-draw posterior push-through and the §9.6 quadrature reference cheap.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import ndtr, owens_t
from scipy.stats import chi2

# --- PROTOCOL §9.3 priors, on z = (xi, log omega, alpha) --------------------
PRIOR_XI_MEAN, PRIOR_XI_SD = 0.0, 10.0
PRIOR_LOGOM_MEAN, PRIOR_LOGOM_SD = np.log(3.0), 0.75
PRIOR_ALPHA_MEAN, PRIOR_ALPHA_SD = 0.0, 5.0

# --- PROTOCOL §9.5 noise scale ----------------------------------------------
SIGMA_Q = 0.0182     # §8.4a measured idiosyncratic per-bracket quote noise
H_BAR = 0.02         # §8.4b measured median tight half-spread (4c spread / 200)

# --- PROTOCOL §9.6 / §9.7 ----------------------------------------------------
N_PUSH = 20000       # posterior draws pushed through z -> p
GOF_LEVEL = 0.99     # chi2 quantile for the UNTRUSTWORTHY mark
GOF_MIN_K = 5        # fewer included brackets => untrustworthy by insufficiency
BAND_LO, BAND_HI = 5.0, 95.0
ALPHA_STARTS = (-6.0, 0.0, 6.0)   # defeat the flat ridge at alpha = 0


# --- the family --------------------------------------------------------------

def sn_cdf(x, xi, omega, alpha):
    """Skew-normal CDF. Broadcasts over parameters and x alike."""
    z = (np.asarray(x, float) - xi) / omega
    return ndtr(z) - 2.0 * owens_t(z, alpha)


def bracket_probs(z, edges):
    """PROTOCOL §9.4. z = (xi, log omega, alpha); returns p of length len(edges)+1.

    Vectorised: z may be (3,) or (N, 3); edges is (n_edges,). Returns (n_br,)
    or (N, n_br). Open wings come from the CDF limits F(-inf)=0, F(+inf)=1.
    """
    z = np.asarray(z, float)
    e = np.asarray(edges, float)
    if z.ndim == 1:
        F = sn_cdf(e, z[0], np.exp(z[1]), z[2])
        p = np.concatenate([[F[0]], np.diff(F), [1.0 - F[-1]]])
    else:
        F = sn_cdf(e[None, :], z[:, 0:1], np.exp(z[:, 1:2]), z[:, 2:3])
        p = np.concatenate([F[:, :1], np.diff(F, axis=1), 1.0 - F[:, -1:]], axis=1)
    return np.clip(p, 1e-12, 1.0)


def cumulative_probs(z, thresholds):
    """PROTOCOL §9.4 cumulative ladders: p_k = 1 - F(threshold_k).

    Supported because the protocol requires it; §8.2 measured **zero** cumulative
    events on this universe, so nothing in Gate 0 exercises this path.
    """
    z = np.asarray(z, float)
    return 1.0 - sn_cdf(np.asarray(thresholds, float), z[0], np.exp(z[1]), z[2])


# --- PROTOCOL §9.5 noise scale ----------------------------------------------

def noise_scale(bid, ask, sigma_q=SIGMA_Q, h_bar=H_BAR):
    """s_k = sigma_q * max(1, h_k / h_bar), h_k the quoted half-spread.

    Both constants are §8.4 measurements. The floor is the point: sigma_q came
    from cross-sectional ladder incoherence, not from the touch, and a 1c book
    does not repeal it.
    """
    h = (np.asarray(ask, float) - np.asarray(bid, float)) / 200.0
    return sigma_q * np.maximum(1.0, h / h_bar)


# --- posterior ---------------------------------------------------------------

def log_prior(z):
    z = np.asarray(z, float)
    return -0.5 * (((z[0] - PRIOR_XI_MEAN) / PRIOR_XI_SD) ** 2
                   + ((z[1] - PRIOR_LOGOM_MEAN) / PRIOR_LOGOM_SD) ** 2
                   + ((z[2] - PRIOR_ALPHA_MEAN) / PRIOR_ALPHA_SD) ** 2)


def log_prior_vec(Z):
    Z = np.asarray(Z, float)
    return -0.5 * (((Z[:, 0] - PRIOR_XI_MEAN) / PRIOR_XI_SD) ** 2
                   + ((Z[:, 1] - PRIOR_LOGOM_MEAN) / PRIOR_LOGOM_SD) ** 2
                   + ((Z[:, 2] - PRIOR_ALPHA_MEAN) / PRIOR_ALPHA_SD) ** 2)


class LadderPosterior:
    """Posterior over (xi, omega, alpha) given one ladder's two-sided quotes.

    `include` is the mask of brackets with BOTH sides quoted. One-sided brackets
    are excluded and never imputed (PROTOCOL §9.5).
    """

    def __init__(self, edges, mid, s, include=None):
        self.edges = np.asarray(edges, float)
        self.mid = np.asarray(mid, float)
        self.s = np.asarray(s, float)
        self.n_br = len(self.mid)
        self.include = (np.ones(self.n_br, bool) if include is None
                        else np.asarray(include, bool))
        self.K = int(self.include.sum())

    def log_post(self, z):
        if not np.all(np.isfinite(z)) or abs(z[1]) > 6.0 or abs(z[2]) > 60.0:
            return -np.inf
        p = bracket_probs(z, self.edges)
        r = (self.mid[self.include] - p[self.include]) / self.s[self.include]
        return float(-0.5 * np.dot(r, r) + log_prior(z))

    def log_post_vec(self, Z):
        Z = np.asarray(Z, float)
        P = bracket_probs(Z, self.edges)
        R = (self.mid[None, self.include] - P[:, self.include]) / self.s[None, self.include]
        return -0.5 * np.sum(R * R, axis=1) + log_prior_vec(Z)

    # --- MAP, multi-start (PROTOCOL §9.6) -----------------------------------
    def map_estimate(self):
        best, best_lp = None, -np.inf
        xi0 = float(np.clip(self.edges.mean(), -20, 20))
        for a0 in ALPHA_STARTS:
            for lo0 in (np.log(2.0), np.log(4.0)):
                r = minimize(lambda z: -self.log_post(z), np.array([xi0, lo0, a0]),
                             method="Nelder-Mead",
                             options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 4000})
                r2 = minimize(lambda z: -self.log_post(z), r.x, method="Nelder-Mead",
                              options={"xatol": 1e-9, "fatol": 1e-11, "maxiter": 4000})
                lp = -float(r2.fun)
                if np.isfinite(lp) and lp > best_lp:
                    best, best_lp = r2.x, lp
        return np.asarray(best, float), best_lp

    def hessian(self, z, h=(1e-3, 1e-3, 1e-3)):
        """Negative-log-posterior Hessian by central differences. 3x3."""
        z = np.asarray(z, float)
        H = np.zeros((3, 3))
        f = lambda q: -self.log_post(q)
        f0 = f(z)
        for i in range(3):
            ei = np.zeros(3); ei[i] = h[i]
            H[i, i] = (f(z + ei) - 2 * f0 + f(z - ei)) / h[i] ** 2
            for j in range(i + 1, 3):
                ej = np.zeros(3); ej[j] = h[j]
                H[i, j] = H[j, i] = (f(z + ei + ej) - f(z + ei - ej)
                                     - f(z - ei + ej) + f(z - ei - ej)) / (4 * h[i] * h[j])
        return H

    # --- Laplace -------------------------------------------------------------
    def laplace(self, rng, n_push=N_PUSH):
        z_map, lp = self.map_estimate()
        H = 0.5 * (self.hessian(z_map) + self.hessian(z_map).T)
        w, V = np.linalg.eigh(H)
        w = np.maximum(w, 1e-6)
        L = V @ np.diag(1.0 / np.sqrt(w))        # Sigma = L L'
        Z = z_map[None, :] + (L @ rng.standard_normal((3, n_push))).T
        return self._summarise(Z, z_map, extra={"cov_floor_hits": int((w <= 1e-6).sum())})

    # --- quadrature reference (PROTOCOL §9.6) --------------------------------
    def quadrature(self, n_axis=81, n_sd=24.0, max_sd=192.0, boundary_tol=1e-4,
                   stretch=3.0):
        """Dense 3-D reference posterior (PROTOCOL §9.6).

        The §9.6 grid is +/- 6 Laplace sd with 61 nodes per axis **and** a stated
        adequacy criterion: boundary mass < 1e-4. That criterion exists to catch
        a reference grid that does not contain the posterior, and on the
        skew-normal it fires -- the posterior in `alpha` is far heavier-tailed
        than its Laplace approximation. The response the criterion demands is to
        widen the reference until it is met, which is done here by doubling the
        half-width. Widening the *reference* makes the §9.6 comparison harder for
        Laplace to pass, never easier, and touches no bar. The achieved extent
        and boundary mass are reported.
        """
        z_map, lp = self.map_estimate()
        H = 0.5 * (self.hessian(z_map) + self.hessian(z_map).T)
        w, V = np.linalg.eigh(H)
        sd = 1.0 / np.sqrt(np.maximum(w, 1e-6))
        u = np.linspace(-1.0, 1.0, n_axis)
        ext = n_sd
        while True:
            # sinh-stretched nodes: ~0.2 Laplace sd near the mode, long reach in
            # the tails. Non-uniform, so each node carries its trapezoid volume.
            t = ext * np.sinh(stretch * u) / np.sinh(stretch)
            dt = np.gradient(t)
            g = np.stack(np.meshgrid(t, t, t, indexing="ij"), -1).reshape(-1, 3)
            dv = np.einsum("i,j,k->ijk", dt, dt, dt).reshape(-1)
            Z = z_map[None, :] + g @ (V * sd[None, :]).T
            lpv = self.log_post_vec(Z)
            wq = np.exp(lpv - lpv.max()) * dv
            wq /= wq.sum()
            edge = np.abs(g).max(axis=1) >= t[-1] - 1e-9
            bmass = float(wq[edge].sum())
            out = self._summarise(Z, z_map, weights=wq,
                                  extra={"boundary_mass": bmass, "grid_sd_extent": ext,
                                         "n_axis": n_axis})
            if bmass < boundary_tol or ext >= max_sd:
                return out
            ext *= 2.0

    # --- MCMC, the independent check on the quadrature reference ------------
    def mcmc(self, rng, n_chains=4, n_draws=20000, n_warm=5000, thin=1):
        """Adaptive random-walk Metropolis on z. Used to validate quadrature.

        Three parameters, so this is cheap and needs no gradient. The proposal
        is seeded from the Laplace covariance and then adapted on the pooled
        warmup draws; split-Rhat and ESS are returned with the summary.
        """
        z_map, _ = self.map_estimate()
        H = 0.5 * (self.hessian(z_map) + self.hessian(z_map).T)
        w, V = np.linalg.eigh(H)
        L = V @ np.diag(1.0 / np.sqrt(np.maximum(w, 1e-6)))
        chains = []
        for c in range(n_chains):
            z = z_map + 0.3 * (L @ rng.standard_normal(3))
            lp = self.log_post(z)
            scale, Lc, warm, draws, acc = 0.8, L, [], [], 0
            for i in range(n_warm + n_draws):
                prop = z + scale * (Lc @ rng.standard_normal(3))
                lpp = self.log_post(prop)
                if np.log(rng.random()) < lpp - lp:
                    z, lp, acc = prop, lpp, acc + 1
                if i < n_warm:
                    if i > n_warm // 4:
                        warm.append(z.copy())
                    if (i + 1) % 500 == 0:
                        scale *= float(np.exp((acc / 500.0 - 0.3) * 1.5))
                        acc = 0
                        if i + 1 == n_warm // 2 and len(warm) > 100:
                            S = np.cov(np.array(warm).T) + 1e-9 * np.eye(3)
                            try:
                                Lc, scale = np.linalg.cholesky(S), 0.9
                            except np.linalg.LinAlgError:
                                pass
                else:
                    draws.append(z.copy())
            chains.append(np.array(draws[::thin]))
        ch = np.array(chains)
        Z = ch.reshape(-1, 3)
        out = self._summarise(Z, z_map, extra={
            "mcmc_rhat_max": float(np.max([_split_rhat(ch[:, :, d]) for d in range(3)])),
            "mcmc_ess_min": float(np.min([_ess(ch[:, :, d]) for d in range(3)])),
            "mcmc_draws": int(Z.shape[0])})
        return out

    # --- shared summary ------------------------------------------------------
    def _summarise(self, Z, z_map, weights=None, extra=None):
        P = bracket_probs(Z, self.edges)
        if weights is None:
            mean = P.mean(axis=0)
            lo = np.percentile(P, BAND_LO, axis=0)
            hi = np.percentile(P, BAND_HI, axis=0)
        else:
            mean = weights @ P
            lo = np.array([_wquantile(P[:, k], weights, BAND_LO / 100.0)
                           for k in range(P.shape[1])])
            hi = np.array([_wquantile(P[:, k], weights, BAND_HI / 100.0)
                           for k in range(P.shape[1])])
        out = {"fit_mean": mean, "fit_lo": lo, "fit_hi": hi,
               "z_map": z_map, "K": self.K}
        out.update(self.goodness_of_fit(mean))
        if extra:
            out.update(extra)
        return out

    # --- PROTOCOL §9.7 -------------------------------------------------------
    def goodness_of_fit(self, p_hat):
        r = (self.mid[self.include] - np.asarray(p_hat)[self.include]) / self.s[self.include]
        x2 = float(np.dot(r, r))
        dof = self.K - 3
        if self.K < GOF_MIN_K:
            return {"gof_x2": x2, "gof_dof": dof, "gof_threshold": float("nan"),
                    "untrustworthy": True, "untrustworthy_reason": "insufficiency"}
        thr = float(chi2.ppf(GOF_LEVEL, dof))
        return {"gof_x2": x2, "gof_dof": int(dof), "gof_threshold": thr,
                "untrustworthy": bool(x2 > thr),
                "untrustworthy_reason": "misfit" if x2 > thr else ""}


def _split_rhat(x):
    """x: (chains, draws) for one parameter."""
    c, n = x.shape
    h = n // 2
    s = np.concatenate([x[:, :h], x[:, h:2 * h]], axis=0)
    m, v = s.mean(axis=1), s.var(axis=1, ddof=1)
    W = v.mean()
    B = h * m.var(ddof=1)
    if W <= 0:
        return 1.0
    return float(np.sqrt(((h - 1) / h * W + B / h) / W))


def _ess(x):
    c, n = x.shape
    v = x.var(axis=1, ddof=1).mean()
    if v <= 0:
        return float(c * n)
    rho, s = 1.0, 0.0
    dev = x - x.mean(axis=1, keepdims=True)
    for lag in range(1, min(n // 2, 400)):
        r = float(np.mean(dev[:, :-lag] * dev[:, lag:]) / v)
        if r < 0.02:
            break
        s += r
    return float(c * n / (1.0 + 2.0 * s))


def _wquantile(v, w, q):
    o = np.argsort(v)
    c = np.cumsum(w[o])
    return float(np.interp(q, c / c[-1], v[o]))


# --- public entry point ------------------------------------------------------

def fit_ladder(edges, bid, ask, rng, method="laplace", include=None, **kw):
    """Fit one ladder from its two-sided quotes. PROTOCOL §9.2-§9.7.

    Returns per-bracket posterior mean and the asymmetric 5%/95% quantiles
    exactly as drawn (§9.10), plus the goodness-of-fit verdict.
    """
    bid, ask = np.asarray(bid, float), np.asarray(ask, float)
    mid = (bid + ask) / 200.0
    s = noise_scale(bid, ask)
    post = LadderPosterior(edges, mid, s, include=include)
    if method == "laplace":
        return post.laplace(rng, **kw)
    if method == "quadrature":
        return post.quadrature(**kw)
    if method == "mcmc":
        return post.mcmc(rng, **kw)
    raise ValueError("unknown method %r" % method)


# --- cross-check against the reused indicator-integral operator (§9.4) -------

def check_against_indicator_operator(z, edges, n_grid=200001, pad=60.0):
    """|analytic p - indicator-integral p| , using fitter.density.bracket_operator."""
    from fitter.density import bracket_operator
    e = np.asarray(edges, float)
    s = np.linspace(e.min() - pad, e.max() + pad, n_grid)
    G = bracket_operator(s, e)
    xi, om, al = z[0], np.exp(z[1]), z[2]
    F = sn_cdf(s, xi, om, al)
    cell = np.concatenate([[s[0]], 0.5 * (s[1:] + s[:-1]), [s[-1]]])
    dens = np.diff(sn_cdf(cell, xi, om, al))     # exact mass of each Voronoi cell
    p_grid = G @ dens
    p_grid = p_grid / p_grid.sum()
    return float(np.max(np.abs(p_grid - bracket_probs(z, e)))), p_grid
