// The GeoSched cost model in JavaScript; mirrors geosched/model.py.
export const DCS = ['Iowa', 'Oregon', 'Singapore', 'Chile', 'Finland'];
export const PUE = [[25, 1.05], [35, 1.07], [50, 1.09], [60, 1.10], [65, 1.17]];
export const T_SUPPLY_C = 20, ECON_MAX_F = 65, P_STATIC = 6.25, P_DYNAMIC = 12.5, CORES_PER_NODE = 64;

export const cop = t => 0.0068 * t * t + 0.0008 * t + 0.458;

export function cooling(tempF) {
  if (tempF < ECON_MAX_F) for (const [top, pue] of PUE) if (tempF < top) return { mode: 'Outside air', overhead: pue - 1 };
  return { mode: 'Chillers (CRAC)', overhead: 1 / cop(T_SUPPLY_C) };
}

export function parseCSV(text) {
  const [head, ...rows] = text.trim().split(/\r?\n/).map(l => l.split(','));
  const out = {};
  head.forEach((h, i) => { out[h] = rows.map(r => +r[i]); });
  return out;
}

// For one week: every data center's temperature, price, cooling mode and all-in cost per MWh of IT energy.
export function week(temp, price, w) {
  return DCS.map(dc => {
    const t = temp[dc][w], p = price[dc][w], c = cooling(t);
    return { dc, temp: t, price: p, ...c, effective: p * (1 + c.overhead) };
  });
}

// Cost in dollars of a job (cores, utilisation 0-1, hours) at each data center in week w.
export function jobCost(rows, cores, util, hours) {
  const kw = cores * (P_STATIC + P_DYNAMIC * util) / 1000;
  return rows.map(r => ({ ...r, kwh: kw * hours * (1 + r.overhead), cost: kw * hours / 1000 * r.effective }));
}
