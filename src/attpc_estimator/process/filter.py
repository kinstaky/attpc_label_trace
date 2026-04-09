from __future__ import annotations

from pathlib import Path

import numpy as np

from ..process.amplitude import max_peak_amplitude
from ..storage.run_paths import resolve_run_file
from ..utils.trace_data import compute_frequency_distribution, sample_cdf_points
from .trace_scan import scan_cleaned_trace_batches

DEFAULT_TRACE_LIMIT = 1000
OSCILLATION_CDF_BIN = 60
OSCILLATION_CUTOFF = 0.6
UNLIMITED_TRACE_LIMIT = -1


def build_filter_rows(
    trace_path: Path,
    run: int,
    amplitude_range: tuple[float, float] | None = None,
    oscillation: bool = False,
    baseline_window_scale: float = 10.0,
    peak_separation: float = 50.0,
    peak_prominence: float = 20.0,
    peak_width: float = 50.0,
    limit: int = DEFAULT_TRACE_LIMIT,
) -> np.ndarray:
    if amplitude_range is None and not oscillation:
        raise ValueError("at least one filter criterion is required")
    if amplitude_range is not None and amplitude_range[0] > amplitude_range[1]:
        raise ValueError("amplitude minimum must be less than or equal to the maximum")
    if limit == 0 or limit < UNLIMITED_TRACE_LIMIT:
        raise ValueError("limit must be positive or use --unlimit")

    run_file = resolve_run_file(trace_path, run)

    selected_rows: list[tuple[int, int, int]] = []
    unlimited = limit == UNLIMITED_TRACE_LIMIT

    def handle_batch(event_id: int, cleaned: np.ndarray) -> None:
        if not unlimited and len(selected_rows) >= limit:
            return
        oscillation_values = _compute_oscillation_values(cleaned) if oscillation else None

        for trace_id, row in enumerate(cleaned):
            if not _matches_filter(
                row=row,
                trace_id=trace_id,
                amplitude_range=amplitude_range,
                oscillation=oscillation,
                oscillation_values=oscillation_values,
                peak_separation=peak_separation,
                peak_prominence=peak_prominence,
                peak_width=peak_width,
            ):
                continue
            selected_rows.append((run, event_id, trace_id))
            if not unlimited and len(selected_rows) >= limit:
                break

    scan_cleaned_trace_batches(
        run_file,
        baseline_window_scale=baseline_window_scale,
        handler=handle_batch,
        progress_desc="Scanning run",
    )

    if not selected_rows:
        return np.empty((0, 3), dtype=np.int64)
    return np.asarray(selected_rows, dtype=np.int64)


def build_amplitude_filter_rows(
    trace_path: Path,
    run: int,
    min_amplitude: float,
    max_amplitude: float,
    baseline_window_scale: float = 10.0,
    peak_separation: float = 50.0,
    peak_prominence: float = 20.0,
    peak_width: float = 50.0,
    limit: int = DEFAULT_TRACE_LIMIT,
) -> np.ndarray:
    return build_filter_rows(
        trace_path=trace_path,
        run=run,
        amplitude_range=(min_amplitude, max_amplitude),
        oscillation=False,
        baseline_window_scale=baseline_window_scale,
        peak_separation=peak_separation,
        peak_prominence=peak_prominence,
        peak_width=peak_width,
        limit=limit,
    )


def normalize_amplitude_range(
    amplitude: list[float] | tuple[float, float] | None,
) -> tuple[float, float] | None:
    if amplitude is None:
        return None
    if len(amplitude) != 2:
        raise ValueError("amplitude must contain two values: minimum and maximum")
    minimum = float(amplitude[0])
    maximum = float(amplitude[1])
    if minimum > maximum:
        raise ValueError("amplitude minimum must be less than or equal to the maximum")
    return minimum, maximum


def default_output_name(
    run_token: str,
    amplitude_range: tuple[float, float] | None,
    oscillation: bool,
) -> str:
    parts = [f"filter_run_{run_token}"]
    if oscillation:
        parts.append("oscillation")
    if amplitude_range is not None:
        parts.append(
            f"amp_{_format_bound(amplitude_range[0])}_{_format_bound(amplitude_range[1])}"
        )
    return "_".join(parts) + ".npy"


def _compute_oscillation_values(cleaned: np.ndarray) -> np.ndarray:
    spectrum = compute_frequency_distribution(cleaned)
    return sample_cdf_points(
        spectrum,
        thresholds=np.asarray([OSCILLATION_CDF_BIN], dtype=np.int64),
    )[:, 0]


def _matches_filter(
    *,
    row: np.ndarray,
    trace_id: int,
    amplitude_range: tuple[float, float] | None,
    oscillation: bool,
    oscillation_values: np.ndarray | None,
    peak_separation: float,
    peak_prominence: float,
    peak_width: float,
) -> bool:
    if oscillation:
        if oscillation_values is None:
            return False
        if float(oscillation_values[trace_id]) >= OSCILLATION_CUTOFF:
            return False

    if amplitude_range is not None:
        amplitude = max_peak_amplitude(
            row=row,
            peak_separation=peak_separation,
            peak_prominence=peak_prominence,
            peak_width=peak_width,
        )
        if not (amplitude_range[0] <= amplitude <= amplitude_range[1]):
            return False

    return True


def _format_bound(value: float) -> str:
    token = f"{value:g}"
    return token.replace("-", "neg").replace(".", "p")
