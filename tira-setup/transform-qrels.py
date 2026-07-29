#!/usr/bin/env python3

from pathlib import Path
import json

def process(src, tgt):
    qids = set()
    with open(src, "r") as r, open(tgt, "w") as f:
        for l in r:
            l = json.loads(l)
            qid = 4500 + int(l["query_id"])
            assert qid not in qids
            qid = f"{qid:04d}"
            f.write(f"{qid} Q0 {l['rel_doc_id']} 1\n")


if __name__ == '__main__':
    for l in ["chinese", "english", "japanese", "korean"]:
        target_dir = Path("qrels-fixed") / l
        target_dir.mkdir(parents=True, exist_ok=True)
        process(Path(l) / "queries.jsonl", target_dir / "qrels.txt")

