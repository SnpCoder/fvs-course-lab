#!/usr/bin/env bash
# Controlled comparison for the GateANN rare-label exploration.
# Run on HUST_7_dxc from fvs-course-lab.
set -euo pipefail

ROOT="/home/xianchangdeng/workspace/lessons/CSD/fvs-course-lab"
LOG="/home/xianchangdeng/workspace/lessons/CSD/logs/exploration_runs.log"
BASE="$ROOT/systems/GateANN-public"
EXP="$ROOT/systems/GateANN-explore"
DATA="$ROOT/datasets/yfcc_course_v1"
RUN_ROOT="$ROOT/course_runs"
cd "$ROOT"
: > "$LOG"

run() {
  local rid="$1"
  local repo="$2"
  local bucket="$3"
  local Ls="$4"
  shift 4
  echo "=== $rid  $(date '+%F %T') ===" >> "$LOG"
  env "$@" python3 adapters/gateann_adapter.py search \
    --repo "$repo" --dataset-root "$DATA" --tier formal --run-root "$RUN_ROOT" \
    --threads 1 --beamwidth 8 --k 10 --bucket "$bucket" --L $Ls \
    --full-adj-neighbors 32 --run-id "$rid" >> "$LOG" 2>&1
  echo "exit=$?  $(date '+%F %T')" >> "$LOG"
}

for r in 1 2 3; do
  # Baseline and the final rare-label path, same Low point.
  run "explore-base-low-r$r" "$BASE" low "320" \
    GATEANN_LABEL_SEEDS=0
  run "explore-seed20-low-r$r" "$EXP" low "320" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=1 GATEANN_SEED_LIMIT=20 GATEANN_LABEL_SEED_MAX=10000
  run "explore-seed40-low-r$r" "$EXP" low "320" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=1 GATEANN_SEED_LIMIT=40 GATEANN_LABEL_SEED_MAX=10000
  run "explore-seed60-low-r$r" "$EXP" low "320" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=1 GATEANN_SEED_LIMIT=60 GATEANN_LABEL_SEED_MAX=10000
  run "explore-seed80-low-r$r" "$EXP" low "320" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=1 GATEANN_SEED_LIMIT=80 GATEANN_LABEL_SEED_MAX=10000

  # Ablations.
  run "explore-seed40-graph-low-r$r" "$EXP" low "320" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=0 GATEANN_SEED_LIMIT=40 GATEANN_LABEL_SEED_MAX=10000
  run "explore-bfs2-low-r$r" "$EXP" low "320" \
    GATEANN_LABEL_SEEDS=0 GATEANN_TUNNEL_VALID_FRONTIER=1 GATEANN_TUNNEL_HOPS=2 GATEANN_TUNNEL_MAX_NODES=512

  # Baseline at larger L, and seed-only at L=640 (budget is deliberately not used).
  run "explore-base-low640-r$r" "$BASE" low "640" GATEANN_LABEL_SEEDS=0
  run "explore-seed40-low640-r$r" "$EXP" low "640" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=1 GATEANN_SEED_LIMIT=40 GATEANN_LABEL_SEED_MAX=10000

  # Check that Medium/High fall back to the original behavior (posting > 10k).
  run "explore-base-medium-r$r" "$BASE" medium "320" GATEANN_LABEL_SEEDS=0
  run "explore-mod-medium-r$r" "$EXP" medium "320" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=1 GATEANN_SEED_LIMIT=40 GATEANN_LABEL_SEED_MAX=10000
  run "explore-base-high-r$r" "$BASE" high "160 320 640" GATEANN_LABEL_SEEDS=0
  run "explore-mod-high-r$r" "$EXP" high "160 320 640" \
    GATEANN_LABEL_SEEDS=1 GATEANN_SEED_ONLY=1 GATEANN_SEED_LIMIT=40 GATEANN_LABEL_SEED_MAX=10000
done

echo "EXPLORATION DONE $(date '+%F %T')" >> "$LOG"
