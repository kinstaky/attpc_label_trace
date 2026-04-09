from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from .config import parse_run, parse_toml_config
from ..process.filter import (
    DEFAULT_TRACE_LIMIT,
    UNLIMITED_TRACE_LIMIT,
    build_filter_rows,
    default_output_name,
    normalize_amplitude_range,
)


def main() -> None:
    args = _parse_args()
    trace_root = Path(args.trace_path).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    run_token = args.run
    run_id = int(run_token)
    amplitude_range = normalize_amplitude_range(args.amplitude)
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output is not None
        else workspace / default_output_name(run_token, amplitude_range, args.oscillation)
    )

    rows = build_filter_rows(
        trace_path=trace_root,
        run=run_id,
        amplitude_range=amplitude_range,
        oscillation=args.oscillation,
        baseline_window_scale=args.baseline_window_scale,
        peak_separation=args.peak_separation,
        peak_prominence=args.peak_prominence,
        peak_width=args.peak_width,
        limit=args.limit,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, rows)

    print(f"saved {len(rows)} filter rows to {output_path}")


def _parse_args() -> argparse.Namespace:
    config_path, config = parse_toml_config(
        sys.argv[1:],
        allowed_keys={
            "trace_path",
            "workspace",
            "run",
            "amplitude",
            "oscillation",
            "unlimit",
            "baseline_window_scale",
            "peak_separation",
            "peak_prominence",
            "peak_width",
            "limit",
            "output",
        },
    )
    parser = argparse.ArgumentParser(
        description="Generate a filter file containing the first matching traces in one run",
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
        help="Workspace directory where the filter file will be written",
    )
    parser.add_argument(
        "-r",
        "--run",
        required="run" not in config,
        type=parse_run,
        default=config.get("run"),
        help="Run identifier to filter",
    )
    parser.add_argument(
        "--amplitude",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=config.get("amplitude"),
        help="Inclusive lower and upper bounds for the highest detected peak amplitude",
    )
    parser.add_argument(
        "--oscillation",
        action="store_true",
        default=bool(config.get("oscillation", False)),
        help="Keep traces whose CDF F(60) is below 0.6",
    )
    parser.add_argument(
        "--baseline-window-scale",
        type=float,
        default=config.get("baseline_window_scale", 10.0),
        help="Baseline-removal filter scale used before peak detection and FFT",
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
        "--limit",
        type=int,
        default=config.get("limit", DEFAULT_TRACE_LIMIT),
        help=f"Maximum number of matching traces to keep, default {DEFAULT_TRACE_LIMIT}",
    )
    parser.add_argument(
        "--unlimit",
        action="store_true",
        default=bool(config.get("unlimit", False)),
        help="Disable the row limit and keep every matching trace in the selected run",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=config.get("output"),
        help="Optional explicit output .npy path",
    )
    args = parser.parse_args()
    if args.amplitude is None and not args.oscillation:
        parser.error("at least one filter criterion is required: --amplitude MIN MAX and/or --oscillation")
    if args.unlimit:
        args.limit = UNLIMITED_TRACE_LIMIT
    return args
