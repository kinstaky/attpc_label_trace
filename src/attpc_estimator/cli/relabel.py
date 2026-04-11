from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from ..process.relabel import (
    RELABEL_LABEL_CHOICES,
    build_relabel_rows,
    print_ratio,
    ratio_items_for_label,
)
from ..storage.run_paths import format_run_id
from .config import parse_run, parse_toml_config
from .progress import tqdm_reporter


def main() -> None:
    args = _parse_args()
    trace_path = Path(args.trace_path).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    run_token = args.run
    selected_run = int(run_token) if run_token is not None else None
    run_name = format_run_id(selected_run) if selected_run is not None else None

    if not workspace.is_dir():
        raise SystemExit(f"workspace not found: {workspace}")

    try:
        with tqdm_reporter("Relabeling traces") as progress:
            rows, metrics = build_relabel_rows(
                trace_path=trace_path,
                workspace=workspace,
                run=selected_run,
                label=args.label,
                baseline_window_scale=args.baseline_window_scale,
                peak_separation=args.peak_separation,
                peak_prominence=args.peak_prominence,
                peak_width=args.peak_width,
                progress=progress,
            )
    except NotImplementedError as exc:
        raise SystemExit(str(exc)) from exc

    if run_token is None:
        output_path = workspace / "labeled_relabel.npy"
    else:
        output_path = workspace / f"run_{run_name}_labeled_relabel.npy"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, rows)

    print(f"saved relabel rows with shape {rows.shape} to {output_path}")
    print(f"total traces: {len(rows)}")
    for name, ratio in ratio_items_for_label(args.label, metrics):
        print_ratio(name, ratio)


def _parse_args() -> argparse.Namespace:
    config_path, config = parse_toml_config(
        sys.argv[1:],
        allowed_keys={
            "trace_path",
            "workspace",
            "run",
            "label",
            "baseline_window_scale",
            "peak_separation",
            "peak_prominence",
            "peak_width",
        },
    )
    parser = argparse.ArgumentParser(
        description="Relabel labeled traces using FFT CDF and amplitude heuristics",
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        default=str(config_path),
        help="Path to a TOML config file. Defaults to config.toml.",
    )
    parser.add_argument(
        "-t",
        "--trace-path",
        required="trace_path" not in config,
        default=config.get("trace_path"),
        help="Path to a trace file or a directory containing run_<run>.h5 files",
    )
    parser.add_argument(
        "-w",
        "--workspace",
        required="workspace" not in config,
        default=config.get("workspace"),
        help="Workspace directory containing the SQLite labels database and outputs",
    )
    parser.add_argument(
        "-r",
        "--run",
        type=parse_run,
        default=config.get("run"),
        help="Optional run identifier. When omitted, relabel labeled traces across all runs present in both workspace and database.",
    )
    parser.add_argument(
        "--label",
        choices=RELABEL_LABEL_CHOICES,
        required="label" not in config,
        default=config.get("label"),
        help="Relabel mode: noise uses the current zero-peak heuristic, oscillation uses the FFT CDF rule, saturation is reserved for future implementation.",
    )
    parser.add_argument(
        "--baseline-window-scale",
        type=float,
        default=config.get("baseline_window_scale", 10.0),
        help="Baseline-removal filter scale used before taking the FFT",
    )
    parser.add_argument(
        "--peak-separation",
        type=float,
        default=config.get("peak_separation", 50.0),
        help="Minimum separation between peaks",
    )
    parser.add_argument(
        "--peak-prominence",
        type=float,
        default=config.get("peak_prominence", 20.0),
        help="Prominence of peaks",
    )
    parser.add_argument(
        "--peak-width",
        type=float,
        default=config.get("peak_width", 50.0),
        help="Maximum width of peaks",
    )
    return parser.parse_args()
