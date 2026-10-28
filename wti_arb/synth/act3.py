"""Act III: exp-spline density, roughness prior with a hyperprior, integrate-forward
likelihood, optional martingale constraint, NUTS. Hand-rolled in numpy with analytic
gradients (no JAX/Stan dependency; Python 3.9).

Model
  grid      s_k uniform in x = log(s/F0) on [-c v, +c v], v = ATM sigma*sqrt(T), c = extent_sd
  basis     cubic B-splines in x, m coefficients, uniform clamped knots
  density   p_k = w_k exp(phi_k) / Z,  phi = B theta       (positive, normalised by construction)
  gauge     B-splines sum to one, so theta + const is the same density: theta = Q eta with
            Q an orthonormal basis of the sum-zero subspace
  prior     second-difference (P-spline) penalty D2 theta ~ N(0, tau^2 I). In the eigenbasis
            V of Q'D2'D2 Q (eigenvalues e_j) the coordinates u_j are independent a priori,
            u_j ~ N(0, tau^2/e_j). The one e_j = 0 direction (the exponential tilt) gets
            N(0, 30^2). tau ~ half-Cauchy(1), sampled as log tau.
  tau       integrated out exactly (1-d quadrature over log tau on a fixed grid): the
            marginal prior on the penalised coordinates depends only on S = sum e_j u_j^2,
            so the sampler sees m-1 coordinates and no funnel. Both the non-centred and the
            centred parameterisation with tau sampled were tried first: the likelihood pins
            some directions to 1e-4 and leaves others to the prior (condition number 1e8),
            and either choice left NUTS at ESS ~ 20. tau draws are recovered per sample from
            p(tau | u) for reporting.
  metric    dense: the Gauss-Newton Hessian at the MAP; NUTS runs in whitened coordinates
            with a diagonal correction adapted during warmup.
  lik       C_hat_i = D sum_k p_k (s_k - K_i)^+ (puts likewise); Gaussian, sd = half-spread
  Stage 14  optional N(F0; mean_theta, se_F0^2); off for the diagnostic run
  sampler   NUTS (Hoffman & Gelman 2014, Alg. 6), dual-averaging step size, split-Rhat,
            ESS, divergence count
  fallback  "laplace": MAP + Gaussian from the Gauss-Newton Hessian, for CI (and the
            "unconverged" injection uses NUTS with a deliberately short warmup)

Why half-Cauchy on tau rather than the writeup's Gamma on lambda = 1/tau^2: it is the
standard weakly-informative scale prior, heavy-tailed enough to let the data choose very
rough or very smooth, and its scale (1) is the order of the second difference a lognormal
body produces at this knot spacing (~0.4).
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import minimize

from . import black76

TILT_SD = 30.0
TAU_SCALE = 1.0
# hyperprior on tau. "lognormal": log tau ~ N(log TAU_LN_MED, TAU_LN_SD^2). "halfcauchy": tau ~ C+(0, TAU_SCALE).
# The half-Cauchy was the first choice; its Cauchy-like marginal on the prior-dominated wing
# directions left NUTS at ESS ~ 40 (see FINDINGS_SYNTHETIC.md, sampler notes). Both are kept.
TAU_PRIOR = "lognormal"
TAU_LN_MED = 0.5
TAU_LN_SD = 1.0


# --------------------------------------------------------------------------
# basis
# --------------------------------------------------------------------------

def bspline_basis(x: np.ndarray, m: int, x_lo: float, x_hi: float, degree: int = 3) -> np.ndarray:
    n_inner = m - degree - 1
    inner = np.linspace(x_lo, x_hi, n_inner + 2)[1:-1]
    t = np.concatenate([[x_lo] * (degree + 1), inner, [x_hi] * (degree + 1)])
    return BSpline.design_matrix(np.clip(x, x_lo, x_hi), t, degree).toarray()


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

class Model:
    def __init__(self, K: np.ndarray, right: np.ndarray, mid: np.ndarray, hs: np.ndarray, F0: float, D: float, T: float,
                 atm_sigma: float, se_F0: float = 0.05, m: int = 24, n_grid: int = 400, extent_sd: float = 7.0,
                 martingale: bool = True, hs_floor: float = 0.0):
        self.K = np.asarray(K, float)
        self.is_call = np.asarray(right) == "C"
        self.mid = np.asarray(mid, float)
        # hs_floor: a quote cannot locate a price more precisely than the tick; 0 = writeup as
        # specified (tolerance = half-spread exactly)
        self.hs = np.maximum(np.asarray(hs, float), hs_floor)
        self.F0, self.D, self.T = float(F0), float(D), float(T)
        self.se_F0 = float(max(se_F0, 0.005))
        self.martingale = martingale
        v = max(atm_sigma, 0.05) * np.sqrt(T)
        self.v = v
        self.extent_sd = extent_sd
        self.x_lo, self.x_hi = -extent_sd * v, extent_sd * v
        self.x = np.linspace(self.x_lo, self.x_hi, n_grid)
        self.s = F0 * np.exp(self.x)
        h = np.diff(self.s)
        w = np.zeros(n_grid)
        w[:-1] += 0.5 * h
        w[1:] += 0.5 * h
        self.w = w
        self.logw = np.log(w)
        self.m = m
        self.B = bspline_basis(self.x, m, self.x_lo, self.x_hi)
        pay_c = np.maximum(self.s[None, :] - self.K[:, None], 0.0)
        pay_p = np.maximum(self.K[:, None] - self.s[None, :], 0.0)
        self.G = D * np.where(self.is_call[:, None], pay_c, pay_p)
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
        self.dim = m - 1  # u coordinates; tau is integrated out analytically (1-d quadrature)
        self.nll_scale = 1.0 / np.maximum(self.hs, 1e-4)
        # tau quadrature grid for the marginal prior on the penalised coordinates:
        #   p(u_pen) = int prod_j N(u_j; 0, tau^2/e_j) p(tau) dtau, p(tau) half-Cauchy(TAU_SCALE)
        self.logtau_grid = np.linspace(-7.0, 5.0, 361)
        tau_g = np.exp(self.logtau_grid)
        self.inv_tau2 = 1.0 / tau_g ** 2
        if TAU_PRIOR == "halfcauchy":
            log_p_tau = -np.log1p((tau_g / TAU_SCALE) ** 2) + self.logtau_grid  # incl. Jacobian d tau / d log tau
        else:
            log_p_tau = -0.5 * ((self.logtau_grid - np.log(TAU_LN_MED)) / TAU_LN_SD) ** 2
        self.prior_const = (-self.q_pen * self.logtau_grid + log_p_tau
                            + 0.5 * float(np.sum(np.log(self.eig[self.penalised]))))

    # --- parameter maps -------------------------------------------------------
    def theta_from(self, psi: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        """theta, u, and the posterior-mean tau given u (for reporting)."""
        u = np.asarray(psi, float)
        S = float(np.sum(self.eig[self.penalised] * u[self.penalised] ** 2))
        _, _, wq = self._marginal_prior(S)
        tau_mean = float(np.exp(self.logtau_grid) @ wq)
        return self.QV @ u, u, tau_mean

    def tau_draw(self, psi: np.ndarray, rng: np.random.Generator) -> float:
        u = np.asarray(psi, float)
        S = float(np.sum(self.eig[self.penalised] * u[self.penalised] ** 2))
        _, _, wq = self._marginal_prior(S)
        k = rng.choice(len(wq), p=wq / wq.sum())
        return float(np.exp(self.logtau_grid[k]))

    def _marginal_prior(self, S: float):
        a = self.prior_const - 0.5 * S * self.inv_tau2
        mx = a.max()
        ex = np.exp(a - mx)
        Z = ex.sum()
        wq = ex / Z
        lse = mx + np.log(Z)
        dlse_dS = -0.5 * float(wq @ self.inv_tau2)
        return lse, dlse_dS, wq

    def density(self, theta: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        lg = self.B @ theta + self.logw
        lg -= lg.max()
        p = np.exp(lg)
        p /= p.sum()
        return p, p / self.w

    def mean(self, p: np.ndarray) -> float:
        return float(self.s @ p)

    # --- log posterior ---------------------------------------------------------
    def _lik_terms(self, theta):
        p, _ = self.density(theta)
        Chat = self.G @ p
        r = (self.mid - Chat) * self.nll_scale
        bbar = p @ self.B
        J = self.G @ (p[:, None] * self.B) - np.outer(Chat, bbar)  # dChat/dtheta, n x m
        mean = float(self.s @ p)
        dmean = (self.s * p) @ self.B - mean * bbar
        return p, r, J, mean, dmean

    def logpost(self, psi: np.ndarray, with_grad: bool = True):
        u = np.asarray(psi, float)
        if not np.all(np.isfinite(u)) or np.max(np.abs(u)) > 1e4:
            return -np.inf if not with_grad else (-np.inf, np.zeros(self.dim))
        theta = self.QV @ u
        if with_grad:
            p, r, J, mean, dmean = self._lik_terms(theta)
            g_theta = J.T @ (r * self.nll_scale)
        else:  # value only: no Jacobian (the slice sampler lives here)
            p, _ = self.density(theta)
            r = (self.mid - self.G @ p) * self.nll_scale
            mean = float(self.s @ p)
        lp = -0.5 * float(r @ r)
        if self.martingale:
            zf = (mean - self.F0) / self.se_F0
            lp += -0.5 * zf * zf
            if with_grad:
                g_theta = g_theta - zf / self.se_F0 * dmean
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

    def gauss_newton(self, psi: np.ndarray) -> np.ndarray:
        """Positive-definite approximation to the negative Hessian of logpost at psi."""
        u = np.asarray(psi, float)
        theta = self.QV @ u
        p, r, J, mean, dmean = self._lik_terms(theta)
        Ju = J @ self.QV
        H = (Ju * self.nll_scale[:, None] ** 2).T @ Ju
        if self.martingale:
            gm = self.QV.T @ dmean
            H += np.outer(gm, gm) / self.se_F0 ** 2
        pen = self.penalised
        S = float(np.sum(self.eig[pen] * u[pen] ** 2))
        _, dlse_dS, _ = self._marginal_prior(S)
        prior = np.full(self.dim, 1.0 / TILT_SD ** 2)
        prior[pen] = -2.0 * dlse_dS * self.eig[pen]
        return H + np.diag(prior)

    def chi2(self, theta: np.ndarray) -> Tuple[float, np.ndarray]:
        p, _ = self.density(theta)
        r = (self.mid - self.G @ p) * self.nll_scale
        return float(r @ r), r

    # --- summaries -------------------------------------------------------------
    def summarise(self, thetas: np.ndarray, edges: np.ndarray, s_eval: Optional[np.ndarray] = None) -> Dict[str, object]:
        M = thetas.shape[0]
        n_e = len(edges)
        means = np.empty(M)
        bracket = np.empty((M, n_e + 1))
        dens_eval = np.empty((M, len(s_eval))) if s_eval is not None else None
        chi2 = np.empty(M)
        resid = np.empty((M, len(self.K)))
        edge_mass = np.empty((M, 2))
        s_edges = np.concatenate([[self.s[0]], 0.5 * (self.s[1:] + self.s[:-1]), [self.s[-1]]])
        n_edge_cells = max(int(0.025 * len(self.s)), 2)
        for i in range(M):
            p, f = self.density(thetas[i])
            means[i] = self.s @ p
            cum = np.concatenate([[0.0], np.cumsum(p)])
            c = np.interp(edges, s_edges, cum, left=0.0, right=1.0)
            bracket[i] = np.concatenate([[c[0]], np.diff(c), [1.0 - c[-1]]])
            if dens_eval is not None:
                dens_eval[i] = np.interp(s_eval, self.s, f, left=0.0, right=0.0)
            r = (self.mid - self.G @ p) * self.nll_scale
            chi2[i] = r @ r
            resid[i] = r
            edge_mass[i] = [p[:n_edge_cells].sum(), p[-n_edge_cells:].sum()]
        out = {"mean_F": means, "bracket": bracket, "chi2": chi2, "resid": resid, "edge_mass": edge_mass}
        if dens_eval is not None:
            out["density_at"] = dens_eval
        return out


class Whitened:
    """psi = centre + L xi; exposes logpost(xi) for the sampler."""

    def __init__(self, model: Model, centre: np.ndarray, L: np.ndarray):
        self.model = model
        self.centre = centre
        self.L = L
        self.dim = model.dim

    def logpost(self, xi: np.ndarray, with_grad: bool = True):
        psi = self.centre + self.L @ xi
        if not with_grad:
            return self.model.logpost(psi, False)
        lp, g = self.model.logpost(psi)
        return lp, self.L.T @ g

    def psi(self, xi: np.ndarray) -> np.ndarray:
        return self.centre + xi @ self.L.T


# --------------------------------------------------------------------------
# NUTS
# --------------------------------------------------------------------------

class NUTS:
    def __init__(self, model, rng: np.random.Generator, max_depth: int = 8, target_accept: float = 0.8,
                 final_frac: float = 0.25):
        self.m = model
        self.rng = rng
        self.max_depth = max_depth
        self.delta = target_accept
        self.final_frac = final_frac  # share of warmup after the last metric update (Stan: 10%; we need more)
        self.divergences = 0
        self.depths: List[int] = []

    def _leapfrog(self, q, p, grad, eps, inv_mass):
        p = p + 0.5 * eps * grad
        q = q + eps * inv_mass * p
        lp, grad = self.m.logpost(q)
        if not np.isfinite(lp):
            lp = -np.inf
            grad = np.zeros_like(grad)
        p = p + 0.5 * eps * grad
        return q, p, lp, grad

    def _find_eps(self, q, inv_mass):
        eps = 1.0
        lp, grad = self.m.logpost(q)
        p = self.rng.standard_normal(q.size) / np.sqrt(inv_mass)
        H0 = -lp + 0.5 * np.sum(inv_mass * p * p)
        q1, p1, lp1, _ = self._leapfrog(q, p, grad, eps, inv_mass)
        H1 = -lp1 + 0.5 * np.sum(inv_mass * p1 * p1)
        a = 1.0 if (np.isfinite(H1) and (H0 - H1) > np.log(0.5)) else -1.0
        for _ in range(60):
            eps *= 2.0 ** a
            q1, p1, lp1, _ = self._leapfrog(q, p, grad, eps, inv_mass)
            H1 = -lp1 + 0.5 * np.sum(inv_mass * p1 * p1)
            if not np.isfinite(H1):
                if a > 0:
                    eps /= 2.0
                    break
                continue
            if a * (H0 - H1) < a * np.log(0.5):
                break
        return float(np.clip(eps, 1e-8, 10.0))

    def _build(self, q, p, grad, logu, v, j, eps, H0, inv_mass):
        if j == 0:
            q1, p1, lp1, g1 = self._leapfrog(q, p, grad, v * eps, inv_mass)
            H1 = -lp1 + 0.5 * np.sum(inv_mass * p1 * p1)
            if not np.isfinite(H1):
                H1 = np.inf
            n1 = 1 if logu <= -H1 else 0
            s1 = 1 if logu < 1000.0 - H1 else 0
            if s1 == 0:
                self.divergences += 1
            alpha = float(min(1.0, np.exp(min(H0 - H1, 0.0)))) if np.isfinite(H1) else 0.0
            return q1, p1, g1, q1, p1, g1, q1, lp1, n1, s1, alpha, 1
        qm, pm, gm, qp, pp, gp, q1, lp1, n1, s1, a1, na1 = self._build(q, p, grad, logu, v, j - 1, eps, H0, inv_mass)
        if s1 == 1:
            if v == -1:
                qm, pm, gm, _, _, _, q2, lp2, n2, s2, a2, na2 = self._build(qm, pm, gm, logu, v, j - 1, eps, H0, inv_mass)
            else:
                _, _, _, qp, pp, gp, q2, lp2, n2, s2, a2, na2 = self._build(qp, pp, gp, logu, v, j - 1, eps, H0, inv_mass)
            if n1 + n2 > 0 and self.rng.uniform() < n2 / float(n1 + n2):
                q1, lp1 = q2, lp2
            a1 += a2
            na1 += na2
            dq = qp - qm
            s1 = s2 * (1 if (dq @ (inv_mass * pm)) >= 0 else 0) * (1 if (dq @ (inv_mass * pp)) >= 0 else 0)
            n1 += n2
        return qm, pm, gm, qp, pp, gp, q1, lp1, n1, s1, a1, na1

    def run(self, q0: np.ndarray, n_warmup: int, n_samples: int, inv_mass: Optional[np.ndarray] = None,
            adapt_mass: bool = True, keep_warmup: bool = False) -> Dict[str, object]:
        q = np.array(q0, float)
        d = q.size
        warm_draws = np.empty((n_warmup, d)) if keep_warmup else None
        inv_mass = np.ones(d) if inv_mass is None else np.array(inv_mass, float)
        eps = min(self._find_eps(q, inv_mass), 0.5)
        mu = np.log(10.0 * eps)
        self.eps_trace: List[float] = []
        Hbar, log_eps_bar, gamma, t0, kappa = 0.0, 0.0, 0.05, 10.0, 0.75
        lp, grad = self.m.logpost(q)
        draws = np.empty((n_samples, d))
        lps = np.empty(n_samples)
        win_end: List[int] = []
        if adapt_mass and n_warmup >= 100:
            a = int(0.15 * n_warmup)
            b = n_warmup - int(self.final_frac * n_warmup)
            size = 25
            cur = a
            while cur + size < b:
                cur += size
                win_end.append(cur)
                size *= 2
            win_end.append(b)
        win_buf: List[np.ndarray] = []
        self.depths = []
        accept_stats: List[float] = []
        da_it = 0  # dual-averaging iteration counter; restarts with every metric window
        for it in range(n_warmup + n_samples):
            p0 = self.rng.standard_normal(d) / np.sqrt(inv_mass)
            H0 = -lp + 0.5 * np.sum(inv_mass * p0 * p0)
            logu = -H0 + np.log(self.rng.uniform())
            qm = qp = q
            pm = pp = p0
            gm = gp = grad
            j, n, s = 0, 1, 1
            q_new, lp_new = q, lp
            alpha, n_alpha = 0.0, 1
            while s == 1 and j < self.max_depth:
                v = 1 if self.rng.uniform() < 0.5 else -1
                if v == -1:
                    qm, pm, gm, _, _, _, q1, lp1, n1, s1, alpha, n_alpha = self._build(qm, pm, gm, logu, v, j, eps, H0, inv_mass)
                else:
                    _, _, _, qp, pp, gp, q1, lp1, n1, s1, alpha, n_alpha = self._build(qp, pp, gp, logu, v, j, eps, H0, inv_mass)
                if s1 == 1 and self.rng.uniform() < min(1.0, n1 / float(n)):
                    q_new, lp_new = q1, lp1
                n += n1
                dq = qp - qm
                s = s1 * (1 if (dq @ (inv_mass * pm)) >= 0 else 0) * (1 if (dq @ (inv_mass * pp)) >= 0 else 0)
                j += 1
            self.depths.append(j)
            if q_new is not q:
                q, lp = q_new, lp_new
                _, grad = self.m.logpost(q)
            accept_stat = alpha / max(n_alpha, 1)
            if it < n_warmup:
                if warm_draws is not None:
                    warm_draws[it] = q
                da_it += 1
                m_it = da_it
                Hbar = (1 - 1.0 / (m_it + t0)) * Hbar + (self.delta - accept_stat) / (m_it + t0)
                log_eps = mu - np.sqrt(m_it) / gamma * Hbar
                eta = m_it ** (-kappa)
                log_eps_bar = eta * log_eps + (1 - eta) * log_eps_bar
                eps = float(np.exp(log_eps))
                self.eps_trace.append(eps)
                if win_end:
                    win_buf.append(q.copy())
                    if it + 1 == win_end[0]:
                        arr = np.array(win_buf)
                        nw = len(arr)
                        var = arr.var(axis=0, ddof=1) if nw > 5 else np.ones(d)
                        # regularise toward the whitened scale (1), not toward 1e-3
                        inv_mass = np.maximum((nw / (nw + 5.0)) * var + (5.0 / (nw + 5.0)) * 1.0, 1e-6)
                        win_buf = []
                        win_end.pop(0)
                        eps = min(self._find_eps(q, inv_mass), 0.5)
                        mu = np.log(10.0 * eps)
                        Hbar, log_eps_bar, da_it = 0.0, 0.0, 0
                if it + 1 == n_warmup:
                    eps = float(np.exp(log_eps_bar))
                    self.divergences = 0
            else:
                draws[it - n_warmup] = q
                lps[it - n_warmup] = lp
                accept_stats.append(accept_stat)
        return {"draws": draws, "logpost": lps, "eps": eps, "inv_mass": inv_mass, "divergences": self.divergences,
                "mean_depth": float(np.mean(self.depths[n_warmup:])) if n_samples else 0.0,
                "accept": float(np.mean(accept_stats)) if accept_stats else 0.0, "warm_draws": warm_draws,
                "last": q}


# --------------------------------------------------------------------------
# coordinate slice sampler (whitened coordinates)
# --------------------------------------------------------------------------

class SliceSampler:
    """Stepping-out / shrinkage slice sampling (Neal 2003), one whitened coordinate at a
    time in random order, widths adapted during warmup from the running standard deviation.
    No step size, no gradient, and no trouble with the wall-plus-plateau geometry that the
    prior-dominated wing coefficients produce (see FINDINGS_SYNTHETIC.md, sampler notes)."""

    def __init__(self, model, rng: np.random.Generator, max_steps: int = 20):
        self.m = model
        self.rng = rng
        self.max_steps = max_steps
        self.n_evals = 0

    def _lp(self, q):
        self.n_evals += 1
        v = self.m.logpost(q, False)
        return v if np.isfinite(v) else -np.inf

    def _update(self, q, lp, k, width):
        logy = lp + np.log(self.rng.uniform())
        x0 = q[k]
        u = self.rng.uniform()
        L = x0 - width * u
        R = L + width
        j = int(self.rng.integers(0, self.max_steps + 1))
        kk = self.max_steps - j
        qL = q.copy()
        qR = q.copy()
        while j > 0:
            qL[k] = L
            if self._lp(qL) <= logy:
                break
            L -= width
            j -= 1
        while kk > 0:
            qR[k] = R
            if self._lp(qR) <= logy:
                break
            R += width
            kk -= 1
        qn = q.copy()
        for _ in range(200):
            x1 = L + self.rng.uniform() * (R - L)
            qn[k] = x1
            lp1 = self._lp(qn)
            if lp1 > logy:
                return qn, lp1
            if x1 < x0:
                L = x1
            else:
                R = x1
        return q, lp

    def run(self, q0: np.ndarray, n_warmup: int, n_samples: int, thin: int = 1) -> Dict[str, object]:
        q = np.array(q0, float)
        d = q.size
        lp = self._lp(q)
        widths = np.full(d, 2.0)
        draws = np.empty((n_samples, d))
        lps = np.empty(n_samples)
        buf: List[np.ndarray] = []
        kept = 0
        for it in range(n_warmup + n_samples * thin):
            for k in self.rng.permutation(d):
                q, lp = self._update(q, lp, k, widths[k])
            if it < n_warmup:
                buf.append(q.copy())
                if len(buf) >= 50 and (it + 1) % 50 == 0:
                    arr = np.array(buf[-200:])
                    widths = np.maximum(2.5 * arr.std(axis=0), 1e-3)
            elif (it - n_warmup) % thin == 0:
                draws[kept] = q
                lps[kept] = lp
                kept += 1
        return {"draws": draws, "logpost": lps, "widths": widths, "n_evals": self.n_evals}


# --------------------------------------------------------------------------
# diagnostics
# --------------------------------------------------------------------------

def split_rhat(chains: np.ndarray) -> np.ndarray:
    c, n, d = chains.shape
    half = n // 2
    parts = np.concatenate([chains[:, :half], chains[:, half:2 * half]], axis=0)
    n2 = half
    means = parts.mean(axis=1)
    vars_ = parts.var(axis=1, ddof=1)
    W = vars_.mean(axis=0)
    B = n2 * means.var(axis=0, ddof=1)
    var_hat = (n2 - 1) / n2 * W + B / n2
    return np.sqrt(var_hat / np.maximum(W, 1e-300))


def ess(chains: np.ndarray) -> np.ndarray:
    """Bulk ESS per dimension: pooled autocorrelation, Geyer initial positive sequence."""
    c, n, d = chains.shape
    out = np.empty(d)
    for k in range(d):
        x = chains[:, :, k]
        x = x - x.mean(axis=1, keepdims=True)
        var = x.var(axis=1, ddof=1).mean()
        if var <= 0:
            out[k] = c * n
            continue
        acf = np.zeros(n)
        for ch in range(c):
            f = np.fft.rfft(np.concatenate([x[ch], np.zeros(n)]))
            acf += np.fft.irfft(f * np.conj(f))[:n] / n
        acf /= (c * var)
        rho_sum, t, prev_pair = 0.0, 1, np.inf
        while t + 1 < n:
            pair = acf[t] + acf[t + 1]
            if pair < 0:
                break
            pair = min(pair, prev_pair)
            rho_sum += pair
            prev_pair = pair
            t += 2
        out[k] = c * n / max(1.0 + 2.0 * rho_sum, 1e-6)
    return out


# --------------------------------------------------------------------------
# drivers
# --------------------------------------------------------------------------

def map_estimate(model: Model, psi0: Optional[np.ndarray] = None, maxiter: int = 3000) -> np.ndarray:
    psi0 = np.zeros(model.dim) if psi0 is None else np.asarray(psi0, float)

    def f(p):
        lp, g = model.logpost(p)
        return -lp, -g
    res = minimize(f, psi0, jac=True, method="L-BFGS-B", options={"maxiter": maxiter, "maxcor": 30})
    return res.x


def prepare(model: Model) -> Tuple[np.ndarray, np.ndarray]:
    """MAP and the whitening factor L with L L' = GN^-1."""
    psi = map_estimate(model)
    H = model.gauss_newton(psi)
    H = 0.5 * (H + H.T)
    w, V = np.linalg.eigh(H)
    w = np.maximum(w, 1e-8)
    L = V @ np.diag(1.0 / np.sqrt(w))
    return psi, L


def sample(model: Model, rng: np.random.Generator, sampler: str = "nuts", n_chains: int = 4, n_warmup: int = 400,
           n_samples: int = 400, max_depth: int = 8, target_accept: float = 0.8) -> Dict[str, object]:
    t0 = time.time()
    psi_map, L = prepare(model)
    d = model.dim
    if sampler == "laplace":
        M = n_chains * n_samples
        psi = psi_map[None, :] + (L @ rng.standard_normal((d, M))).T
        thetas = psi @ model.QV.T
        taus = np.array([model.tau_draw(p, rng) for p in psi])
        return {"psi": psi, "thetas": thetas, "taus": taus, "rhat_max": 1.0, "ess_min": float(M),
                "divergences": 0, "converged": True, "sampler": "laplace", "seconds": time.time() - t0,
                "psi_map": psi_map, "mean_depth": 0.0, "accept": 1.0}
    centre, Lcur = psi_map, L
    states = [0.5 * rng.standard_normal(d) for _ in range(n_chains)]
    n_final_warm = n_warmup
    if sampler == "nuts" and n_warmup >= 150:
        # Stan-style dense metric: two windows of NUTS warmup pooled across chains, each
        # followed by re-whitening with the pooled posterior covariance (regularised to I)
        for frac in (0.3, 0.3):
            w = int(frac * n_warmup)
            n_final_warm -= w
            pooled, ends = [], []
            for c in range(n_chains):
                nuts = NUTS(Whitened(model, centre, Lcur), rng, max_depth=max_depth, target_accept=target_accept)
                res = nuts.run(states[c], w, 0, keep_warmup=True)
                pooled.append(res["warm_draws"][w // 2:])
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
    white = Whitened(model, centre, Lcur)
    chains, divs, depths, accepts = [], 0, [], []
    for c in range(n_chains):
        if sampler == "slice":
            sl = SliceSampler(white, rng)
            res = sl.run(states[c], n_final_warm, n_samples)
            chains.append(res["draws"])
            depths.append(res["n_evals"] / float(n_final_warm + n_samples))
            accepts.append(1.0)
        else:
            nuts = NUTS(white, rng, max_depth=max_depth, target_accept=target_accept)
            res = nuts.run(states[c], n_final_warm, n_samples)
            chains.append(res["draws"])
            divs += res["divergences"]
            depths.append(res["mean_depth"])
            accepts.append(res["accept"])
    ch = np.array(chains)
    rhat = split_rhat(ch) if n_chains > 1 and n_samples >= 4 else np.ones(d)
    es = ess(ch)
    xi = ch.reshape(-1, d)
    psi = white.psi(xi)
    thetas = psi @ model.QV.T
    taus = np.array([model.tau_draw(p, rng) for p in psi])
    rhat_max = float(np.nanmax(rhat))
    ess_min = float(np.nanmin(es))
    converged = bool(rhat_max < 1.01 and ess_min >= 400 and divs == 0)
    return {"psi": psi, "thetas": thetas, "taus": taus, "rhat": rhat, "rhat_max": rhat_max, "ess": es,
            "ess_min": ess_min, "divergences": int(divs), "converged": converged, "sampler": sampler,
            "seconds": time.time() - t0, "psi_map": psi_map, "mean_depth": float(np.mean(depths)),
            "accept": float(np.mean(accepts)), "n_chains": n_chains, "n_warmup": n_warmup, "n_samples": n_samples}


def atm_sigma(K: np.ndarray, right: np.ndarray, mid: np.ndarray, F0: float, D: float, T: float) -> float:
    K = np.asarray(K, float)
    idx = np.argsort(np.abs(K - F0))[:6]
    iv = black76.implied_vol(np.maximum(np.asarray(mid, float)[idx], 0.0), F0, K[idx], T, D, np.asarray(right)[idx])
    iv = iv[np.isfinite(iv)]
    if iv.size == 0:
        return 0.5
    return float(np.median(iv))
