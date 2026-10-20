"""Run the whole pipeline:  python run_all.py   (or)   python run_all.py --cookie-cats cookie_cats.csv"""
import subprocess, sys
from pathlib import Path
src = Path(__file__).parent / "src"
cc = sys.argv[sys.argv.index("--cookie-cats") + 1] if "--cookie-cats" in sys.argv else None
def run(script, *args):
    print(f"\n{'='*70}\n>> {script}\n{'='*70}", flush=True)
    subprocess.run([sys.executable, script, *args], cwd=src, check=True)
run("generate_data.py")
run("build_db.py", *( [str(Path(cc).resolve())] if cc else [] ))
for s in ("run_sql.py", "ab_test.py", "prepost.py", "segmentation.py", "economy_liveops.py", "dashboard.py"):
    run(s)
