---
configs:
- config_name: inputs
  data_files:
  - split: test
    path: ["queries.jsonl"]
- config_name: truths
  data_files:
  - split: test
    path: ["qrels.txt", "queries.jsonl"]

tira_configs:
  resolve_inputs_to: "."
  resolve_truths_to: "."
  baseline:
    link: https://github.com/NTCIR-ToT/bench/tree/main/tira-setup/naive-baseline
    command: /baseline.py $inputDataset/queries.jsonl $outputDir/run.txt.gz
    format:
      name: ["run.txt"]
  input_format:
    name: "*.jsonl"
  truth_format:
    name: "qrels.txt"
  evaluator:
    image: mam10eks/ntcir-tot:eval-0.0.1
    command: /eval.py $inputDataset $inputRun  $outputDir
---

# NTCIR-ToT 2026: Chinese Test Set

```
tira-cli dataset-submission --path chinese/ --task ntcir-tot --split test --dry-run
```
