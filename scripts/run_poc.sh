#!/usr/bin/env bash
# PoC benchmark run (subscription-only, Claude Code headless runner).
# Three resumable stages; re-running skips completed trials.
set -uo pipefail
cd "$(dirname "$0")/.."

ALL_MODELS="claude-fable-5,claude-opus-4-8,claude-sonnet-5,claude-haiku-4-5,claude-sonnet-4-5,claude-opus-4-1"
REPO_MODELS="claude-fable-5,claude-sonnet-5,claude-haiku-4-5,claude-sonnet-4-5"

echo "=== stage 1/3: condition none — all generate tasks, 6 models ==="
lgtm run --models "$ALL_MODELS" \
  --conditions none \
  --variants v1-plain,v4-speed-pressure,v5-safety-hint \
  --trials 2 --concurrency 4 --timeout 300 --out results

echo "=== stage 2/3: repo conditions — 4 generate tasks, 4 models ==="
lgtm run --models "$REPO_MODELS" \
  --conditions clean-repo,dirty-repo \
  --task-filter user-lookup-by-email,search-products-like,order-by-column,insert-from-form \
  --variants v1-plain \
  --trials 2 --concurrency 4 --timeout 420 --out results

echo "=== stage 3/3: edit tasks — 4 models ==="
lgtm run --models "$REPO_MODELS" \
  --conditions clean-repo,dirty-repo \
  --task-filter edit- \
  --trials 2 --concurrency 4 --timeout 420 --out results

echo "=== report ==="
lgtm report results/*.jsonl --out results/report.md
echo DONE
