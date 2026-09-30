"""Energy, cooling and cost model of GeoSched (Sai and Raj, IEEE 2023), Section V.

E_total = E_server + E_cooling
P_core(u) = P_static + P_dynamic_peak * u                    (Eq. 3)
P_j = c * P_core(u),  E_j = P_j * t                          (Eqs. 4-5)
CRAC:  P_CRAC = P_dc / COP,  COP = 0.0068 T^2 + 0.0008 T + 0.458   (Eqs. 6-7, T = supply air, deg C)
Air economizer:  P_air = (PUE - 1) * P_dc, PUE from Table V  (Eq. 8)
Cost(j, dc) = T_j * P_total(j, dc) * C_MWh(dc);  dc_j = argmin Cost   (Eqs. 9-11)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
DCS = ["Iowa", "Oregon", "Singapore", "Chile", "Finland"]
TRACE_OF = {"Iowa": "A", "Oregon": "B", "Singapore": "C", "Chile": "D", "Finland": "E"}
J_PER_MWH = 3.6e9


@dataclass
class Params:
    """Model settings. The paper does not print every constant; the defaults below are stated assumptions."""
    p_static_w: float = 6.25          # idle watts per core (2013-era 16-core server idling near 100 W)
    p_dynamic_w: float = 12.5         # extra watts per core at 100% utilisation (peak near 300 W)
    cores_per_node: int = 64          # the paper: "max core count in node to be 64"; CPU 1.0 = 64 cores
    t_supply_c: float = 20.0          # CRAC supply-air temperature
    economizer_max_f: float = 65.0    # outside air cooling only below 65 F (top of Table V)
    share_interval_s: int = 300       # data centers share utilisation every 5 minutes
    batch_classes: tuple = (0, 1)     # classes 0-1 may move to another data center; 2-3 stay local
    iowa_price: str = "Iowa"          # "Iowa" (MISO West 2013 average) or "Iowa_as_plotted" (paper's Fig. 4 series)


def cop(t_supply_c: float) -> float:
    return 0.0068 * t_supply_c ** 2 + 0.0008 * t_supply_c + 0.458


def _pue_table():
    with open(DATA / "pue.csv") as f:
        return [(float(r["max_temp_f"]), float(r["pue"])) for r in csv.DictReader(f)]


PUE = _pue_table()


def cooling_overhead(temp_f: float, p: Params = Params()) -> float:
    """Cooling watts per watt of IT power: air economizer (PUE - 1) when cool enough, otherwise CRAC (1 / COP)."""
    if temp_f < p.economizer_max_f:
        for top, pue in PUE:
            if temp_f < top:
                return pue - 1
    return 1 / cop(p.t_supply_c)


def _weekly(name):
    with open(DATA / name) as f:
        rows = list(csv.DictReader(f))
    return {k: [float(r[k]) for r in rows] for k in rows[0] if k != "week"}


TEMP_F = _weekly("weekly_temp_f.csv")
PRICE = _weekly("weekly_price_usd_mwh.csv")


def week_of(day_of_year: float) -> int:
    return min(int(day_of_year // 7), 52)


def profile(dc: str, day_of_year: float, p: Params = Params()):
    """(temperature F, price $/MWh, cooling overhead) for a data center on a given day of 2013."""
    w = week_of(day_of_year)
    t = TEMP_F[dc][w]
    price = PRICE[p.iowa_price if dc == "Iowa" else dc][w]
    return t, price, cooling_overhead(t, p)


def job_power_w(cpu: float, util: float, p: Params = Params()):
    """(total, dynamic) watts drawn by a job using `cpu` normalised CPU at utilisation `util`."""
    cores = cpu * p.cores_per_node
    return cores * (p.p_static_w + p.p_dynamic_w * util), cores * p.p_dynamic_w * util


def cost_rate(dc: str, day_of_year: float, p: Params = Params()) -> float:
    """Dollars per joule of IT energy, including cooling: the ranking GeoSched minimises (Eq. 10)."""
    _, price, ovh = profile(dc, day_of_year, p)
    return (1 + ovh) * price / J_PER_MWH


def nodes():
    with open(DATA / "nodes.csv") as f:
        rows = list(csv.DictReader(f))
    n = sum(int(r["node_count"]) for r in rows)
    cpu = sum(int(r["node_count"]) * float(r["cpu"]) for r in rows)
    mem = sum(int(r["node_count"]) * float(r["memory"]) for r in rows)
    return n, cpu, mem
