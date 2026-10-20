"""
Player segmentation: RFM features over each player's first 30 days + K-Means.
R = days since last active, F = number of active days, M = total spend (USD).
"""
import json, sqlite3, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from config import *

con = sqlite3.connect(DB)
df = pd.read_sql_query("""
  SELECT p.player_id, p.platform, p.version,
         30 - MAX(d.day_offset) AS recency, COUNT(DISTINCT d.day_offset) AS frequency,
         SUM(d.rounds) AS rounds, COALESCE((SELECT SUM(amount_usd) FROM purchases u WHERE u.player_id=p.player_id),0) AS monetary
  FROM players p JOIN daily_activity d USING(player_id) GROUP BY p.player_id""", con)
con.close()

# Two-stage clustering: spend is zero-inflated (~98% of players never pay), so one K-Means would
# just isolate "payers" vs "everyone else". Stage 1 splits payers / non-payers; stage 2 clusters each.
df["segment"] = ""
pay = df.monetary > 0
# Stage 2a: non-payers on recency + frequency
Xn = StandardScaler().fit_transform(np.column_stack([df.loc[~pay, "recency"], np.log1p(df.loc[~pay, "frequency"])]))
samp = np.random.default_rng(1).choice(len(Xn), 10000, replace=False)
sil = {k: float(silhouette_score(Xn[samp], KMeans(k, n_init=5, random_state=1).fit_predict(Xn[samp]))) for k in range(2, 6)}
print("non-payer silhouette by k:", {k: round(v, 3) for k, v in sil.items()})
cn = pd.Series(KMeans(3, n_init=10, random_state=1).fit_predict(Xn), index=df.index[~pay])
gn = df.loc[~pay].groupby(cn).agg(frequency=("frequency", "mean"), recency=("recency", "mean"))
nm = {gn.frequency.idxmax(): "Engaged free players", gn.recency.idxmax(): "Churned / one-and-done"}
nm.update({c: "Casual / at-risk" for c in gn.index if c not in nm})
df.loc[~pay, "segment"] = cn.map(nm)
# Stage 2b: payers on log(spend) + frequency -> whales vs minnows
Xp = StandardScaler().fit_transform(np.column_stack([np.log1p(df.loc[pay, "monetary"]), np.log1p(df.loc[pay, "frequency"])]))
cp = pd.Series(KMeans(2, n_init=10, random_state=1).fit_predict(Xp), index=df.index[pay])
whale_c = df.loc[pay].groupby(cp).monetary.mean().idxmax()
df.loc[pay, "segment"] = cp.map(lambda c: "Whales" if c == whale_c else "Minnows (payers)")

total_rev = df.monetary.sum()
prof = df.groupby("segment").agg(players=("player_id", "count"), avg_active_days=("frequency", "mean"),
                                 days_since_last_active=("recency", "mean"), avg_rounds=("rounds", "mean"),
                                 payer_rate=("monetary", lambda s: (s > 0).mean()), arpu=("monetary", "mean"),
                                 revenue=("monetary", "sum")).round(3)
prof["pct_players"] = (prof.players / len(df) * 100).round(1)
prof["pct_revenue"] = (prof.revenue / total_rev * 100).round(1)
actions = {
  "Whales": "VIP treatment: early access to content, personal offers, protect from churn (monitor drops in sessions).",
  "Minnows (payers)": "Nudge up the value ladder: bundles, battle-pass / starter-pack upsell, limited-time offers.",
  "Payers": "Protect and grow: bundle offers, battle-pass upsell, early access to events.",
  "Engaged free players": "Convert: first-purchase offer timed after a hard level, rewarded-ads, social features.",
  "Casual / at-risk": "Re-engage: push/email with daily reward streaks, easier-level boosts, event invites.",
  "Churned / one-and-done": "Fix onboarding/early difficulty; win-back campaign with free currency, low priority for spend.",
}
prof["recommended_action"] = [actions[s] for s in prof.index]
prof = prof.sort_values("arpu", ascending=False)
print(prof.drop(columns=["recommended_action", "revenue"]).to_string())
prof.to_csv(OUT / "segment_profile.csv"); df.to_csv(OUT / "player_segments.csv", index=False)
json.dump({"silhouette": sil}, open(OUT / "segmentation_results.json", "w"))

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
p = prof.sort_values("pct_players", ascending=False)
x = np.arange(len(p)); ax[0].bar(x - .2, p.pct_players, .4, label="% of players", color="#4C78A8")
ax[0].bar(x + .2, p.pct_revenue, .4, label="% of revenue", color="#F58518")
ax[0].set_xticks(x); ax[0].set_xticklabels(p.index, rotation=20, ha="right"); ax[0].legend(); ax[0].set_title("Players vs revenue by segment")
sc = df.sample(6000, random_state=1)
for s, c in zip(prof.index, plt.cm.tab10.colors):
    d = sc[sc.segment == s]; ax[1].scatter(d.frequency + np.random.rand(len(d)) * .6, np.log1p(d.monetary), s=6, alpha=.5, color=c, label=s)
ax[1].set_xlabel("Active days (30d)"); ax[1].set_ylabel("log(1+spend)"); ax[1].legend(fontsize=7, markerscale=2); ax[1].set_title("RFM clusters")
plt.tight_layout(); plt.savefig(OUT / "segments.png", dpi=130)
