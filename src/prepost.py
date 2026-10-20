"""
Pre/post analysis: a new daily-login reward shipped to ALL players on REWARD_LAUNCH (no control group).
Shows the naive pre/post estimate vs an interrupted-time-series (ITS) estimate that adjusts for
a pre-existing trend, plus a placebo test.  Outcome: D1 retention by install-date cohort.
"""
import json, sqlite3, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from config import *

con = sqlite3.connect(DB)
df = pd.read_sql_query("""
  SELECT p.install_date AS dt, COUNT(*) AS n, SUM(d.player_id IS NOT NULL) AS ret
  FROM players p LEFT JOIN daily_activity d ON d.player_id=p.player_id AND d.day_offset=1
  GROUP BY p.install_date ORDER BY p.install_date""", con)
con.close()
df["dt"] = pd.to_datetime(df.dt); df["rate"] = df.ret / df.n
df["t"] = (df.dt - df.dt.min()).dt.days
L = (pd.Timestamp(REWARD_LAUNCH) - df.dt.min()).days

# naive: 14 days before vs 14 days after
pre = df[(df.t >= L - 14) & (df.t < L)]; post = df[(df.t >= L) & (df.t < L + 14)]
p0, p1 = pre.ret.sum() / pre.n.sum(), post.ret.sum() / post.n.sum()
_, p_naive, _, _ = stats.chi2_contingency([[pre.ret.sum(), pre.n.sum() - pre.ret.sum()],
                                           [post.ret.sum(), post.n.sum() - post.ret.sum()]], correction=False)
naive = (p1 - p0) * 100

# ITS: rate = b0 + b1*t + b2*post + b3*(t-L)*post  (weighted by cohort size)
def its(d, L):
    post_ = (d.t >= L).astype(float)
    X = np.column_stack([np.ones(len(d)), d.t, post_, (d.t - L) * post_])
    w = np.sqrt(d.n.values); Xw, yw = X * w[:, None], d.rate.values * w
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    resid = yw - Xw @ beta; s2 = resid @ resid / (len(d) - X.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(Xw.T @ Xw)))
    return beta, se, X
beta, se, X = its(df, L)
shift, shift_se = beta[2] * 100, se[2] * 100
# placebo: fake launch 14 days earlier, using only pre-launch data
beta_p, se_p, _ = its(df[df.t < L], L - 14)
res = dict(naive_pp=naive, naive_p=p_naive, pre_rate=p0, post_rate=p1, pre_trend_pp_per_day=beta[1] * 100,
           its_shift_pp=shift, its_ci=[shift - 1.96 * shift_se, shift + 1.96 * shift_se],
           placebo_shift_pp=beta_p[2] * 100, placebo_ci=[(beta_p[2] - 1.96 * se_p[2]) * 100, (beta_p[2] + 1.96 * se_p[2]) * 100])
print(f"Naive pre/post: {p0:.2%} -> {p1:.2%} = {naive:+.2f}pp (p={p_naive:.1e})")
print(f"Pre-launch trend: {res['pre_trend_pp_per_day']:+.3f}pp/day")
print(f"ITS level shift: {shift:+.2f}pp  95% CI [{res['its_ci'][0]:+.2f}, {res['its_ci'][1]:+.2f}]")
print(f"Placebo shift (should be ~0): {res['placebo_shift_pp']:+.2f}pp CI [{res['placebo_ci'][0]:+.2f}, {res['placebo_ci'][1]:+.2f}]")
json.dump(res, open(OUT / "prepost_results.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(df.dt, df.rate * 100, "o", ms=4, color="#4C78A8", label="D1 retention by install date")
pre_t = df.t < L
ax.plot(df.dt[pre_t], (X @ beta)[pre_t] * 100, color="#E45756", label="ITS fit")
ax.plot(df.dt[~pre_t], (X @ beta)[~pre_t] * 100, color="#E45756")
cf = beta[0] + beta[1] * df.t[~pre_t]                       # counterfactual: pre-trend continues
ax.plot(df.dt[~pre_t], cf * 100, "--", color="grey", label="Counterfactual (pre-trend continues)")
ax.axvline(pd.Timestamp(REWARD_LAUNCH), color="k", ls=":"); ax.text(pd.Timestamp(REWARD_LAUNCH), ax.get_ylim()[0] + .2, " reward launch")
ax.set_ylabel("D1 retention %"); ax.set_title("Pre/post: naive vs trend-adjusted impact of the daily reward"); ax.legend()
plt.tight_layout(); plt.savefig(OUT / "prepost.png", dpi=130)
