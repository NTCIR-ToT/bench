#!/usr/bin/env python3
"""Generate the LaTeX table body rows for the participation overview table.

Reads the per-language ``runs_by_team`` counts from
``plots/2026/participation-summary.json`` and prints the tabular rows
(one row per team, sorted alphabetically, plus a final sum row and a
per-row/column sum), matching the ``table-participation`` LaTeX table.
"""
import json
from pathlib import Path

LANGUAGES = ["en", "zh", "ja", "ko"]

SUMMARY_PATH = (
    Path(__file__).resolve().parent.parent
    / "plots" / "2026" / "participation-summary.json"
)


def load_runs_by_team_per_language(summary_path: Path) -> dict:
    with open(summary_path) as f:
        data = json.load(f)

    runs_by_language = {entry["language"]: entry["runs_by_team"] for entry in data}

    teams = sorted({team for lang in LANGUAGES for team in runs_by_language.get(lang, {})})

    return teams, runs_by_language


def main():
    teams, runs_by_language = load_runs_by_team_per_language(SUMMARY_PATH)

    column_sums = {lang: 0 for lang in LANGUAGES}
    total_sum = 0

    lines = []
    for team in teams:
        counts = [runs_by_language.get(lang, {}).get(team, 0) for lang in LANGUAGES]
        row_sum = sum(counts)
        total_sum += row_sum
        for lang, count in zip(LANGUAGES, counts):
            column_sums[lang] += count

        cells = [str(c) if c else "-" for c in counts]
        lines.append(f"{team} & " + " & ".join(cells) + f" & {row_sum}\\\\")

    lines.append("\\midrule")
    lines.append(
        "$\\sum$ & "
        + " & ".join(str(column_sums[lang]) for lang in LANGUAGES)
        + f" & {total_sum}\\\\"
    )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
