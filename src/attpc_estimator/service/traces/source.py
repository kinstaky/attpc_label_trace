from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np

from ...model.label import StoredLabel
from ...model.trace import TraceRecord, TraceRef
from ...storage.run_paths import collect_run_files, extract_run_id
from .loader import TraceLoader
from .navigation import Navigator
from .prefetch import TracePrefetcher
from .selection import (
    FilterRowsSelector,
    LabeledReviewSelector,
    RandomUnlabeledSelector,
    trace_refs_from_filter_rows,
)

CACHE_RADIUS = 5


class TraceSource:
    def __init__(
        self,
        *,
        run_files: Mapping[int, Path],
        selector: RandomUnlabeledSelector | LabeledReviewSelector | FilterRowsSelector,
        labels: Mapping[TraceRef, StoredLabel] | None = None,
        baseline_window_scale: float = 10.0,
        prefetch_radius: int = CACHE_RADIUS,
    ) -> None:
        self.run_files = {int(run): path.resolve() for run, path in run_files.items()}
        self.selector = selector
        self.baseline_window_scale = baseline_window_scale
        self.prefetch_radius = prefetch_radius
        self._labels = dict(labels or {})
        self._navigator = Navigator(
            review_mode=isinstance(selector, (LabeledReviewSelector, FilterRowsSelector))
        )
        self._navigator.replace_stack(selector.initial_refs(self._labels))
        self._loader = TraceLoader(
            run_files=self.run_files,
            labels=self._labels,
            baseline_window_scale=baseline_window_scale,
        )
        self._prefetcher = TracePrefetcher(self._loader)

    @classmethod
    def for_label_mode(
        cls,
        trace_file: Path,
        *,
        labels: Mapping[TraceRef, StoredLabel] | None = None,
        baseline_window_scale: float = 10.0,
        prefetch_radius: int = CACHE_RADIUS,
    ) -> TraceSource:
        trace_file_resolved = trace_file.resolve()
        run = extract_run_id(trace_file_resolved)
        return cls(
            run_files={run: trace_file_resolved},
            selector=RandomUnlabeledSelector(trace_file_resolved),
            labels=labels,
            baseline_window_scale=baseline_window_scale,
            prefetch_radius=prefetch_radius,
        )

    @classmethod
    def for_review_mode(
        cls,
        trace_file: Path,
        *,
        family: str,
        label: str | None,
        labels: Mapping[TraceRef, StoredLabel] | None = None,
        baseline_window_scale: float = 10.0,
        prefetch_radius: int = CACHE_RADIUS,
    ) -> TraceSource:
        trace_file_resolved = trace_file.resolve()
        run = extract_run_id(trace_file_resolved)
        return cls(
            run_files={run: trace_file_resolved},
            selector=LabeledReviewSelector(run=run, family=family, label=label),
            labels=labels,
            baseline_window_scale=baseline_window_scale,
            prefetch_radius=prefetch_radius,
        )

    @classmethod
    def for_filter_rows(
        cls,
        trace_path: Path | Mapping[int, Path],
        rows: np.ndarray,
        *,
        labels: Mapping[TraceRef, StoredLabel] | None = None,
        baseline_window_scale: float = 10.0,
        prefetch_radius: int = CACHE_RADIUS,
    ) -> TraceSource:
        run_files = (
            {int(run): path.resolve() for run, path in trace_path.items()}
            if isinstance(trace_path, Mapping)
            else collect_run_files(trace_path)
        )
        for ref in trace_refs_from_filter_rows(rows):
            if ref.run not in run_files:
                raise ValueError(f"filter row references missing run {ref.run}")
        return cls(
            run_files=run_files,
            selector=FilterRowsSelector(rows),
            labels=labels,
            baseline_window_scale=baseline_window_scale,
            prefetch_radius=prefetch_radius,
        )

    @property
    def trace_cache(self) -> dict[TraceRef, TraceRecord]:
        return self._prefetcher.cache_snapshot()

    def current_trace(self) -> TraceRecord | None:
        current_ref = self._navigator.current_ref()
        if current_ref is None:
            return None
        return self.get_trace(current_ref)

    def trace_count(self) -> int:
        return len(self._navigator.stack)

    def next_trace(self) -> TraceRecord:
        self._ensure_forward_capacity(self._navigator.index + self.prefetch_radius + 2)
        try:
            ref = self._navigator.next_ref(clamp_at_end=self.selector.clamp_at_end)
        except LookupError as exc:
            raise LookupError(self.selector.empty_message) from exc
        record = self._require_trace(ref)
        self._schedule_prefetch()
        return record

    def previous_trace(self) -> TraceRecord:
        try:
            ref = self._navigator.previous_ref()
        except LookupError as exc:
            raise LookupError("no trace history is available") from exc
        self._ensure_forward_capacity(self._navigator.index + self.prefetch_radius + 2)
        record = self._require_trace(ref)
        self._schedule_prefetch()
        return record

    def get_trace(self, ref: TraceRef) -> TraceRecord | None:
        cached = self._prefetcher.get_cached(ref)
        if cached is not None:
            return cached
        record = self._loader.try_load(ref)
        if record is None:
            return None
        self._prefetcher.store_current(ref, record)
        return record

    def get_progress(self) -> dict[str, int] | None:
        return self._navigator.progress()

    def replace_labels(self, labels: Mapping[TraceRef, StoredLabel]) -> None:
        self._labels = dict(labels)
        self._loader.replace_labels(self._labels)
        self._prefetcher.replace_labels(self._labels)

    def apply_label(self, ref: TraceRef, family: str, label: str) -> None:
        self._labels[ref] = StoredLabel(family=family, label=label)
        self._loader.update_label(ref, family, label)
        self._prefetcher.update_cached_label(ref, family, label)

        rebuilt = self.selector.on_label_updated(
            ref,
            family,
            label,
            list(self._navigator.stack),
            self._navigator.index,
            self._labels,
        )
        if rebuilt is not None:
            current_ref = self._navigator.current_ref()
            self._navigator.replace_stack(rebuilt, keep_current_ref=current_ref)
        self._schedule_prefetch()

    def close(self) -> None:
        self._prefetcher.close()
        self._loader.close()

    def _wait_for_prefetch(self, timeout: float = 1.0) -> bool:
        return self._prefetcher.wait(timeout=timeout)

    def _require_trace(self, ref: TraceRef) -> TraceRecord:
        record = self.get_trace(ref)
        if record is None:
            raise LookupError(
                f"trace {ref.run}/{ref.event_id}/{ref.trace_id} is not available"
            )
        return record

    def _ensure_forward_capacity(self, target_size: int) -> None:
        additions = self.selector.ensure_forward_size(
            list(self._navigator.stack),
            self._navigator.index,
            max(0, target_size),
            self._labels,
        )
        self._navigator.extend_stack(additions)

    def _schedule_prefetch(self) -> None:
        self._ensure_forward_capacity(self._navigator.index + self.prefetch_radius + 2)
        self._prefetcher.schedule(self._navigator.window(self.prefetch_radius))
