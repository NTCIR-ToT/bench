#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
dataset_root="$(cd -- "$script_dir/.." && pwd)"
output_root="${1:-$script_dir}"

languages=(english chinese japanese korean)
positions=(1 10 100)

for language in "${languages[@]}"; do
  queries="$dataset_root/$language/queries.jsonl"
  qrels="$dataset_root/$language/qrels.txt"

  for position in "${positions[@]}"; do
    output_dir="$output_root/${language}-position-${position}"
    mkdir -p "$output_dir"

    python3 "$script_dir/baseline.py" \
      "$queries" \
      "$output_dir/run.txt.gz" \
      --qrels "$qrels" \
      --position "$position"
  done
done
