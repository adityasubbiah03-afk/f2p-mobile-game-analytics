# F2P Mobile Game Player Analytics

End-to-end product analytics case study for a free-to-play mobile puzzle game: SQL metrics, an A/B test,
a pre/post impact study, player segmentation, a LiveOps/economy review and a KPI dashboard.
Written as if briefing a Product Manager: each section answers a business question and ends with a recommendation.

> **Data note:** the dataset is **synthetic**. It mirrors the schema of the public Kaggle *Cookie Cats* A/B test
> (`userid, version, sum_gamerounds, retention_1, retention_7`) and adds purchases, soft-currency and a LiveOps event.
> Effects were planted in the simulator (see `src/generate_data.py`) so the methods have something to find.
> **The numbers below are not real-world findings.** To run on the real Cookie Cats file:
> `python run_all.py --cookie-cats cookie_cats.csv` (the A/B section then uses the real data; the rest stays simulated).

## Run it
```bash
pip install -r requirements.txt
python run_all.py          # ~1 minute; writes everything to /outputs
```

## Stack
Python (pandas, NumPy, SciPy, scikit-learn, matplotlib) · SQLite/SQL (CTEs, window functions, cohort joins) ·
BI-ready CSV extracts for Looker Studio / Tableau / Power BI (`outputs/bi_extracts/`).

## 1. Core metrics in SQL (`sql/`)
DAU/installs/ARPDAU, weekly cohort retention (D1/D7/D14/D30), a 14-day player funnel, ARPU/ARPPU/payer conversion
by platform and variant, event comparison and a soft-currency sink/source table. Results: `outputs/sql_results/`.

Headline: ~47% D1, ~19% D7, ~10% D30 retention; ~2% of players ever pay; 21% reach 100+ rounds in 14 days.

## 2. A/B test: should we move the progression gate from level 30 to level 40?
**Hypothesis:** a later gate lets players enjoy the game longer, so retention rises.
**Design:** 90k players randomised 50/50. Primary metrics D1 and D7 retention (Bonferroni, alpha = 0.025);
guardrails: rounds played, payer conversion, ARPU.

| Check | Result |
|---|---|
| Sample-ratio mismatch | 44,905 vs 45,095, p = 0.53, randomisation OK |
| Minimum detectable effect (80% power) | D1 1.03pp, D7 0.82pp |
| D1 retention | 47.12% vs 47.30%, diff +0.19pp, 95% CI [-0.46, +0.84], p = 0.57 |
| **D7 retention** | **19.66% vs 18.18%, diff -1.48pp, 95% CI [-1.98, -0.97], p < 0.001** |
| ARPU | $0.272 vs $0.264, diff CI [-0.060, +0.046], no detectable change |

**Recommendation: do not ship gate_40.** It does not help D1 and significantly hurts D7. Monetisation shows no offsetting gain
(the ARPU CI includes zero, so the test cannot rule out a small effect either way). Keep the gate at level 30; if the team
still wants to test a later gate, pair it with an easier ramp to level 30 so players don't lose momentum before D7.

## 3. Pre/post: did the new daily-login reward work? (no control group)
The reward shipped to everyone on 12 Aug, so a naive before/after comparison is all a team would normally have.
D1 retention was already drifting upward (+0.055pp per day), which inflates the naive result.

| Method | Estimated D1 lift |
|---|---|
| Naive 14 days before vs after | +3.80pp |
| Interrupted time series (adjusts for trend) | +3.12pp, 95% CI [+0.65, +5.60] |
| Placebo (fake launch 14 days earlier) | -0.31pp, CI [-2.59, +1.96], i.e. no effect, as it should be |

In the simulator the planted effect is about +2.3pp: the trend-adjusted CI covers it and the naive estimate overshoots.
**Recommendation:** treat the reward as a likely positive (the CI excludes zero) but not as +3.8pp. For future launches,
hold out 5-10% of players, which would give a clean estimate instead of a wide interval.

## 4. Segmentation: who are our players and what do we do with each?
Two-stage K-Means (spend is zero-inflated, so payers are split off first). Non-payers cluster on recency and frequency;
payers on log-spend and frequency. k = 3 for non-payers was chosen for actionability (silhouette is highest at k = 2: 0.53 vs 0.42).

| Segment | % players | % revenue | Avg active days (30d) | Action |
|---|---|---|---|---|
| Whales | 0.7% | 82.3% | 8.1 | VIP offers, early content access, watch for session drops (churn risk is expensive) |
| Minnows (payers) | 1.3% | 17.7% | 7.3 | Starter packs / battle-pass upsell to climb the value ladder |
| Engaged free players | 46.3% | 0% | 8.3 | Time a first-purchase offer after a hard level; rewarded ads |
| Casual / at-risk | 35.9% | 0% | 4.3 | Daily-reward streaks, event invites, easier-level boosts |
| Churned / one-and-done | 15.8% | 0% | 2.1 | Fix onboarding; low-cost win-back only |

**Takeaway:** revenue is extremely concentrated (0.7% of players = 82%), so whale retention is the single most valuable KPI to monitor.

## 5. LiveOps and economy
**Weekend event (22-23 Aug)** vs the weekends either side, using only players 3-30 days old so tenure mix matches:
active rate 14.9% -> 16.9% (+12.9%, p < 0.001), revenue per eligible player +46% (**directional only: two event days**),
and the coin sink/source ratio rose from 0.78 to 0.96, so the event shop worked as a currency sink as well as a revenue driver.
**Recommendation:** repeat the event monthly, and test it as a proper experiment (staggered rollout) to get a defensible revenue lift.

**Economy health:** the sink/source ratio falls from 0.94 in days 0-3 to 0.70 by days 14-30; net coins added per active day
rises from ~9 to ~51. Veteran players are earning far more than they spend, a classic hoarding/inflation setup.
**Recommendation:** add a late-game sink (cosmetics, limited-time store, upgrade tiers) aimed at day-14+ players, and monitor the ratio.

## 6. Dashboard
`outputs/dashboard.png` is the one-page view. To rebuild it in Looker Studio (free) or Tableau, connect the CSVs in
`outputs/bi_extracts/` (`daily_kpis`, `retention_curve_by_variant`, `segment_profile`, `funnel`, `economy_by_tenure`).
DAU/ARPDAU panels stop at 30 Aug: the simulation stops installs then and tracks players for 30 days, so later dates are a truncation artifact.

## Limitations
- Synthetic data: effect sizes are illustrative. Real data adds bots, outliers (Cookie Cats has a player with ~50k rounds), seasonality and novelty effects.
- D1/D7 retention is measured as "active exactly on day N", matching Cookie Cats.
- A/B test is a fixed-horizon analysis; no sequential testing or peeking correction.
- Event revenue lift rests on two days; segmentation is descriptive, not causal.

## Next steps
Swap in real Cookie Cats data, add CUPED variance reduction to the A/B test, build an LTV model by segment, and test the late-game sink as an experiment.
