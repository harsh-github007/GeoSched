# GeoSched — paper-informed simulator and interactive explainer

A new independent implementation of the method described in **Reducing Cloud Workload Costs in Geographically Distributed Data Centers with GeoSched**, by Vishnuvajjhula Pranav Sai and Harsh Raj (IEEE, 2023).

[Explainer](https://harsh-github007.github.io/GeoSched/) · [Paper](https://ieeexplore.ieee.org/document/10307394) · [Preprint PDF](https://harsh-github007.github.io/GeoSched/paper/preprint.pdf) · [Model specification](https://raw.githubusercontent.com/harsh-github007/GeoSched/main/MODEL.md)

## What is implemented

A discrete-time simulator with individual task-to-node placement, atomic resource reservations, stale per-node snapshots, latency-class routing, queues, job completion, and whole-site IT/cooling/cost accounting. Five-second steps and five-minute sharing follow the paper. Power constants, queue policy, profile interpolation and other unspecified choices are documented in `MODEL.md`.

The implementation prevents pooled capacity from masking machine fragmentation, avoids counting idle power per job, clips energy to the run window, and reports unserved work.

## Run locally

Python 3.9+; the simulator uses only the standard library.

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m simulator.run --all-months --output results/demo.json
python3 -m http.server 4175
```

The included result is a **synthetic demonstration**: 500 jobs, 8 machines per site, one-hour windows, six seasonal profiles. It is not the paper's Google trace and does not establish reproduction of the paper's reported savings.

For a prepared normalized task trace (schema in `MODEL.md`):

```bash
python3 -m simulator.run --trace your-trace.json --full-capacity \
  --seconds 432000 --all-months --output results/your-run.json
```

This selects five days and Table IV node capacities. Pass `--settings settings.json` to override power constants, supply temperature or time intervals; the complete settings and input fingerprint are recorded in every result. Actual successful Google jobs, accurate task requests, runtime estimates trained only on historical data, and original hourly prices/weather must be supplied to make a stronger reproduction comparison. No download or expensive full experiment starts automatically.

## Browser model

```bash
npm test
```

The browser prices a single hypothetical job using the paper's incremental-cost equations and lets you choose latency class, origin and site availability. It is an explanatory model, separate from the task-level Python simulator. The year chart uses the weekly figure-derived CSVs in `data/`. The site presents paper results separately from generated synthetic demo results.

## Original reference source

`original/` retains Anirudh Jayakumar's cost-aware `util` branch at commit `44a629e3fd173c71fe0f1d285d79d354bfd772bb`, with original author headers. [Upstream](https://bitbucket.org/anirudhnair/geosched/src/util/). It is not used by the new engine. Its one-day defaults and historical implementation quirks differ from the published settings. `bash build-original.sh` builds it explicitly with `GEO`; run from `original/src/GeoSim`.

## Result integrity

The paper reports 11.7% lower cost and 8.2% less energy. Those values are **not** targets to tune this implementation toward. New results are published with their inputs, settings and unfinished-work counts. See `MODEL.md` for every assumption and known limitation.
