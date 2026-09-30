#!/usr/bin/env python3
"""Create per-language analyses for the NTCIR-2026 Tip-of-the-Tongue task."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import click
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.manifold import TSNE


DEFAULT_METRICS = (
    "ndcg_cut_10",
    "ndcg_cut_1000",
    "recip_rank",
    "recall_1000",
)
METRIC_LABELS = {
    "ndcg_cut_10": "NDCG@10",
    "ndcg_cut_1000": "NDCG@1000",
    "recip_rank": "MRR",
    "recall_1000": "Recall@1000",
}
LLM_SYMBOLS = {
    "with-llm": r"$\checkmark$",
    "without-llm": r"$\times$",
}
TRAINING_DATA_LABELS = {
    "this-year": "This Year",
    "no-training": "None",
}
LANGUAGE_NAMES = {
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
}


def default_data_root() -> Path:
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        candidate = parent / "ntcir-results" / "ntcir-2026"
        if candidate.is_dir():
            return candidate
    return script_path.parent / "../../ntcir-results/ntcir-2026"


@dataclass
class LanguageData:
    language: str
    run_metadata: pd.DataFrame
    per_topic: pd.DataFrame
    run_results: pd.DataFrame


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as reader:
        return [json.loads(line) for line in reader if line.strip()]


def discover_languages(data_root: Path) -> list[str]:
    runs_root = data_root / "runs"
    if not runs_root.is_dir():
        raise click.ClickException(f"Missing runs directory: {runs_root}")
    return sorted(
        directory.name
        for directory in runs_root.iterdir()
        if directory.is_dir() and (directory / "metadata.jsonl").is_file()
    )


def normalized(value: object, default: str = "unknown") -> str:
    if value is None:
        return default
    value = str(value).strip()
    return value or default


def load_run_metadata(data_root: Path, language: str) -> pd.DataFrame:
    metadata_path = data_root / "runs" / language / "metadata.jsonl"
    if not metadata_path.is_file():
        raise click.ClickException(
            f"Missing metadata for {language}: {metadata_path}"
        )

    rows = []
    for entry in load_jsonl(metadata_path):
        upload = entry.get("upload_metadata") or {}
        run_id = normalized(
            upload.get("run_id")
            or entry.get("run_display_name")
            or entry.get("software")
        )
        rows.append(
            {
                "run_id": run_id,
                "team": normalized(upload.get("team") or entry.get("team")),
                "training_data": normalized(upload.get("training-data")),
                "llm": normalized(upload.get("llm")),
                "description": normalized(
                    upload.get("description") or entry.get("description"), ""
                ),
            }
        )

    metadata = pd.DataFrame(rows).drop_duplicates(subset=["run_id"], keep="last")
    if metadata.empty:
        raise click.ClickException(f"No runs found in {metadata_path}")
    return metadata.sort_values(["team", "run_id"]).reset_index(drop=True)


def evaluation_files(data_root: Path, language: str) -> list[Path]:
    files = sorted((data_root / "send-back").glob(f"*/{language}/*.eval.txt"))
    if not files:
        files = sorted(
            (data_root / "send-back-complete").glob(f"*/{language}/*.eval.txt")
        )
    if not files:
        raise click.ClickException(
            f"No evaluation files found for language {language}"
        )
    return files


def load_evaluations(
    data_root: Path, language: str, metrics: Iterable[str]
) -> pd.DataFrame:
    selected_metrics = set(metrics)
    rows = []
    for eval_path in evaluation_files(data_root, language):
        run_id = eval_path.name.removesuffix(".eval.txt").strip()
        with eval_path.open(encoding="utf-8") as reader:
            for line_number, line in enumerate(reader, start=1):
                tokens = line.split()
                if len(tokens) != 3:
                    raise click.ClickException(
                        f"Expected three columns in "
                        f"{eval_path}:{line_number}, got {line!r}"
                    )
                measure, topic_id, value = tokens
                if measure not in selected_metrics or topic_id == "all":
                    continue
                rows.append(
                    {
                        "run_id": run_id,
                        "topic_id": topic_id,
                        "metric": measure,
                        "value": float(value),
                    }
                )

    evaluations = pd.DataFrame(rows)
    if evaluations.empty:
        raise click.ClickException(
            f"None of the requested metrics occur in the {language} evaluations"
        )
    duplicates = evaluations.duplicated(["run_id", "topic_id", "metric"])
    if duplicates.any():
        duplicate = evaluations.loc[duplicates].iloc[0].to_dict()
        raise click.ClickException(f"Duplicate evaluation value: {duplicate}")
    return evaluations


def build_language_data(
    data_root: Path, language: str, metrics: list[str], primary_metric: str
) -> LanguageData:
    metadata = load_run_metadata(data_root, language)
    evaluations = load_evaluations(data_root, language, metrics)

    evaluated_runs = set(evaluations["run_id"])
    metadata_runs = set(metadata["run_id"])
    if evaluated_runs != metadata_runs:
        raise click.ClickException(
            f"Run mismatch for {language}; "
            f"missing metadata={sorted(evaluated_runs - metadata_runs)}, "
            f"missing evaluations={sorted(metadata_runs - evaluated_runs)}"
        )

    per_topic = (
        evaluations.pivot(
            index=["run_id", "topic_id"], columns="metric", values="value"
        )
        .reset_index()
        .rename_axis(columns=None)
        .merge(metadata, on="run_id", validate="many_to_one")
    )
    missing_metrics = [metric for metric in metrics if metric not in per_topic]
    if missing_metrics:
        raise click.ClickException(
            f"Missing metrics for {language}: {missing_metrics}"
        )

    topic_counts = per_topic.groupby("run_id")["topic_id"].nunique()
    if topic_counts.nunique() != 1:
        raise click.ClickException(
            f"Runs for {language} cover different topic counts: "
            f"{topic_counts.to_dict()}"
        )

    run_results = (
        per_topic.groupby(
            ["run_id", "team", "training_data", "llm"], as_index=False
        )[metrics]
        .mean()
        .sort_values(primary_metric, ascending=False)
        .reset_index(drop=True)
    )
    return LanguageData(language, metadata, per_topic, run_results)


def write_participation_summary(data: LanguageData, output_dir: Path) -> dict:
    summary = {
        "language": data.language,
        "language_name": LANGUAGE_NAMES.get(data.language, data.language),
        "num_groups": int(data.run_metadata["team"].nunique()),
        "num_runs": int(len(data.run_metadata)),
        "num_topics": int(data.per_topic["topic_id"].nunique()),
        "runs_by_team": {
            key: int(value)
            for key, value in data.run_metadata["team"].value_counts().items()
        },
        "runs_by_training_data": {
            key: int(value)
            for key, value in data.run_metadata["training_data"].value_counts().items()
        },
        "runs_by_llm_usage": {
            key: int(value)
            for key, value in data.run_metadata["llm"].value_counts().items()
        },
    }
    (output_dir / "participation-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def latex_escape(value: object) -> str:
    text = str(value)
    for source, replacement in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
    ):
        text = text.replace(source, replacement)
    return text


def bold_best_scores(
    latex_results: pd.DataFrame,
    metrics: list[str],
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Wrap the highest value of each metric column in \\textbf{}.

    When ``group_columns`` is given, the highest value is determined
    separately within each group (e.g. per language) instead of over the
    whole table.
    """
    latex_results = latex_results.copy()
    metric_columns = [METRIC_LABELS.get(metric, metric) for metric in metrics]
    metric_columns = [column for column in metric_columns if column in latex_results.columns]
    if not metric_columns:
        return latex_results

    groups = (
        latex_results.groupby(group_columns).groups
        if group_columns
        else {None: latex_results.index}
    )
    for column in metric_columns:
        latex_results[column] = latex_results[column].map(lambda value: f"{value:.4f}")
    for indices in groups.values():
        for column in metric_columns:
            best_index = latex_results.loc[indices, column].astype(float).idxmax()
            latex_results.loc[best_index, column] = (
                r"\textbf{" + latex_results.loc[best_index, column] + "}"
            )
    return latex_results


def write_results_table(
    results: pd.DataFrame,
    output_dir: Path,
    stem: str,
    text_columns: list[str],
    caption: str,
    label: str,
    latex_column_transforms: dict[str, dict] | None = None,
    bold_max_metrics: list[str] | None = None,
    bold_group_columns: list[str] | None = None,
    custom_latex_builder=None,
) -> None:
    results.to_csv(output_dir / f"{stem}.csv", index=False, float_format="%.4f")
    (output_dir / f"{stem}.html").write_text(
        results.to_html(index=False, float_format=lambda value: f"{value:.4f}"),
        encoding="utf-8",
    )

    latex_results = results.rename(columns=METRIC_LABELS).copy()
    transforms = latex_column_transforms or {}
    for column, mapping in transforms.items():
        latex_results[column] = latex_results[column].map(mapping)
    for column in text_columns:
        if column in transforms:
            continue
        latex_results[column] = latex_results[column].map(latex_escape)
    if bold_max_metrics:
        column_format = "".join(
            "l" if pd.api.types.is_object_dtype(latex_results[column]) else "r"
            for column in latex_results.columns
        )
        latex_results = bold_best_scores(
            latex_results, bold_max_metrics, bold_group_columns
        )
    else:
        column_format = None
    if custom_latex_builder is not None:
        latex = custom_latex_builder(latex_results, column_format, caption, label)
    else:
        latex_results = latex_results.rename(columns=latex_escape)
        latex = latex_results.to_latex(
            index=False,
            float_format="%.4f",
            escape=False,
            caption=caption,
            label=label,
            column_format=column_format,
        )
    (output_dir / f"{stem}.tex").write_text(latex, encoding="utf-8")


def build_grouped_latex_table(
    latex_results: pd.DataFrame,
    column_format: str | None,
    caption: str,
    label: str,
    group_column: str,
    header_labels: dict[str, str] | None = None,
) -> str:
    """Render a LaTeX table with a \\midrule between groups and the group
    column collapsed into a \\multirow cell instead of being repeated."""
    labels = header_labels or {}
    columns = list(latex_results.columns)
    headers = [latex_escape(labels.get(column, column)) for column in columns]
    if column_format is None:
        column_format = "".join(
            "l" if pd.api.types.is_object_dtype(latex_results[column]) else "r"
            for column in columns
        )
    column_format = "@{}" + column_format + "@{}"
    group_index = columns.index(group_column)

    lines = [
        r"\begin{table}",
        r"\caption{" + caption + "}",
        r"\label{" + label + "}",
        r"\begin{tabular}{" + column_format + "}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
    ]
    groups = list(latex_results.groupby(group_column, sort=False))
    for group_position, (group_value, group_df) in enumerate(groups):
        rows = group_df.reset_index(drop=True)
        for row_position, row in rows.iterrows():
            values = [str(value) for value in row.tolist()]
            if row_position == 0:
                values[group_index] = (
                    r"\multirow{" + str(len(rows)) + "}{*}{" + str(group_value) + "}"
                )
            else:
                values[group_index] = ""
            lines.append(" & ".join(values) + r" \\")
        if group_position < len(groups) - 1:
            lines.append(r"\midrule")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


def write_result_tables(
    data: LanguageData, output_dir: Path, metrics: list[str]
) -> None:
    columns = ["run_id", "team", "training_data", "llm", *metrics]
    results = data.run_results[columns].copy()
    write_results_table(
        results,
        output_dir,
        "results",
        ["run_id", "team", "training_data", "llm"],
        caption=f"NTCIR-2026 ToT results for {data.language}.",
        label=f"tab:results-{data.language}",
    )


def write_combined_result_table(
    all_results: pd.DataFrame,
    output_dir: Path,
    metrics: list[str],
    primary_metric: str,
) -> None:
    columns = ["language", "run_id", "team", "training_data", "llm", *metrics]
    results = (
        all_results[columns]
        .sort_values(["language", primary_metric], ascending=[True, False])
        .reset_index(drop=True)
    )
    results["language"] = results["language"].map(
        lambda value: LANGUAGE_NAMES.get(value, value)
    )
    write_results_table(
        results,
        output_dir,
        "table-results-all-languages",
        ["language", "run_id", "team", "training_data", "llm"],
        caption="NTCIR-2026 ToT results across all languages.",
        label="table-results-all-languages",
        latex_column_transforms={
            "training_data": TRAINING_DATA_LABELS,
            "llm": LLM_SYMBOLS,
        },
        bold_max_metrics=metrics,
        bold_group_columns=["language"],
        custom_latex_builder=lambda latex_results, column_format, caption, label: (
            build_grouped_latex_table(
                latex_results,
                column_format,
                caption,
                label,
                group_column="language",
                header_labels={
                    "language": "Language",
                    "run_id": "Run",
                    "team": "Team",
                    "llm": "LLM",
                },
            )
        ),
    )


def write_combined_best_per_team_table(
    all_results: pd.DataFrame,
    output_dir: Path,
    metrics: list[str],
    primary_metric: str,
) -> None:
    columns = ["language", "run_id", "team", "training_data", "llm", *metrics]
    best_per_team = (
        all_results[columns]
        .sort_values(primary_metric, ascending=False)
        .groupby(["language", "team"], as_index=False)
        .first()
    )
    best_per_team["language"] = best_per_team["language"].map(
        lambda value: LANGUAGE_NAMES.get(value, value)
    )
    results = best_per_team.sort_values(
        ["language", primary_metric], ascending=[True, False]
    ).reset_index(drop=True)
    write_results_table(
        results,
        output_dir,
        "results-all-languages-best-per-team",
        ["language", "run_id", "team", "training_data", "llm"],
        caption="NTCIR-2026 ToT best run per team across all languages.",
        label="tab:results-all-languages-best-per-team",
        latex_column_transforms={"llm": LLM_SYMBOLS},
    )


def save_figure(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", dpi=600)
    plt.close(fig)


def plot_metric_distribution_by_run(
    data: LanguageData, output_dir: Path, metrics: list[str]
) -> None:
    fig, axes = plt.subplots(
        1, len(metrics), figsize=(max(4 * len(metrics), 8), 5), sharey=True
    )
    for ax, metric in zip(np.atleast_1d(axes), metrics):
        order = data.run_results.sort_values(metric)["run_id"].tolist()
        values = [
            data.per_topic.loc[data.per_topic["run_id"] == run_id, metric].to_numpy()
            for run_id in order
        ]
        ax.boxplot(
            values,
            tick_labels=order,
            flierprops={"marker": "d", "markersize": 3},
        )
        ax.tick_params(axis="x", labelrotation=90, labelsize=6)
        ax.set_title(METRIC_LABELS.get(metric, metric))
        ax.set_ylim(0, 1)
    save_figure(fig, output_dir / "metric-distribution-by-run.pdf")


def plot_metric_distribution_by_topic(
    data: LanguageData, output_dir: Path, metrics: list[str]
) -> None:
    fig, axes = plt.subplots(
        len(metrics), 1, figsize=(20, max(3 * len(metrics), 4)), squeeze=False
    )
    for row, metric in enumerate(metrics):
        ax = axes[row, 0]
        grouped = data.per_topic.groupby("topic_id")[metric]
        order = grouped.median().sort_values().index
        means = grouped.mean().reindex(order)
        medians = grouped.median().reindex(order)
        lower = grouped.quantile(0.25).reindex(order)
        upper = grouped.quantile(0.75).reindex(order)
        x = np.arange(len(order))
        ax.fill_between(x, lower, upper, color="lightgrey", label="IQR")
        ax.plot(x, means, color="grey", label="mean")
        ax.plot(x, medians, color="black", linestyle="--", label="median")
        ax.set_ylabel(METRIC_LABELS.get(metric, metric))
        ax.set_ylim(0, 1)
        ax.set_xticks(x)
        ax.set_xticklabels(order, rotation=90, fontsize=3)
        ax.legend(loc="upper left")
    save_figure(fig, output_dir / "metric-distribution-by-topic.pdf")


def plot_metric_correlations(
    data: LanguageData, output_dir: Path, metrics: list[str]
) -> None:
    pairs = [
        (metrics[left], metrics[right])
        for left in range(len(metrics) - 1)
        for right in range(left + 1, len(metrics))
    ]
    columns = min(3, len(pairs))
    rows = math.ceil(len(pairs) / columns)
    fig, axes = plt.subplots(rows, columns, figsize=(4 * columns, 3.5 * rows))
    axes = list(np.atleast_1d(axes).flat)
    for ax, (y_metric, x_metric) in zip(axes, pairs):
        ax.scatter(
            data.run_results[x_metric],
            data.run_results[y_metric],
            alpha=0.6,
            color="grey",
        )
        ax.set_xlabel(METRIC_LABELS.get(x_metric, x_metric))
        ax.set_ylabel(METRIC_LABELS.get(y_metric, y_metric))
        tau = data.run_results[[x_metric, y_metric]].corr(method="kendall").iloc[0, 1]
        ax.set_title(f"Kendall's tau = {tau:.3f}")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    for ax in axes[len(pairs) :]:
        ax.axis("off")
    save_figure(fig, output_dir / "metric-correlation.pdf")


def plot_tsne(
    data: LanguageData, output_dir: Path, primary_metric: str
) -> None:
    matrix = data.per_topic.pivot(
        index="run_id", columns="topic_id", values=primary_metric
    ).fillna(0)
    if len(matrix) < 3:
        return

    components = TSNE(
        n_components=2,
        perplexity=min(5, len(matrix) - 1),
        init="pca",
        learning_rate="auto",
        random_state=32,
    ).fit_transform(matrix)
    frame = pd.DataFrame(components, columns=["x", "y"], index=matrix.index)
    frame = frame.join(data.run_metadata.set_index("run_id")[["team"]])

    markers = (
        "o",
        "p",
        "P",
        "*",
        "H",
        "+",
        "X",
        "x",
        "d",
        "v",
        "s",
        "^",
        "<",
        ">",
    )
    fig, ax = plt.subplots(figsize=(9, 9))
    for index, (team, group) in enumerate(frame.groupby("team")):
        ax.scatter(
            group["x"],
            group["y"],
            marker=markers[index % len(markers)],
            label=team,
        )
        for run_id, row in group.iterrows():
            ax.annotate(
                run_id,
                (row["x"], row["y"]),
                xytext=(3, -3),
                textcoords="offset points",
                fontsize=6,
            )
    ax.legend(loc="best")
    ax.set_xlabel("latent dimension 1")
    ax.set_ylabel("latent dimension 2")
    ax.set_xticks([])
    ax.set_yticks([])
    save_figure(fig, output_dir / "tsne-runs-by-team.pdf")


def plot_run_category(
    data: LanguageData,
    output_dir: Path,
    primary_metric: str,
    category: str,
    filename: str,
) -> None:
    order = data.run_results.sort_values(primary_metric)["run_id"].tolist()
    fig, ax = plt.subplots(figsize=(max(12, len(order) * 0.35), 4))
    sns.boxplot(
        data=data.per_topic,
        x="run_id",
        y=primary_metric,
        hue=category,
        order=order,
        dodge=False,
        palette="colorblind",
        flierprops={"marker": "d", "markersize": 3},
        ax=ax,
    )
    ax.tick_params(axis="x", rotation=90, labelsize=6)
    ax.set_xlabel(None)
    ax.set_ylabel(METRIC_LABELS.get(primary_metric, primary_metric))
    ax.set_ylim(0, 1)
    ax.legend(title=category.replace("_", " "), bbox_to_anchor=(1, 1))
    save_figure(fig, output_dir / filename)


def write_topic_summary(
    data: LanguageData, output_dir: Path, metrics: list[str]
) -> None:
    rows = []
    for metric in metrics:
        medians = data.per_topic.groupby("topic_id")[metric].median()
        rows.append(
            {
                "metric": metric,
                "topics_with_median_zero": int((medians == 0).sum()),
                "topics_with_median_one": int((medians == 1).sum()),
                "median_topic_score": float(medians.median()),
            }
        )
    pd.DataFrame(rows).to_csv(output_dir / "topic-summary.csv", index=False)


def analyze_language(
    data_root: Path,
    output_root: Path,
    language: str,
    metrics: list[str],
    primary_metric: str,
) -> tuple[dict, pd.DataFrame]:
    data = build_language_data(data_root, language, metrics, primary_metric)
    output_dir = output_root / language
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = write_participation_summary(data, output_dir)
    write_result_tables(data, output_dir, metrics)
    write_topic_summary(data, output_dir, metrics)
    plot_metric_distribution_by_run(data, output_dir, metrics)
    plot_metric_distribution_by_topic(data, output_dir, metrics)
    plot_metric_correlations(data, output_dir, metrics)
    plot_tsne(data, output_dir, primary_metric)
    plot_run_category(
        data,
        output_dir,
        primary_metric,
        "training_data",
        "performance-by-training-data.pdf",
    )
    plot_run_category(
        data,
        output_dir,
        primary_metric,
        "llm",
        "performance-by-llm-usage.pdf",
    )

    results = data.run_results.copy()
    results.insert(0, "language", language)
    return summary, results


@click.command()
@click.option(
    "--data-root",
    type=click.Path(path_type=Path, file_okay=False),
    default=default_data_root,
    show_default=True,
    help="Directory containing runs/, send-back/, and aggregated results.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("plots/2026"),
    show_default=True,
    help="Directory in which language-specific outputs are created.",
)
@click.option(
    "--language",
    "languages",
    multiple=True,
    help="Language code to process. Repeat to select multiple languages.",
)
@click.option(
    "--metric",
    "metrics",
    multiple=True,
    help="trec_eval measure to analyze. Repeat to select multiple measures.",
)
@click.option(
    "--primary-metric",
    default="ndcg_cut_1000",
    show_default=True,
    help="Measure used to rank runs and order topics.",
)
def main(
    data_root: Path,
    output_dir: Path,
    languages: tuple[str, ...],
    metrics: tuple[str, ...],
    primary_metric: str,
) -> None:
    """Generate tables and plots for every selected language."""
    data_root = data_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    selected_languages = list(languages) or discover_languages(data_root)
    selected_metrics = list(metrics) or list(DEFAULT_METRICS)

    if primary_metric not in selected_metrics:
        raise click.UsageError("--primary-metric must also be included in --metric")
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    all_results = []
    for language in selected_languages:
        click.echo(
            f"Analyzing {LANGUAGE_NAMES.get(language, language)} ({language})"
        )
        summary, results = analyze_language(
            data_root,
            output_dir,
            language,
            selected_metrics,
            primary_metric,
        )
        summaries.append(summary)
        all_results.append(results)

    (output_dir / "participation-summary.json").write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    combined_results = pd.concat(all_results, ignore_index=True)
    write_combined_result_table(
        combined_results,
        output_dir,
        selected_metrics,
        primary_metric,
    )
    write_combined_best_per_team_table(
        combined_results,
        output_dir,
        selected_metrics,
        primary_metric,
    )
    click.echo(f"Wrote analyses to {output_dir}")


if __name__ == "__main__":
    main()
