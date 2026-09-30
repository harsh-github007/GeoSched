"""GeoSim: an event-driven simulator of five data centers sharing one meta-scheduler.

Every data center receives its own job trace. On arrival a job is placed by the scheduler:
  * DumbSched runs every job at the data center it arrived at.
  * GeoSched runs latency-sensitive jobs (classes 2-3) locally and sends batch jobs (classes 0-1) to the
    data center with the lowest Cost(j, dc), among those whose last shared state shows room for the job.
A job that does not fit where it is sent waits in that data center's queue.
"""
from __future__ import annotations

import datetime as dt
import heapq
from collections import deque

import numpy as np

from .model import DCS, J_PER_MWH, Params, job_power_w, nodes, profile, cost_rate

WINDOW_S = 5 * 86400


def _day_of_year(start: dt.datetime, t: float) -> float:
    return (start - dt.datetime(start.year, 1, 1)).total_seconds() / 86400 + t / 86400


def simulate(traces: dict, start: dt.datetime, scheduler: str = "geosched", p: Params = Params(), seed: int = 0):
    """traces: dc -> dict of numpy arrays (arrival_s, sched_class, cpu, mem, runtime_s), times from window start."""
    rng = np.random.default_rng(seed)
    n_nodes, cap_cpu, cap_mem = nodes()
    free_cpu = {d: cap_cpu for d in DCS}
    free_mem = {d: cap_mem for d in DCS}
    shared = dict(free_cpu)                    # last utilisation each data center published
    next_share = 0.0
    running = []                               # heap of (end, seq, dc, cpu, mem)
    queue = {d: deque() for d in DCS}
    acc = {d: dict(jobs=0, moved_in=0, cpu_seconds=0.0, it_j=0.0, cool_j=0.0, cost=0.0, dyn_j=0.0,
                   dyn_cool_j=0.0, dyn_cost=0.0) for d in DCS}

    # all arrivals, in time order
    arr = []
    for d in DCS:
        tr = traces[d]
        util = np.clip(rng.beta(2.0, 7.0, size=len(tr["arrival_s"])), 0.01, 1.0)   # mean 0.22 (Birke et al. 2012)
        for i in range(len(tr["arrival_s"])):
            arr.append((float(tr["arrival_s"][i]), d, int(tr["sched_class"][i]), min(float(tr["cpu"][i]), cap_cpu),
                        min(float(tr["mem"][i]), cap_mem), float(tr["runtime_s"][i]), float(util[i])))
    arr.sort(key=lambda x: x[0])
    seq = 0

    def start_job(t, dc, job):
        nonlocal seq
        _, origin, klass, cpu, mem, rt, u = job
        free_cpu[dc] -= cpu
        free_mem[dc] -= mem
        seq += 1
        heapq.heappush(running, (t + rt, seq, dc, cpu, mem))
        _, price, ovh = profile(dc, _day_of_year(start, t), p)
        tot_w, dyn_w = job_power_w(cpu, u, p)
        a = acc[dc]
        a["jobs"] += 1
        a["moved_in"] += origin != dc
        a["cpu_seconds"] += cpu * max(0.0, min(t + rt, WINDOW_S) - t)
        a["it_j"] += tot_w * rt
        a["cool_j"] += tot_w * rt * ovh
        a["cost"] += tot_w * rt * (1 + ovh) * price / J_PER_MWH
        a["dyn_j"] += dyn_w * rt
        a["dyn_cool_j"] += dyn_w * rt * ovh
        a["dyn_cost"] += dyn_w * rt * (1 + ovh) * price / J_PER_MWH

    def fits(dc, job):
        return free_cpu[dc] >= job[3] - 1e-9 and free_mem[dc] >= job[4] - 1e-9

    def finish_until(t):
        while running and running[0][0] <= t:
            end, _, dc, cpu, mem = heapq.heappop(running)
            free_cpu[dc] += cpu
            free_mem[dc] += mem
            q = queue[dc]
            while q and fits(dc, q[0]):
                start_job(end, dc, q.popleft())

    for job in arr:
        t, origin, klass = job[0], job[1], job[2]
        finish_until(t)
        while next_share <= t:
            shared = dict(free_cpu)
            next_share += p.share_interval_s
        dc = origin
        if scheduler == "geosched" and klass in p.batch_classes:
            day = _day_of_year(start, t)
            ok = [d for d in DCS if shared[d] >= job[3]] or [origin]
            dc = min(ok, key=lambda d: cost_rate(d, day, p))
        if fits(dc, job) and not queue[dc]:
            start_job(t, dc, job)
        else:
            queue[dc].append(job)
    finish_until(float("inf"))

    out = {}
    for d in DCS:
        a = acc[d]
        # idle power of every core for the whole window, cooled at the window's mean overhead
        _, price, ovh = profile(d, _day_of_year(start, WINDOW_S / 2), p)
        idle_j = cap_cpu * p.cores_per_node * p.p_static_w * WINDOW_S
        out[d] = dict(
            jobs=a["jobs"], moved_in=a["moved_in"],
            utilization_pct=100 * a["cpu_seconds"] / (cap_cpu * WINDOW_S),
            job_energy_kj=(a["it_j"] + a["cool_j"]) / 1e3, job_cost_usd=a["cost"],
            dynamic_energy_kj=(a["dyn_j"] + a["dyn_cool_j"]) / 1e3, dynamic_cost_usd=a["dyn_cost"],
            cooling_energy_kj=a["cool_j"] / 1e3,
            idle_energy_kj=idle_j * (1 + ovh) / 1e3,
        )
    return out
