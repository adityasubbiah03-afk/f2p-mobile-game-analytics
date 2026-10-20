"""One-page KPI dashboard (PNG) + tidy CSV extracts you can drop straight into Looker Studio / Tableau / Power BI."""
import sqlite3, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import *

con = sqlite3.connect(DB)
res = OUT / "sql_results"
dau = pd.read_csv(res / "01_dau.csv", parse_dates=["dt"])
funnel = pd.read_csv(res / "03_funnel.csv")
curve = pd.read_sql_query("""
  SELECT p.version, d.day_offset, 1.0*COUNT(DISTINCT d.player_id)/(SELECT COUNT(*) FROM players q WHERE q.version=p.version) AS retention
  FROM players p JOIN daily_activity d USING(player_id) WHERE d.day_offset<=30 GROUP BY p.version, d.day_offset""", con)
seg = pd.read_csv(OUT / "segment_profile.csv")
eco = pd.read_csv(res / "06_economy.csv")
con.close()

# --- extracts for BI tools
ext = OUT / "bi_extracts"; ext.mkdir(exist_ok=True)
dau.to_csv(ext / "daily_kpis.csv", index=False); curve.to_csv(ext / "retention_curve_by_variant.csv", index=False)
seg.drop(columns=["recommended_action"]).to_csv(ext / "segment_profile.csv", index=False)
pd.read_csv(OUT / "player_segments.csv").to_csv(ext / "player_segments.csv", index=False)
funnel.to_csv(ext / "funnel.csv", index=False); eco.to_csv(ext / "economy_by_tenure.csv", index=False)

# --- dashboard (DAU/ARPDAU shown only while installs are still flowing; the simulation stops installs
# on 30 Aug and tracks each player for 30 days, so later dates are a truncation artifact, not a real decline)
dau = dau[dau.dt <= "2026-08-30"]
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
fig, ax = plt.subplots(2, 3, figsize=(16, 8.5))
ax[0, 0].plot(dau.dt, dau.dau, color="#4C78A8"); ax[0, 0].set_title("DAU"); ax[0, 0].tick_params(axis="x", rotation=30)
ev0, ev1 = pd.Timestamp(EVENT_START), pd.Timestamp(EVENT_END)
ax[0, 0].axvspan(ev0, ev1 + pd.Timedelta(days=1), color="#E45756", alpha=.25, label="LiveOps event"); ax[0, 0].legend()
ax[0, 1].plot(dau.dt, dau.arpdau, color="#54A24B"); ax[0, 1].set_title("ARPDAU ($)"); ax[0, 1].tick_params(axis="x", rotation=30)
ax[0, 1].axvspan(ev0, ev1 + pd.Timedelta(days=1), color="#E45756", alpha=.25)
for v, c in zip(["gate_30", "gate_40"], ["#4C78A8", "#F58518"]):
    d = curve[curve.version == v]; ax[0, 2].plot(d.day_offset, d.retention * 100, label=v, color=c)
ax[0, 2].set_title("Retention curve by A/B variant (%)"); ax[0, 2].set_xlabel("day since install"); ax[0, 2].legend()
ax[1, 0].barh(funnel.step[::-1], funnel.pct_of_installs[::-1] * 100, color="#72B7B2"); ax[1, 0].set_title("14-day player funnel (% of installs)")
s = seg.sort_values("pct_revenue")
ax[1, 1].barh(s.segment, s.pct_revenue, color="#F58518"); ax[1, 1].set_title("% of revenue by segment")
for i, (r, n) in enumerate(zip(s.pct_revenue, s.pct_players)): ax[1, 1].text(r + 1, i, f"{n:.1f}% of players", va="center", fontsize=8)
ax[1, 1].set_xlim(0, 110)
ax[1, 2].plot(eco.day_offset, eco.sink_source_ratio, marker="o", ms=3, color="#B279A2"); ax[1, 2].axhline(1, ls="--", color="k", lw=.8)
ax[1, 2].set_title("Coin sink/source ratio by tenure"); ax[1, 2].set_xlabel("day since install")
plt.suptitle("F2P Mobile Game: Product Analytics Dashboard (synthetic data)", fontsize=14, y=1.0)
plt.tight_layout(); plt.savefig(OUT / "dashboard.png", dpi=120, bbox_inches="tight")
print("dashboard + BI extracts written")
