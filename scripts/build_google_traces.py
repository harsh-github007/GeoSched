"""Build traces/google_trace_{A..E}.csv from Google's 2011 cluster trace (clusterdata-2011-2).

As in the paper: five traces of five consecutive days each (25 of the trace's 29 days), one per data center.
Needs internet access and about 3 GB of downloads; files are cached in traces/raw/ and processed one at a time.

    python scripts/build_google_traces.py            # all 500 parts of job and task events
    python scripts/build_google_traces.py --parts 50 # a quick test on the first 50 parts (about 3 days)
"""
import argparse
import csv
import gzip
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from geosched.traces import ROOT, write_trace  # noqa: E402

BASE = "https://storage.googleapis.com/clusterdata-2011-2"
RAW = ROOT / "traces" / "raw"
START_US = 600 * 10**6              # the trace begins 600 s after time zero
DAY_US = 86400 * 10**6
SUBMIT, SCHEDULE, EVICT, FAIL, FINISH, KILL, LOST = range(7)


def fetch(kind, i):
    name = f"part-{i:05d}-of-00500.csv.gz"
    path = RAW / kind / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(f"{BASE}/{kind}/{name}", timeout=120) as r:
                    data = r.read()
                path.write_bytes(data)
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 4:
                    raise
                print(f"  retry {kind}/{name}: {e}")
                time.sleep(3 * (attempt + 1))
    return path


def rows(path):
    with gzip.open(path, "rt", newline="") as f:
        yield from csv.reader(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", type=int, default=500)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    parts = range(args.parts)

    jobs = {}
    print("job events...")
    with ThreadPoolExecutor(args.workers) as ex:
        for n, path in enumerate(ex.map(lambda i: fetch("job_events", i), parts)):
            for r in rows(path):
                t, jid, ev = int(r[0]), int(r[2]), int(r[3])
                j = jobs.setdefault(jid, {"submit": None, "schedule": None, "end": None, "class": int(r[5]), "user": r[4]})
                if ev == SUBMIT and j["submit"] is None:
                    j["submit"] = t
                elif ev == SCHEDULE and j["schedule"] is None:
                    j["schedule"] = t
                elif ev in (FAIL, FINISH, KILL, LOST):
                    j["end"] = t
            if n % 50 == 0:
                print(f"  {n + 1}/{len(parts)} parts, {len(jobs):,} jobs")

    print("task events (CPU and memory requests)...")
    seen, cpu, mem = {}, {}, {}
    with ThreadPoolExecutor(args.workers) as ex:
        for n, path in enumerate(ex.map(lambda i: fetch("task_events", i), parts)):
            for r in rows(path):
                if r[5] != "0" or not r[9]:
                    continue
                jid, idx = int(r[2]), int(r[3])
                b = seen.get(jid)
                if b is None:
                    b = seen[jid] = bytearray()
                if idx >= len(b):
                    b.extend(b"\0" * (idx + 1 - len(b)))
                if b[idx]:
                    continue
                b[idx] = 1
                cpu[jid] = cpu.get(jid, 0.0) + float(r[9])
                mem[jid] = mem.get(jid, 0.0) + float(r[10] or 0)
            if n % 50 == 0:
                print(f"  {n + 1}/{len(parts)} parts")

    for k, trace in enumerate("ABCDE"):
        lo, hi = START_US + 5 * k * DAY_US, START_US + 5 * (k + 1) * DAY_US
        out = []
        for jid, j in jobs.items():
            if j["submit"] is None or not (lo <= j["submit"] < hi) or j["schedule"] is None or j["end"] is None:
                continue
            if jid not in cpu or j["end"] <= j["schedule"]:
                continue
            out.append([jid, j["submit"] - lo, j["schedule"] - lo, j["end"] - lo, j["class"], int(sum(seen[jid])),
                        round(cpu[jid], 5), round(mem[jid], 5), j["user"][:12], "", "", ""])
        out.sort(key=lambda r: r[1])
        write_trace(ROOT / "traces" / f"google_trace_{trace}.csv", out)
        print(f"trace {trace}: {len(out):,} jobs")


if __name__ == "__main__":
    main()
