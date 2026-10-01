# GeoSched: original simulator and interactive explainer

An interactive explanation of **Reducing Cloud Workload Costs in Geographically Distributed Data Centers with GeoSched** by Vishnuvajjhula Pranav Sai and Harsh Raj (IEEE, 2023).

- [Interactive explainer](https://harsh-github007.github.io/GeoSched/)
- [Published paper](https://ieeexplore.ieee.org/document/10307394)
- [Preprint](paper/preprint.pdf)
- [Original upstream source](https://bitbucket.org/anirudhnair/geosched/src/util/)

## Original source

`original/` contains the C++ simulator, trace processor, data-center inputs and five bundled one-day workload CSVs from Anirudh Jayakumar's original GeoSched repository, **util branch**, commit `44a629e3fd173c71fe0f1d285d79d354bfd772bb`. Source files retain upstream author headers. Unrelated binaries, generated logs, presentations and large unused archives are omitted.

The default upstream `master` branch selects destinations randomly. The `util` branch includes the cost-aware scheduler (`GEO`) and a cooling load balancer (`LOAD`). The upstream Makefile defaults to `LOAD`; the build helper below explicitly selects `GEO`.

The previous Python reimplementation, its trace-generation scripts and its reported Google/synthetic results were removed. They must not be attributed to this original simulator.

## Build and run

Requires a C++11 compiler and POSIX threads. The cost-aware source compiled with Apple Clang on an M1 Max.

```bash
bash build-original.sh
cd original/src/GeoSim
./GeoSim
```

Run from that directory: upstream paths refer to `../../datacenters/` and `../../workloads/`. The simulator writes site trace logs in its current directory. Building does not launch the experiment automatically.

### Settings and limits

- `DataCenter.cpp` defines `MAX_TIME` as 24 hours and `TIMEINC` as five minutes.
- `main.cpp` selects five bundled `5_*_1day.csv` workloads.
- These defaults are **not** the six five-day runs described in the 2023 paper. The XML configuration alone does not change all hardcoded settings.
- The cost-aware branch checks per-task/node fit, keeps latency-sensitive work local and drops a batch job when no site passes the fit check.
- Historical implementation quirks are retained: the feasibility check does not reserve capacity while checking multiple tasks, and several calculations use integer intermediates. This source snapshot is a reference, not a validated claim of exact numerical reproduction.
- No new simulation result is published here. The explainer labels the paper's reported 11.7% cost reduction and 8.2% energy reduction as paper results.

## Browser explainer

The static site uses a separate JavaScript illustration of the paper's cost equations. It is **not** the C++ simulator and does not execute Google trace jobs in the browser. Weekly temperatures and prices in `data/` were transcribed from the paper; Iowa uses the documented MISO West 2013 average of $31.81/MWh because the plotted series appears to duplicate its temperature line. See `data/weekly_price_usd_mwh.csv` for both series.

```bash
python3 -m http.server 4175
npm test
```

The original source can be inspected independently of the interactive illustration. For reproduction, first align workload duration, input mapping, admission behavior and energy accounting with the specific experiment being compared.
