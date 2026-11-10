#!/usr/bin/env python3
"""Summarize the GateANN rare-label exploration runs.

Inputs are the 39 controlled runs under
artifacts/course_runs_results/gateann/formal_1000000/{low,medium,high}/explore-*
Each variant has 3 independent repeats. The smoke runs are deliberately ignored.
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "course_runs_results" / "gateann" / "formal_1000000"
OUT = ROOT / "exploration" / "results"
OUT.mkdir(parents=True, exist_ok=True)


def variant(run_id: str) -> str:
    if "seed40-graph" in run_id:
        return "seed40+graph"
    for tag in ("seed20", "seed40", "seed60", "seed80"):
        if tag in run_id:
            return tag
    if "bfs2" in run_id:
        return "bfs2"
    if "base" in run_id:
        return "baseline"
    if "mod" in run_id:
        return "seed-fallback"
    raise ValueError(run_id)


files = []
for path in glob.glob(str(ART / "*" / "explore-*" / "results.csv")):
    if re.search(r"-r[123]/results\.csv$", path):
        files.append(path)
assert len(files) == 39, len(files)

rows = []
for path in files:
    run_id = Path(path).parent.name
    d = pd.read_csv(path)
    d["run_id"] = run_id
    d["variant"] = variant(run_id)
    d["repeat"] = int(re.search(r"-r([123])$", run_id).group(1))
    rows.append(d)
raw = pd.concat(rows, ignore_index=True)
assert len(raw) == 51, len(raw)  # 39 process runs, high has 3 L rows

# Parse the diagnostic line emitted by the modified binary.
internal = []
for log in glob.glob(str(ART / "*" / "explore-*" / "run.log")):
    run_id = Path(log).parent.name
    if not re.search(r"-r[123]$", run_id):
        continue
    for line in Path(log).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("TUNNELSTATS L="):
            continue
        fields = {}
        for token in line.split()[1:]:
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        internal.append(
            {
                "run_id": run_id,
                "L": int(fields["L"]),
                "tunnel_valid": float(fields.get("tunnel_valid", 0)),
                "tunnel_invalid": float(fields.get("tunnel_invalid", 0)),
                "seed_candidates": float(fields.get("seed_candidates", 0)),
                "seed_inserted": float(fields.get("seed_inserted", 0)),
                "seed_valid": float(fields.get("seed_valid", 0)),
            }
        )
intdf = pd.DataFrame(internal)
# The original baseline binary does not emit TUNNELSTATS; those rows stay 0.
raw = raw.merge(intdf, on=["run_id", "L"], how="left", validate="one_to_one")
for col in ["tunnel_valid", "tunnel_invalid", "seed_candidates", "seed_inserted", "seed_valid"]:
    raw[col] = raw[col].fillna(0.0)

METRICS = [
    "recall_percent",
    "mean_latency_us",
    "qps",
    "mean_ios",
    "peak_rss_kb",
    "filter_skips",
    "tunnel_time_us",
    "process_time_us",
    "seed_candidates",
    "seed_inserted",
    "seed_valid",
    "tunnel_invalid",
]
records = []
for keys, g in raw.groupby(["variant", "bucket", "L"], sort=False):
    variant_name, bucket, L = keys
    rec = {
        "variant": variant_name,
        "bucket": bucket,
        "L": int(L),
        "n": len(g),
        "selectivity_median": g["selectivity_median"].iloc[0],
    }
    for m in METRICS:
        rec[f"{m}_median"] = g[m].median()
        rec[f"{m}_min"] = g[m].min()
        rec[f"{m}_max"] = g[m].max()
    records.append(rec)
summary = pd.DataFrame(records)
summary.to_csv(OUT / "exploration_summary.csv", index=False)

# Per-repeat paired values for the headline Low L=320 comparison.
headline = raw[(raw.bucket == "low") & (raw.L == 320) & (raw.variant.isin(["baseline", "seed40"]))]
headline = headline[
    ["variant", "repeat", "run_id", "recall_percent", "mean_latency_us", "qps", "mean_ios",
     "peak_rss_kb", "filter_skips", "seed_inserted", "seed_valid"]
].sort_values(["variant", "repeat"])
headline.to_csv(OUT / "headline_low_L320.csv", index=False)

# Seed-limit curve.
curve = summary[(summary.bucket == "low") & (summary.L == 320) & summary.variant.str.startswith("seed")]
curve = curve.sort_values("variant")
curve.to_csv(OUT / "seed_limit_curve.csv", index=False)

# Ablations at Low L=320.
abl = summary[(summary.bucket == "low") & (summary.L == 320)]
abl = abl[abl.variant.isin(["baseline", "seed40+graph", "bfs2", "seed40"])]
abl = abl.sort_values("variant")
abl.to_csv(OUT / "ablations_low_L320.csv", index=False)

# Medium/High fallback check.
fallback = summary[
    (summary.variant.isin(["baseline", "seed-fallback"]))
    & (summary.bucket.isin(["medium", "high"]))
].sort_values(["bucket", "L", "variant"])
fallback.to_csv(OUT / "fallback_medium_high.csv", index=False)

# Key facts used by the report.
base_low = summary[(summary.variant == "baseline") & (summary.bucket == "low") & (summary.L == 320)].iloc[0]
seed40 = summary[(summary.variant == "seed40") & (summary.bucket == "low") & (summary.L == 320)].iloc[0]
seed20 = summary[(summary.variant == "seed20") & (summary.bucket == "low") & (summary.L == 320)].iloc[0]
bfs = summary[(summary.variant == "bfs2") & (summary.bucket == "low") & (summary.L == 320)].iloc[0]
graph = summary[(summary.variant == "seed40+graph") & (summary.bucket == "low") & (summary.L == 320)].iloc[0]
base_low640 = summary[(summary.variant == "baseline") & (summary.bucket == "low") & (summary.L == 640)].iloc[0]
seed40_low640 = summary[(summary.variant == "seed40") & (summary.bucket == "low") & (summary.L == 640)].iloc[0]

facts = [
    ["low_baseline_L320", f"{base_low.recall_percent_median:.2f}% / {base_low.mean_latency_us_median:.1f} us / {base_low.mean_ios_median:.2f} IO"],
    ["low_seed20_L320", f"{seed20.recall_percent_median:.2f}% / {seed20.mean_latency_us_median:.1f} us / {seed20.mean_ios_median:.2f} IO"],
    ["low_seed40_L320", f"{seed40.recall_percent_median:.2f}% / {seed40.mean_latency_us_median:.1f} us / {seed40.mean_ios_median:.2f} IO"],
    ["low_seed40_L640", f"{seed40_low640.recall_percent_median:.2f}% / {seed40_low640.mean_latency_us_median:.1f} us / {seed40_low640.mean_ios_median:.2f} IO"],
    ["low_baseline_L640", f"{base_low640.recall_percent_median:.2f}% / {base_low640.mean_latency_us_median:.1f} us / {base_low640.mean_ios_median:.2f} IO"],
    ["low_seed40_plus_graph", f"{graph.recall_percent_median:.2f}% / {graph.mean_latency_us_median:.1f} us / {graph.mean_ios_median:.2f} IO"],
    ["low_bfs2", f"{bfs.recall_percent_median:.2f}% / {bfs.mean_latency_us_median:.1f} us / {bfs.mean_ios_median:.2f} IO, skips={bfs.filter_skips_median:.0f}"],
    ["rss_baseline_mib", f"{base_low.peak_rss_kb_median/1024:.1f}"],
    ["rss_seed40_mib", f"{seed40.peak_rss_kb_median/1024:.1f}"],
    ["seed40_delta_recall_pp", f"{seed40.recall_percent_median - base_low.recall_percent_median:.2f}"],
    ["seed40_delta_latency_pct", f"{(seed40.mean_latency_us_median/base_low.mean_latency_us_median-1)*100:.1f}"],
    ["seed40_delta_ios_pct", f"{(seed40.mean_ios_median/base_low.mean_ios_median-1)*100:.1f}"],
]
pd.DataFrame(facts, columns=["key", "value"]).to_csv(OUT / "key_facts.csv", index=False)

print(summary[["variant", "bucket", "L", "n", "recall_percent_median", "mean_latency_us_median", "mean_ios_median", "peak_rss_kb_median"]].to_string(index=False))
print("\nHeadline:")
print(headline.to_string(index=False))
print("\nKey facts:")
for k, v in facts:
    print(f"  {k}: {v}")
