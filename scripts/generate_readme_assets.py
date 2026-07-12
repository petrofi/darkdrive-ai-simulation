"""Generate deterministic README charts from committed aggregate metrics."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = PROJECT_ROOT / "docs" / "metrics" / "readme_metrics.json"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "assets" / "readme"
DPI = 180

INK = "#172033"
MUTED = "#5B6475"
GRID = "#D9DEE8"
BACKGROUND = "#F8FAFC"
BLUE = "#0072B2"
SKY = "#56B4E9"
GREEN = "#009E73"
ORANGE = "#E69F00"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"
GRAY = "#7A8495"


def load_metrics(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Metrics source not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    require_keys(
        data,
        ("datasets", "readme_dataset_chart_ids", "models_session_c2", "closed_loop", "project_progression"),
        "metrics root",
    )
    return data


def require_keys(container: dict[str, Any], keys: tuple[str, ...], context: str) -> None:
    missing = [key for key in keys if key not in container]
    if missing:
        raise ValueError(f"Missing required fields in {context}: {', '.join(missing)}")


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titleweight": "bold",
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "figure.facecolor": BACKGROUND,
            "axes.facecolor": BACKGROUND,
            "savefig.facecolor": BACKGROUND,
            "legend.frameon": False,
        }
    )


def style_axis(axis: plt.Axes, *, grid_axis: str = "y") -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis=grid_axis, color=GRID, linewidth=0.8, alpha=0.8)
    axis.set_axisbelow(True)


def wrap_labels(labels: list[str], width: int = 15) -> list[str]:
    return ["\n".join(textwrap.wrap(label, width=width)) for label in labels]


def save_figure(figure: plt.Figure, filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    figure.savefig(
        output_path,
        dpi=DPI,
        bbox_inches="tight",
        facecolor=BACKGROUND,
        metadata={"Software": "DarkDrive generate_readme_assets.py"},
    )
    plt.close(figure)
    with Image.open(output_path) as image:
        optimized = image.convert("RGB")
        optimized.save(output_path, format="PNG", optimize=True)
    return output_path


def add_source_note(figure: plt.Figure, text: str) -> None:
    figure.text(0.01, 0.012, text, color=MUTED, fontsize=8.5, ha="left", va="bottom")


def generate_dataset_distribution(metrics: dict[str, Any]) -> Path:
    datasets_by_id = {item["id"]: item for item in metrics["datasets"]}
    selected = []
    for dataset_id in metrics["readme_dataset_chart_ids"]:
        if dataset_id not in datasets_by_id:
            raise ValueError(f"Dataset chart references unknown id: {dataset_id}")
        item = datasets_by_id[dataset_id]
        require_keys(
            item,
            ("label", "near_zero_pct", "left_pct", "right_pct", "strong_turn_pct"),
            f"dataset {dataset_id}",
        )
        selected.append(item)

    labels = [item["label"] for item in selected]
    x = np.arange(len(selected))
    width = 0.24
    figure, (direction_axis, strong_axis) = plt.subplots(
        2,
        1,
        figsize=(12, 8.2),
        gridspec_kw={"height_ratios": [2.15, 1], "hspace": 0.38},
    )
    figure.suptitle("Steering Distribution Across Dataset Stages", fontsize=19, fontweight="bold", y=0.98)
    figure.text(
        0.5,
        0.94,
        "Recovery and curve-focused data reduced straight-driving concentration while preserving direction coverage.",
        ha="center",
        color=MUTED,
        fontsize=10.5,
    )

    series = (
        ("Near-zero", "near_zero_pct", GRAY),
        ("Left", "left_pct", BLUE),
        ("Right", "right_pct", ORANGE),
    )
    for index, (name, key, color) in enumerate(series):
        values = [float(item[key]) for item in selected]
        bars = direction_axis.bar(x + (index - 1) * width, values, width, label=name, color=color)
        direction_axis.bar_label(bars, fmt="%.1f", padding=2, fontsize=8, color=INK)
    direction_axis.set_ylabel("Share of rows (%)")
    direction_axis.set_ylim(0, 66)
    direction_axis.set_xticks(x, wrap_labels(labels))
    direction_axis.legend(ncols=3, loc="upper center")
    direction_axis.set_title("Mutually exclusive steering direction buckets", loc="left", fontsize=13)
    style_axis(direction_axis)

    strong_values = [float(item["strong_turn_pct"]) for item in selected]
    strong_bars = strong_axis.bar(x, strong_values, width=0.54, color=GREEN)
    strong_axis.bar_label(strong_bars, fmt="%.1f", padding=3, fontsize=8.5, color=INK)
    strong_axis.set_ylabel("Share of rows (%)")
    strong_axis.set_ylim(0, 34)
    strong_axis.set_xticks(x, wrap_labels(labels))
    strong_axis.set_title("Strong-turn coverage (overlaps left/right categories)", loc="left", fontsize=13)
    style_axis(strong_axis)
    add_source_note(
        figure,
        "Source: committed dataset reports via docs/metrics/readme_metrics.json. Definitions: near-zero <= 0.05; strong turn >= 0.5 absolute steering.",
    )
    figure.subplots_adjust(bottom=0.12, top=0.89)
    return save_figure(figure, "dataset_distribution.png")


def generate_model_evaluation(metrics: dict[str, Any]) -> Path:
    models = metrics["models_session_c2"]
    if not models:
        raise ValueError("models_session_c2 must not be empty")
    for model in models:
        require_keys(model, ("label", "mae", "rmse", "strong_turn_mae", "evaluation_split"), "model")
        if model["evaluation_split"] != "complete Session C2, 4163 rows":
            raise ValueError("All README model comparisons must use the complete Session C2 split")

    labels = [model["label"] for model in models]
    y = np.arange(len(models))
    colors = [BLUE if model["id"] == "kaggle_jungle_mix_v1" else GRAY for model in models]
    panels = (
        ("MAE", "mae", 0.25),
        ("RMSE", "rmse", 0.36),
        ("Strong-turn MAE", "strong_turn_mae", 0.68),
    )
    figure, axes = plt.subplots(1, 3, figsize=(13.2, 6.4), sharey=True)
    figure.suptitle("Model Evaluation on the Same Session C2 Holdout", fontsize=19, fontweight="bold", y=0.98)
    figure.text(
        0.5,
        0.93,
        "Raw errors are shown on separate zero-based axes; lower is better.",
        ha="center",
        color=MUTED,
        fontsize=10.5,
    )
    for axis, (title, key, upper) in zip(axes, panels):
        values = [float(model[key]) for model in models]
        bars = axis.barh(y, values, color=colors, height=0.62)
        axis.set_xlim(0, upper)
        axis.set_xlabel("Absolute steering error")
        axis.set_title(title, loc="left", fontsize=13)
        axis.bar_label(bars, labels=[f"{value:.6f}" for value in values], padding=3, fontsize=8.5)
        style_axis(axis, grid_axis="x")
    axes[0].set_yticks(y, wrap_labels(labels, width=17))
    axes[0].invert_yaxis()
    figure.text(
        0.5,
        0.068,
        "Blue identifies Kaggle Jungle Mix V1, used in the simulator demo. It is not the best on every metric and is not a promoted release model.",
        ha="center",
        color=BLUE,
        fontsize=9.2,
    )
    add_source_note(
        figure,
        "Source: EXP-006/007/008/009/014/019 committed evaluation reports; complete 4,163-row Session C2 holdout.",
    )
    figure.subplots_adjust(left=0.18, right=0.98, bottom=0.22, top=0.86, wspace=0.25)
    return save_figure(figure, "model_evaluation_session_c2.png")


def generate_closed_loop_runtime(metrics: dict[str, Any]) -> Path:
    active = metrics["closed_loop"]["active_run"]
    require_keys(
        active,
        (
            "total_frames",
            "successful_predictions",
            "operational_inference_failures",
            "average_inference_latency_ms",
            "p95_inference_latency_ms",
            "runtime_seconds",
            "protocol_verdict",
            "emergency_stop_reason",
        ),
        "closed-loop active run",
    )

    figure = plt.figure(figsize=(12, 6.5))
    grid = figure.add_gridspec(2, 2, height_ratios=[1.05, 1], width_ratios=[1.25, 1], hspace=0.38, wspace=0.28)
    figure.suptitle("Verified Active Closed-Loop Unity Run", fontsize=20, fontweight="bold", y=0.98)
    figure.text(
        0.5,
        0.935,
        "Controlled 20-second simulation-only diagnostic on CPU",
        ha="center",
        color=MUTED,
        fontsize=10.5,
    )

    frame_axis = figure.add_subplot(grid[0, 0])
    successful = int(active["successful_predictions"])
    shutdown_rows = int(active["recorded_shutdown_rows"])
    frame_axis.barh([0], [successful], color=GREEN, height=0.42, label="Successful predictions")
    frame_axis.barh([0], [shutdown_rows], left=[successful], color=ORANGE, height=0.42, label="Controlled shutdown row")
    frame_axis.set_xlim(0, int(active["total_frames"]) * 1.08)
    frame_axis.set_yticks([])
    frame_axis.set_xlabel("Recorded frames")
    frame_axis.set_title(f"{active['total_frames']:,} frames | {successful:,} successful predictions", loc="left", fontsize=13)
    frame_axis.legend(loc="lower left", ncols=1)
    style_axis(frame_axis, grid_axis="x")

    latency_axis = figure.add_subplot(grid[1, 0])
    latency_names = ["Average", "P95"]
    latency_values = [float(active["average_inference_latency_ms"]), float(active["p95_inference_latency_ms"])]
    latency_bars = latency_axis.barh(latency_names, latency_values, color=[BLUE, SKY], height=0.55)
    latency_axis.bar_label(latency_bars, labels=[f"{value:.3f} ms" for value in latency_values], padding=4, fontsize=10)
    latency_axis.set_xlim(0, max(latency_values) * 1.35)
    latency_axis.set_xlabel("CPU model inference latency (ms)")
    latency_axis.set_title("Inference latency", loc="left", fontsize=13)
    latency_axis.invert_yaxis()
    style_axis(latency_axis, grid_axis="x")

    summary_axis = figure.add_subplot(grid[:, 1])
    summary_axis.axis("off")
    summary_lines = [
        ("Protocol verdict", str(active["protocol_verdict"]), GREEN),
        ("Runtime", f"{active['runtime_seconds']:.3f} s", INK),
        ("Operational inference failures", str(active["operational_inference_failures"]), GREEN),
        ("Backend", "EIO4 / WebSocket / Unity compat", INK),
        ("Shutdown", f"controlled {active['emergency_stop_reason']} stop", ORANGE),
    ]
    start_y = 0.88
    for index, (label, value, color) in enumerate(summary_lines):
        y_position = start_y - index * 0.17
        summary_axis.text(0.02, y_position, label.upper(), fontsize=8.5, color=MUTED, fontweight="bold")
        summary_axis.text(0.02, y_position - 0.065, value, fontsize=14, color=color, fontweight="bold")
    summary_axis.text(
        0.02,
        0.03,
        "The one unsuccessful record was produced by the bounded max-runtime shutdown; it was not an operational model failure.",
        fontsize=9,
        color=MUTED,
        wrap=True,
    )
    add_source_note(
        figure,
        "Source: sanitized aggregate from verified session 20260712T080700_749131Z; raw runtime logs remain ignored.",
    )
    figure.subplots_adjust(left=0.07, right=0.98, bottom=0.11, top=0.87)
    return save_figure(figure, "closed_loop_runtime_v1.png")


def generate_project_progression(metrics: dict[str, Any]) -> Path:
    stages = metrics["project_progression"]
    if len(stages) < 2:
        raise ValueError("project_progression requires at least two stages")
    x = np.arange(len(stages))
    figure, axis = plt.subplots(figsize=(13, 5.4))
    figure.suptitle("DarkDrive Engineering Progression", fontsize=19, fontweight="bold", y=0.96)
    figure.text(
        0.5,
        0.89,
        "Ordered verified phases; dates are intentionally omitted where a committed milestone date is not available.",
        ha="center",
        color=MUTED,
        fontsize=10,
    )
    axis.plot(x, np.zeros_like(x), color=GRID, linewidth=4, zorder=1)
    stage_colors = [GRAY, SKY, BLUE, GREEN, ORANGE, PURPLE, VERMILLION]
    axis.scatter(x, np.zeros_like(x), s=470, color=stage_colors, edgecolor=BACKGROUND, linewidth=3, zorder=2)
    for index, (position, stage) in enumerate(zip(x, stages)):
        axis.text(position, 0, str(index + 1), ha="center", va="center", color="white", fontsize=11, fontweight="bold", zorder=3)
        direction = 1 if index % 2 == 0 else -1
        axis.plot([position, position], [0.12 * direction, 0.34 * direction], color=stage_colors[index], linewidth=1.5)
        axis.text(
            position,
            0.47 * direction,
            "\n".join(textwrap.wrap(stage, width=18)),
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color=INK,
        )
    axis.set_xlim(-0.55, len(stages) - 0.45)
    axis.set_ylim(-0.9, 0.9)
    axis.axis("off")
    add_source_note(
        figure,
        "Source: committed project documentation and verified 2026-07-12 Unity compatibility/active-run evidence.",
    )
    figure.subplots_adjust(left=0.04, right=0.96, bottom=0.1, top=0.82)
    return save_figure(figure, "project_progression.png")


def main() -> int:
    try:
        configure_style()
        metrics = load_metrics(METRICS_PATH)
        outputs = [
            generate_dataset_distribution(metrics),
            generate_model_evaluation(metrics),
            generate_closed_loop_runtime(metrics),
            generate_project_progression(metrics),
        ]
        print("README assets generated successfully")
        for output in outputs:
            with Image.open(output) as image:
                print(f"- {output.relative_to(PROJECT_ROOT)}: {image.width}x{image.height}, {output.stat().st_size:,} bytes")
        print("Training-loss chart omitted: no single committed, comparable per-epoch source covers the README experiments.")
        return 0
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"README asset generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
