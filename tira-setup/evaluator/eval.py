#!/usr/bin/env python3

import gzip
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def usage() -> str:
    return "Usage: /eval.py <inputDataset> <inputRun> <outputDir>"


def resolve_qrels_path(input_dataset: Path) -> Path:
    qrels_path = input_dataset / "qrels.txt"
    if not qrels_path.is_file():
        raise FileNotFoundError(f"Missing qrels.txt in {input_dataset}")
    return qrels_path


def resolve_run_path(input_run: Path) -> Path:
    if input_run.is_file():
        return input_run

    if not input_run.is_dir():
        raise FileNotFoundError(f"Run input does not exist: {input_run}")

    for candidate_name in ("run.txt", "run.txt.gz"):
        candidate = input_run / candidate_name
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(f"Missing run.txt or run.txt.gz in {input_run}")


def copy_run_to_temp(run_path: Path, destination: Path) -> None:
    if run_path.suffix == ".gz":
        with gzip.open(run_path, "rt", encoding="utf-8") as src, destination.open(
            "w", encoding="utf-8"
        ) as dst:
            shutil.copyfileobj(src, dst)
        return

    shutil.copyfile(run_path, destination)


def main() -> int:
    if len(sys.argv) != 4:
        print(usage(), file=sys.stderr)
        return 1

    input_dataset = Path(sys.argv[1])
    input_run = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    qrels_path = resolve_qrels_path(input_dataset)
    run_path = resolve_run_path(input_run)

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        temp_run_path = temp_dir / "run.txt"
        copy_run_to_temp(run_path, temp_run_path)

        result = subprocess.run(
            ["trec_eval", str(qrels_path), str(temp_run_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    (output_dir / "trec_eval.txt").write_text(result.stdout, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
