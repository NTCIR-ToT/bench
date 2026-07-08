#!/usr/bin/env python3

import argparse
import gzip
import json
import uuid
from pathlib import Path


RUN_NAME = "naive-baseline"
DOCS_PER_QUERY = 1000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a random TREC run with UUID document ids."
    )
    parser.add_argument("queries", help="Path to the queries.jsonl file")
    parser.add_argument("output", help="Path to the output run file")
    parser.add_argument(
        "--qrels",
        help="Optional path to qrels.txt for placing the relevant document in the run",
    )
    parser.add_argument(
        "--position",
        type=int,
        help="Optional 1-based rank at which the relevant document should be placed",
    )
    return parser.parse_args()


def open_output(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "wt", encoding="utf-8")
    return path.open("w", encoding="utf-8")


def load_relevant_documents(path: Path) -> dict[str, str]:
    relevant_documents = {}

    with path.open("r", encoding="utf-8") as qrels_file:
        for line_number, line in enumerate(qrels_file, start=1):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) < 4:
                raise ValueError(f"Invalid qrels line {line_number}: {line.rstrip()}")

            query_id, _, doc_id, relevance = parts[:4]
            if int(relevance) <= 0 or query_id in relevant_documents:
                continue

            relevant_documents[query_id] = doc_id

    return relevant_documents


def main() -> None:
    args = parse_args()
    queries_path = Path(args.queries)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.position is not None and not 1 <= args.position <= DOCS_PER_QUERY:
        raise ValueError(f"--position must be between 1 and {DOCS_PER_QUERY}")
    if args.position is not None and args.qrels is None:
        raise ValueError("--position requires --qrels")

    relevant_documents = {}
    if args.qrels is not None:
        relevant_documents = load_relevant_documents(Path(args.qrels))

    with queries_path.open("r", encoding="utf-8") as queries_file, open_output(output_path) as output_file:
        for line_number, line in enumerate(queries_file, start=1):
            if not line.strip():
                continue

            query = json.loads(line)
            query_id = query.get("query_id") or query.get("id")
            if query_id is None:
                raise ValueError(f"Missing query id in line {line_number}")

            for rank in range(1, DOCS_PER_QUERY + 1):
                doc_id = str(uuid.uuid4())
                if (
                    args.position is not None
                    and rank == args.position
                    and query_id in relevant_documents
                ):
                    doc_id = relevant_documents[query_id]
                score = DOCS_PER_QUERY - rank + 1
                output_file.write(
                    f"{query_id} Q0 {doc_id} {rank} {score} {RUN_NAME}\n"
                )


if __name__ == "__main__":
    main()
