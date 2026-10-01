"""Five-second ticks, atomic per-task placement and five-minute resource snapshots."""
from collections import deque
from dataclasses import dataclass, asdict
import heapq
import math
from .model import Settings, job_cost, overhead

@dataclass(frozen=True)
class Task:
    cpu: float
    memory: float
    def __post_init__(self):
        if not all(math.isfinite(x) and x >= 0 for x in (self.cpu,self.memory)) or self.cpu == 0:
            raise ValueError('task requires finite positive CPU and nonnegative memory')

@dataclass(frozen=True)
class Job:
    id: str
    origin: str
    arrival_s: float
    duration_s: float
    predicted_s: float
    scheduling_class: int
    utilization: float
    tasks: tuple
    def __post_init__(self):
        if not self.tasks or self.scheduling_class not in range(4):
            raise ValueError('job needs tasks and a class from 0 to 3')
        if not all(math.isfinite(x) and x >= 0 for x in (self.arrival_s,self.predicted_s)) or not math.isfinite(self.duration_s) or self.duration_s <= 0 or not 0 <= self.utilization <= 1:
            raise ValueError('invalid job timing/utilization')

def allocation(nodes, tasks):
    """First-fit with shadow reservations; returns all placements or None without mutation."""
    reserved = {}
    plan = []
    for task in tasks:
        for i, (cpu, mem) in enumerate(nodes):
            used_cpu, used_mem = reserved.get(i, (0., 0.))
            cpu -= used_cpu; mem -= used_mem
            if cpu + 1e-10 >= task.cpu and mem + 1e-10 >= task.memory:
                reserved[i] = (used_cpu + task.cpu, used_mem + task.memory)
                plan.append(i); break
        else:
            return None
    return plan

class Site:
    def __init__(self, name, nodes):
        self.name = name
        self.capacity = [tuple(n) for n in nodes]
        if not nodes or any(cpu <= 0 or mem < 0 for cpu, mem in nodes):
            raise ValueError('invalid nodes')
        self.total_cpu = sum(cpu for cpu,_ in nodes)
        self.free = [list(n) for n in nodes]
        self.queue = deque()
        self.dynamic_w = 0.
        self.busy_cpu = 0.
        self.stats = dict(arrived=0,started=0,completed=0,moved=0,rejected=0,wait_s=0.,cpu_seconds=0.,it_j=0.,cooling_j=0.,cost_usd=0.)


def simulate(jobs, node_map, profile_at, horizon_s, scheduler='geosched', settings=Settings()):
    """profile_at(name, time_s) returns Profile. Window accounting clips to horizon_s.

    Assumptions: FIFO queues, first-fit tasks, no node shutdown, fixed per-job utilization,
    predicted duration supplied by caller, no data-transfer cost, no cross-site retry.
    Snapshot infeasibility falls back to the local queue, never silently drops work.
    """
    if scheduler not in ('geosched','local') or horizon_s <= 0:
        raise ValueError('invalid scheduler/horizon')
    sites = {name:Site(name,nodes) for name,nodes in node_map.items()}
    jobs = sorted(jobs, key=lambda j:(j.arrival_s,j.id))
    if len({j.id for j in jobs}) != len(jobs) or any(j.origin not in sites for j in jobs):
        raise ValueError('job IDs must be unique and origins known')
    running = []; serial = 0; cursor = 0
    snapshots = {name:[n[:] for n in s.free] for name,s in sites.items()}
    next_share = 0
    def start(site, job, t):
        nonlocal serial
        plan = allocation(site.free,job.tasks)
        if plan is None: return False
        for i,task in zip(plan,job.tasks):
            site.free[i][0] -= task.cpu; site.free[i][1] -= task.memory
        cpu = sum(task.cpu for task in job.tasks)
        watts = cpu * settings.cores_per_normalized_cpu * settings.dynamic_w_per_core * job.utilization
        site.dynamic_w += watts; site.busy_cpu += cpu
        site.stats['started'] += 1; site.stats['moved'] += site.name != job.origin
        site.stats['wait_s'] += t - job.arrival_s
        serial += 1
        heapq.heappush(running,(t+job.duration_s,serial,site.name,job,plan,watts,cpu))
        return True
    t = 0
    while t < horizon_s:
        while running and running[0][0] <= t:
            _,_,name,job,plan,watts,cpu = heapq.heappop(running)
            site = sites[name]
            for i,task in zip(plan,job.tasks):
                site.free[i][0] += task.cpu; site.free[i][1] += task.memory
            site.dynamic_w -= watts; site.busy_cpu -= cpu; site.stats['completed'] += 1
        # Release first, then retry queues, then publish the state used for new arrivals.
        for site in sites.values():
            while site.queue and start(site,site.queue[0],t): site.queue.popleft()
        if t >= next_share:
            snapshots = {name:[n[:] for n in site.free] for name,site in sites.items()}
            next_share += settings.share_s
        while cursor < len(jobs) and jobs[cursor].arrival_s <= t:
            job = jobs[cursor];cursor += 1;sites[job.origin].stats['arrived'] += 1
            candidates = [name for name in sites if allocation(sites[name].capacity,job.tasks) is not None]
            if not candidates:
                sites[job.origin].stats['rejected'] += 1;continue
            dest = job.origin
            if scheduler == 'geosched' and job.scheduling_class < 2:
                feasible = [name for name in candidates if allocation(snapshots[name],job.tasks) is not None]
                if feasible:
                    dest = min(feasible,key=lambda name:(job_cost(sum(x.cpu for x in job.tasks),job.utilization,job.predicted_s,profile_at(name,t),settings),name))
            if allocation(sites[dest].capacity,job.tasks) is None:
                sites[job.origin].stats['rejected'] += 1;continue
            site = sites[dest]
            if site.queue or not start(site,job,t):site.queue.append(job)
        interval = min(settings.step_s,horizon_s-t)
        for name,site in sites.items():
            profile = profile_at(name,t)
            idle = site.total_cpu * settings.cores_per_normalized_cpu * settings.static_w_per_core
            it = (idle + max(0.,site.dynamic_w)) * interval
            cooling = it * overhead(profile,settings)
            site.stats['it_j'] += it;site.stats['cooling_j'] += cooling
            site.stats['cost_usd'] += (it+cooling)*profile.price_usd_mwh/3.6e9
            site.stats['cpu_seconds'] += max(0.,site.busy_cpu)*interval
        t += settings.step_s
    # Jobs completing exactly at the observation boundary count as completed.
    for end,_,name,*_ in running:
        if end <= horizon_s:sites[name].stats['completed'] += 1
    output = {}
    for name,site in sites.items():
        output[name] = dict(site.stats,queued=len(site.queue),running=site.stats['started']-site.stats['completed'],
                           energy_j=site.stats['it_j']+site.stats['cooling_j'],
                           utilization_pct=100*site.stats['cpu_seconds']/(horizon_s*site.total_cpu))
    return dict(scheduler=scheduler,horizon_s=horizon_s,settings=asdict(settings),sites=output,
                input_jobs=len(jobs),arrived_jobs=cursor,not_arrived=len(jobs)-cursor)
