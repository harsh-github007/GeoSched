"""Job traces in the paper's custom format (Table I), and a synthetic generator calibrated to Table II and Figs 1-2.

Trace columns: job_id, arrival_time, scheduled_time, finish_time (microseconds from the start of the 5-day
window), schedule_class, tasks, total_cpu, total_memory, user, sla_param1..3.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .model import DATA, DCS, TRACE_OF, nodes

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["job_id", "arrival_time", "scheduled_time", "finish_time", "schedule_class", "tasks",
          "total_cpu", "total_memory", "user", "sla_param1", "sla_param2", "sla_param3"]
HOURS = 120
JOBS_PER_HOUR = 550           # Fig. 1: most hours see 400-700 arriving jobs per trace
TARGET_UTIL = 0.15            # Fig. 6: DumbSched utilisation is 13.5-16.5% at every data center


def read_trace(path) -> dict:
    with open(path) as f:
        rows = list(csv.DictReader(f))
    a = lambda k, t=float: np.array([t(r[k]) for r in rows])
    arrival = a("arrival_time") / 1e6
    return dict(arrival_s=arrival, sched_class=a("schedule_class", int), tasks=a("tasks", int),
                cpu=a("total_cpu"), mem=a("total_memory"),
                runtime_s=np.maximum(a("finish_time") / 1e6 - a("scheduled_time") / 1e6, 1.0))


def write_trace(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(rows)


def _stats():
    with open(DATA / "trace_stats.csv") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        out.setdefault(r["trace"], []).append(
            (float(r["avg_cpu"]), float(r["avg_mem"]), float(r["avg_runtime_s"]), float(r["share_pct"]) / 100))
    return out


def synthetic(trace: str, seed: int = 0):
    """One 5-day trace matching the paper's per-class averages, class mix and hourly arrival pattern.

    Table II's CPU and memory are per task. The number of tasks per job is heavy-tailed, as in the Google
    trace, and its mean is set so that running every job locally uses about 15% of a data center's CPU.
    """
    rng = np.random.default_rng(seed + ord(trace))
    st = _stats()[trace]
    shares = np.array([s[3] for s in st])
    shares /= shares.sum()
    level = np.exp(rng.normal(0, 0.15, HOURS))
    level[rng.random(HOURS) < 0.04] *= rng.uniform(1.4, 2.0)           # occasional bursts, as in Fig. 1
    counts = rng.poisson(JOBS_PER_HOUR * level)
    arrival = np.concatenate([h * 3600 + np.sort(rng.uniform(0, 3600, c)) for h, c in enumerate(counts)])
    n = len(arrival)
    klass = rng.choice(4, size=n, p=shares)
    sd = 1.0
    runtime = np.array([rng.lognormal(np.log(st[k][2]) - sd ** 2 / 2, sd) for k in klass])
    cpu_task = np.array([st[k][0] for k in klass]) * rng.lognormal(-0.18, 0.6, n)
    mem_task = np.array([st[k][1] for k in klass]) * rng.lognormal(-0.18, 0.6, n)
    raw_tasks = np.floor(rng.pareto(1.6, n) + 1)
    _, cap_cpu, _ = nodes()
    need = TARGET_UTIL * cap_cpu * HOURS * 3600
    scale = need / float(np.sum(cpu_task * raw_tasks * np.minimum(runtime, HOURS * 3600 - arrival)))
    tasks = np.maximum(1, np.round(raw_tasks * scale)).astype(int)
    rows = []
    for i in range(n):
        at = int(arrival[i] * 1e6)
        rows.append([i, at, at, at + int(runtime[i] * 1e6), int(klass[i]), int(tasks[i]),
                     round(float(cpu_task[i] * tasks[i]), 5), round(float(mem_task[i] * tasks[i]), 5),
                     int(rng.integers(0, 900)), "", "", ""])
    return rows


def load(source: str = "synthetic") -> dict:
    """dc -> trace arrays; source is 'synthetic' or 'google' (files in traces/)."""
    out = {}
    for dc in DCS:
        path = ROOT / "traces" / f"{source}_trace_{TRACE_OF[dc]}.csv"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing: run scripts/make_synthetic_traces.py or scripts/build_google_traces.py")
        out[dc] = read_trace(path)
    return out
