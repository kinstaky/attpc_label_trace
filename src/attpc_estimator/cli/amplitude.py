from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from .config import parse_run, parse_toml_config
from ..process.amplitude import (
    build_amplitude_histogram,
    build_labeled_amplitude_histograms,
)
from ..storage.run_paths import resolve_run_file


def main() -> None:
    args = _parse_args()
    trace_root = Path(args.trace_path).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    run_token = args.run
    run_id = int(run_token)

    if args.labeled:
        payload = build_labeled_amplitude_histograms(
            trace_path=trace_root,
            workspace=workspace,
            run=run_id,
            baseline_window_scale=args.baseline_window_scale,
            peak_separation=args.peak_separation,
            peak_prominence=args.peak_prominence,
            peak_width=args.peak_width,
        )
        output_path = workspace / f"run_{run_token}_labeled_amp.npz"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            output_path,
            run_id=payload["run_id"],
            label_keys=payload["label_keys"],
            label_titles=payload["label_titles"],
            trace_counts=payload["trace_counts"],
            histograms=payload["histograms"],
        )
        print(f"saved labeled amplitude histograms to {output_path}")
        print(f"labels: {payload['label_keys'].tolist()}")
        print(f"trace counts: {payload['trace_counts'].tolist()}")
        return

    try:
        trace_file_path = resolve_run_file(trace_root, run_token)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    histogram = build_amplitude_histogram(
        trace_file_path=trace_file_path,
        baseline_window_scale=args.baseline_window_scale,
        peak_separation=args.peak_separation,
        peak_prominence=args.peak_prominence,
        peak_width=args.peak_width,
    )
    output_path = workspace / f"run_{run_token}_amp.npy"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, histogram)

    print(f"saved amplitude histogram with shape {histogram.shape} to {output_path}")
    print(f"total histogram count: {int(histogram.sum())}")


def _parse_args() -> argparse.Namespace:
    config_path, config = parse_toml_config(
        sys.argv[1:],
        allowed_keys={
            "trace_path",
            "run",
            "workspace",
            "baseline_window_scale",
            "peak_separation",
            "peak_prominence",
            "peak_width",
            "labeled",
        },
    )
    parser = argparse.ArgumentParser(
        description="Compute peak-amplitude histograms for all traces or labeled traces",
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
        "-r",
        "--run",
        required="run" not in config,
        type=parse_run,
        default=config.get("run"),
        help="Run number",
    )
    parser.add_argument(
        "-w",
        "--workspace",
        required="workspace" not in config,
        default=config.get("workspace"),
        help="Path to store result files and locate the labels database",
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
    parser.add_argument(
        "--labeled",
        action="store_true",
        default=bool(config.get("labeled", False)),
        help="Process only labeled traces for the selected run and save one histogram per label",
    )
    return parser.parse_args()
