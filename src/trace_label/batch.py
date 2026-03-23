from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path
import sys

import h5py
import numpy as np
from numba import njit
from tqdm import tqdm

from .cli_config import parse_toml_config


PAD_TRACE_OFFSET = 5
CDF_THRESHOLDS = np.arange(1, 151, dtype=np.int64)
CDF_VALUE_BINS = 100


def main() -> None:
    args = _parse_args()
    input_path = Path(args.input_file).expanduser().resolve()
    output_path = _resolve_output_path(input_path=input_path, output_file=args.output_file)

    if not input_path.is_file():
        raise SystemExit(f"input file not found: {input_path}")

    histogram = build_trace_cdf_histogram(
        input_path=input_path,
        baseline_window_scale=args.baseline_window_scale,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, histogram)

    print(f"saved CDF histogram with shape {histogram.shape} to {output_path}")
    print(f"total histogram count: {int(histogram.sum())}")
    print(f"thresholds: {CDF_THRESHOLDS.tolist()}")


def _parse_args() -> argparse.Namespace:
    config_path, config = parse_toml_config(
        sys.argv[1:],
        section_names=("batch",),
        allowed_keys={"input_file", "output_file", "baseline_window_scale"},
    )
    parser = argparse.ArgumentParser(
        description="Compute a 2D histogram of transformed CDF values for all pad traces",
    )
    parser.add_argument(
        "-c",
        "--connfig",
        "--config",
        dest="config_file",
        default=str(config_path),
        help="Path to a TOML config file. Defaults to config.toml.",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        required="input_file" not in config,
        default=config.get("input_file"),
        help="Path to the trace input file",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default=config.get("output_file"),
        help="Optional output .npy path. Defaults to <input-stem>_cdf_hist2d.npy next to the input file.",
    )
    parser.add_argument(
        "--baseline-window-scale",
        type=float,
        default=config.get("baseline_window_scale", 20.0),
        help="Baseline-removal filter scale used before taking the FFT",
    )
    return parser.parse_args()


def _resolve_output_path(input_path: Path, output_file: str | None) -> Path:
    if output_file:
        return Path(output_file).expanduser().resolve()
    return input_path.with_name(f"{input_path.stem}_cdf_hist2d.npy")


def build_trace_cdf_histogram(
    input_path: Path,
    baseline_window_scale: float = 20.0,
    thresholds: np.ndarray = CDF_THRESHOLDS,
) -> np.ndarray:
    with h5py.File(input_path, "r") as handle:
        events = handle["events"]
        min_event = int(events.attrs["min_event"])
        max_event = int(events.attrs["max_event"])
        bad_events = {int(event_id) for event_id in events.attrs["bad_events"]}
        event_counts = _collect_event_counts(events=events, min_event=min_event, max_event=max_event, bad_events=bad_events)
        total_traces = sum(trace_count for _, trace_count in event_counts)
        histogram = np.zeros((len(thresholds), CDF_VALUE_BINS), dtype=np.int64)

        with tqdm(total=total_traces, desc="Processing pad traces", unit="trace") as progress:
            for event_id, trace_count in event_counts:
                pads = events[f"event_{event_id}"]["get"]["pads"]
                traces = np.asarray(pads[:, PAD_TRACE_OFFSET:], dtype=np.float32)
                cleaned = preprocess_traces(traces, baseline_window_scale=baseline_window_scale)
                spectrum = compute_frequency_distribution(cleaned)
                samples = sample_cdf_points(spectrum, thresholds=thresholds)
                _accumulate_cdf_histogram_numba(samples, histogram)
                progress.update(trace_count)
                progress.set_postfix_str(f"event={event_id}")

    return histogram


def _collect_event_counts(
    events: h5py.Group,
    min_event: int,
    max_event: int,
    bad_events: set[int],
) -> list[tuple[int, int]]:
    event_counts: list[tuple[int, int]] = []
    for event_id in range(min_event, max_event + 1):
        if event_id in bad_events:
            continue
        pads = events[f"event_{event_id}"]["get"]["pads"]
        trace_count = int(pads.shape[0])
        if trace_count > 0:
            event_counts.append((event_id, trace_count))
    return event_counts


def preprocess_traces(traces: np.ndarray, baseline_window_scale: float) -> np.ndarray:
    traces_array = np.asarray(traces, dtype=np.float32)
    if traces_array.ndim != 2:
        raise ValueError(f"expected a 2D trace matrix, got shape {traces_array.shape}")

    trace_matrix = np.array(traces_array, copy=True)
    sample_count = trace_matrix.shape[1]

    if sample_count < 2:
        return trace_matrix

    trace_matrix[:, 0] = trace_matrix[:, 1]
    trace_matrix[:, -1] = trace_matrix[:, -2]

    bases = _replace_baseline_peaks(trace_matrix)
    baseline_filter = _get_baseline_filter(sample_count=sample_count, baseline_window_scale=baseline_window_scale)
    transformed = np.fft.rfft(bases, axis=1)
    filtered = np.fft.irfft(
        transformed * baseline_filter[np.newaxis, :],
        n=sample_count,
        axis=1,
    ).astype(np.float32, copy=False)
    return trace_matrix - filtered


def compute_frequency_distribution(traces: np.ndarray) -> np.ndarray:
    trace_matrix = np.asarray(traces, dtype=np.float32)
    if trace_matrix.ndim != 2:
        raise ValueError(f"expected a 2D trace matrix, got shape {trace_matrix.shape}")
    return np.abs(np.fft.rfft(trace_matrix, axis=1)).astype(np.float32, copy=False)


def sample_cdf_points(spectrum: np.ndarray, thresholds: np.ndarray = CDF_THRESHOLDS) -> np.ndarray:
    spectrum_array = np.asarray(spectrum, dtype=np.float32)
    if spectrum_array.ndim != 2:
        raise ValueError(f"expected a 2D spectrum matrix, got shape {spectrum_array.shape}")
    thresholds_array = np.asarray(thresholds, dtype=np.int64)
    return _sample_cdf_points_numba(spectrum_array, thresholds_array)


@njit(cache=True)
def _replace_baseline_peaks(trace_matrix: np.ndarray) -> np.ndarray:
    bases = trace_matrix.copy()
    row_count, sample_count = bases.shape

    for row_index in range(row_count):
        row = bases[row_index]

        mean = 0.0
        for sample_index in range(sample_count):
            mean += float(row[sample_index])
        mean /= sample_count

        variance = 0.0
        for sample_index in range(sample_count):
            diff = float(row[sample_index]) - mean
            variance += diff * diff
        sigma = np.sqrt(variance / sample_count)
        cutoff = sigma * 1.5

        valid_sum = 0.0
        valid_count = 0
        for sample_index in range(sample_count):
            if abs(float(row[sample_index]) - mean) <= cutoff:
                valid_sum += float(row[sample_index])
                valid_count += 1

        replacement = mean if valid_count == 0 else valid_sum / valid_count
        for sample_index in range(sample_count):
            if abs(float(row[sample_index]) - mean) > cutoff:
                row[sample_index] = replacement

    return bases


@lru_cache(maxsize=None)
def _get_baseline_filter(sample_count: int, baseline_window_scale: float) -> np.ndarray:
    window = np.arange(sample_count, dtype=np.float32) - (sample_count // 2)
    full_filter = np.fft.ifftshift(np.sinc(window / baseline_window_scale)).astype(np.float32, copy=False)
    return np.ascontiguousarray(full_filter[: sample_count // 2 + 1])


@njit(cache=True)
def _accumulate_cdf_histogram_numba(samples: np.ndarray, histogram: np.ndarray) -> None:
    row_count, column_count = samples.shape
    value_bin_count = histogram.shape[1]

    for row_index in range(row_count):
        for column_index in range(column_count):
            value = float(samples[row_index, column_index])
            if value <= 0.0:
                value_bin_index = 0
            elif value >= 1.0:
                value_bin_index = value_bin_count - 1
            else:
                value_bin_index = int(value * value_bin_count)

            histogram[column_index, value_bin_index] += 1


@njit(cache=True)
def _sample_cdf_points_numba(spectrum: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    row_count, bin_count = spectrum.shape
    threshold_count = thresholds.shape[0]
    samples = np.zeros((row_count, threshold_count), dtype=np.float32)

    for row_index in range(row_count):
        total = 0.0
        for bin_index in range(bin_count):
            total += float(spectrum[row_index, bin_index])
        if total <= 0.0:
            continue

        cumulative = np.empty(bin_count, dtype=np.float32)
        running = 0.0
        for bin_index in range(bin_count):
            running += float(spectrum[row_index, bin_index]) / total
            cumulative[bin_index] = running

        for threshold_index in range(threshold_count):
            threshold = thresholds[threshold_index]
            if threshold <= 0:
                samples[row_index, threshold_index] = 0.0
            elif threshold >= bin_count:
                samples[row_index, threshold_index] = 1.0
            else:
                samples[row_index, threshold_index] = cumulative[threshold - 1]

    return samples


if __name__ == "__main__":
    main()
