"""Load CSVs into SQLite and apply schema. Optionally replace the A/B table with the real Cookie Cats CSV."""
import sqlite3, sys, pandas as pd
from config import *

def build(cookie_cats=None):
    if DB.exists(): DB.unlink()
    con = sqlite3.connect(DB)
    for t in ("players", "daily_activity", "purchases"):
        pd.read_csv(DATA / f"{t}.csv").to_sql(t, con, index=False)
    con.executescript((SQL / "00_schema.sql").read_text())
    if cookie_cats:                      # real data replaces the derived view
        con.execute("DROP VIEW ab_test")
        pd.read_csv(cookie_cats).assign(
            retention_1=lambda d: d.retention_1.astype(int),
            retention_7=lambda d: d.retention_7.astype(int)).to_sql("ab_test", con, index=False)
    con.commit(); con.close()
    print("database built:", DB)

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else None)
