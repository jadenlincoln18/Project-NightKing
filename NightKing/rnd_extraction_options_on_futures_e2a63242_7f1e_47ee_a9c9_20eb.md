# Risk-Neutral Density Extraction from Options on Futures

*A reference-grade external survey — how academia and trading desks actually do it, what's correct, what's wrong, and complete computational recipes.*

---

**Scope.** This document surveys the state of the art of extracting the risk-neutral density (RND) of an underlying **futures** contract from a cross-section of exchange-listed options on that future. The intended reader has Shreve I under his belt, is comfortable with SDEs, no-arbitrage pricing, Girsanov, and the second-derivative Breeden–Litzenberger identity. The intended use case is (a) benchmarking a home-grown RND pipeline against decades of academic and practitioner work, and (b) auditing that pipeline for canonical failure modes.

Companion document (not repeated here): `nightking-strategy-writeup.md`. Section 8 of this document positions the NightKing choices against the external landscape; everything else is method-neutral.

**Notation** (used throughout).

- $F_t \equiv F(t,T)$ — futures price at $t$ for delivery/settlement at $T$.
- $r$ — the risk-free rate to $T$; $B(t,T) = e^{-r(T-t)}$.
- $\tau = T-t$ — time to expiry.
- $C(K,\tau), P(K,\tau)$ — undiscounted market prices of European calls / puts struck at $K$.
- $\mathbb{Q}$ — the risk-neutral (pricing) measure; $\mathbb{Q}^F$ the $T$-forward measure under which $F$ is a martingale.
- $q(K) \equiv q(K \mid F_t, \tau)$ — the marginal RND of $F_T$, evaluated at strike $K$.
- $\sigma(K,\tau)$ — Black-76 implied volatility (BS76-IV).
- $w(k,\tau) = \sigma(K,\tau)^2 \tau$ — total implied variance, expressed in log-moneyness $k = \log(K/F_t)$.
- $\phi_\tau(u) = \mathbb{E}^\mathbb{Q}[e^{iu\log F_T}\mid \mathcal F_t]$ — the characteristic function of $\log F_T$.

---

## 1. Foundations

### 1.1 Options on futures ≠ options on spot

Every practitioner accident in this area starts with someone treating the underlying like a stock. It isn't. A futures price is not a traded asset in the usual sense: no cash changes hands at inception, mark-to-market happens continuously, and the *forward* price at $t$ for delivery at $T$ satisfies (under the standard cost-of-carry paradigm)
$$F(t,T) = S_t\, e^{(r-y)(T-t)}$$
where $y$ collects dividend yield, convenience yield, storage cost — whatever applies to the specific commodity or index. Under $\mathbb{Q}$, the spot $S_t$ has drift $r-y$; under the same measure the *futures* price $F_t$ has drift zero:
$$dF_t = F_t\, \sigma_F(t)\, dW_t^\mathbb{Q},\qquad F_0 = \text{spot forward}.$$

This is the martingality of futures under $\mathbb{Q}$ (or more precisely under $\mathbb{Q}^T$ when interest rates are stochastic; for our purposes, treating $r$ as deterministic on the relevant horizon, the two coincide). It has two immediate consequences that shape every RND method:

1. **No drift term to sanitize.** In stock RND work (Aït-Sahalia & Lo 1998 on SPX cash) one must be careful with the dividend curve and repo/borrow costs; the "implied forward" is a separate object. On options on futures, the underlying of the option *is* the forward. There is no dividend leakage, no repo. The mean of the extracted density $q$ must equal $F_t$; that is a hard constraint, not an aspiration.
2. **Black-76, not Black-Scholes.** For a European call struck $K$, expiring at $T$, written on $F(t,T)$:
$$C(K,\tau) = e^{-r\tau}\,\bigl[F_t\,\Phi(d_1) - K\,\Phi(d_2)\bigr],\qquad d_{1,2}=\frac{\log(F_t/K)\pm \tfrac{1}{2}\sigma^2\tau}{\sigma\sqrt{\tau}}.$$
Same functional form as Black–Scholes with $S_0 \to F_t$ and $r \to 0$ inside the $d_i$'s — the discount factor is applied once, outside. Any code that plugs the spot into a stock Black–Scholes calculator and then compares to option-on-future quotes will be wrong by roughly $F/S$ in strike location.

Two subtler points that trip people up:

- **Physical delivery vs cash settlement.** WTI (CL) is a physically delivered contract on NYMEX; Brent (BZ) is cash-settled off an ICE benchmark; the E-mini S&P (ES) is cash-settled. This changes basis mechanics (roll behaviour, convergence to spot at expiry) but does *not* change the RND math for a *single expiry*. It matters when you are gluing together term structures.
- **Options expiry ≠ futures expiry.** For crude, options on the front-month contract expire ~3 business days before the underlying future expires. For gold, several days. For nat-gas, the day before. Which $F$ enters Black-76 is the futures price of the *underlying contract of that option*, not the front-month print. Confusing the two produces immediate put-call parity violations.
- **Weekly vs standard.** Weeklies on CL trade with different tick sizes and lower depth; the option chain that hits screens is a mix of standard monthlies and short-dated weeklies referencing possibly the same underlying future. Filter carefully.

### 1.2 Breeden–Litzenberger from first principles

Every method in this document is, at bottom, an answer to one identity. Under $\mathbb{Q}$ the price of a European call is
$$C(K,\tau) = e^{-r\tau}\,\mathbb{E}^\mathbb{Q}\!\bigl[(F_T-K)^+\bigr] = e^{-r\tau}\!\int_K^\infty (x-K)\,q(x)\,dx.$$
Differentiate once in $K$ (Leibniz; the boundary term at $x=K$ vanishes because the integrand vanishes there):
$$\frac{\partial C}{\partial K} = -e^{-r\tau}\!\int_K^\infty q(x)\,dx = -e^{-r\tau}\,\mathbb{Q}(F_T \ge K).$$
Differentiate again:
$$\boxed{\;q(K) = e^{r\tau}\,\frac{\partial^2 C(K,\tau)}{\partial K^2}\;}\qquad (\text{Breeden–Litzenberger, 1978}).$$

Equivalently:

- The undiscounted call price $\tilde C(K) = e^{r\tau} C(K)$ satisfies $q(K) = \partial^2 \tilde C/\partial K^2$.
- $-\partial C/\partial K = e^{-r\tau}\,\text{CDF}^c(K)$ is the discounted "risk-neutral survival function" — the price of a digital call struck at $K$. This is the *digital replication* relationship exploited later in Section 6.
- $\partial P/\partial K = e^{-r\tau}\,\mathbb{Q}(F_T \le K)$ (via put-call parity: $C - P = e^{-r\tau}(F_t - K)$, differentiate once).

**Geometry.** A picture worth ten equations:

```
        C(K)
          |\ 
          | \  slope = -e^{-rτ} P(F_T ≥ K)      <-- 1st derivative = digital
          |  \ 
          |   \   convex ⇒ 2nd derivative ≥ 0   <-- density
          |    \_ 
          |      \___
          +-----------\----> K
                      ^
                      F_t (kink at intrinsic changes to strict convexity)
```

The call price is a **convex, monotone-decreasing, non-negative** function of strike; the digital price is its (negative) slope; the density is its curvature.

### 1.3 Why the second derivative is the numerical villain

Take a call function that is exactly right, add microstructure noise of standard deviation $\varepsilon$ to each price, and ask what happens to a naive central-difference estimator of the second derivative on a strike grid of spacing $\Delta K$:
$$\hat q(K) \approx e^{r\tau}\,\frac{C(K+\Delta K) - 2C(K) + C(K-\Delta K)}{\Delta K^2}.$$
The bias goes as $O(\Delta K^2)$ (higher-order derivatives of $C$), the *variance* goes as $O(\varepsilon^2/\Delta K^4)$. Any hope of consistency requires $\Delta K \to 0$ *and* $\varepsilon/\Delta K^2 \to 0$ jointly — a mean-integrated-squared-error rate of $\varepsilon^{4/(4+\text{smoothness})}$, in the ballpark of nonparametric derivative estimation.

But on a real option chain $\Delta K$ is fixed by contract design — $\$0.25$ or $\$0.50$ for CL, $\$1.00$ for GC/SI at short strikes, wider in the wings — and $\varepsilon$ is fixed by the bid-ask spread and the discreteness of quotes. What you can *choose* is how much smoothness to impose. Every method in Section 2 amounts to some structural regularization: parametric families (very smooth by fiat), splines in IV (smooth in a lower-noise coordinate), maximum-entropy (smoothest density consistent with moment constraints), Bayesian curvature-penalized fits, etc. There is no free lunch. The bias–variance frontier is dictated by physics; the method just chooses where to sit on it.

An equivalent restatement: the map $C(\cdot) \mapsto C''(\cdot)$ is a *discontinuous inverse problem* in the sense of Tikhonov. Direct inversion (finite differences on raw call prices) is unstable; every stable method incorporates a regularization prior, whether stated or hidden.

### 1.4 Static no-arbitrage constraints — the algebra any RND method must obey

Absence of static arbitrage (Carr–Madan 2005; Roper 2010; Cousot 2007) at a fixed expiry $\tau$ requires the call surface $C(K)$ to be:

1. **Non-negative:** $C(K) \ge 0$.
2. **Monotone decreasing:** $\partial C/\partial K \in [-e^{-r\tau}, 0]$. Right endpoint $0$ (as $K \to \infty$, no OTM value), left endpoint $-e^{-r\tau}$ (fully in-the-money digital).
3. **Convex:** $\partial^2 C/\partial K^2 \ge 0$ — the butterfly non-negativity condition. Buying a butterfly for zero net cost anywhere would be free money; equivalent to positivity of $q$.
4. **Bounded intrinsic:** $C(K) \ge e^{-r\tau}\max(F_t-K, 0)$.
5. **Asymptotic:** $\lim_{K\to\infty} C(K) = 0$, $\lim_{K \to 0} C(K) = e^{-r\tau} F_t$ (for OTM/ITM boundaries).

Across expiries, the additional constraint is **calendar spread non-negativity**: the same butterfly for a longer expiry cannot cost less than for a shorter one. In terms of total variance $w(k,\tau) = \sigma(k,\tau)^2 \tau$, this becomes:
$$\partial_\tau w(k,\tau) \ge 0 \quad \text{for all } k, \tau.$$
This is Fengler (2009)'s and Gatheral–Jacquier (2014)'s workhorse condition and is what SSVI is built around.

In implied-volatility coordinates the butterfly condition becomes the celebrated Gatheral $g$-function:
$$g(k) = \left(1 - \frac{k\,w'(k)}{2w(k)}\right)^{2} - \frac{w'(k)^2}{4}\left(\frac{1}{w(k)} + \frac{1}{4}\right) + \frac{w''(k)}{2} \ge 0.$$
If $g(k) < 0$ anywhere, the resulting density is negative there. **This is the single most important algebraic sanity check** for anyone doing IV-space smoothing.

Finally, Lee's moment formula (Lee 2004) constrains the *tails* of any implied-vol slice:
$$\limsup_{k\to\infty} \frac{w(k,\tau)}{|k|} = \psi_R \in [0,2],\qquad \limsup_{k\to-\infty} \frac{w(k,\tau)}{|k|} = \psi_L \in [0,2],$$
where the constants are related to the highest finite moment of $F_T$. Slices flatter than linear are consistent with an underlying whose highest finite moment is $p_R = \tfrac{1}{2\psi_R}(1+\psi_R/2)^2$ (and mirror image on the left). Extrapolating a fit outside the traded range as *flat IV*, for instance, implies infinite moments and violates Lee. This is not a theoretical curio; it drives whether Section 6's expected shortfall integrals converge.

### 1.5 "Risk-neutral" ≠ "physical"

The RND $q$ is the density of $F_T$ under $\mathbb{Q}$. The physical density $p$ (statistician's forecast) is what nature actually samples from. The two are linked by the *pricing kernel* (state-price density per unit probability),
$$m(x) = \frac{q(x)}{p(x)}\,e^{-r\tau},$$
which under a representative-agent economy is (up to normalization) proportional to the marginal utility of consumption at state $x$. Under CRRA utility with risk aversion $\gamma$, $m(x) \propto x^{-\gamma}$; the RND is therefore a *reweighting* of the physical density that upweights bad-outcome states and downweights good ones. Empirically, on equity indices, $q$ has a fatter left tail than $p$ — the "crash premium" (Aït-Sahalia & Lo 2000; Bliss & Panigirtzoglou 2004; Jackwerth 2000). On commodities, the sign of the wedge depends on the aggregate hedging position (see Hamilton–Wu 2014 on oil).

The practical implication for anyone comparing RNDs to prediction-market or Kalshi implied probabilities: **prediction-market probabilities are estimates of $p$, not $q$**. Kalshi traders are not risk-neutral pricing agents; they can post directional views, they can be uninformed retail, they can be arbitrageurs. The gap between the extracted $q$ and the market-implied $p$ is not automatically an arbitrage — it may be a risk premium. Anyone trading the wedge without a hedge is trading risk premia by another name. This point is elaborated in Section 6.

A related sin: the "favorite-longshot bias" from the horse-racing literature (Thaler & Ziemba 1988; Snowberg & Wolfers 2010) shows that even in prediction markets, long-shots trade rich relative to their empirical frequency. If Kalshi exhibits a similar bias, the naive "$q$ vs Kalshi" gap will have a systematic sign at bracket edges regardless of any oil-market risk premium.

---

## 2. The full taxonomy of extraction methods

Every method is a choice of how to regularize the discontinuous inverse problem $C \mapsto C''$. They cluster into five families. I annotate each with mathematical form, assumptions, strengths, failure modes, and canonical citations. The order goes: parametric density families, smile-parameterization methods (still parametric, but in IV space), non-parametric direct methods, Bayesian / entropy methods, and calibrated model methods.

### 2.1 Parametric density families

Assume $F_T$ has a density of a specified functional form, invert option prices to find the parameters. Best when data are thin, worst when the true density violates the functional form.

#### 2.1.1 Single lognormal (Black-76 baseline)

$$q(x) = \text{LN}(x; \mu, s^2),\qquad C_{\text{B76}}(K; F, \sigma) = e^{-r\tau}[F\Phi(d_1) - K\Phi(d_2)],$$
one free parameter (the flat ATM IV). This is the null hypothesis every other method is measured against. Any dispersion of implied vols across strikes ("the smile") is *by definition* the failure of the lognormal. Useful only as a sanity check: does the extracted mean equal $F_t$? Does the extracted variance match the ATM implied variance times $\tau$?

#### 2.1.2 Mixture of lognormals (Ritchey 1990; Melick–Thomas 1997; Bahra 1997)

$$q(x) = \sum_{i=1}^k \pi_i \,\text{LN}(x; \mu_i, s_i^2), \qquad \sum \pi_i = 1,\ \pi_i \ge 0.$$
Two or three components suffice to capture most smiles. The call price is a corresponding weighted sum of Black-76 prices with mixture-component forwards $F_i = e^{\mu_i+s_i^2/2}$; the martingale constraint $\mathbb{E}[F_T] = F_t$ becomes
$$\sum_i \pi_i \,e^{\mu_i + s_i^2/2} = F_t.$$
Melick & Thomas (1997) is the canonical crude-oil paper — they extracted three-lognormal RNDs from options on NYMEX WTI during the 1990 Gulf crisis and showed genuine bimodality developing weeks before Desert Storm. Bahra (1997) is the Bank of England methodology paper that made mixtures the central-bank workhorse for two decades.

**Strengths.** Analytically tractable, arbitrage-free by construction (each component is a valid density; convex combinations preserve validity), interpretable ("two regimes").

**Weaknesses.**
- Ill-conditioned when one component is very narrow — the likelihood surface has spikes that trap optimizers (Cooper 1999 discusses this at length; the two-lognormal fit is *notoriously* sensitive to starting values).
- Tail behaviour is lognormal by construction: heaviest tail is still $O(x^{-1-1/\text{something}}\log x)$-suppressed. Not appropriate for markets with strong jump risk.
- Number of components $k$ is a modeler choice; adding components eventually overfits.

#### 2.1.3 Generalized Beta of the Second Kind (Bookstaber–McDonald 1987)

$$q(x; a,b,p,q) = \frac{|a| x^{ap-1}}{b^{ap} B(p,q)(1 + (x/b)^a)^{p+q}},\qquad x>0.$$
Nests lognormal, GB1, Burr, Pareto, and others as limiting or special cases. Four free parameters give substantial flexibility while remaining analytically tractable — call prices are computable via incomplete beta functions. Used in central-bank practitioner work (e.g., Bu & Hadri 2007 for FTSE options). Less popular than mixtures because harder to interpret and the fitting is only weakly better on typical data.

#### 2.1.4 Edgeworth / Gram–Charlier expansions (Jarrow–Rudd 1982; Corrado–Su 1996)

Take a lognormal reference density $f_0(x)$, correct for skew $\lambda_3$ and excess kurtosis $\lambda_4$:
$$q(x) = f_0(x)\left[1 + \tfrac{\lambda_3}{3!} H_3(z) + \tfrac{\lambda_4}{4!} H_4(z)\right],\qquad z = \tfrac{\log x - \mu}{s}.$$
Call price is closed-form:
$$C(K) = C_{\text{B76}}(K) + \lambda_3\,Q_3(K) + \lambda_4\,Q_4(K),$$
with $Q_3, Q_4$ explicit vega-like sensitivities.

**The catastrophic problem.** $q$ is not guaranteed to be non-negative. The truncation of the Hermite series with cumulants larger than a critical threshold produces bumps that dip below zero in the tails. In quiet markets ($\sigma \sim 15\%$, mild skew) it works; in stressed markets it fails silently. The seminal Corrado–Su paper used it on S&P 500 index options in a low-vol pre-'87 sample; extension to post-crisis regimes routinely produces negative wings.

Verdict: **useful only pedagogically.** Do not deploy.

#### 2.1.5 Pure-jump Lévy families: Variance Gamma, NIG, CGMY

Under a Lévy process, $\log F_T$ has a characteristic function of Lévy–Khintchine form. Three practitioner favorites:

- **Variance Gamma (Madan–Carr–Chang 1998).** $F_T = F_0 \exp(\omega\tau + X_\tau)$, $X_\tau$ a time-changed Brownian motion with gamma clock. Characteristic function of $X_\tau$:
$$\phi_\tau(u) = \bigl(1 - i\theta\nu u + \tfrac{1}{2}\sigma^2\nu u^2\bigr)^{-\tau/\nu}.$$
Three parameters. Fat tails, controlled skew, closed-form density in special-function form.

- **Normal Inverse Gaussian (NIG; Barndorff-Nielsen 1997).** Similar spirit, different subordinator (inverse Gaussian). Four parameters. Slightly heavier tails than VG.

- **CGMY (Carr–Geman–Madan–Yor 2002).** A four-parameter Lévy density $k(x) = C\bigl[e^{-G|x|}/|x|^{1+Y}\mathbb{1}_{x<0} + e^{-Mx}/x^{1+Y}\mathbb{1}_{x>0}\bigr]$; nests VG at $Y=0$. Rich tail control (independent left/right decay rates $G, M$), $Y \in (0,2)$ tunes activity between finite-activity (small $Y$) and diffusion-like (large $Y$).

For all three, the RND is obtained by Fourier inversion of $\phi_\tau$ (Carr–Madan 1999 for prices; Fang–Oosterlee 2008's COS method for direct density recovery). Assumptions: independent increments (no stochastic vol *within* the model), which is often unrealistic at long horizons but fine for a single expiry snapshot.

**Strengths.** Genuine fat tails, small parameter count, characteristic-function machinery is fast (a few thousand FFT operations per calibration).

**Weaknesses.** No term-structure coherence across expiries — refit each expiry independently, which then produces calendar arbitrage if you're not careful (Carr–Wu 2004 "Time-Changed Lévy Processes" is the fix but is much more complex).

#### 2.1.6 SABR-implied densities (Hagan et al. 2002)

SABR is a stochastic-vol model:
$$dF_t = \alpha_t F_t^\beta\, dW_t,\qquad d\alpha_t = \nu\alpha_t\,dZ_t,\qquad d\langle W,Z\rangle = \rho\,dt.$$
Hagan's asymptotic expansion gives an approximate IV formula $\sigma_{\text{SABR}}(K; F, \alpha, \beta, \rho, \nu, \tau)$. Ubiquitous on interest-rate desks. On oil / commodities, less used at short horizon (typically $\beta \approx 1$ chosen a priori, then $\alpha, \rho, \nu$ fit).

The RND is obtained by stripping SABR-implied prices from Black-76 on a fine grid and finite-differencing $C''$. Two caveats:

1. Hagan's expansion is asymptotic in short time. For $\tau \gtrsim 3$ months and pronounced smiles the expansion produces negative densities near the ATM (documented by Obłój 2008; the "SABR negative density" problem). Fixes exist (Hagan et al. 2014 "Arbitrage-Free SABR", solve the PDE directly).
2. It is still, at bottom, a parametric family — the tails are constrained to whatever SABR produces, which in short time is close to lognormal.

### 2.2 Implied-volatility smile methods

The dominant methodology on desks. The pipeline is: interpolate/smooth in IV space, invert to a call surface via Black-76, differentiate twice in $K$. Working in IV space rather than price space is one of the most reliable pieces of advice in the literature (Section 3.1).

#### 2.2.1 Cubic-spline in IV (Shimko 1993; Malz 1997)

Fit a natural cubic spline to observed $(K_i, \sigma_i)$ pairs. Extrapolate flat outside the traded range (Shimko) or with a Malz-style linear extrapolation in delta. Recover $C(K) = C_{\text{B76}}(K; \sigma_{\text{spline}}(K))$; differentiate twice.

Simple, fast, was the workhorse until SVI supplanted it. Fails in exactly two regimes:

1. **Sparse chains.** When only 5–8 strikes are liquid, the natural spline overshoots in the wings.
2. **No baked-in arbitrage control.** Nothing in a cubic-spline fit guarantees butterfly-non-negativity. You have to check $g(k) \ge 0$ post-hoc and reject or re-fit.

#### 2.2.2 SVI — Stochastic Volatility Inspired (Gatheral 2004)

The workhorse. Total variance parameterized as
$$w(k) = a + b\bigl[\rho(k-m) + \sqrt{(k-m)^2 + \sigma^2}\bigr],$$
five parameters per expiry slice:

- $a$ — vertical shift (minimum variance);
- $b$ — overall smile slope / call-put wing weight ($b \ge 0$);
- $\rho \in [-1, 1]$ — skew;
- $m$ — horizontal shift (ATM);
- $\sigma \ge 0$ — smile curvature at ATM.

**Why SVI.** (i) Compact, five parameters describe SPX smiles to two IV digits over a wide moneyness band. (ii) Asymptotic behaviour matches Lee's moment formula exactly (each wing is linear in $|k|$, so both $\psi_L$ and $\psi_R$ are finite). (iii) It arises as the large-strike, large-maturity limit of Heston (Gatheral & Jacquier 2011), so it is model-consistent, not ad-hoc.

**Fitting.** Nonlinear least squares in $\chi = (a,b,\rho,m,\sigma)$ with vega-weighted residuals against market IVs. Zeliade (2009) proposed the widely used "quasi-explicit" method: fix $(m,\sigma)$ and solve a linear program in $(a,b,\rho)$, then outer-loop on $(m,\sigma)$. Cuts fitting time from seconds to milliseconds per slice.

**Butterfly arbitrage.** The Gatheral $g$-function (Sec 1.4) must be non-negative pointwise. In practice, one either constrains during optimization (penalize $\min_k g(k) < 0$ with a large Lagrangian) or grids $g$ post-fit and rejects/re-fits if violated. Roper (2010) and Gatheral–Jacquier (2014) give sufficient conditions on $\chi$ for butterfly-free SVI slices: after fitting, verify
$$b(1+|\rho|) \le \frac{4}{\tau}\quad\text{and}\quad \text{a mild condition on the interior}$$
(the exact set of sufficient conditions is somewhat weaker than these but complicated; the practical route is grid-check $g$).

**Failure modes.** (i) Fit gets stuck in a local optimum when initialization is far. (ii) Extrapolation past the last traded strike inherits the linear wing behaviour, which is often too heavy (implies $F_T$ has only finite moments up to $p^*$ inversely proportional to wing slope) — must be verified against the strategy's tail-sensitivity needs. (iii) Very short-dated smiles ($\tau < 5$ days) are ill-fit — the density gets peaky and SVI cannot resolve.

#### 2.2.3 SSVI — Surface SVI (Gatheral–Jacquier 2014)

Extends SVI across maturities in one closed-form surface:
$$w(k, \theta_t) = \frac{\theta_t}{2}\Bigl\{1 + \rho\varphi(\theta_t)k + \sqrt{(\varphi(\theta_t)k + \rho)^2 + (1-\rho^2)}\Bigr\},$$
with $\theta_t$ ATM total variance (grows in $t$) and $\varphi$ a smooth positive function. Two natural choices:

- **Heston-like:** $\varphi(\theta) = \tfrac{1}{\lambda\theta}\bigl(1 - \tfrac{1-e^{-\lambda\theta}}{\lambda\theta}\bigr)$.
- **Power-law:** $\varphi(\theta) = \eta\theta^{-\gamma}(1+\theta)^{\gamma-1}$, with $\gamma \in (0,1/2]$ and $\eta(1+|\rho|) \le 2$ sufficient for full static-arb freedom.

SSVI is arbitrage-free *across* strikes and maturities *by construction* (under the sufficient conditions), which is huge — it means you can back out RNDs at any expiry, including non-listed ones, by interpolation in $\theta$, and calendar arbitrage between them is impossible. This is the modern practitioner default when a *surface* is needed rather than a single slice.

**Extensions.** eSSVI (Corbetta et al. 2019) generalizes $\varphi$ and $\rho$ to be maturity-dependent while preserving arb-freedom; this loosens the fit quality vs. the "one global smile shape" of SSVI. Nelson–Siegel–Svensson analogues in the ATM curve $\theta_t$ are used in central-bank surveys to smooth the term structure component.

#### 2.2.4 Explicit no-arb constrained fits (Fengler 2009)

Fengler's insight: fit $C(K)$ itself with a smoothing spline under linear inequality constraints,
$$\min_{c} \sum_i w_i (C(K_i) - C_i)^2 + \lambda \!\int C''(K)^2\, dK$$
subject to $C''(K_j) \ge 0$, $-e^{-r\tau} \le C'(K_j) \le 0$ pointwise on a fine grid. The result is a natural cubic spline whose knot coefficients solve a **quadratic program** — genuinely arbitrage-free, no post-hoc rejection needed.

The subtlety: since call prices span 4–6 orders of magnitude across strikes, unweighted least squares over-weights the ITM tail. Fengler recommends *vega-weighted* residuals ($w_i = 1/\text{vega}_i^2$), which effectively translates the fit into IV-space error — the best of both worlds (smoothness in $C$-space, error metric in IV-space).

**Recommended for:** producing an arbitrage-guaranteed surface from raw market prices when you distrust the smile parameterization.

**Watch for:** hyperparameter $\lambda$ needs cross-validation. Too small → interpolation of noise; too large → oversmoothing tails.

### 2.3 Non-parametric direct methods

#### 2.3.1 Finite differences on raw calls

The naive Breeden–Litzenberger implementation: forward, central, or backward differences on quoted call prices. Discussed for completeness — it is almost never used in practice on real data because of the $O(1/\Delta K^4)$ variance blow-up (Sec 1.3). The one legitimate use is on model-generated, noise-free option prices (unit tests, model calibration checks). If you see this on real data in production, treat as a bug.

#### 2.3.2 Positive convolution approximation (Bondarenko 2003)

Non-parametric, but with monotonicity/convexity of $C(K)$ enforced by construction. The density is written as
$$q(x) = \int \pi(y)\,\phi_h(x-y)\,dy,$$
a convolution of a non-negative "spectrum" $\pi \ge 0$ with a smoothing kernel $\phi_h$. Since $\phi_h$ is fixed and $\pi \ge 0$ is enforced (via reparameterization $\pi = \psi^2$ or by non-negative least squares), the resulting $q$ is automatically non-negative, and hence $C(K) = e^{-r\tau} \int (x-K)^+ q(x)\, dx$ is automatically convex in $K$. Bondarenko's kernel choice (Epanechnikov or Gaussian) and bandwidth $h$ are the two hyperparameters.

**Strengths.** Fully non-parametric, arb-free by construction, smooth. Very stable in the mid-range.

**Weaknesses.** Tail behaviour driven by the kernel (typically thin-tailed); requires careful boundary handling. Bandwidth selection matters — leave-one-out CV or Bondarenko's suggested plug-in bandwidth.

#### 2.3.3 Kernel smoothing of IV then differentiate (Aït-Sahalia–Lo 1998)

$$\hat\sigma(K) = \frac{\sum_i K_h(K-K_i)\,\sigma_i}{\sum_i K_h(K-K_i)},$$
Nadaraya–Watson (or local-linear) smoother in the IV surface, then Black-Scholes-invert to get $C$, differentiate. Asymptotic theory is well-developed (Aït-Sahalia–Lo derive uniform convergence rates). Not currently the practitioner default because SVI and SSVI generally beat it on small chains, but it shines on very large chains (SPX has $10^3$ traded strikes across expiries; kernel methods scale gracefully).

**Failure mode.** On small chains, boundary effects near the traded-range edges dominate; local-linear helps but does not eliminate.

#### 2.3.4 Constrained least-squares on butterfly prices

Instead of fitting $C(K)$ or $\sigma(K)$, fit the butterfly prices $\text{Bfly}(K; \Delta K) = C(K-\Delta K) - 2C(K) + C(K+\Delta K)$ directly — these are the discrete approximations to $q$ scaled by $\Delta K^2 e^{-r\tau}$. Impose $\text{Bfly}_i \ge 0$ as inequality constraints. Rarely used standalone because with unequal strike grids the interpretation gets messy, but conceptually clean and sometimes used as a diagnostic layer over another method.

### 2.4 Bayesian / entropy methods

Reformulate the problem as: among all densities consistent with the observed option prices (as moment constraints), pick the one that maximizes some information-theoretic objective. The advantage is that "consistent with the data" and "sensible prior" get formally separated.

#### 2.4.1 Maximum entropy (Buchen–Kelly 1996; Stutzer 1996)

Maximize Shannon entropy $H[q] = -\int q(x)\log q(x)\,dx$ subject to
$$\int q(x)\,dx = 1,\qquad e^{-r\tau}\!\int (x-K_i)^+ q(x)\,dx = C_i, \ i = 1,\ldots,n.$$
Solution by Lagrangian duality is
$$q(x) = \exp\!\Bigl(-\lambda_0 - 1 - \sum_i \lambda_i \max(x - K_i, 0)\Bigr),$$
with $\lambda_i$'s solving the dual (a convex $n$-variable optimization). Buchen–Kelly showed that for typical inputs this produces a smooth piecewise-exponential density that hits every price exactly — no fitting error. If a prior $q_0$ is available, replace $H$ with $-D_{\text{KL}}(q \| q_0) = -\int q\log(q/q_0)\,dx$ (Kullback–Leibler cross-entropy).

**Strengths.**
- Uniquely determined by data + entropy criterion — no arbitrary functional form.
- Convex problem, globally optimal.
- With KL against a lognormal prior, provides a principled way to graft market data onto a Black-76 baseline.

**Weaknesses.**
- Exact interpolation. Noisy prices propagate directly into density.
- Piecewise-exponential shape has kinks at each strike; not the smoothness practitioners typically want.
- Getting a good prior is half the battle (Rubinstein 1994's implied trees can be seen as an early attempt at combining a diffusion prior with option data).

Extensions: Neri–Schneider (2013) give a family of exponential-polynomial max-entropy densities; Cont & Tankov (2004) discuss max-entropy for pricing kernels.

#### 2.4.2 Bayesian nonparametrics with log-density splines (Monteiro–Tütüncü–Vicente 2008; Figlewski 2010; Reid 2012)

Represent $\log q(x)$ (or $q$ directly) as a linear combination of basis functions $\{B_j(x)\}_{j=1}^m$ with coefficients $\beta_j$, then penalize the curvature of $\beta$ to enforce smoothness:
$$\ell(\beta) = -\sum_i \frac{(C_i - \hat C_i(\beta))^2}{2\sigma^2_{C,i}} - \frac{\lambda}{2}\int q''(x)^2\,dx - \eta\cdot \Bigl(\int x q(x)dx - F_t\Bigr)^2.$$
Bases in common use: B-splines, natural cubic splines with equispaced knots, Bernstein polynomials, log-spline (Kooperberg–Stone). The last term enforces the martingale condition softly (or hard via a Lagrange multiplier).

In a fully Bayesian setup, one puts a hyperprior on the smoothing parameter $\lambda$ (Gamma(0.001, 0.001) is standard; more informative if there is a natural scale), samples $\beta$'s posterior via HMC or Metropolis, and gets an *ensemble* of densities. The ensemble is the point: you can propagate posterior uncertainty into bracket-probability confidence intervals, Kalshi arbitrage p-values, etc.

**Where this sits in the literature.**
- Kooperberg & Stone (1991) "logspline density estimation" — general univariate density estimation from samples; the option-pricing lift is the moment constraints.
- Monteiro et al. (2008) — cubic splines on the density with non-negativity enforced by penalties. Called out by Figlewski (2010) as one of the best empirical performers.
- Figlewski (2010) "Estimating the Implied Risk Neutral Density" — the reference review; discusses splines on IV, splines on the density, and how to attach tails.
- Reid (2012, 2013 University of Konstanz theses) — Gaussian-process priors on $\log q$ with a Matérn covariance. Attractive but slow (matrix inversions).

**Strengths.**
- Flexible; can approximate arbitrary smooth densities.
- Bayesian treatment automatically propagates uncertainty.
- Martingale and normalization constraints handled naturally (Lagrange multipliers or hard-projection into the constrained subspace).

**Weaknesses.**
- Choice of basis and knot placement is a modeling decision — cross-validation or reversible-jump MCMC to handle it.
- Slow — HMC on $O(20)$-dim posteriors is fine, but full uncertainty quantification against a 100-strike chain and a large grid can take seconds per chain.
- Tail extrapolation still needs an explicit story (Figlewski attaches GEV tails; Monteiro uses polynomial decay).

#### 2.4.3 Gaussian-process priors on log-density

Same idea as 2.4.2 with a nonparametric-Bayesian prior. $\log q(x) \sim \text{GP}(0, K_\theta(x,x'))$; observations are the option prices which are linear functionals of $q$. Kernel choice (RBF, Matérn 5/2) dictates smoothness. Reid (2012) and follow-ups. Elegant but computationally expensive ($O(n^3)$ per gradient in the option-price-count $n$; scaling to full CL chains stresses hardware).

#### 2.4.4 Neural-network parameterizations

Recent (2019+): parameterize $q(x)$ or $\sigma(K,\tau)$ with a neural net, backprop through the pricing map. Ackerer–Tagasovska–Vatter (2020) "Deep Smoothing of the Implied Volatility Surface"; Cuchiero et al. (2020) "Generative adversarial networks in local vol"; Horvath–Muguruza–Tomas (2021) on rough-vol calibration.

**Verdict for RND extraction:** overkill. Neural nets excel when *dimensionality is high and structure is unclear*; RND from a single expiry is a smooth 1D density regularization problem with clear inductive biases. Splines, SVI, and Bayesian methods are competitive and interpretable. Where NNs pull their weight is calibrating rough-vol models to entire surfaces in milliseconds.

### 2.5 Calibrated model methods

Instead of extracting $q$ non-parametrically, calibrate a stochastic model to option prices and read off $q$ analytically or via a fast transform.

#### 2.5.1 Local volatility (Dupire 1994)

Given a full continuum of arbitrage-free call prices $C(K,\tau)$, Dupire's formula recovers the unique local-vol function $\sigma_{\text{loc}}(K,\tau)$ consistent with those prices:
$$\sigma_{\text{loc}}^2(K,\tau) = \frac{2\,\partial_\tau C}{K^2 \partial^2_{KK}C}.$$
Given $\sigma_{\text{loc}}$, the RND at any expiry is obtained by simulating (or PDE-solving) the SDE $dF_t = F_t \sigma_{\text{loc}}(F_t,t)\,dW_t$ to $T$ and taking the marginal.

Circular for our purposes: recovering $\sigma_{\text{loc}}$ *requires* $\partial^2_{KK}C$, which is the very quantity we're trying to compute robustly. In practice, one uses an arbitrage-free smoothing (Fengler, SSVI) to get $C(K,\tau)$, then reads off $\sigma_{\text{loc}}$ from Dupire, then reads off the RND — but the RND was already sitting in the smoothed $C$ surface. Local vol is more useful as an *interpolation object* than an RND-extraction primitive.

#### 2.5.2 Stochastic volatility (Heston 1993; Bates 1996)

Heston:
$$dF_t = \sqrt{v_t}\, F_t\, dW_t^F,\qquad dv_t = \kappa(\theta - v_t)dt + \xi\sqrt{v_t}\, dW_t^v,\quad d\langle W^F, W^v\rangle = \rho\,dt.$$
Five parameters $(v_0, \kappa, \theta, \xi, \rho)$. Characteristic function $\phi_\tau(u)$ is known in closed form (with the usual complex-logarithm branch-cut care; see Albrecher et al. 2007 for the "little Heston trap").

**RND recovery via Carr–Madan (1999) FFT.**
1. Compute $\phi_\tau(u)$ from Heston parameters.
2. The dampened call transform is $\psi(v) = \frac{e^{-r\tau}\phi_\tau(v - (\alpha+1)i)}{\alpha^2+\alpha-v^2+i(2\alpha+1)v}$; call price at log-strike $k$ is
$$C(k) = \frac{e^{-\alpha k}}{\pi}\int_0^\infty e^{-ivk}\psi(v)\,dv.$$
3. Density: invert $\phi_\tau$ directly, $q(x) = \tfrac{1}{2\pi}\int e^{-iu\log x} \phi_\tau(u)\,du / x$.

**Alternative: Fang–Oosterlee COS method (2008).** Truncate the log-space integration to $[a,b]$, expand $\phi_\tau$ in Fourier-cosine series, get prices and densities in $O(N)$ per strike; typically $N=128$ suffices for four-digit accuracy. Faster than FFT for most desk workflows.

**Where this fits.** Heston is a smooth-parametric model — the extracted RND is exactly whatever Heston can produce. Great for smoothly interpolating across expiries; not great when the market genuinely has jumps (crude on OPEC decision day) or non-Heston smile shapes.

**Extensions.** Bates (1996) = Heston + jumps in $F$; Duffie–Pan–Singleton (2000) affine jump-diffusion umbrella; Barndorff-Nielsen–Shephard non-Gaussian OU; SVCJ (Eraker–Johannes–Polson 2003) with jumps in both.

#### 2.5.3 Rough volatility (Bayer–Friz–Gatheral 2016; Bergomi 2016)

Model log-vol as a fractional Brownian motion with Hurst $H \approx 0.1$ (empirical for equity indices). Reproduces the observed power-law explosion of the short-dated ATM skew. Not yet a desk standard for RND extraction but growing.

For RND: no closed-form characteristic function; rely on Monte Carlo or the recent hybrid schemes (Bayer et al. 2016). Neural-network calibration (Horvath et al. 2021) makes this tractable for surface calibration but is overkill for a single-slice density.

**Verdict.** For NightKing-style single-expiry work, rough vol is not a natural fit; the payoff of the extra realism is small vs. the parameter count and calibration cost. But: it is the *state of the art* for stochastic-volatility modeling, so it belongs in any serious literature map.

---

## 3. What's correct — practices that survive scrutiny

These are the operational choices that show up, over and over, in the papers cited above and in central-bank practitioner surveys (Bahra 1997; BoE Quarterly Bulletin RND columns; ECB working papers on FX-options RNDs; Fed IFDPs on oil).

### 3.1 Interpolate in implied-volatility space, not price space

Call prices on a single expiry span 4–6 orders of magnitude across strikes — deep OTM options trade at pennies, deep ITM at hundreds of dollars. A single unweighted least-squares interpolator (spline, kernel, whatever) *will* prefer to fit the ITM tail and ignore the OTM tail because that's where the absolute residuals live. But the RND-relevant information — the curvature of $C$ — is concentrated in the OTM wings.

Implied volatility is $O(1)$ everywhere: front-month CL might trade 25% ATM, 40% far-OTM put, 32% far-OTM call. Same functional dynamic range. Residuals in IV space are approximately residuals in the risk-neutral log-density space, up to a Jacobian; interpolating in IV automatically vega-weights the fit.

Equivalently: if you insist on interpolating in price space (e.g., Fengler's spline in $C$), *weight residuals by $1/\text{vega}^2$*. This is the Fengler–Rindler prescription and is not optional in the wings — without it the tails come out visibly wrong.

### 3.2 Use OTM options only

Put-call parity says any OTM put has an equivalent OTM call (given the correct forward), so there is no information *loss* from restricting to OTM. But there is information *gain*: OTM options have tighter effective bid-ask spreads (as a fraction of the option's own vega), no early-exercise concerns (for American-style options, only OTM options are guaranteed to have low early-exercise premia), and no confusion about which side of the parity you're pricing from.

Standard convention:
$$\sigma(K) = \begin{cases}\text{IV from put } P(K) & K < F_t \\ \text{IV from call } C(K) & K \ge F_t\end{cases}$$
At-the-money, use whichever is tighter or blend by inverse-spread weighting. Any dataset that includes both ITM calls and ITM puts and treats them as independent observations is double-counting information *and* introducing noise (each ITM leg has parity-derived redundancy plus microstructure noise from its own quote).

### 3.3 Enforce arbitrage constraints inside the optimizer, not post-hoc

The naive workflow — fit unconstrained, then check for arb violations, then reject or refit — has three problems. First, the fitted parameters can be very close to the constraint boundary, so tiny perturbations in the next snapshot flip the arb-check sign, producing spurious time-series signal. Second, the constrained optimum is often materially different from the unconstrained optimum projected onto the constraint set (the projection is not the same as constrained optimization). Third, if you *do* reject and refit with different starting values, you have introduced path-dependent noise into your production pipeline.

The right idiom is Fengler-style: express constraints as linear inequalities (or the Gatheral-$g$ condition as a polynomial inequality) and solve the constrained problem directly — quadratic program, sequential quadratic programming, or interior-point. All standard optimizers handle this. In Bayesian settings, enforce constraints by rejecting samples that violate them, or (better) reparameterize so violations are impossible (e.g., in max-entropy, exponential form guarantees $q \ge 0$; in log-density splines, exponentiate at the end).

### 3.4 Weight by vega

Related to §3.1 but distinct. Even within IV space, not all $\sigma_i$ observations are equally informative. Vega is highest ATM (per unit IV, an ATM option's price moves the most), so an IV observation near ATM has less microstructure noise per unit vega than a wing observation. But precisely because wing options have low vega, their IV *estimate* has high noise. The two effects roughly cancel in one specific weighting: **weight the residual $(\sigma_i - \hat\sigma(K_i))^2$ by $\text{vega}_i^2$** (or equivalently, fit call-price residuals with unit weights via the change of variables). This is what Zeliade (2009), Fengler (2009), and most SVI implementations do.

Specifically:
$$L(\chi) = \sum_i \text{vega}(K_i, \sigma_{\text{mkt},i})^2 \bigl(\sigma_{\text{SVI}}(K_i; \chi) - \sigma_{\text{mkt},i}\bigr)^2.$$

### 3.5 Fit the forward $F_t$ from the option chain via put-call parity regression

This is the point where the NightKing pipeline earned its "−8pt bug" via lived experience. The temptation is to source $F_t$ externally — from the front-month print, from a broker forward curve, from federal (fedarb, Bloomberg BFV, etc.). This is wrong for exactly the reason the NightKing writeup identifies: externally-sourced anchors are stale, quoted at slightly different times, or refer to a slightly different contract, and the resulting mis-anchoring shifts *every* extracted density by the same amount.

The correct method: implied forward from put-call parity. For each traded strike where both a call and a put exist,
$$F_t = K + e^{r\tau}\,\bigl(C(K) - P(K)\bigr).$$
Collect these implied-forward estimates across strikes and take (i) the median (robust), (ii) an inverse-variance weighted mean using bid-ask spreads to estimate variance, or (iii) an outright OLS regression of $C(K)-P(K)$ on $K$ across all strikes, extracting slope $-e^{-r\tau}$ and intercept $e^{-r\tau} F_t$. This last variant also gives an implicit sanity check: if the regressed slope deviates materially from $-e^{-r\tau}$, either your interest rate is wrong or you have a parity-violating dataset (stale quotes, timing skew, wrong expiry).

### 3.6 Propagate uncertainty; don't ship point estimates

Every method above produces a *point* density $\hat q$. Downstream trading logic (butterflies, Kalshi arbitrage) then computes bracket probabilities $\hat P([a,b]) = \int_a^b \hat q(x)\,dx$ and treats them as if they were the true values. This ignores that both $\hat q$ and $\hat P$ have uncertainty — the option chain has finitely many strikes with non-zero bid-ask spreads, the fitting procedure has its own noise, and the smoothing hyperparameters were themselves selected from finite data.

Two canonical routes:

1. **Bayesian ensemble.** Run HMC (or Metropolis, or SVI-the-variational-inference-kind) on the posterior of the density parameters and get $M$ samples $\{q^{(m)}\}$. Bracket probability is a distribution: $\{P^{(m)}([a,b])\}_{m=1}^M$, and confidence intervals are order statistics thereof. This is native for Section 2.4 methods and can be bolted on to SVI by placing priors on $(a,b,\rho,m,\sigma)$ from the Jacobian of the fit.

2. **Bootstrap.** Resample option quotes with replacement (or, more sophisticatedly, perturb each quote by a Gaussian with std equal to half the bid-ask spread), re-run the whole pipeline $B$ times, get $B$ densities and $B$ bracket probabilities. Simpler than Bayesian, no prior specification, but the resampling scheme needs care (option prices are dependent — you can't just IID resample).

Either way, ship the *interval*, not the point.

### 3.7 Compare bracket probabilities (integrals), not point densities

Densities are pointwise objects with unbounded variance under noise perturbation; integrals of densities are smoother functionals with $\sqrt{n}$-consistent behaviour. When comparing $\hat q$ from options to a Kalshi bracket $[a,b]$, the right object to compute is $\int_a^b \hat q(x)\,dx$, not $\hat q$ at a point. This is a mathematical statement (integrals average out noise) and a business statement (Kalshi contracts settle on bracket outcomes, not on point densities).

Related: report probabilities in coordinates that traders actually operate in — $P(F_T \ge \text{strike})$, quintile masses, expected shortfall at 5%. Point densities are for plotting, not for decision-making.

### 3.8 Handle roll boundaries explicitly

Continuous-futures series (constructed by rolling from front-month to next-month at some rule) introduce a discontinuity at each roll that corrupts any window straddling the roll — an implied vol of the pre-roll contract is not comparable to an implied vol of the post-roll contract at the same relative moneyness. For RND work, the cleanest choice is to (a) fit each expiry to the specific underlying contract at that expiry, and (b) never mix data across rolls in a single fit. If you need term-structure interpolation, use SSVI on the specific-contract series, not on the continuous one.

### 3.9 Compute the diagnostic quartet

Every extracted RND should ship with four diagnostics:

1. **Butterfly non-negativity check.** $\min_x q(x) \ge -\epsilon$ (with $\epsilon$ a small tolerance for numerical roundoff).
2. **Integrates to unity.** $\bigl|\!\int q\,dx - 1\bigr| < 10^{-3}$.
3. **Mean equals implied forward.** $\bigl|\!\int x q(x)\,dx - F_t\bigr| < 10^{-3} F_t$.
4. **Reprices the chain.** Recompute all option prices from $\hat q$ via $C(K) = e^{-r\tau} \int (x-K)^+ q(x)\,dx$; compare to market. In-sample IV RMSE < 0.5% is the practitioner's rule of thumb; failure indicates a bug or an unfittable smile.

All four must pass. Method development that only checks #4 ("the fit looks good") routinely produces densities that violate #1 or #3 silently.

---

## 4. What's incorrect — canonical failure modes

Most RND work in the wild suffers from one or more of the following. Each is named, tagged with its symptom, and (where possible) attributed to the paper that first documented or fixed it.

### 4.1 Naive Breeden–Litzenberger finite differences on raw call prices

**Symptom.** Density spikes negative between strikes; the wings blow up; from one snapshot to the next, $\hat q$ changes dramatically.

**Mechanism.** Sec 1.3: variance of the FD estimator is $O(\varepsilon^2/\Delta K^4)$. With $\Delta K = \$0.50$ on CL and $\varepsilon \sim \$0.02$ from tick-level noise, the FD variance is $\sim 6 \times 10^{-4}$ per unit density — comparable to or larger than the density itself in the wings.

**Fix.** Any of the smoothing methods in Sec 2. If you *must* do FDs, do them on a smoothed $C$ surface, not on raw quotes.

### 4.2 Unconstrained cubic-spline of raw call prices

**Symptom.** Density has multiple sharp negative excursions between knots; butterfly checks fail.

**Mechanism.** A cubic spline through call quotes is a *cubic in $K$*, which has no convexity guarantee. Between knots the function is free to wiggle. Even monotonicity is not preserved.

**Fix.** Use Fengler's shape-constrained spline (2009) which explicitly imposes $C''\ge 0$ and $-e^{-r\tau}\le C'\le 0$. Or spline in IV space and impose the Gatheral-$g$ condition post-fit.

### 4.3 Edgeworth / Gram–Charlier in high-vol or heavy-tail regimes

**Symptom.** Density dips negative in one or both tails; skew/kurtosis coefficients estimated on stressed markets are large enough to trigger the negativity.

**Mechanism.** The Hermite series truncation is a valid approximation only when the true density is a small perturbation of the reference density; large moments push the higher Hermite polynomials out of controlled range.

**Fix.** Do not use Corrado–Su style methods on stressed samples. Use mixtures, SVI, or Bayesian methods instead.

### 4.4 Extrapolating parametric fits past the last traded strike without asymptotic control

**Symptom.** Extracted moments (variance, skew, kurtosis) explode as you push the extrapolation range wider; expected shortfall estimates change by 20% depending on where you truncate.

**Mechanism.** Tail probabilities dominate risk-neutral moments — the third and fourth moments in particular are dominated by $|x-F|^k q(x)$ integrated over $|x-F|$ large. Where the traded chain ends, some *default* tail behaviour takes over. Flat-IV extrapolation implies infinite moments (Lee bound). Cubic-spline extrapolation is completely uncontrolled. SVI's linear-in-$|k|$ wing is heavy but finite.

**Fix.** Attach explicit tails from a well-behaved family (Figlewski 2010's GEV, or Ait-Sahalia–Duarte-style Pareto tails, or Bahra-style lognormal tails). Match at the last traded strike to first-derivative continuity (density and its slope).

### 4.5 Bid-ask midpoint as "the price" without microstructure adjustment

**Symptom.** Consistent bias in extracted density across days; density skew tracks bid-ask spread rather than actual market view.

**Mechanism.** Market-maker inventory imbalances, one-way flow, and quote-lag mean that the midpoint is not always the fair value. Options in the far wings sometimes have quotes that haven't updated in seconds while the front moved; the midpoint of a stale quote is not fair.

**Fix.** (a) Filter for stale quotes (drop any option whose quote age exceeds a threshold). (b) Use weighted-midpoint where the weight comes from bid/ask depth (if available). (c) In Bayesian fits, model per-strike observation noise as proportional to bid-ask spread rather than as a global constant. See Christoffersen–Jacobs (2004) on the microstructure-corrected pricing of index options.

### 4.6 Time-independent (single-slice) surfaces

**Symptom.** Densities at adjacent expiries produce calendar-arbitrage butterflies — you could buy a short-dated OTM butterfly and finance it by selling a longer-dated OTM butterfly at the same strike for a profit.

**Mechanism.** Each slice is fit independently; nothing enforces $\partial_\tau w(k,\tau) \ge 0$.

**Fix.** Fit a surface, not slices. SSVI (2.2.3) is the cleanest solution. Alternatively, fit slice-by-slice with an SVI parameterization and then post-hoc smooth the parameter trajectories in $\tau$ subject to the calendar-arb constraint (Fengler 2009 hybrid).

### 4.7 Confusing RND with physical density

**Symptom.** "The market is pricing a 30% chance of $80 oil by December" — quoted without qualification. Traders take positions based on this as though the market were forecasting under $\mathbb{P}$.

**Mechanism.** Sec 1.5. $q$ and $p$ differ by the pricing kernel; on equity index options $q$'s left tail is systematically fatter than $p$'s due to the crash-risk premium; on commodities the wedge is sign-dependent on aggregate hedging demand.

**Fix.** Either (a) state the risk-premium assumption explicitly and back it out from historical realized-vs-implied comparisons, or (b) restrict claims to $q$-language ("the risk-neutral probability of $F_T \ge 80$"), or (c) use a proper physical-density model (e.g., a GARCH model on the underlying) as an independent object rather than trying to derive $p$ from $q$.

### 4.8 Options-on-future RND treated as options-on-spot RND

**Symptom.** The extracted density mean systematically deviates from the traded futures print by a nearly-constant multiplicative factor.

**Mechanism.** Treating $F_t = S_t$ in the Black-76 formula, effectively using spot Black-Scholes with $r=0$ and reading the density off $C''$. The mean comes out as $S_t$, not $F_t$; on commodities with strong contango or backwardation the two differ by 5–20% for a 3-month expiry.

**Fix.** Use Black-76 with the correct forward for the specific option's underlying (Sec 3.5).

### 4.9 Externally-sourced forward — the fedarb-style bug

**Symptom.** Bracket probabilities computed against Kalshi consistently show a systematic wedge with the same sign across brackets; the wedge disappears when you re-fit the forward from parity.

**Mechanism.** The external forward source (a printed futures level, an OTC broker quote, an external analytics feed) is stale, off-time, or refers to a different contract. Because the same wrong forward is used for every strike, *every* bracket probability shifts in the same direction, mimicking a systematic wedge that a naive strategy will trade against — and get filled adversely.

**Fix.** Sec 3.5 — always fit forward from parity in the same snapshot as the IVs.

### 4.10 Roll-boundary contamination

**Symptom.** Time series of extracted vol or density skew shows a discontinuity that isn't in the market — the underlying just rolled from front to next contract.

**Mechanism.** Continuous-futures series (roll-adjusted) don't preserve level; roll-unadjusted series preserve level but jump. Neither is what you want inside a single RND fit.

**Fix.** Never mix contracts in one fit; always identify the specific underlying futures contract that each option references and use *that* contract's front price as $F_t$.

### 4.11 Using implied vol computed with a wrong reference rate

**Symptom.** Small but persistent bias in the forward; put-call parity slope regression comes out slightly off $-e^{-r\tau}$.

**Mechanism.** Options on futures require *some* discount factor for the option premium, and the correct rate is the funding rate for the option premium (typically Fed Funds OIS, or SOFR, on the relevant tenor). Using Treasury yields or LIBOR (RIP) introduces small biases.

**Fix.** SOFR-OIS bootstrap for the relevant tenor. On short tenors the practical difference is small (basis points), but downstream calibration of an entire pipeline can accumulate.

### 4.12 Not accounting for early exercise (when applicable)

On NYMEX crude, the standard options are American-style with early exercise. The Black-76 formula is European; using it on American quotes without adjustment injects the early-exercise premium into the extracted density.

**Fix.** Either (a) restrict to options with negligible early-exercise premium (deep OTM), (b) use an American-to-European de-Americanization (Barone-Adesi–Whaley quadratic approximation, or a proper CRR binomial de-Am), or (c) use a *strictly* European option chain (e.g., WTI has both LO — American — and WBW — European weekly — series; use the European when available). NightKing's use of Databento is likely fine because most listed futures options with liquid Kalshi analogues are Europe-adjacent, but this is a nontrivial gotcha for CL specifically.

### 4.13 Ignoring settlement conventions and quote timing

**Symptom.** Density on the settlement snapshot looks fine; density on intraday snapshots is noisier for reasons that don't correspond to actual market moves.

**Mechanism.** Options and futures settle at slightly different closing times; using a 4:00pm option snapshot with a 4:15pm futures print introduces a 15-minute mismatch. Same problem intraday if quotes are asynchronous.

**Fix.** Timestamp-align. For settlement work, use exchange-published settlement prices for both options and futures. For intraday, use the tightest simultaneous snapshot achievable.

---

## 5. Computational recipes

Executable pseudocode for three methods that cover the practitioner spectrum: SVI (parametric-in-IV, standard workhorse), mixture of lognormals (parametric-in-density, central-bank standard, robust when smiles are simple), and Bayesian log-density spline (Section 2.4.2, the NightKing family). Each recipe includes objective, constraints, diagnostics, and rough compute cost.

Syntax is Python-flavoured pseudocode. Where a real Python name exists (`scipy.optimize.minimize`, `cvxpy`), I use it. Real implementations should be built around `pandas` for chain manipulation and `numpy`/`scipy` for optimization; `PyMC` or `NumPyro` for the Bayesian variant.

### 5.0 Common pre-processing (do this once, feed all recipes)

```python
# INPUT: raw option chain from Databento or CME EOS
#        columns: [timestamp, expiry, K, side, bid, ask, oi, vol]
#        futures snapshot for the same expiry's underlying contract

def preprocess(chain, futures_snapshot, r):
    # 0. Timestamp-align
    t0 = pd.Timestamp.now(tz='UTC')  # or snapshot time
    tau = (chain.expiry - t0) / np.timedelta64(1, 'Y')
    df = chain.assign(tau=tau)

    # 1. Sanity filters
    df = df[df.ask > df.bid > 0]                    # positive spread
    df = df[df.ask - df.bid < 0.5*df.ask]           # spread < 50% of ask
    df = df[(df.oi > 0) | (df.vol > 0)]             # nonzero interest
    df['mid'] = 0.5*(df.bid + df.ask)
    df['spread'] = df.ask - df.bid

    # 2. Implied forward via parity regression across strikes where both C and P exist
    #    C(K) - P(K) = e^{-r*tau} (F - K)
    both = df.pivot_table(index='K', columns='side', values='mid').dropna()
    y = both['C'] - both['P']
    X = np.column_stack([np.ones(len(both)), -both.index])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    # beta[0] = e^{-r*tau} * F, beta[1] = e^{-r*tau}
    disc = beta[1]           # implied discount factor
    F_implied = beta[0] / disc
    r_implied = -np.log(disc) / tau.iloc[0]  # sanity: should match r

    # 3. OTM-only selection
    df['is_otm'] = ((df.side == 'C') & (df.K >= F_implied)) | \
                   ((df.side == 'P') & (df.K <  F_implied))
    df = df[df.is_otm]

    # 4. Black-76 implied volatilities
    df['iv'] = df.apply(lambda row: black76_iv(row.mid, F_implied, row.K, tau.iloc[0],
                                              r, row.side), axis=1)
    df['vega'] = black76_vega(F_implied, df.K, tau.iloc[0], r, df.iv)
    df['log_moneyness'] = np.log(df.K / F_implied)
    df['total_var'] = df.iv**2 * tau.iloc[0]

    return df, F_implied, tau.iloc[0], r_implied
```

**Cost.** ~milliseconds per chain (100–1000 strikes).

**Diagnostics returned.** `F_implied`, `r_implied` (should track your input $r$ within a few basis points), post-filter count of usable strikes (should be $\ge 8$ for stable fits).

### 5.1 SVI-based extraction end-to-end

**Objective.**
$$\min_{a,b,\rho,m,\sigma} \sum_i \text{vega}_i^2\,\bigl(\sigma_{\text{SVI}}(k_i;a,b,\rho,m,\sigma) - \sigma_{\text{mkt},i}\bigr)^2$$
subject to
$$b \ge 0,\quad |\rho| \le 1,\quad \sigma > 0,\quad a + b\sigma\sqrt{1-\rho^2} \ge 0$$
(the last enforces $w(k) \ge 0$ everywhere) plus butterfly non-negativity checked via Gatheral's $g(k)$.

**Recipe.**

```python
import numpy as np
from scipy.optimize import minimize, differential_evolution

def svi_total_variance(k, a, b, rho, m, sigma):
    return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))

def svi_iv(k, tau, params):
    a, b, rho, m, sigma = params
    w = svi_total_variance(k, a, b, rho, m, sigma)
    return np.sqrt(np.maximum(w, 1e-8) / tau)

def fit_svi(df, tau):
    """
    df: preprocessed chain (from 5.0), columns [log_moneyness, iv, vega, total_var]
    tau: time to expiry (years)
    """
    k = df.log_moneyness.values
    w_mkt = df.total_var.values
    vega = df.vega.values
    weights = vega ** 2

    def loss(params):
        a, b, rho, m, sigma = params
        w_model = svi_total_variance(k, a, b, rho, m, sigma)
        return np.sum(weights * (w_model - w_mkt) ** 2)

    # ---- Zeliade quasi-explicit inner solve for (a, b, rho) given (m, sigma) ----
    def inner_solve(m, sigma):
        # For fixed (m, sigma), w is linear in {a, d = b*rho, c = b}:
        # w = a + d*(k-m) + c*sqrt((k-m)^2 + sigma^2)
        y = k - m
        z = np.sqrt(y**2 + sigma**2)
        X = np.column_stack([np.ones_like(k), y, z])
        # Weighted linear least squares with box constraints on the transformed params.
        # Solved via cvxpy or scipy.optimize.lsq_linear.
        result = lsq_linear(np.sqrt(weights)[:, None] * X,
                            np.sqrt(weights) * w_mkt,
                            bounds=([-np.inf, -np.inf, 0], [np.inf, np.inf, np.inf]))
        a_, d, c = result.x
        b_ = c
        rho_ = d / c if c > 1e-10 else 0.0
        rho_ = np.clip(rho_, -0.999, 0.999)
        return a_, b_, rho_, result.cost

    # Outer 2D search over (m, sigma)
    bounds = [(k.min() - 0.5, k.max() + 0.5), (1e-3, 2.0)]
    outer = differential_evolution(
        lambda x: inner_solve(*x)[3],
        bounds, tol=1e-8, seed=42, workers=-1)
    m_hat, sigma_hat = outer.x
    a_hat, b_hat, rho_hat, _ = inner_solve(m_hat, sigma_hat)

    params = (a_hat, b_hat, rho_hat, m_hat, sigma_hat)
    return params

def gatheral_g(k, params, tau):
    """Butterfly check. Must be non-negative for every k in the traded range."""
    a, b, rho, m, sigma = params
    y = k - m
    z = np.sqrt(y**2 + sigma**2)
    w = svi_total_variance(k, *params)
    dw = b * (rho + y / z)
    d2w = b * sigma**2 / z**3
    term1 = (1 - k*dw/(2*w))**2
    term2 = (dw**2 / 4) * (1/w + 1/4)
    return term1 - term2 + d2w / 2

def extract_rnd_from_svi(params, tau, F, r, k_grid=None):
    if k_grid is None:
        k_grid = np.linspace(-3.0, 3.0, 5001)  # ±3 log-moneyness, fine grid
    K = F * np.exp(k_grid)
    iv = svi_iv(k_grid, tau, params)
    # Black-76 call price at each strike
    C = black76_call(F, K, tau, r, iv)
    # Central-difference 2nd derivative on the fine (uniform in K? or in k?) grid
    # SAFER: work in K space with a uniform grid to keep FD analysis simple
    K_uniform = np.linspace(F*np.exp(-2.5), F*np.exp(2.5), 5001)
    iv_u = svi_iv(np.log(K_uniform/F), tau, params)
    C_u = black76_call(F, K_uniform, tau, r, iv_u)
    dK = K_uniform[1] - K_uniform[0]
    q = np.exp(r*tau) * (C_u[:-2] - 2*C_u[1:-1] + C_u[2:]) / dK**2
    return K_uniform[1:-1], q
```

**Diagnostics.**

1. In-sample IV RMSE. Compute `svi_iv(df.log_moneyness, tau, params)` and compare to `df.iv`. Should be < 0.5–1.0% for standard smiles.
2. Butterfly: `g = gatheral_g(k_grid, params, tau)`; assert `g.min() >= -1e-6`.
3. Density integrates to 1: `q.sum() * dK`.
4. Density mean equals F: `(K_uniform[1:-1] * q).sum() * dK`.

**Cost.** Zeliade quasi-explicit fit: ~10 ms per slice on modern CPU (dominated by the outer 2D differential evolution; can drop to <1 ms with a good warm start). Density extraction: ~1 ms on a 5000-point grid.

**Watchouts.**
- `differential_evolution` is a safe default but slow. In production, cache previous $(m,\sigma)$ and use L-BFGS-B from a warm start; fall back to DE only when the warm-started fit misses tolerance.
- Numerical instability if $\sigma \to 0$ (the SVI cusp) — keep the lower bound at $10^{-3}$.
- Tail extrapolation past $|k| > 2.5$ is on you; the linear-wing behaviour of SVI implies finite moments up to $p_R = 1/(2\psi_R)(1+\psi_R/2)^2$ where $\psi_R = b(1+\rho)$. If your strategy computes ES(0.01), verify tail parameters imply finite 4th moment (or attach GEV tails).

### 5.2 Mixture of lognormals

**Model.**
$$q(x) = \sum_{i=1}^k \pi_i \,\text{LN}(x; \mu_i, s_i^2), \qquad \sum \pi_i = 1,\ \pi_i \ge 0.$$
Call price:
$$C(K) = e^{-r\tau}\sum_{i=1}^k \pi_i \bigl[F_i\Phi(d_{1,i}) - K\Phi(d_{2,i})\bigr],$$
$F_i = e^{\mu_i + s_i^2/2}$, $d_{1,i} = \bigl(\log(F_i/K) + s_i^2/2\bigr)/s_i$, $d_{2,i} = d_{1,i} - s_i$.

**Constraints.**
- Martingality: $\sum \pi_i F_i = F_t$.
- Simplex: $\pi_i \ge 0$, $\sum\pi_i = 1$.
- Positivity: $s_i > 0$.

**Recipe.**

```python
from scipy.optimize import minimize
from scipy.stats import lognorm

def ln_call(F, K, tau, r, sigma):
    # Black-76 with underlying = F
    d1 = (np.log(F/K) + 0.5*sigma**2*tau) / (sigma*np.sqrt(tau))
    d2 = d1 - sigma*np.sqrt(tau)
    return np.exp(-r*tau) * (F * norm.cdf(d1) - K * norm.cdf(d2))

def mixture_call(K, tau, r, F, pi, mu, s):
    # pi, mu, s are k-vectors
    Fi = np.exp(mu + 0.5*s**2)
    # martingale check: sum(pi * Fi) should equal F; enforce via constraint
    C = np.zeros_like(K)
    for i in range(len(pi)):
        C += pi[i] * ln_call(Fi[i], K, tau, r, s[i]/np.sqrt(tau))
    return C

def fit_mixture(df, F, tau, r, k=3, n_starts=25):
    K = df.K.values
    C_mkt = df.mid.values * (df.side == 'C') + \
            (df.mid.values + np.exp(-r*tau)*(F - df.K.values)) * (df.side == 'P')
    vega = df.vega.values
    weights = 1.0 / (vega + 1e-6)  # equal-in-IV-space weighting

    def unpack(x):
        pi_raw = x[0:k]; mu = x[k:2*k]; s = x[2*k:3*k]
        pi = np.exp(pi_raw); pi /= pi.sum()  # simplex reparam
        return pi, mu, np.abs(s) + 1e-3

    def loss(x):
        pi, mu, s = unpack(x)
        Fi = np.exp(mu + 0.5*s**2)
        # Soft martingale penalty (or enforce via constraint below)
        mart_pen = 1e4 * (np.sum(pi * Fi) - F)**2
        C_model = mixture_call(K, tau, r, F, pi, mu, s)
        return np.sum(weights * (C_model - C_mkt)**2) + mart_pen

    # Multistart
    best = None
    for seed in range(n_starts):
        rng = np.random.default_rng(seed)
        # Initialize: k components spread around log(F), with s ~ ATM IV * sqrt(tau)
        iv_atm = df.iv[np.argmin(np.abs(df.log_moneyness))]
        x0 = np.concatenate([
            rng.standard_normal(k),
            np.log(F) + rng.standard_normal(k) * iv_atm * np.sqrt(tau) * 0.3,
            np.abs(iv_atm * np.sqrt(tau) + rng.standard_normal(k) * 0.05)
        ])
        result = minimize(loss, x0, method='L-BFGS-B',
                          options=dict(maxiter=500, ftol=1e-10))
        if best is None or result.fun < best.fun:
            best = result
    return unpack(best.x)

def mixture_rnd(pi, mu, s, x_grid):
    q = np.zeros_like(x_grid)
    for i in range(len(pi)):
        q += pi[i] * lognorm(s=s[i], scale=np.exp(mu[i])).pdf(x_grid)
    return q
```

**Diagnostics.**

1. Martingale: $|\sum \pi_i F_i - F_t| < 10^{-3} F_t$.
2. In-sample IV RMSE: implied vols back out from mixture prices; compare to market IVs.
3. Density integrates to 1 (automatic if pi sums to 1 and each LN is normalized).
4. Non-degenerate: check no $\pi_i < 10^{-4}$ (component collapse to zero mass) and no $s_i < 10^{-3}$ (component collapse to a spike). Cooper (1999) discusses these failure modes.

**Cost.** L-BFGS-B on $3k$ parameters is fast (~5 ms per start); 25 starts $\to$ ~150 ms. Real production uses fewer starts once a warm cache is in place.

**Watchouts.**
- Extremely sensitive to starting values with $k=2$ and worse with $k=3$. Multistart is not optional.
- The soft martingale penalty coefficient (`1e4` above) is scale-dependent; if $F \sim 80$ (crude) it's fine, but for very different asset scales adjust so the penalty matches typical squared-price residuals.
- Cooper (1999) documents "spike" pathologies where one $s_i \to 0$. Enforce $s_i > s_{\min}$ explicitly if this recurs.
- Consider parametric parity conversion: convert put mids to call-equivalents via parity *before* fitting to avoid asymmetric side-of-the-book bias.

### 5.3 Bayesian log-density spline (NightKing-style)

**Model.**
Represent the log-density on a bounded interval $[x_{\min}, x_{\max}]$ (chosen wide, e.g., $F/4$ to $4F$) as a cubic B-spline expansion with $M$ knots:
$$\log q(x) = \sum_{j=1}^{M} \beta_j\, B_j(x) - \log Z(\beta),$$
where $Z(\beta) = \int e^{\sum \beta_j B_j(x)}\,dx$ is the normalizing constant. Exponentiate: $q(x) = e^{\sum \beta_j B_j(x)}/Z(\beta)$. Non-negativity is automatic.

**Priors.**
- Curvature penalty on $\log q$: $\beta \sim \mathcal N(0, (\lambda D_2^\top D_2)^{-1})$ where $D_2$ is the second-difference matrix on the spline coefficients (a P-spline penalty, Eilers & Marx 1996).
- Hyperprior: $\lambda \sim \text{Gamma}(a_\lambda, b_\lambda)$ (uninformative, $a_\lambda = b_\lambda = 10^{-3}$).
- Optionally: prior on $\beta$ centered on a lognormal (encodes "the density is close to Black-76 unless the data say otherwise").

**Likelihood.**
For each observed OTM option with mid $y_i$ and side $s_i$ struck at $K_i$:
$$y_i = e^{-r\tau} \int \text{payoff}_{s_i}(x, K_i)\, q(x; \beta)\, dx + \epsilon_i,$$
with $\epsilon_i \sim \mathcal N(0, \sigma_i^2)$ and $\sigma_i$ proportional to bid-ask spread or to $1/\text{vega}_i$ (equivalent in IV-space).

**Constraints.**
- Martingale: $\int x q(x;\beta)\,dx = F_t$. Enforce via a Lagrange multiplier $\mu_F$ added to the log-posterior, or hard-project onto the constraint manifold via SLSQP.
- Normalization: automatic through $Z(\beta)$.

**Posterior.**
$$\log p(\beta, \lambda \mid \text{data}) = -\sum_i \frac{(y_i - \hat y_i(\beta))^2}{2\sigma_i^2} - \frac{\lambda}{2}\beta^\top D_2^\top D_2 \beta + \log p(\lambda) - \mu_F\bigl(\int x q\,dx - F_t\bigr)^2 + \text{const}.$$

**Recipe.**

```python
import numpy as np
import pymc as pm
from scipy.interpolate import BSpline
from scipy.integrate import simpson

def build_bspline_basis(x_grid, n_knots=25, degree=3):
    knots_int = np.quantile(x_grid, np.linspace(0, 1, n_knots))
    # Extend for cubic B-spline boundary
    knots = np.concatenate([
        np.full(degree, knots_int[0]),
        knots_int,
        np.full(degree, knots_int[-1]),
    ])
    n_basis = len(knots) - degree - 1
    B = np.zeros((len(x_grid), n_basis))
    for j in range(n_basis):
        c = np.zeros(n_basis); c[j] = 1.0
        spl = BSpline(knots, c, degree)
        B[:, j] = spl(x_grid)
    return B, knots, degree

def payoff_matrix(x_grid, K, side, tau, r):
    """For each option i, returns e^{-r*tau} * payoff_i(x) for all x_grid."""
    n_x, n_opt = len(x_grid), len(K)
    P = np.zeros((n_opt, n_x))
    for i in range(n_opt):
        if side[i] == 'C':
            P[i] = np.exp(-r*tau) * np.maximum(x_grid - K[i], 0)
        else:
            P[i] = np.exp(-r*tau) * np.maximum(K[i] - x_grid, 0)
    return P

def fit_bayes_spline(df, F, tau, r, n_knots=25, n_samples=2000):
    K = df.K.values; side = df.side.values
    y = df.mid.values
    # Observation std: proportional to spread / vega (roughly one IV point at ATM)
    sigma_obs = np.maximum(df.spread.values / 2, 1e-3 * df.vega.values)

    # Grid: from F/4 to 4F, 800 points
    x_grid = np.linspace(F/4, 4*F, 800)
    dx = x_grid[1] - x_grid[0]
    B, knots, degree = build_bspline_basis(x_grid, n_knots=n_knots)
    n_basis = B.shape[1]
    P = payoff_matrix(x_grid, K, side, tau, r)

    # Second-difference penalty matrix (P-spline)
    D2 = np.diff(np.eye(n_basis), n=2, axis=0)
    Pen = D2.T @ D2  # (n_basis, n_basis) positive semidefinite

    with pm.Model() as model:
        lam = pm.Gamma('lambda', alpha=1e-3, beta=1e-3)
        # zero-mean multivariate normal on beta with precision lam * Pen
        # Use a small ridge (1e-6 * I) to make the precision matrix full rank
        beta = pm.MvNormal('beta', mu=np.zeros(n_basis),
                           tau=lam*Pen + 1e-6*np.eye(n_basis),
                           shape=n_basis)
        # Density on the grid
        log_q_unnorm = pm.math.dot(B, beta)
        q = pm.math.exp(log_q_unnorm - pm.math.logsumexp(log_q_unnorm)) / dx
        # Predicted option prices
        pred = pm.math.dot(P, q) * dx
        # Martingale constraint via soft penalty
        mart = pm.math.sum(x_grid * q) * dx - F
        pm.Potential('mart_penalty', -0.5 * (mart / (1e-3*F))**2)
        # Likelihood
        pm.Normal('y_obs', mu=pred, sigma=sigma_obs, observed=y)

        trace = pm.sample(n_samples, tune=1500, target_accept=0.95,
                          chains=4, cores=4, return_inferencedata=True)

    return trace, x_grid, B, dx

def posterior_bracket_probability(trace, x_grid, B, dx, a, b):
    beta_samples = trace.posterior['beta'].stack(draws=('chain','draw')).values  # (n_basis, n_samples)
    log_q_unnorm = B @ beta_samples                                              # (n_x, n_samples)
    q_samples = np.exp(log_q_unnorm - np.log(np.sum(np.exp(log_q_unnorm),
                                                    axis=0, keepdims=True))) / dx
    mask = (x_grid >= a) & (x_grid <= b)
    prob_samples = np.sum(q_samples[mask, :], axis=0) * dx   # (n_samples,)
    return prob_samples  # posterior distribution of P([a, b])
```

**Diagnostics.**

1. HMC diagnostics: `arviz.summary(trace)`; look for $\hat R < 1.01$, ESS $\ge 400$ per chain. Divergences $\to$ increase `target_accept`, tighten priors, or restart with better initialization.
2. Posterior mean density integrates to 1: (auto by construction).
3. Posterior mean of $\int x q\,dx$ tracks $F$ within tolerance (auto if the martingale penalty is respected; check the posterior of `mart`).
4. In-sample IV RMSE: compute posterior-predictive prices from `trace.posterior_predictive`, convert to IVs, RMSE vs. market.
5. Prior-posterior comparison: fit with the option-data likelihood turned off; the prior alone should look reasonable (uninformative-flat if the prior is uninformative).

**Cost.** HMC on a 25-basis + 1-hyperparam model with 4 chains × 2000 samples: 30–90 seconds per snapshot on a modern CPU. Faster with `NumPyro` + JAX (GPU). For real-time work, a Laplace approximation around the MAP (via `scipy.optimize.minimize` on the log-posterior + numerical Hessian) gets a Gaussian posterior in ~1 second at the cost of true tail uncertainty.

**Watchouts.**
- The soft martingale penalty coefficient (`1e-3*F` above) trades off constraint enforcement vs. data-fit tension. Too tight and the sampler struggles; too loose and the constraint is nominal.
- Choice of $n_{\text{knots}}$: too few $\to$ oversmoothing; too many $\to$ curvature penalty does all the work. Cross-validate: hold out 10% of strikes, refit, measure held-out MSE across $n_{\text{knots}} \in \{15, 20, 25, 30, 40\}$.
- Boundary knots: place at $F/4$ and $4F$ (wide enough to capture the tail behaviour for typical commodity RNDs) but check that the density is essentially zero at the boundaries. If not, extend.
- Log-scale grid: for very fat-tailed densities, use `x_grid = F * np.exp(np.linspace(-3, 3, 800))` and integrate with $q(x)\,dx$ = $\tilde q(k)\,dk$ where $\tilde q(k) = q(F e^k) \cdot F e^k$.
- Prior mean can be centered on a lognormal (i.e., $\log q_0(x) = -\log(x s\sqrt{2\pi}) - (\log x - \mu)^2/(2s^2)$ with $s = \sigma_{\text{ATM}}\sqrt\tau$, $\mu = \log F - s^2/2$). This grafts Black-76 as the null and the option data as evidence. In pymc: `beta_0 = np.linalg.pinv(B) @ log_q0_grid`, `beta ~ MvNormal(mu=beta_0, tau=lam*Pen)`.
- Downstream: `posterior_bracket_probability` returns a *distribution* over $P([a,b])$; use its 5th and 95th percentiles for confidence bands, and the median as the point estimate. Never ship the mean of the point densities — that averages out tail dispersion.

### 5.4 Which recipe to use when

| Chain size | Recommended method | Rationale |
|---|---|---|
| $<8$ liquid OTM strikes | Mixture of 2 lognormals | Not enough data for anything richer |
| 8–25 strikes | SVI | Sweet spot; 5 params, well-conditioned |
| $>25$ strikes | SVI + Bayesian spline | SVI as anchor / prior mean, Bayesian for uncertainty |
| Full surface, many expiries | SSVI + optional per-slice Bayesian | Calendar arb-free surface |
| Full academic / policy report | Bayesian spline + Fengler for comparison | Uncertainty quantification is central |

### 5.5 A note on tail attachment

All four recipes (SVI, mixture, Bayesian, non-parametric) produce densities on the *traded* strike range. For any moment or bracket probability that depends materially on the tail, attach explicit tails:

- **Generalized Pareto (Figlewski 2010, Ait-Sahalia–Duarte 2003).** Fit GPD to the last 5–10% of quotes with continuity of $q$ and $q'$ at the attachment point. Guarantees finite $p$-th moment if shape parameter $\xi < 1/p$.
- **Lognormal tails (Bahra 1997).** Simpler; match density and slope at attachment.
- **Power law.** Explicit control of tail-index.

Rule of thumb: if $\int_0^{K_{\min}} q + \int_{K_{\max}}^\infty q > 0.02$, tails matter and you must attach.

---

## 6. From RND to trading — the bridge

The RND $q$ is the intermediate object; the trading signal is derived from it. There are three canonical downstream uses: (a) comparing $q$ to the physical density $p$ (the risk-premium literature), (b) comparing $q$ to prediction-market implied probabilities (NightKing's exact game), and (c) mapping $q$ into an explicit hedged position via option-portfolio replication. This section maps each and calls out the statistical-inference machinery that makes the results trustworthy.

### 6.1 RND vs physical density: the risk-premium debate

The fundamental theorem of asset pricing says $q$ and $p$ are related by the pricing kernel $m$:
$$q(x) = p(x)\cdot m(x)\cdot e^{r\tau},$$
with $m$ the state-price-per-unit-probability, or equivalently, the marginal-utility ratio $u'(x)/u'(c_0)$ under a representative-agent economy. Rosenberg & Engle (2002) estimate $m$ semi-parametrically for the S&P 500 and find it (a) monotone decreasing in wealth (as expected), (b) time-varying, and (c) implying reasonable levels of risk aversion once combined with GARCH-forecasted $p$. Bliss & Panigirtzoglou (2004) do the same across FTSE and S&P and confirm the pattern. Jackwerth (2000) famously found that post-'87 the pricing kernel is *non-monotone* — the "pricing-kernel puzzle" — which subsequent literature has tried variously to explain (heterogeneous beliefs, ambiguity aversion, or estimation artifacts from finite samples).

On commodities the analogous work is thinner but growing:

- **Hamilton & Wu (2014)** "Risk Premia in Crude Oil Futures Prices": document a positive risk premium in oil futures at intermediate horizons, likely reflecting hedging demand from producers and airlines. Implies $q$'s mean is *below* the physical expectation of $F_T$.
- **Christoffersen–Jacobs–Mimouni (2010)** on option-pricing model comparison in energy.
- **BoE Quarterly Bulletin RND boxes** (various years) publish option-implied densities for commodities as regular monetary-policy diagnostics.

**Operational implication for NightKing.** If you extract $q$ from CL options and Kalshi is publishing $p$-style bracket probabilities, then even in a perfectly efficient market $q \ne p$; the wedge is the oil-market risk premium. Trading the wedge without a hedge means taking a directional bet on that risk premium (which, for oil, is likely to work in one direction on average and cost you in a shock). Two responses:

1. **Estimate the wedge and remove it.** Use a historical regression of realized $F_T$ vs. the ex-ante RND mean to estimate a level of risk premium; adjust the density before comparing to Kalshi. This is a Rosenberg–Engle-style calibration.
2. **Hedge it out.** Build a position that is $\Delta$-neutral in the futures itself: buying an option-package that pays if $F_T \in [a,b]$ and shorting the corresponding Kalshi bracket while trading a futures overlay to zero net directional exposure. This isolates the *disagreement between RND and Kalshi conditional on the terminal bucket*, not the directional risk premium.

Option (2) is much cleaner in principle but requires two things: (i) sensible bid-ask economics on all three legs (option package, Kalshi contract, futures hedge), and (ii) understanding that even after the delta hedge, you have residual gamma and vega exposure to the path, plus Kalshi's discrete-tick microstructure.

### 6.2 RND vs prediction-market brackets

Kalshi trades bracket contracts of the form "WTI settles in $[a,b]$ at expiry" with prices $\text{K}(a,b) \in [0,1]$ that at settlement pay $1$ if the outcome falls in the bucket, $0$ otherwise. If we take Kalshi prices at face value as probabilities (they're not, exactly — they embed liquidity, funding cost, and Kalshi's own take rate), then the extraction is:
$$\hat P^{\text{Kalshi}}([a,b]) = \frac{\text{K}(a,b)}{\sum_j \text{K}(\text{bucket}_j)}$$
(re-normalizing so the total probability sums to 1; the raw Kalshi bracket prices typically sum to slightly more than 1 due to house margin, giving a first-order picture of the take).

The RND-based prediction from Section 5:
$$\hat P^{\text{RND}}([a,b]) = \int_a^b \hat q(x)\,dx.$$

The naive strategy: buy Kalshi's bracket when $\hat P^{\text{Kalshi}} < \hat P^{\text{RND}} - \varepsilon$, sell when it's the other way; hedge with a corresponding option package to zero out delta.

What can go wrong:

1. **Risk premium wedge, Section 6.1.** Systematic bias in one direction that trades against you if unhedged.
2. **Favorite–longshot bias in Kalshi.** Empirically observed in horse-racing markets (Thaler–Ziemba 1988; Snowberg–Wolfers 2010); if Kalshi bracket prices at the wings are systematically overpriced (as a fraction of true $p$), you'll systematically "sell" mid-buckets and "buy" wing-buckets, which loses to the bias.
3. **RND uncertainty.** Your $\hat q$ has posterior variance; the point estimate of $\hat P^{\text{RND}}$ is itself uncertain. If the posterior 5–95% band overlaps $\hat P^{\text{Kalshi}}$, there is no statistically significant wedge. Trading anyway is trading noise.
4. **Timestamp mismatch.** Kalshi tick times $\ne$ option chain snapshot times $\ne$ futures snapshot times. On fast-moving days the wedge you're seeing is stale-quote artifact, not real disagreement.

### 6.3 Statistical significance of density-vs-market gaps

Two classes of tests are relevant.

**Coverage / calibration tests.** Given a sequence of realized $F_T$'s (over many expiries) and the corresponding ex-ante RNDs, is the RND well-calibrated? Two canonical machinery:

- **Berkowitz (2001) test.** For each realized $F_T^{(t)}$, compute the probability integral transform (PIT) $u_t = \hat F_{q_t}(F_T^{(t)})$ (evaluate ex-ante CDF at the ex-post realization). Under correct calibration, $\{u_t\}$ should be IID Uniform(0,1). Apply the inverse normal to get $z_t = \Phi^{-1}(u_t) \sim \mathcal N(0,1)$ IID. Berkowitz's test uses a likelihood-ratio test on an AR(1) with drift for the $z$'s; if it rejects, calibration is bad.
- **Christoffersen (1998) interval coverage.** For each realized $F_T^{(t)}$, record whether it lands in the ex-ante $\alpha$-tile bucket. Over many trials the empirical frequency should equal $\alpha$; Christoffersen's test provides an LR for this.

Apply these separately to the RND vs. to the Kalshi-implied density; both should pass if both are well-calibrated. If only one passes, you have a defensible "which side is right" narrative.

**Density-comparison tests.** For a snapshot, is $\hat q - \hat P^{\text{Kalshi}}$ statistically significantly non-zero? Under the Bayesian setup of §5.3, this is directly computable:
$$\text{p-value} = 2\min\!\bigl(\Pr[\hat q > \hat P^{\text{Kalshi}}], \Pr[\hat q < \hat P^{\text{Kalshi}}]\bigr),$$
where the probabilities are over the posterior draws of $\hat q$'s bracket probability. If the p-value is $> 0.10$ for a given bucket, don't trade that bucket.

**Multiple-testing correction.** With, say, 20 brackets on WTI, running each test independently at 5% p yields an expected 1 false discovery per snapshot. Apply Benjamini–Hochberg FDR at 10% or Bonferroni for stricter control. This is not optional: the difference between "we found a wedge" and "we ran 20 tests until one hit" is FDR discipline.

### 6.4 Trading structures

Given a bracket-level wedge, the concrete option-side trade is a *butterfly*, *condor*, or *digital*. Under Breeden–Litzenberger the mapping is exact:

- **Butterfly** with strikes $\{K-\Delta, K, K+\Delta\}$ has payoff $\max(\Delta - |F_T - K|, 0)/\Delta$; price $\approx q(K)\cdot \Delta$ for small $\Delta$. As $\Delta \to 0$ this approaches the (scaled) density at $K$; for finite $\Delta$, it is (approximately) $\int_{K-\Delta}^{K+\Delta} q(x)\bigl(1 - |x-K|/\Delta\bigr)\,dx$ — a triangular kernel average. Not literally a bracket probability, but close if $\Delta$ is small.

- **Iron condor** with strikes $\{K_1, K_2, K_3, K_4\}$ (short a strangle, long a wider strangle): payoff is $\propto \min(K_2 - K_1, F_T - K_1, K_4 - F_T, K_4 - K_3)^+$. Approximates a rectangular payoff in the $[K_2, K_3]$ range.

- **Digital call replication** (Bhagavatula–2002; Carr–Madan–1998 static replication). A digital call struck at $K$ pays 1 if $F_T \ge K$. Static replicating position: a long call spread $\{K, K+\Delta\}$ divided by $\Delta$. Price: $[C(K) - C(K+\Delta)]/\Delta$. As $\Delta \to 0$, price $\to -\partial C/\partial K = e^{-r\tau}\mathbb{Q}(F_T \ge K)$.

For a Kalshi bracket $[a,b]$, the *exact* option replication is a *long digital at $a$ minus long digital at $b$*, which in terms of listed options is $(C(a) - C(a+\Delta_a))/\Delta_a - (C(b) - C(b+\Delta_b))/\Delta_b$. In practice you round $a$ and $b$ to nearest listed strikes and accept the residual approximation error — the discrete-strike Breeden–Litzenberger approximation error. This can be quantified: for a smooth density, error is $O(\Delta^2)\cdot q''(K)$ at each edge.

**Delta and gamma exposure of the aggregate position.** After combining the option side and the Kalshi side (Kalshi contracts have $\Delta = 1$ within the bucket at settlement, and time-varying $\Delta$ before), you have some residual delta and gamma. Overlay futures to zero the delta at trade inception; monitor gamma-vega during the life of the position.

### 6.5 Vega and gamma risk of the density arbitrage

A subtle point: even a well-executed density arbitrage is not "riskless". The option package that replicates a bracket has

- **Vega:** positive at the bracket's center strikes (long butterfly = long vega there), negative at the wings. Net vega depends on which strikes contribute most.
- **Gamma:** butterflies are long gamma at the center strike, short outside; the aggregate gamma of a bracket replication is small but nonzero.
- **Theta:** the mirror image of gamma.

Before expiry, if IV shifts (which it will, on macro news), the option package price moves independently of the Kalshi price. If your convergence horizon is 1–2 weeks and IV can swing 5% in that window, the mark-to-market P&L is dominated by IV moves, not by the density-vs-Kalshi wedge you're supposedly trading. The trade only "realizes" at expiry, so you must be willing to hold and margin for the full life.

---

## 7. Literature map — annotated

Grouped by topic. Full URLs at the end.

### 7.1 Foundational (must-read for background)

- **Black, F. (1976).** "The Pricing of Commodity Contracts." *Journal of Financial Economics* 3(1–2), 167–179. The original Black-76 formula for options on futures. Two pages of algebra that every subsequent RND paper on commodities builds on.
- **Breeden, D. T. & Litzenberger, R. H. (1978).** "Prices of State-Contingent Claims Implicit in Option Prices." *Journal of Business* 51(4), 621–651. The seminal result: $q(K) = e^{r\tau}\partial^2 C/\partial K^2$. Everything in this document, ultimately, is a stable way to compute the RHS.
- **Ross, S. A. (1976).** "Options and Efficiency." *Quarterly Journal of Economics* 90(1), 75–89. The theoretical case for options completing the market and revealing state prices.
- **Cox, J., Ross, S. & Rubinstein, M. (1979).** Binomial trees; not directly about RND extraction but the natural discrete analogue.
- **Rubinstein, M. (1994).** "Implied Binomial Trees." *Journal of Finance* 49(3), 771–818. First serious attempt at a non-parametric RND from options: fit a tree that reproduces all option prices exactly, subject to a smoothness prior on the terminal density.
- **Jackwerth, J. C. & Rubinstein, M. (1996).** "Recovering Probability Distributions from Option Prices." *Journal of Finance* 51(5), 1611–1632. Extends 1994 with a "maximum smoothness" objective on the log-density. Documented the sharp change in RND shape post-1987 crash.
- **Aït-Sahalia, Y. & Lo, A. W. (1998).** "Nonparametric Estimation of State-Price Densities Implicit in Financial Asset Prices." *Journal of Finance* 53(2), 499–547. Kernel-smoothing approach; asymptotic theory. The academic gold standard for large-chain non-parametric estimation.
- **Bahra, B. (1997).** "Implied Risk-Neutral Probability Density Functions from Option Prices: Theory and Application." Bank of England Working Paper No. 66. The Bank of England methodology paper; introduced double-lognormal to a policy audience. Still the reference for central-bank RND practice.
- **Melick, W. R. & Thomas, C. P. (1997).** "Recovering an Asset's Implied PDF from Option Prices: An Application to Crude Oil During the Gulf Crisis." *Journal of Financial and Quantitative Analysis* 32(1), 91–115. The seminal commodities-RND paper. Three-lognormal fits on WTI options, showing bimodality developing before Desert Storm. Directly relevant to NightKing's asset class.
- **Malz, A. M. (1997).** "Estimating the Probability Distribution of the Future Exchange Rate from Option Prices." *Journal of Derivatives* 5(2), 18–36. Spline-in-IV method for FX options; Federal Reserve Bank of New York methodology.

### 7.2 Modern smile parameterizations

- **Gatheral, J. (2004).** "A Parsimonious Arbitrage-Free Implied Volatility Parameterization with Application to the Valuation of Volatility Derivatives." Presentation at Global Derivatives, Madrid. The original SVI slides. Not a formal paper but universally cited.
- **Gatheral, J. (2006).** *The Volatility Surface: A Practitioner's Guide.* Wiley. Chapter on SVI + full context of smile modeling.
- **Gatheral, J. & Jacquier, A. (2014).** "Arbitrage-free SVI Volatility Surfaces." *Quantitative Finance* 14(1), 59–71. arXiv:1204.0646. The SSVI paper. If you build a surface with any modern approach, this is the reference.
- **Roper, M. (2010).** "Arbitrage-Free Implied Volatility Surfaces." Preprint, University of Sydney. Rigorous statement of the static-arbitrage conditions on IV surfaces; complements Gatheral–Jacquier.
- **Fengler, M. R. (2009).** "Arbitrage-Free Smoothing of the Implied Volatility Surface." *Quantitative Finance* 9(4), 417–428. The shape-constrained spline approach. Practically the most useful "pull an arbitrage-free surface from a messy chain" method.
- **Lee, R. W. (2004).** "The Moment Formula for Implied Volatility at Extreme Strikes." *Mathematical Finance* 14(3), 469–480. The extremal-slope bound on implied vol. Constrains any acceptable wing extrapolation.
- **Corbetta, J., Cohen, S. & Cousin, A. (2019).** "eSSVI Model with Arbitrage-free Interpolation." arXiv:1906.03854. Extends SSVI to maturity-dependent skew.

### 7.3 Non-parametric

- **Bondarenko, O. (2003).** "Estimation of Risk-Neutral Densities Using Positive Convolution Approximation." *Journal of Econometrics* 116(1–2), 85–112. The PCA method. Non-parametric, arb-free by construction. Underrated — should be on more desks.
- **Figlewski, S. (2010).** "Estimating the Implied Risk-Neutral Density for the U.S. Market Portfolio." In *Volatility and Time Series Econometrics: Essays in Honor of Robert F. Engle* (T. Bollerslev, J. R. Russell & M. Watson eds.), Oxford University Press. Also the 2017 update "Risk Neutral Densities: A Review" (SSRN). *The* practitioner-oriented review paper. Read cover to cover. Discusses spline-in-IV + GEV tail attachment as the workhorse.
- **Monteiro, A. M., Tütüncü, R. H. & Vicente, L. N. (2008).** "Recovering Risk-Neutral Probability Density Functions from Options Prices Using Cubic Splines and Ensuring Nonnegativity." *European Journal of Operational Research* 187(2), 525–542. Cubic-spline density with QP-enforced non-negativity. NightKing's direct spiritual ancestor.
- **Rompolis, L. S. & Tzavalis, E. (2008).** "Recovering Risk Neutral Densities from Option Prices: A New Approach." *Journal of Financial and Quantitative Analysis* 43(4), 1037–1053. Orthogonal-polynomial expansion; useful alternative.
- **Jackwerth, J. C. (1999).** "Option-Implied Risk-Neutral Distributions and Implied Binomial Trees: A Literature Review." *Journal of Derivatives* 7(2), 66–82. Earlier review companion to Figlewski.

### 7.4 Bayesian and entropy

- **Buchen, P. W. & Kelly, M. (1996).** "The Maximum Entropy Distribution of an Asset Inferred from Option Prices." *Journal of Financial and Quantitative Analysis* 31(1), 143–159. The maximum-entropy method for RND. Analytically elegant.
- **Stutzer, M. (1996).** "A Simple Nonparametric Approach to Derivative Security Valuation." *Journal of Finance* 51(5), 1633–1652. Independent development of the entropy approach, from an econometric angle.
- **Neri, C. & Schneider, L. (2012).** "Maximum Entropy Distributions Inferred from Option Portfolios on an Asset." *Finance and Stochastics* 16(2), 293–318. Modern extension to exponential-polynomial families.
- **Reid, S. (2012–2013).** University of Cambridge / Konstanz technical reports on GP priors for RND. Less widely cited but a nice bridge to modern nonparametric-Bayes.
- **Eilers, P. H. C. & Marx, B. D. (1996).** "Flexible Smoothing with B-splines and Penalties." *Statistical Science* 11(2), 89–121. Not a finance paper but the reference for the penalized-B-spline (P-spline) machinery underlying most log-density-spline RND methods.
- **Kooperberg, C. & Stone, C. J. (1991).** "A Study of Logspline Density Estimation." *Computational Statistics & Data Analysis* 12(3), 327–347. Origin of logspline density estimation.

### 7.5 Calibrated model methods

- **Dupire, B. (1994).** "Pricing with a Smile." *Risk* 7, 18–20. The local-vol formula. 
- **Heston, S. (1993).** "A Closed-Form Solution for Options with Stochastic Volatility with Applications to Bond and Currency Options." *Review of Financial Studies* 6(2), 327–343. The Heston model.
- **Carr, P. & Madan, D. B. (1999).** "Option Valuation Using the Fast Fourier Transform." *Journal of Computational Finance* 3, 463–520. The FFT-based option pricing via characteristic function — works for Heston, Levy processes, anything with a computable $\phi_\tau$.
- **Fang, F. & Oosterlee, C. W. (2008).** "A Novel Pricing Method for European Options Based on Fourier-Cosine Series Expansions." *SIAM Journal on Scientific Computing* 31(2), 826–848. The COS method. Faster than Carr–Madan in most cases; also directly gives densities.
- **Bayer, C., Friz, P. & Gatheral, J. (2016).** "Pricing Under Rough Volatility." *Quantitative Finance* 16(6), 887–904. rBergomi and rough-vol modeling.
- **Bergomi, L. (2016).** *Stochastic Volatility Modeling.* CRC Press. The desk-quant reference on stochastic volatility.
- **Hagan, P. S., Kumar, D., Lesniewski, A. S. & Woodward, D. E. (2002).** "Managing Smile Risk." *Wilmott Magazine*, 84–108. SABR.
- **Madan, D. B., Carr, P. P. & Chang, E. C. (1998).** "The Variance Gamma Process and Option Pricing." *European Finance Review* 2(1), 79–105. The VG model.
- **Carr, P., Geman, H., Madan, D. B. & Yor, M. (2002).** "The Fine Structure of Asset Returns: An Empirical Investigation." *Journal of Business* 75(2), 305–332. CGMY.

### 7.6 Risk premium / pricing kernel

- **Rosenberg, J. V. & Engle, R. F. (2002).** "Empirical Pricing Kernels." *Journal of Financial Economics* 64(3), 341–372. Semi-parametric estimation of the pricing kernel from options.
- **Bliss, R. R. & Panigirtzoglou, N. (2004).** "Option-Implied Risk Aversion Estimates." *Journal of Finance* 59(1), 407–446. Estimation of representative-agent CRRA parameters from options; also a nice methodological discussion of interpolation choices.
- **Jackwerth, J. C. (2000).** "Recovering Risk Aversion from Option Prices and Realized Returns." *Review of Financial Studies* 13(2), 433–451. The pricing-kernel puzzle paper.
- **Aït-Sahalia, Y. & Lo, A. W. (2000).** "Nonparametric Risk Management and Implied Risk Aversion." *Journal of Econometrics* 94, 9–51. Companion to their 1998 paper, adds the risk-aversion angle.
- **Ross, S. A. (2015).** "The Recovery Theorem." *Journal of Finance* 70(2), 615–648. A more speculative but influential result: under strong assumptions, $p$ can be recovered from $q$ + transition structure. Extensively critiqued (Boriçič 2015; Bakshi–Chabi-Yo–Gao 2018 among others).
- **Hamilton, J. D. & Wu, J. C. (2014).** "Risk Premia in Crude Oil Futures Prices." *Journal of International Money and Finance* 42, 9–37. The commodities-specific risk-premium reference.

### 7.7 Central-bank practitioner surveys

- **Bahra 1997** (BoE), already listed.
- **Cooper, N. (1999).** "Testing Techniques for Estimating Implied RNDs from the Prices of European-style Options." Bank of England internal paper (unpublished but widely circulated); documents the spike pathology in mixture fits.
- **Bliss, R. R. & Panigirtzoglou, N. (2002).** "Testing the Stability of Implied Probability Density Functions." *Journal of Banking and Finance* 26(2–3), 381–422. Comparison of methods across stability criteria.
- **Fusai, G. & Meucci, A. (2003).** *Risk-Neutral vs Historical Distribution.* SSRN. Central-bank oriented walkthrough.
- **ECB Working Paper No. 440 (Andersen & Wagener 2005).** FX options RND methodology at ECB; useful comparison to BoE.
- **Kim, Cho & Kim (2007), IMF WP 10/181** (Cheng 2010): "A New Framework To Estimate the Risk-Neutral Probability Density Functions." IMF walkthrough.
- **Datta et al. (2017).** "Taking Options into the Fed's Toolbox." Fed IFDP. Discusses RND use in FOMC deliberations.

### 7.8 Textbook chapters

- **Gatheral, J. (2006).** *The Volatility Surface.* Chapters 3–5 (SVI and its context), 8 (density from options).
- **Rebonato, R. (2004).** *Volatility and Correlation.* Wiley. Chapter on smile modeling.
- **Wilmott, P. (2006).** *Paul Wilmott On Quantitative Finance.* Chapters on option-implied distributions.
- **Bergomi, L. (2016).** *Stochastic Volatility Modeling.* Chapters on Heston, local-vol, rough-vol.
- **Cont, R. & Tankov, P. (2004).** *Financial Modelling with Jump Processes.* Chapters 5–9 for the Levy and characteristic-function machinery; Chapter 13 for calibration from options.

### 7.9 URLs

- Bahra 1997: https://www.bankofengland.co.uk/working-paper/1997/implied-risk-neutral-probability-density-functions-from-option-prices
- Figlewski 2010 review (2017 update): https://pages.stern.nyu.edu/~sfiglews/documents/RND%20Review%20ver4.pdf
- Gatheral–Jacquier 2014 SSVI: https://arxiv.org/abs/1204.0646
- Bondarenko 2003 PCA: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=375781
- Fengler 2009: https://edoc.hu-berlin.de/bitstreams/4af0fb58-fda0-4e91-8fb2-fa451714a275/download
- Carr–Madan 1999 FFT: https://engineering.nyu.edu/sites/default/files/2019-01/CarrMadan2_0.pdf
- Fang–Oosterlee 2008 COS: https://mpra.ub.uni-muenchen.de/9319/
- Rosenberg–Engle 2002: https://www.stern.nyu.edu/rengle/EPK.pdf
- Melick–Thomas 1997 (JFQA): https://www.jstor.org/stable/2331317
- Jackwerth–Rubinstein 1996: https://www.jstor.org/stable/2329531
- Monteiro–Tütüncü–Vicente 2008: https://www.sciencedirect.com/science/article/abs/pii/S0377221707002871
- Buchen–Kelly 1996: https://www.jstor.org/stable/2331391
- Bliss–Panigirtzoglou 2004: https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2004.00637.x
- Roper 2010: https://arxiv.org/abs/1004.3170
- Aït-Sahalia–Lo 1998: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=225414

---

## 8. Situating NightKing in the external landscape

The reader has (presumably) read `nightking-strategy-writeup.md`; this section positions the Act II design against the literature reviewed above.

**The architectural choice: hybrid SVI + Bayesian log-density spline.** This is a two-stage pipeline where Stage 9–10 fits SVI to each expiry slice with vega weights and arbitrage constraints, and Stage 11–15 uses that SVI fit as either (a) an initial reference density for a Bayesian log-density spline with a P-spline curvature penalty, hyperprior on the smoothing parameter, and a martingale constraint enforced via Lagrange multiplier, or (b) a straight-through delivery when the chain is thin. The final output is a *posterior ensemble* of densities, not a point density, and the trading logic downstream compares posterior bracket-probability distributions to Kalshi bracket prices.

### 8.1 What NightKing gets right relative to standard practice

1. **IV-space fitting with vega weights** (§3.1, §3.4). This is Fengler–Rindler orthodoxy. Not novel; correctly implemented is what matters.
2. **Arbitrage enforcement inside the optimizer, not post-hoc** (§3.3). SVI slice fit with the Gatheral-$g$ check baked in as a constraint or as a rejection layer is the modern practitioner default. The Bayesian layer's exponential parameterization automatically enforces $q \ge 0$; the martingale Lagrange multiplier enforces the mean constraint.
3. **Implied forward via parity regression** (§3.5). The "−8pt bug" resolution — always fit forward from the same-snapshot option chain, never source externally — is exactly the fix Bahra (1997), Malz (1997), and every subsequent central-bank paper explicitly warns about. NightKing having lived this bug and fixed it puts it a full step ahead of desk implementations that treat forward as an input parameter.
4. **Posterior uncertainty propagation** (§3.6). Shipping bracket-probability *distributions* rather than point estimates is *not* standard practice on desks (bootstrap or Bayesian ensembles are rare in production RND pipelines). This is one of NightKing's genuine advantages: it lets the trading logic operate on p-values (or Bayes factors) rather than point wedges, dramatically reducing false-positive trades on noise.
5. **Bracket integrals rather than point densities** (§3.7). Kalshi settles on brackets; comparing integrals to integrals is dimensionally correct. Anyone comparing point densities to bracket prices is conflating different objects.
6. **Martingale constraint as Lagrange multiplier** (§5.3). Enforcing $\int x q(x) dx = F_t$ explicitly is done in Bahra (1997) via parametric mean-matching, in Monteiro–Tütüncü–Vicente (2008) via a linear constraint on spline coefficients, and in Buchen–Kelly (1996) via the max-entropy dual (mean is implicitly a moment constraint if you add it). NightKing's Lagrangian implementation matches the last of these in spirit.
7. **Hyperprior on the curvature penalty $\lambda$** (§5.3). This is standard P-spline Bayesian machinery (Eilers–Marx 1996; Lang–Brezger 2004). It removes the need for ad-hoc cross-validation of $\lambda$ at every snapshot. Ratable improvement over any paper that fixes $\lambda$ arbitrarily.
8. **Explicit choice of SVI as smile prior** (§2.2.2). SVI has near-canonical status. Using it as a warm start for the Bayesian layer means the Bayesian layer gets sensible initial curvature and the sampler converges fast.

### 8.2 Where reviewers might push back

1. **Tail behaviour.** SVI has linear-in-$|k|$ wings; the Bayesian layer with a P-spline on a bounded interval has whatever tails the boundary conditions dictate. If a reviewer runs Lee's moment formula on your smile and the implied finite-moment order is 3 or 4, they will ask whether your bracket probabilities in the far wings are meaningful. Attach GEV or Pareto tails explicitly (Figlewski 2010; Aït-Sahalia–Duarte 2003) and document.
2. **Uniqueness of the Bayesian solution.** With 25 basis functions and $\sim$50–100 strikes worth of likelihood, the log-posterior can have multiple modes if the prior is too flat. Standard defense: report chain diagnostics ($\hat R$, ESS, divergences), show trace plots, run multiple chains.
3. **Model selection for the number of knots $n_{\text{knots}}$.** A skeptical reader will ask why you chose 25 and not 15 or 40. Defense: cross-validation on held-out strikes; sensitivity analysis; reversible-jump MCMC over $n_{\text{knots}}$ if you want to be maximally defensible.
4. **Ignoring calendar structure.** Fitting each expiry independently (as opposed to fitting an SSVI surface) leaves you open to calendar arbitrage across expiries. Defense: (a) NightKing is trading a single expiry-bracket at a time, so cross-expiry arbitrage isn't the strategy's exposure; (b) if you *do* want to compare multi-expiry Kalshi contracts, migrate to SSVI (Gatheral–Jacquier 2014) at that stage.
5. **Physical vs risk-neutral conflation.** If you compare $\hat q^\mathbb{Q}$ to Kalshi $\hat p^\mathbb{P}$ without articulating a risk-premium adjustment, an academic reviewer will flag it immediately. Defense options: (a) restrict claims to "risk-neutral wedge" without physical-density interpretation; (b) estimate the wedge historically and adjust; (c) hedge the risk premium out via the option-side futures overlay (§6.1).
6. **American-exercise premium on CL options.** WTI options are American on the LO series. Unless you're using the European WBW weeklies exclusively, you have an American-to-European correction to apply.
7. **Roll boundaries** (§4.10). If any part of the pipeline uses a continuous-futures series (for historical calibration, for backtest, or for regime detection), you have a landmine. Verify that Stage 9 forward and Stage 11 spline are both keyed to the specific expiry's underlying contract.

### 8.3 Defensible substitutions if any component fails

- **If SVI won't fit** (e.g., ultra-short-dated options with jagged smiles): fall back to Fengler (2009) shape-constrained spline in $C$-space with vega weights, then differentiate. This is more robust for very-short-dated smiles but produces no compact parametric summary.
- **If Bayesian HMC is too slow** for real-time work: use Laplace approximation around the MAP. Fit MAP with L-BFGS-B on the log-posterior, compute Hessian numerically or via autodiff, sample from the Gaussian approximation. Gives you posterior uncertainty at ~100× speedup. Bias is bounded when the true posterior is unimodal (verifiable via a slow HMC run on representative snapshots).
- **If the martingale constraint tension breaks the sampler**: switch from soft penalty to hard projection. After each HMC leapfrog step, project the density onto the martingale constraint manifold via a small linear correction on the coefficients (SLSQP or KKT-solved). Standard trick in constrained Bayesian inference.
- **If chain thinness kills the Bayesian layer**: revert to double-lognormal (Bahra 1997) with mean constraint. Ships an interpretable point density; accept lower fidelity.
- **If Kalshi's take rate distorts the comparison**: fit a market-microstructure model to Kalshi prices (add a symmetric per-bracket bid-ask, or a per-bracket house margin) before comparing to RND. Simple and effective.

### 8.4 The one thing that isn't in the literature

Across the papers reviewed above, I found no example of a pipeline that combines: (a) SVI slice fit as warm start, (b) Bayesian log-density spline with hyperpriored curvature, (c) Lagrange-multiplier martingale, (d) posterior-sample propagation into prediction-market bracket p-values, and (e) full-time-series calibration against realized outcomes via Berkowitz + Christoffersen.

Each ingredient exists somewhere in isolation; the combination — which is what NightKing is — is genuinely novel as a *system*, even if no individual piece is.

That means two things for Jaden:

1. **You are entitled to claim novelty in the systems-integration sense.** No reviewer will find a paper that does exactly what you are doing. The individual pieces are defensible from citations; the combination is your contribution.
2. **You are exposed to failure modes that no prior paper has documented against your specific pipeline.** Take that seriously. The diagnostic quartet (§3.9) plus the coverage tests (§6.3) are non-negotiable pieces of the operational discipline.

Good hunting.

---

*End of document.*
