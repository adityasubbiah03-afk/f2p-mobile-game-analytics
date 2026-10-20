from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
SQL = ROOT / "sql"
DB = DATA / "game.db"
for p in (DATA, OUT):
    p.mkdir(exist_ok=True)

# Key dates in the simulated game timeline
FIRST_INSTALL = "2026-07-15"
N_INSTALL_DAYS = 47            # installs 15 Jul - 30 Aug
DATA_END = "2026-09-30"        # all players have >=31 days of observation
REWARD_LAUNCH = "2026-08-12"   # "new daily login reward" shipped to everyone (pre/post study)
EVENT_START, EVENT_END = "2026-08-22", "2026-08-23"   # weekend LiveOps event (Sat-Sun)
