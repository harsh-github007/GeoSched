"""Write traces/synthetic_trace_{A..E}.csv, calibrated to the paper's Table II and Figs 1-2."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from geosched.traces import ROOT, synthetic, write_trace  # noqa: E402

for t in "ABCDE":
    rows = synthetic(t)
    write_trace(ROOT / "traces" / f"synthetic_trace_{t}.csv", rows)
    print(f"trace {t}: {len(rows):,} jobs")
