from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import h5py

from ...model.label import StoredLabel
from ...model.trace import TraceRecord, TraceRef
from ...utils.trace_data import load_trace_record


class TraceLoader:
    def __init__(
        self,
        *,
        run_files: Mapping[int, Path],
        labels: Mapping[TraceRef, StoredLabel],
        baseline_window_scale: float,
    ) -> None:
        self.run_files = {int(run): path.resolve() for run, path in run_files.items()}
        self.labels = dict(labels)
        self.baseline_window_scale = baseline_window_scale
        self._handles: dict[int, h5py.File] = {}

    def replace_labels(self, labels: Mapping[TraceRef, StoredLabel]) -> None:
        self.labels = dict(labels)

    def update_label(self, ref: TraceRef, family: str, label: str) -> None:
        self.labels[ref] = StoredLabel(family=family, label=label)

    def load(self, ref: TraceRef) -> TraceRecord:
        record = load_trace_record(
            self._get_handle(ref.run),
            run=ref.run,
            event_id=ref.event_id,
            trace_id=ref.trace_id,
            baseline_window_scale=self.baseline_window_scale,
        )
        stored_label = self.labels.get(ref)
        if stored_label is None:
            record.family = None
            record.label = None
        else:
            record.family = stored_label.family
            record.label = stored_label.label
        return record

    def try_load(self, ref: TraceRef) -> TraceRecord | None:
        try:
            return self.load(ref)
        except LookupError:
            return None

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()

    def _get_handle(self, run: int) -> h5py.File:
        handle = self._handles.get(run)
        if handle is None:
            handle = h5py.File(self.run_files[run], "r")
            self._handles[run] = handle
        return handle
