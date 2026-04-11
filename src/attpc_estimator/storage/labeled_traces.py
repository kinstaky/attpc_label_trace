from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

from ..utils.label_keys import LabeledTraceRow, canonical_label_key
from ..utils.trace_data import load_pad_traces
from .labels_db import LabelRepository
from .run_paths import collect_run_files, labels_db_path, resolve_run_file


def iter_labeled_trace_batches(
    trace_path: Path,
    workspace_path: Path,
    run: int | None,
) -> tuple[list[tuple[list[LabeledTraceRow], np.ndarray]], int]:
    trace_root = Path(trace_path).expanduser().resolve()
    workspace_root = Path(workspace_path).expanduser().resolve()
    run_files = (
        {run: resolve_run_file(trace_root, run)}
        if run is not None
        else collect_run_files(trace_root)
    )

    repository = LabelRepository(labels_db_path(workspace_root))
    repository.initialize()
    try:
        labeled_rows = repository.list_labeled_traces(run=run)
    finally:
        repository.connection.close()

    rows_by_run: dict[int, dict[int, list[LabeledTraceRow]]] = {}
    row_count = 0
    for run_id, event_id, trace_id, family, label in labeled_rows:
        if run_id not in run_files:
            continue
        rows_by_run.setdefault(run_id, {}).setdefault(event_id, []).append(
            LabeledTraceRow(
                run=run_id,
                event_id=event_id,
                trace_id=trace_id,
                label_key=canonical_label_key(family, label),
            )
        )
        row_count += 1

    batches: list[tuple[list[LabeledTraceRow], np.ndarray]] = []
    for run_id in sorted(rows_by_run):
        with h5py.File(run_files[run_id], "r") as handle:
            for event_id in sorted(rows_by_run[run_id]):
                event_rows = sorted(
                    rows_by_run[run_id][event_id],
                    key=lambda row: row.trace_id,
                )
                trace_ids = np.asarray(
                    [row.trace_id for row in event_rows],
                    dtype=np.int64,
                )
                try:
                    traces = load_pad_traces(
                        handle,
                        run=run_id,
                        event_id=event_id,
                        trace_ids=trace_ids,
                    )
                except LookupError:
                    continue
                batches.append((event_rows, traces))
    return batches, row_count


def _read_labeled_trace_rows(
    trace_path: Path,
    workspace_path: Path,
    run: int | None,
) -> tuple[np.ndarray, list[LabeledTraceRow]]:
    batches, row_count = iter_labeled_trace_batches(
        trace_path=trace_path,
        workspace_path=workspace_path,
        run=run,
    )

    trace_matrix: np.ndarray | None = None
    ordered_rows: list[LabeledTraceRow] = []
    row_index = 0

    for event_rows, traces in batches:
        if trace_matrix is None:
            trace_matrix = np.empty((row_count, traces.shape[1]), dtype=np.float32)
        batch_size = len(event_rows)
        trace_matrix[row_index : row_index + batch_size] = traces
        ordered_rows.extend(event_rows)
        row_index += batch_size

    if trace_matrix is None:
        return np.empty((0, 0), dtype=np.float32), []
    return trace_matrix[:row_index], ordered_rows


def read_labeled_trace(
    trace_path: Path,
    workspace_path: Path,
    run: int | None,
) -> tuple[np.ndarray, list[str]]:
    traces, labeled_rows = _read_labeled_trace_rows(
        trace_path=trace_path, workspace_path=workspace_path, run=run
    )
    return traces, [row.label_key for row in labeled_rows]
