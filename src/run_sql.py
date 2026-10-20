"""Run every analytics query in /sql and save results to outputs/sql_results/*.csv"""
import sqlite3, pandas as pd
from config import *

def run():
    out = OUT / "sql_results"; out.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    for f in sorted(SQL.glob("0[1-9]_*.sql")):
        df = pd.read_sql_query(f.read_text(), con)
        df.to_csv(out / f"{f.stem}.csv", index=False)
        print(f"\n== {f.stem} ({len(df)} rows) ==")
        print(df.head(8).to_string(index=False))
    con.close()

if __name__ == "__main__":
    run()
