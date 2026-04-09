from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
from tqdm import tqdm

from ..storage.labels_db import LabelRepository
from ..storage.run_paths import labels_db_path, resolve_run_file
from ..utils.trace_data import PAD_TRACE_OFFSET, preprocess_traces

NORMAL_LABEL_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("normal:0", "0 peak", ("0",)),
    ("normal:1", "1 peak", ("1",)),
    ("normal:2", "2 peaks", ("2",)),
    ("normal:3", "3 peaks", ("3",)),
    ("normal:4+", "4+ peaks", ("4", "5", "6", "7", "8", "9")),
)


@dataclass(frozen=True, slots=True)
class GroupedLabeledRun:
    run: int
    run_file: Path
    label_keys: list[str]
    label_titles: list[str]
    trace_counts: np.ndarray
    grouped_traces: dict[int, list[tuple[int, int]]]


def load_grouped_labeled_run(
    trace_path: Path,
    workspace: Path,
    run: int,
) -> GroupedLabeledRun:
    run_file = resolve_run_file(trace_path, run)

    repository = LabelRepository(labels_db_path(workspace))
    repository.initialize()
    try:
        labeled_rows = repository.list_labeled_traces(run=run)
        strange_label_names = [row["name"] for row in repository.list_strange_labels()]
    finally:
        repository.connection.close()

    label_keys, label_titles = build_label_metadata(strange_label_names)
    trace_counts = np.zeros(len(label_titles), dtype=np.int64)
    grouped_traces = group_labeled_traces(
        labeled_rows=labeled_rows,
        strange_label_names=strange_label_names,
        trace_counts=trace_counts,
    )
    return GroupedLabeledRun(
        run=run,
        run_file=run_file,
        label_keys=label_keys,
        label_titles=label_titles,
        trace_counts=trace_counts,
        grouped_traces=grouped_traces,
    )


def scan_grouped_labeled_trace_batches(
    grouped_run: GroupedLabeledRun,
    *,
    baseline_window_scale: float,
    handler: Callable[[int, np.ndarray, np.ndarray], None],
    progress_desc: str = "Processing labeled pad traces",
) -> None:
    total_traces = sum(
        len(grouped_traces) for grouped_traces in grouped_run.grouped_traces.values()
    )
    with h5py.File(grouped_run.run_file, "r") as handle:
        events = handle["events"]
        with tqdm(total=total_traces, desc=progress_desc, unit="trace") as progress:
            for event_id in sorted(grouped_run.grouped_traces):
                grouped_traces = sorted(
                    grouped_run.grouped_traces[event_id],
                    key=lambda item: item[0],
                )
                trace_ids = np.asarray(
                    [trace_id for trace_id, _ in grouped_traces],
                    dtype=np.int64,
                )
                label_indices = np.asarray(
                    [label_index for _, label_index in grouped_traces],
                    dtype=np.int64,
                )
                pads = events[f"event_{event_id}"]["get"]["pads"]
                traces = np.asarray(
                    pads[trace_ids, PAD_TRACE_OFFSET:], dtype=np.float32
                )
                cleaned = preprocess_traces(
                    traces,
                    baseline_window_scale=baseline_window_scale,
                )
                handler(event_id, cleaned, label_indices)
                progress.update(len(grouped_traces))
                progress.set_postfix_str(f"run={grouped_run.run},event={event_id}")


def build_label_metadata(
    strange_label_names: list[str],
) -> tuple[list[str], list[str]]:
    label_keys = [entry[0] for entry in NORMAL_LABEL_GROUPS]
    label_titles = [entry[1] for entry in NORMAL_LABEL_GROUPS]
    label_keys.extend(f"strange:{name}" for name in strange_label_names)
    label_titles.extend(strange_label_names)
    return label_keys, label_titles


def group_labeled_traces(
    labeled_rows: list[tuple[int, int, int, str, str]],
    strange_label_names: list[str],
    trace_counts: np.ndarray,
) -> dict[int, list[tuple[int, int]]]:
    strange_index_map = {
        name: len(NORMAL_LABEL_GROUPS) + idx
        for idx, name in enumerate(strange_label_names)
    }
    grouped: dict[int, list[tuple[int, int]]] = {}

    for _, event_id, trace_id, family, label in labeled_rows:
        label_index = resolve_label_index(
            family=family,
            label=label,
            strange_index_map=strange_index_map,
        )
        if label_index is None:
            continue
        grouped.setdefault(event_id, []).append((trace_id, label_index))
        trace_counts[label_index] += 1

    return grouped


def resolve_label_index(
    family: str,
    label: str,
    strange_index_map: dict[str, int],
) -> int | None:
    if family == "normal":
        if label in {"0", "1", "2", "3"}:
            return int(label)
        if label in {"4", "5", "6", "7", "8", "9"}:
            return 4
        return None
    if family == "strange":
        return strange_index_map.get(label)
    return None
