from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import re
from typing import Any

import h5py
import numpy as np

from ..process.progress import ProgressReporter, emit_progress
from ..process.amplitude import AMPLITUDE_BIN_COUNT, _accumulate_peak_histogram
from ..process.cdf import _accumulate_cdf_histogram_numba
from ..storage.run_paths import collect_run_files
from ..utils.label_keys import label_title_from_key
from ..utils.trace_data import (
    CDF_THRESHOLDS,
    CDF_VALUE_BINS,
    collect_event_counts,
    compute_frequency_distribution,
    load_pad_traces,
    preprocess_traces,
    sample_cdf_points,
)
from .histogram_jobs import HistogramJobManager

ARTIFACT_SUFFIXES = {
    ("cdf", "all"): ("_cdf.npy",),
    ("cdf", "labeled"): ("_labeled_cdf.npz", "_labeled_cdf.npy"),
    ("amplitude", "all"): ("_amp.npy",),
    ("amplitude", "labeled"): ("_labeled_amp.npz", "_labeled_amp.npy"),
}


class HistogramService:
    def __init__(
        self, trace_path: Path, workspace: Path, baseline_window_scale: float = 10.0
    ) -> None:
        self.trace_path = trace_path
        self.workspace = workspace
        self.baseline_window_scale = baseline_window_scale
        self.run_files = collect_run_files(trace_path)
        self.jobs = HistogramJobManager()

    def bootstrap_state(self) -> dict[str, Any]:
        run_ids = sorted(self.run_files)
        filter_files = self._filter_files()
        return {
            "runs": run_ids,
            "filterFiles": [{"name": path.name} for path in filter_files],
            "histogramAvailability": {
                str(run_id): {
                    metric: {
                        mode: (
                            bool(filter_files)
                            if mode == "filtered"
                            else self._artifact_path(metric=metric, mode=mode, run=run_id)
                            is not None
                        )
                        for mode in ("all", "labeled", "filtered")
                    }
                    for metric in ("cdf", "amplitude")
                }
                for run_id in run_ids
            },
        }

    def get_histogram(
        self,
        *,
        metric: str,
        mode: str,
        run: int,
        filter_file: str | None = None,
        veto: bool = False,
        progress: ProgressReporter | None = None,
    ) -> dict[str, Any]:
        self._validate_histogram_request(
            metric=metric,
            mode=mode,
            run=run,
            filter_file=filter_file,
        )
        resolved_veto = veto if mode == "filtered" else False
        if mode == "filtered":
            return self._build_filtered_histogram(
                metric=metric,
                run=run,
                filter_file=filter_file,
                veto=resolved_veto,
                progress=progress,
            )

        artifact_path = self._artifact_path(metric=metric, mode=mode, run=run)
        if artifact_path is None:
            raise LookupError(
                f"no {metric} histogram artifact found for run {run} in {mode} mode"
            )

        payload = _load_artifact_payload(artifact_path, allow_pickle=mode == "labeled")
        if metric == "cdf":
            return self._normalize_cdf_payload(
                run=run,
                mode=mode,
                payload=payload,
                veto=resolved_veto,
            )
        return self._normalize_amplitude_payload(
            run=run,
            mode=mode,
            payload=payload,
            veto=resolved_veto,
        )

    def create_histogram_job(
        self,
        *,
        metric: str,
        mode: str,
        run: int,
        filter_file: str | None = None,
        veto: bool = False,
    ) -> str:
        if mode != "filtered":
            raise ValueError("histogram jobs are only available for filtered mode")
        self._validate_histogram_request(
            metric=metric,
            mode=mode,
            run=run,
            filter_file=filter_file,
        )
        return self.jobs.create_job(
            lambda progress: self.get_histogram(
                metric=metric,
                mode=mode,
                run=run,
                filter_file=filter_file,
                veto=veto,
                progress=progress,
            )
        )

    def next_job_message(
        self,
        job_id: str,
        after_index: int,
    ) -> tuple[int, dict] | None:
        return self.jobs.next_message(job_id, after_index)

    def _filter_files(self) -> list[Path]:
        return sorted(self.workspace.glob("filter_*.npy"))

    def _validate_histogram_request(
        self,
        *,
        metric: str,
        mode: str,
        run: int,
        filter_file: str | None,
    ) -> None:
        if metric not in {"cdf", "amplitude"}:
            raise ValueError("metric must be 'cdf' or 'amplitude'")
        if mode not in {"all", "labeled", "filtered"}:
            raise ValueError("mode must be 'all', 'labeled', or 'filtered'")
        if run not in self.run_files:
            raise ValueError(f"run {run} is not available")
        if mode == "filtered":
            self._filter_path(filter_file)

    def _filter_path(self, name: str | None) -> Path:
        if not name:
            raise ValueError("filterFile is required when mode is 'filtered'")
        filter_path = self.workspace / name
        if filter_path not in self._filter_files():
            raise ValueError(f"filter file not found: {name}")
        return filter_path

    def _artifact_path(self, metric: str, mode: str, run: int) -> Path | None:
        suffixes = ARTIFACT_SUFFIXES[(metric, mode)]
        for suffix in suffixes:
            pattern = re.compile(rf"^run_(\d+){re.escape(suffix)}$")
            for candidate in sorted(self.workspace.glob(f"run_*{suffix}")):
                match = pattern.match(candidate.name)
                if match is not None and int(match.group(1)) == run:
                    return candidate
        return None

    def _normalize_cdf_payload(
        self,
        run: int,
        mode: str,
        payload: np.ndarray,
        *,
        title: str = "All traces",
        filter_file: str | None = None,
        veto: bool = False,
        trace_count: int | None = None,
    ) -> dict[str, Any]:
        if mode in {"all", "filtered"}:
            histogram = np.asarray(payload, dtype=np.int64)
            resolved_trace_count = (
                int(trace_count)
                if trace_count is not None
                else int(histogram.sum() // len(CDF_THRESHOLDS)) if histogram.size else 0
            )
            series = [
                {
                    "labelKey": "all" if mode == "all" else "filtered",
                    "title": title,
                    "traceCount": resolved_trace_count,
                    "histogram": histogram.tolist(),
                }
            ]
        else:
            loaded = _mapping_payload(payload)
            label_keys = loaded["label_keys"].tolist()
            label_titles = loaded["label_titles"].tolist()
            trace_counts = loaded["trace_counts"].astype(np.int64)
            histograms = loaded["histograms"].astype(np.int64)
            series = []
            for index, label_key in enumerate(label_keys):
                if int(trace_counts[index]) == 0:
                    continue
                series.append(
                    {
                        "labelKey": str(label_key),
                        "title": str(label_titles[index]),
                        "traceCount": int(trace_counts[index]),
                        "histogram": histograms[index].tolist(),
                    }
                )
        return {
            "metric": "cdf",
            "mode": mode,
            "run": run,
            "filterFile": filter_file,
            "veto": veto,
            "thresholds": CDF_THRESHOLDS.tolist(),
            "valueBinCount": CDF_VALUE_BINS,
            "series": series,
        }

    def _normalize_amplitude_payload(
        self,
        run: int,
        mode: str,
        payload: np.ndarray,
        *,
        title: str = "All traces",
        filter_file: str | None = None,
        veto: bool = False,
        trace_count: int | None = None,
    ) -> dict[str, Any]:
        if mode in {"all", "filtered"}:
            histogram = np.asarray(payload, dtype=np.int64)
            series = [
                {
                    "labelKey": "all" if mode == "all" else "filtered",
                    "title": title,
                    "traceCount": trace_count,
                    "histogram": histogram.tolist(),
                }
            ]
        else:
            loaded = _mapping_payload(payload)
            label_keys = [str(value) for value in loaded["label_keys"].tolist()]
            trace_counts = loaded["trace_counts"].astype(np.int64)
            histogram_matrix = loaded.get("histograms")
            grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
            for index, label_key in enumerate(label_keys):
                if int(trace_counts[index]) == 0:
                    continue
                grouped_key = _amplitude_group_key(label_key)
                if histogram_matrix is not None:
                    histogram = np.asarray(histogram_matrix[index], dtype=np.int64)
                else:
                    histogram = np.asarray(loaded[label_key], dtype=np.int64)
                if grouped_key not in grouped:
                    grouped[grouped_key] = {
                        "labelKey": grouped_key,
                        "title": label_title_from_key(grouped_key),
                        "traceCount": 0,
                        "histogram": np.zeros_like(histogram),
                    }
                grouped[grouped_key]["traceCount"] += int(trace_counts[index])
                grouped[grouped_key]["histogram"] += histogram
            series = [
                {
                    **entry,
                    "histogram": entry["histogram"].tolist(),
                }
                for entry in grouped.values()
            ]
        return {
            "metric": "amplitude",
            "mode": mode,
            "run": run,
            "filterFile": filter_file,
            "veto": veto,
            "binCount": AMPLITUDE_BIN_COUNT,
            "series": series,
        }

    def _build_filtered_histogram(
        self,
        *,
        metric: str,
        run: int,
        filter_file: str | None,
        veto: bool,
        progress: ProgressReporter | None = None,
    ) -> dict[str, Any]:
        filter_path = self._filter_path(filter_file)
        rows = np.asarray(np.load(filter_path), dtype=np.int64)
        if rows.ndim != 2 or rows.shape[1] != 3:
            raise ValueError(
                f"filter file must contain an Nx3 integer array: {filter_path.name}"
            )
        grouped_trace_ids, trace_count = self._resolve_filtered_trace_ids(
            run=run,
            rows=rows,
            veto=veto,
        )
        if trace_count == 0:
            return self._empty_filtered_payload(
                metric=metric,
                run=run,
                filter_file=filter_path.name,
                veto=veto,
            )

        title_prefix = "Vetoed traces" if veto else "Filtered traces"
        title = f"{title_prefix} · {filter_path.stem}"
        if metric == "cdf":
            histogram = self._build_filtered_cdf_histogram(
                run=run,
                grouped_trace_ids=grouped_trace_ids,
                total_traces=trace_count,
                progress=progress,
            )
            return self._normalize_cdf_payload(
                run=run,
                mode="filtered",
                payload=histogram,
                title=title,
                filter_file=filter_path.name,
                veto=veto,
                trace_count=trace_count,
            )
        histogram = self._build_filtered_amplitude_histogram(
            run=run,
            grouped_trace_ids=grouped_trace_ids,
            total_traces=trace_count,
            progress=progress,
        )
        return self._normalize_amplitude_payload(
            run=run,
            mode="filtered",
            payload=histogram,
            title=title,
            filter_file=filter_path.name,
            veto=veto,
            trace_count=trace_count,
        )

    def _empty_filtered_payload(
        self,
        *,
        metric: str,
        run: int,
        filter_file: str,
        veto: bool,
    ) -> dict[str, Any]:
        if metric == "cdf":
            return {
                "metric": "cdf",
                "mode": "filtered",
                "run": run,
                "filterFile": filter_file,
                "veto": veto,
                "thresholds": CDF_THRESHOLDS.tolist(),
                "valueBinCount": CDF_VALUE_BINS,
                "series": [],
            }
        return {
            "metric": "amplitude",
            "mode": "filtered",
            "run": run,
            "filterFile": filter_file,
            "veto": veto,
            "binCount": AMPLITUDE_BIN_COUNT,
            "series": [],
        }

    def _build_filtered_cdf_histogram(
        self,
        *,
        run: int,
        grouped_trace_ids: dict[int, np.ndarray],
        total_traces: int,
        progress: ProgressReporter | None = None,
    ) -> np.ndarray:
        histogram = np.zeros((len(CDF_THRESHOLDS), CDF_VALUE_BINS), dtype=np.int64)
        processed_traces = 0
        emit_progress(
            progress,
            current=0,
            total=total_traces,
            unit="trace",
        )
        with h5py.File(self.run_files[run], "r") as handle:
            for event_id in sorted(grouped_trace_ids):
                trace_ids = grouped_trace_ids[event_id]
                batch_size = int(trace_ids.shape[0])
                try:
                    traces = load_pad_traces(
                        handle, run=run, event_id=event_id, trace_ids=trace_ids
                    )
                except LookupError:
                    processed_traces += batch_size
                    emit_progress(
                        progress,
                        current=processed_traces,
                        total=total_traces,
                        unit="trace",
                        message=f"event={event_id}",
                    )
                    continue
                cleaned = preprocess_traces(
                    traces, baseline_window_scale=self.baseline_window_scale
                )
                spectrum = compute_frequency_distribution(cleaned)
                samples = sample_cdf_points(spectrum, thresholds=CDF_THRESHOLDS)
                _accumulate_cdf_histogram_numba(samples, histogram)
                processed_traces += batch_size
                emit_progress(
                    progress,
                    current=processed_traces,
                    total=total_traces,
                    unit="trace",
                    message=f"event={event_id}",
                )
        return histogram

    def _build_filtered_amplitude_histogram(
        self,
        *,
        run: int,
        grouped_trace_ids: dict[int, np.ndarray],
        total_traces: int,
        progress: ProgressReporter | None = None,
    ) -> np.ndarray:
        histogram = np.zeros(AMPLITUDE_BIN_COUNT, dtype=np.int64)
        processed_traces = 0
        emit_progress(
            progress,
            current=0,
            total=total_traces,
            unit="trace",
        )
        with h5py.File(self.run_files[run], "r") as handle:
            for event_id in sorted(grouped_trace_ids):
                trace_ids = grouped_trace_ids[event_id]
                batch_size = int(trace_ids.shape[0])
                try:
                    traces = load_pad_traces(
                        handle, run=run, event_id=event_id, trace_ids=trace_ids
                    )
                except LookupError:
                    processed_traces += batch_size
                    emit_progress(
                        progress,
                        current=processed_traces,
                        total=total_traces,
                        unit="trace",
                        message=f"event={event_id}",
                    )
                    continue
                cleaned = preprocess_traces(
                    traces, baseline_window_scale=self.baseline_window_scale
                )
                for row in cleaned:
                    _accumulate_peak_histogram(
                        row=row,
                        histogram=histogram,
                        peak_separation=50.0,
                        peak_prominence=20.0,
                        peak_width=50.0,
                    )
                processed_traces += batch_size
                emit_progress(
                    progress,
                    current=processed_traces,
                    total=total_traces,
                    unit="trace",
                    message=f"event={event_id}",
                )
        return histogram

    def _resolve_filtered_trace_ids(
        self,
        *,
        run: int,
        rows: np.ndarray,
        veto: bool,
    ) -> tuple[dict[int, np.ndarray], int]:
        run_rows = rows[rows[:, 0] == run]
        grouped = _group_filter_rows_by_event(run_rows)
        if not veto:
            total_traces = int(run_rows.shape[0]) if run_rows.size else 0
            return {
                event_id: np.asarray(trace_ids, dtype=np.int64)
                for event_id, trace_ids in grouped.items()
            }, total_traces

        selected_by_event = {
            event_id: np.asarray(sorted(set(trace_ids)), dtype=np.int64)
            for event_id, trace_ids in grouped.items()
        }
        veto_grouped: dict[int, np.ndarray] = {}
        total_traces = 0
        with h5py.File(self.run_files[run], "r") as handle:
            for event_id, trace_count in collect_event_counts(handle):
                selected_trace_ids = selected_by_event.get(event_id)
                if selected_trace_ids is None or selected_trace_ids.size == 0:
                    veto_trace_ids = np.arange(trace_count, dtype=np.int64)
                else:
                    valid_selected = selected_trace_ids[
                        (selected_trace_ids >= 0) & (selected_trace_ids < trace_count)
                    ]
                    keep_mask = np.ones(trace_count, dtype=bool)
                    keep_mask[valid_selected] = False
                    veto_trace_ids = np.flatnonzero(keep_mask).astype(np.int64, copy=False)
                if veto_trace_ids.size == 0:
                    continue
                veto_grouped[int(event_id)] = veto_trace_ids
                total_traces += int(veto_trace_ids.size)
        return veto_grouped, total_traces


def _group_filter_rows_by_event(rows: np.ndarray) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for _, event_id, trace_id in rows.tolist():
        grouped.setdefault(int(event_id), []).append(int(trace_id))
    return grouped


def _amplitude_group_key(label_key: str) -> str:
    family, _, label = label_key.partition(":")
    if family == "normal" and label in {"4", "5", "6", "7", "8", "9"}:
        return "normal:4+"
    return label_key


def _load_artifact_payload(path: Path, *, allow_pickle: bool) -> Any:
    return np.load(path, allow_pickle=allow_pickle)


def _mapping_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, np.lib.npyio.NpzFile):
        return {key: payload[key] for key in payload.files}
    if isinstance(payload, np.ndarray):
        return payload.item()
    return payload
