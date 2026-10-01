"""Paper equations 1–11, with SI units and explicit assumptions."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Settings:
    static_w_per_core: float = 6.25
    dynamic_w_per_core: float = 12.5
    cores_per_normalized_cpu: int = 64
    supply_c: float = 20
    step_s: int = 5
    share_s: int = 300
    def __post_init__(self):
        if self.step_s <= 0 or self.share_s <= 0 or self.share_s % self.step_s:
            raise ValueError('share_s must be a positive multiple of step_s')
        if not all(math.isfinite(x) for x in (self.static_w_per_core,self.dynamic_w_per_core,self.supply_c)) or min(self.static_w_per_core, self.dynamic_w_per_core) < 0 or self.cores_per_normalized_cpu <= 0:
            raise ValueError('invalid power or core settings')

@dataclass(frozen=True)
class Profile:
    name: str
    temp_f: float
    price_usd_mwh: float
    economizer: bool = True
    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.temp_f, self.price_usd_mwh)) or self.price_usd_mwh < 0:
            raise ValueError('profile must have finite temperature and nonnegative price')

def cop(supply_c):
    return .0068 * supply_c ** 2 + .0008 * supply_c + .458

def overhead(profile, settings=Settings()):
    # Table V: lower bounds inclusive, upper bounds exclusive; 65°F uses CRAC.
    if profile.economizer:
        for top, pue in ((25,1.05),(35,1.07),(50,1.09),(60,1.10),(65,1.17)):
            if profile.temp_f < top:
                return pue - 1
    return 1 / cop(settings.supply_c)

def job_cost(cpu, utilization, duration_s, profile, settings=Settings()):
    """Incremental placement cost (Eq. 9–10); idle power is accounted once site-wide."""
    if cpu < 0 or duration_s < 0 or not 0 <= utilization <= 1:
        raise ValueError('invalid job power inputs')
    dynamic_w = cpu * settings.cores_per_normalized_cpu * settings.dynamic_w_per_core * utilization
    return dynamic_w * duration_s * (1 + overhead(profile, settings)) * profile.price_usd_mwh / 3.6e9
