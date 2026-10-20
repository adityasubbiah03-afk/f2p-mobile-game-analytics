"""
Simulate a free-to-play mobile puzzle game (schema mirrors the Kaggle 'Cookie Cats' A/B test
and extends it with purchases, soft currency and a LiveOps event).

IMPORTANT: this data is SYNTHETIC. Effects are planted so each analysis has something to find:
  * gate_40 slightly lowers D7 retention                      -> A/B test
  * daily-login reward launched 12 Aug lifts D1 retention,
    on top of a slow upward drift in install quality          -> pre/post (confounded)
  * weekend LiveOps event lifts activity, spend and coin sinks -> LiveOps analysis
  * coin sinks shrink with tenure (hoarding)                   -> economy analysis
Swap in the real data with:  python run_all.py --cookie-cats path/to/cookie_cats.csv
"""
import numpy as np, pandas as pd
from config import *

rng = np.random.default_rng(42)
N = 90_000
MAXD = 30

# ---------- players ----------
install_idx = rng.integers(0, N_INSTALL_DAYS, N)
first = pd.Timestamp(FIRST_INSTALL)
install_date = first + pd.to_timedelta(install_idx, unit="D")
version = rng.choice(["gate_30", "gate_40"], N)
platform = rng.choice(["iOS", "Android"], N, p=[0.35, 0.65])
country = rng.choice(["AU", "US", "UK", "IN", "DE", "BR"], N, p=[.12, .30, .15, .18, .10, .15])
launch_idx = (pd.Timestamp(REWARD_LAUNCH) - first).days
post_launch = install_idx >= launch_idx

# latent engagement; slow upward drift in install quality (a pre/post confounder)
q = rng.beta(2, 2.5, N) * (1 + 0.001 * install_idx)

# ---------- activity matrix (player x day offset) ----------
d = np.arange(0, MAXD + 1)
base = np.where(d == 0, 1.0, np.maximum(d, 1.0) ** -0.45)          # decay curve
p = q[:, None] * base[None, :]
gate40 = (version == "gate_40")[:, None]
p = np.where(gate40 & (d[None, :] >= 2), p * 0.955, p)              # gate_40 hurts D7+
p = np.where(post_launch[:, None] & (d[None, :] == 1), p * 1.05, p) # reward lifts D1
p = np.where(post_launch[:, None] & (d[None, :] >= 2), p * 1.02, p)

cal = (install_date.values[:, None] + d[None, :].astype("timedelta64[D]")).astype("datetime64[ns]")
is_weekend = pd.DatetimeIndex(cal.ravel()).dayofweek.values.reshape(N, MAXD + 1) >= 5
is_event = (cal >= np.datetime64(EVENT_START)) & (cal <= np.datetime64(EVENT_END))
p = np.where(is_weekend, p * 1.05, p)
p = np.where(is_event & (d[None, :] >= 1), p * 1.12, p)
p = np.clip(p, 0, 0.98)

active = rng.random((N, MAXD + 1)) < p
active[:, 0] = True
active &= cal <= np.datetime64(DATA_END)

def fmt(arr):
    return pd.DatetimeIndex(arr).strftime("%Y-%m-%d")

# ---------- daily_activity ----------
pi, di = np.nonzero(active)
sessions = 1 + rng.poisson(0.8 + 2.5 * q[pi])
rounds = rng.poisson(sessions * (3.5 + 3 * q[pi]))
ev = is_event[pi, di] & (di >= 1)
earned = (rounds * rng.uniform(8, 12, len(pi)) * np.where(ev, 1.3, 1.0)).round().astype(int)
sink_ratio = np.clip(0.95 - 0.012 * di + np.where(ev, 0.18, 0) + rng.normal(0, 0.05, len(pi)), 0.2, 1.3)
spent = (earned * sink_ratio).round().astype(int)
daily = pd.DataFrame({
    "player_id": pi, "activity_date": fmt(cal[pi, di]),
    "day_offset": di, "sessions": sessions, "rounds": rounds,
    "coins_earned": earned, "coins_spent": spent,
})

# ---------- purchases ----------
payer_prob = np.clip(0.015 + 0.07 * q, 0, 0.3) * np.where(platform == "iOS", 1.5, 1.0)
is_payer = rng.random(N) < payer_prob
rate = np.where(is_payer, rng.lognormal(np.log(0.06), 1.0, N), 0.0)   # purchases per active day
z = (np.log(np.maximum(rate, 1e-9)) - np.log(0.06)) / 1.0
buy = rng.random(len(pi)) < np.clip(rate[pi] * np.where(ev, 1.4, 1.0), 0, 0.9)
bp, bd = pi[buy], di[buy]
tiers = np.array([0.99, 2.99, 4.99, 9.99, 19.99, 49.99])
tier_idx = np.clip(np.floor(rng.normal(1.3 + 1.1 * z[bp], 1.0)), 0, 5).astype(int)
purchases = pd.DataFrame({
    "purchase_id": np.arange(len(bp)), "player_id": bp,
    "purchase_date": fmt(cal[bp, bd]),
    "day_offset": bd, "amount_usd": tiers[tier_idx],
})

players = pd.DataFrame({
    "player_id": np.arange(N), "install_date": install_date.strftime("%Y-%m-%d"),
    "version": version, "platform": platform, "country": country,
})

players.to_csv(DATA / "players.csv", index=False)
daily.to_csv(DATA / "daily_activity.csv", index=False)
purchases.to_csv(DATA / "purchases.csv", index=False)
print(f"players={len(players):,} daily_rows={len(daily):,} purchases={len(purchases):,} "
      f"payers={purchases.player_id.nunique():,} revenue=${purchases.amount_usd.sum():,.0f}")
