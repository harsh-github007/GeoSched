import datetime as dt
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from geosched import DCS, cooling_overhead, cop, cost_rate, simulate  # noqa: E402
from geosched.model import Params  # noqa: E402


def test_cop_formula():
    assert abs(cop(20) - (0.0068 * 400 + 0.0008 * 20 + 0.458)) < 1e-12


def test_pue_table_and_crac():
    assert abs(cooling_overhead(20) - 0.05) < 1e-9       # below 25 F
    assert abs(cooling_overhead(30) - 0.07) < 1e-9
    assert abs(cooling_overhead(62) - 0.17) < 1e-9
    assert abs(cooling_overhead(80) - 1 / cop(Params().t_supply_c)) < 1e-9   # too warm: CRAC


def test_singapore_is_most_expensive_all_year():
    for day in range(0, 365, 7):
        rates = {d: cost_rate(d, day) for d in DCS}
        assert max(rates, key=rates.get) == "Singapore"


def _tiny():
    rng = np.random.default_rng(1)
    tr = {}
    for d in DCS:
        n = 300
        tr[d] = dict(arrival_s=np.sort(rng.uniform(0, 3 * 86400, n)), sched_class=rng.integers(0, 4, n),
                     cpu=rng.uniform(1, 20, n), mem=rng.uniform(1, 20, n), runtime_s=rng.uniform(60, 3600, n))
    return tr


def test_geosched_keeps_latency_sensitive_jobs_local_and_cuts_cost():
    tr = _tiny()
    start = dt.datetime(2013, 1, 15)
    dumb = simulate(tr, start, "dumbsched")
    geo = simulate(tr, start, "geosched")
    assert sum(v["moved_in"] for v in dumb.values()) == 0
    assert sum(v["jobs"] for v in geo.values()) == sum(len(t["arrival_s"]) for t in tr.values())
    local = int(np.sum(tr["Singapore"]["sched_class"] >= 2))
    assert geo["Singapore"]["jobs"] == local
    assert sum(v["job_cost_usd"] for v in geo.values()) < sum(v["job_cost_usd"] for v in dumb.values())
