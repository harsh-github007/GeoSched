# Model specification and provenance

This is a new independent implementation informed by the supplied GeoSched preprint. It is not claimed to reproduce Table VI numerically. The original C++ source is retained under `original/` for reference only; it is not called by the new simulator.

## Paper-defined behavior

| Requirement | Source | Implementation |
|---|---|---|
| Five sites and A–E mapping | Table III | Iowa, Oregon, Singapore, Chile, Finland |
| Heterogeneous machine CPU/memory | Table IV | `--full-capacity` creates all 12,583 listed nodes per site |
| Classes 0–1 may move; 2–3 remain local | Section III-C | Explicit class policy |
| Atomic task allocation on nodes | Simulator description + task resource model | First-fit with temporary reservations and rollback on failure |
| Five-second time steps | Section VI-A2 | `Settings.step_s=5` |
| Five-minute resource sharing | Section VI-A2 | Cached per-node snapshots every 300 seconds |
| Static + utilization-weighted dynamic power | Eq. 2–3 | Constant idle baseline plus active-job dynamic power |
| Cooling overhead | Eq. 6–8, Table V | COP and temperature-dependent PUE |
| Incremental job cost | Eq. 9–11 | Dynamic power + its cooling, converted from J to MWh |
| Idle energy included | End of Section VI-B | Every configured node remains powered throughout the window |
| Six alternate months, day 15 | Section VI-B | `--all-months` selects Jan/Mar/May/Jul/Sep/Nov |
| Five days per experiment | Section III-C, VI-B | Pass `--seconds 432000`; default demo is one hour |

**Node count discrepancy:** Table IV's counts sum to 12,583, although descriptions of the Google cluster often use 12,584. The new implementation follows the actual provided table instead of silently adding a node.

## Explicit assumptions

- Default idle/dynamic constants: 6.25 / 12.5 W per core. The paper cites a power study without listing its chosen values. These are illustrative defaults, not recovered author constants.
- 64 cores per normalized CPU unit follows the paper's maximum-core assumption.
- CRAC supply air is 20°C (assumption). Economizers are available at all five sites by default (assumption; each Profile can disable them).
- PUE intervals are lower-inclusive and upper-exclusive; exactly 65°F uses CRAC. Table boundaries are not defined precisely by the paper.
- CPU utilization is supplied per job. Demo jobs use 0.22 (assumption); no invented fit to the IBM distribution is claimed.
- Each job supplies a predicted duration separately from its actual duration. The demo uses a fixed 120-second prediction; no look-ahead to actual duration in placement.
- FIFO local queues, no preemption or migration after admission, no power-down, no network costs or WAN delays. SLA fields from Table I do not define enforceable deadlines, so deadline compliance is not claimed.
- Snapshot infeasibility falls back to local queuing. Jobs that cannot fit even an empty destination are explicitly rejected. Stale state can queue a job at its chosen destination. First-fit can reject feasible packings; it is not an optimal bin-packing solver.
- Tick-level completion rounds execution to the next 5-second boundary. Energy integrates the occupied resources over these ticks, clipped to the observation window. Queue, running, completed and rejected counts are all exported.
- Weekly temperature/price CSVs were transcribed from paper figures. They are not the original hourly archives. Iowa's default uses the MISO average retained from the prior data preparation, not the suspicious plotted series. A full reproduction needs verified hourly inputs.

## Trace contract

JSON array of jobs. CPU/memory are normalized relative to the largest machine, with **individual task requests** preserved:

```json
[{
  "id": "job-1", "origin": "Iowa", "arrival_s": 0,
  "duration_s": 60, "predicted_s": 120,
  "scheduling_class": 0, "utilization": 0.22,
  "tasks": [{"cpu": 0.25, "memory": 0.1}]
}]
```

No Google download occurs automatically. The upstream bundled one-day traces store aggregate requests, not individual task demands. Dividing aggregates equally would be an additional approximation, so they are not silently converted into paper-quality task traces.

## Reporting rules

- Label synthetic examples as demonstrations, not Google re-runs.
- Keep paper results separate from generated results.
- Compare equal workloads and report completed, running, queued and rejected work before interpreting savings.
- Account for idle power once, site-wide; use incremental power for ranking.
- Preserve parameters, capacity, duration and input provenance in every JSON result.
