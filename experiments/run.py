"""Run GeoSched and DumbSched for alternate months of 2013, as in the paper (Section VI-B).

Each run starts on the 15th at 00:00 GMT and lasts five days. Results go to results/<source>.json.

    python experiments/run.py                 # synthetic traces
    python experiments/run.py google          # traces built from Google's cluster trace
"""
import datetime as dt
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from geosched import load, simulate  # noqa: E402

MONTHS = [1, 3, 5, 7, 9, 11]
SCHEDULERS = ["dumbsched", "geosched"]


def one(args):
    source, month, sched = args
    t0 = time.time()
    res = simulate(load(source), dt.datetime(2013, month, 15), sched)
    return source, month, sched, res, time.time() - t0


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "synthetic"
    jobs = [(source, m, s) for m in MONTHS for s in SCHEDULERS]
    out = {"source": source, "runs": []}
    with ProcessPoolExecutor() as ex:
        for src, m, s, res, secs in ex.map(one, jobs):
            print(f"{dt.date(2013, m, 1):%b} {s:9s} {secs:5.1f}s")
            out["runs"].append({"month": m, "scheduler": s, "datacenters": res})
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / f"{source}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
