"""
LiveOps + game-economy analysis.
 (a) Did the weekend event lift engagement, spend and coin sinks vs the weekends either side?
 (b) Is the soft-currency economy balanced, or are veteran players hoarding coins?
"""
import json, sqlite3, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from config import *

con = sqlite3.connect(DB)
ev = pd.read_sql_query(open(SQL / "05_liveops_event.sql").read(), con)
eco = pd.read_sql_query(open(SQL / "06_economy.sql").read(), con)
con.close()
res = {}

# (a) event lift vs average of the two surrounding weekends
ev["is_event"] = ev.label.eq("EVENT")
g = ev.groupby("is_event").agg(eligible=("eligible", "sum"), active=("active", "sum"), revenue=("revenue", "sum"),
                               sink=("sink_source_ratio", "mean"))
e, b = g.loc[True], g.loc[False]
ar_e, ar_b = e.active / e.eligible, b.active / b.eligible
rv_e, rv_b = e.revenue / e.eligible, b.revenue / b.eligible
_, p_act, _, _ = stats.chi2_contingency([[e.active, e.eligible - e.active], [b.active, b.eligible - b.active]], correction=False)
# revenue: day-level comparison is only 2 vs 4 days -> report lift but flag as directional
res["event"] = dict(active_rate_event=ar_e, active_rate_base=ar_b, active_lift_pct=(ar_e / ar_b - 1) * 100, active_p=p_act,
                    rev_per_eligible_event=rv_e, rev_per_eligible_base=rv_b, revenue_lift_pct=(rv_e / rv_b - 1) * 100,
                    sink_ratio_event=e.sink, sink_ratio_base=b.sink)
print(f"EVENT: active rate {ar_b:.2%} -> {ar_e:.2%} ({res['event']['active_lift_pct']:+.1f}%, p={p_act:.1e}); "
      f"revenue/eligible ${rv_b:.5f} -> ${rv_e:.5f} ({res['event']['revenue_lift_pct']:+.0f}%); "
      f"sink/source {b.sink:.2f} -> {e.sink:.2f}")

# (b) economy health
early, late = eco[eco.day_offset <= 3], eco[eco.day_offset >= 14]
res["economy"] = dict(sink_ratio_d0_3=early.spent.sum() / early.earned.sum(), sink_ratio_d14_30=late.spent.sum() / late.earned.sum(),
                      net_coins_per_active_day_d14_30=late.net_coins_added.sum() / late.active_player_days.sum(),
                      net_coins_per_active_day_d0_3=early.net_coins_added.sum() / early.active_player_days.sum())
print(f"ECONOMY: sink/source D0-3 {res['economy']['sink_ratio_d0_3']:.2f} vs D14-30 {res['economy']['sink_ratio_d14_30']:.2f}; "
      f"net coins per active day D0-3 {res['economy']['net_coins_per_active_day_d0_3']:.0f} vs D14-30 {res['economy']['net_coins_per_active_day_d14_30']:.0f}")
json.dump(res, open(OUT / "economy_liveops_results.json", "w"), indent=2, default=float)

fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
col = ["#E45756" if x else "#4C78A8" for x in ev.is_event]; lbl = ev.dt.str[5:]
ax[0].bar(lbl, ev.active_rate * 100, color=col); ax[0].set_title("Active rate (eligible players), %"); ax[0].tick_params(axis="x", rotation=45)
ax[1].bar(lbl, ev.revenue_per_eligible, color=col); ax[1].set_title("Revenue per eligible player, $"); ax[1].tick_params(axis="x", rotation=45)
ax[2].plot(eco.day_offset, eco.sink_source_ratio, marker="o", ms=3); ax[2].axhline(1, color="k", ls="--", lw=.8)
ax[2].set_title("Coin sink/source ratio by tenure"); ax[2].set_xlabel("days since install"); ax[2].set_ylim(0.4, 1.1)
plt.suptitle("Red = LiveOps event weekend", y=1.02, fontsize=9); plt.tight_layout(); plt.savefig(OUT / "economy_liveops.png", dpi=130, bbox_inches="tight")
