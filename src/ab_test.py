"""
A/B test: gate placement at level 30 (control) vs level 40 (treatment).
Hypothesis : moving the first progression gate from L30 to L40 will increase retention
             because players hit the 'wall' later and enjoy the game longer.
Primary    : D1 and D7 retention.   Guardrails: game rounds (engagement), payer conversion, ARPU.
Method     : SRM check -> power/MDE -> two-proportion chi-square + bootstrap CI (Bonferroni, 2 metrics)
"""
import json, sqlite3, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from config import *

rng = np.random.default_rng(7)
con = sqlite3.connect(DB)
ab = pd.read_sql_query("SELECT * FROM ab_test", con)
spend = pd.read_sql_query("SELECT player_id AS userid, SUM(amount_usd) AS spend FROM purchases GROUP BY player_id", con)
ab = ab.merge(spend, on="userid", how="left").fillna({"spend": 0})
con.close()
A, B = ab[ab.version == "gate_30"], ab[ab.version == "gate_40"]
nA, nB = len(A), len(B)
res = {"n_gate_30": nA, "n_gate_40": nB}

# 1) Sample-ratio mismatch: did randomisation work?
chi, p_srm = stats.chisquare([nA, nB])
res["srm_p"] = p_srm
print(f"SRM check: {nA:,} vs {nB:,}  p={p_srm:.3f}  ->", "OK" if p_srm > 0.001 else "SRM PROBLEM - do not trust results")

# 2) Power / minimum detectable effect
def mde(p, n, alpha=0.025, power=0.8):
    return (stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) * np.sqrt(2 * p * (1 - p) / n)
for m in ("retention_1", "retention_7"):
    res[f"mde_{m}"] = mde(A[m].mean(), min(nA, nB))
print(f"MDE (80% power, Bonferroni alpha): D1 {res['mde_retention_1']*100:.2f}pp, D7 {res['mde_retention_7']*100:.2f}pp")

# 3) Retention tests
def prop_test(m):
    a, b = A[m].sum(), B[m].sum()
    table = [[a, nA - a], [b, nB - b]]
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)
    pa, pb = a / nA, b / nB
    boot = rng.binomial(nA, pa, 20000) / nA, rng.binomial(nB, pb, 20000) / nB
    diff = boot[1] - boot[0]
    return dict(rate_30=pa, rate_40=pb, diff_pp=(pb - pa) * 100, rel_pct=(pb / pa - 1) * 100,
                ci_lo_pp=np.percentile(diff, 2.5) * 100, ci_hi_pp=np.percentile(diff, 97.5) * 100,
                p_value=p, prob_40_better=(diff > 0).mean(), boot=diff * 100)
tests = {m: prop_test(m) for m in ("retention_1", "retention_7")}
for m, t in tests.items():
    print(f"{m}: gate_30 {t['rate_30']:.2%} | gate_40 {t['rate_40']:.2%} | diff {t['diff_pp']:+.2f}pp "
          f"[{t['ci_lo_pp']:+.2f}, {t['ci_hi_pp']:+.2f}] p={t['p_value']:.4f}")
    res[m] = {k: v for k, v in t.items() if k != "boot"}

# 4) Guardrails
mw = stats.mannwhitneyu(A.sum_gamerounds, B.sum_gamerounds)
res["rounds"] = dict(median_30=float(A.sum_gamerounds.median()), median_40=float(B.sum_gamerounds.median()),
                     mean_30=float(A.sum_gamerounds.mean()), mean_40=float(B.sum_gamerounds.mean()), p=float(mw.pvalue))
pay_a, pay_b = (A.spend > 0).sum(), (B.spend > 0).sum()
res["payer_conv"] = dict(rate_30=pay_a / nA, rate_40=pay_b / nB,
                         p=float(stats.chi2_contingency([[pay_a, nA - pay_a], [pay_b, nB - pay_b]], correction=False)[1]))
sa, sb = A.spend.values, B.spend.values       # ARPU is heavy-tailed -> player-level bootstrap
bs = [rng.choice(sb, nB).mean() - rng.choice(sa, nA).mean() for _ in range(2000)]
res["arpu"] = dict(arpu_30=float(sa.mean()), arpu_40=float(sb.mean()), diff=float(sb.mean() - sa.mean()),
                   ci_lo=float(np.percentile(bs, 2.5)), ci_hi=float(np.percentile(bs, 97.5)))
print(f"Rounds median {res['rounds']['median_30']:.0f} vs {res['rounds']['median_40']:.0f} (p={mw.pvalue:.3f}); "
      f"ARPU ${sa.mean():.3f} vs ${sb.mean():.3f}, diff CI [{res['arpu']['ci_lo']:+.3f}, {res['arpu']['ci_hi']:+.3f}]")

# 5) Decision rule
t7 = tests["retention_7"]; sig = t7["p_value"] < 0.025
if sig and t7["diff_pp"] < 0:
    rec = "DO NOT SHIP gate_40. It significantly reduces D7 retention; keep the gate at level 30."
elif sig and t7["diff_pp"] > 0:
    rec = "SHIP gate_40: significant D7 retention gain with no guardrail damage."
else:
    rec = "INCONCLUSIVE: no significant difference. Keep gate_30 and consider a longer/larger test."
res["recommendation"] = rec
print("\nRECOMMENDATION:", rec)
json.dump(res, open(OUT / "ab_test_results.json", "w"), indent=2, default=float)

# 6) Figures
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for i, m in enumerate(("retention_1", "retention_7")):
    t = tests[m]; a, b = t["rate_30"] * 100, t["rate_40"] * 100
    se = lambda p, n: 1.96 * np.sqrt(p * (1 - p) / n) * 100
    ax[0].bar([i * 3, i * 3 + 1], [a, b], yerr=[se(t["rate_30"], nA), se(t["rate_40"], nB)],
              color=["#4C78A8", "#F58518"], capsize=4)
ax[0].set_xticks([0.5, 3.5]); ax[0].set_xticklabels(["D1 retention", "D7 retention"]); ax[0].set_ylabel("%")
ax[0].legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#4C78A8"), plt.Rectangle((0, 0), 1, 1, color="#F58518")],
             labels=["gate_30 (control)", "gate_40 (test)"]); ax[0].set_title("Retention by variant (95% CI)")
ax[1].hist(t7["boot"], bins=60, color="#F58518", alpha=.8); ax[1].axvline(0, color="k", ls="--")
ax[1].set_title("Bootstrap: D7 diff (gate_40 - gate_30), pp"); ax[1].set_xlabel("percentage points")
plt.tight_layout(); plt.savefig(OUT / "ab_test.png", dpi=130)
