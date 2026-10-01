"""Run a labeled demonstration or user-supplied normalized task trace."""
import argparse
from dataclasses import asdict
import hashlib
import csv
import datetime as dt
import json
import random
from pathlib import Path
from .model import Profile, Settings
from .engine import Job, Task, simulate
ROOT = Path(__file__).resolve().parent.parent
NAMES = ['Iowa','Oregon','Singapore','Chile','Finland']
def weekly(file):
    with open(ROOT/'data'/file) as f:return list(csv.DictReader(f))
def profile_provider(start):
    temp, price = weekly('weekly_temp_f.csv'),weekly('weekly_price_usd_mwh.csv')
    def at(name,t):
        day = (start-dt.datetime(start.year,1,1)).total_seconds()/86400+t/86400
        w = min(int(day//7),52)
        return Profile(name,float(temp[w][name]),float(price[w][name]))
    return at
def demo_jobs():
    rng=random.Random(17);out=[]
    for name in NAMES:
        for i in range(100):
            duration=rng.choice([30,60,120,240])
            out.append(Job(f'{name}-{i}',name,rng.randrange(0,1800),duration,120,rng.randrange(4),.22,
                           tuple(Task(.125,.1) for _ in range(rng.randrange(1,5)))))
    return out
def trace_jobs(path):
    rows=json.loads(Path(path).read_text())
    return [Job(str(j['id']),j['origin'],j['arrival_s'],j['duration_s'],j['predicted_s'],j['scheduling_class'],
                j['utilization'],tuple(Task(**x) for x in j['tasks'])) for j in rows]
def table_nodes():
    with open(ROOT/'data/nodes.csv') as f:
        rows=list(csv.DictReader(f))
    return [(float(r['cpu']),float(r['memory'])) for r in rows for _ in range(int(r['node_count']))]
def main():
    p=argparse.ArgumentParser();p.add_argument('--trace');p.add_argument('--full-capacity',action='store_true')
    p.add_argument('--seconds',type=int,default=3600);p.add_argument('--start',default='2013-01-15')
    p.add_argument('--output',default='results/demo.json');p.add_argument('--all-months',action='store_true')
    p.add_argument('--settings',help='JSON overrides for simulator.model.Settings')
    args=p.parse_args()
    if args.seconds<=0:p.error('--seconds must be positive')
    settings=Settings(**json.loads(Path(args.settings).read_text())) if args.settings else Settings()
    jobs=trace_jobs(args.trace) if args.trace else demo_jobs()
    nodes=table_nodes() if args.full_capacity else [(1.,1.)]*8
    start=dt.datetime.fromisoformat(args.start)
    starts=[start.replace(month=m,day=15) for m in [1,3,5,7,9,11]] if args.all_months else [start]
    results=[]
    for date in starts:
        profiles=profile_provider(date)
        runs={s:simulate(jobs,{n:nodes for n in NAMES},profiles,args.seconds,s,settings) for s in ['local','geosched']}
        totals={s:{'cost_usd':sum(x['cost_usd'] for x in r['sites'].values()),'energy_j':sum(x['energy_j'] for x in r['sites'].values()),'completed':sum(x['completed'] for x in r['sites'].values())} for s,r in runs.items()}
        results.append(dict(start=date.isoformat(),runs=runs,totals=totals));print(date.date(),totals,flush=True)
    fingerprint=hashlib.sha256(json.dumps([asdict(j) for j in jobs],sort_keys=True).encode()).hexdigest()
    out=dict(trace_sha256=fingerprint,input_jobs=len(jobs),settings=asdict(settings),demo_seed=None if args.trace else 17,source='user-supplied normalized task trace' if args.trace else 'synthetic demonstration, not Google data',
             capacity='Table IV' if args.full_capacity else '8 identical nodes per site (demonstration)',
             assumptions='See MODEL.md; no numerical reproduction claim',experiments=results)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
