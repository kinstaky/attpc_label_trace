from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import random

import h5py
import numpy as np

from ...model.label import StoredLabel
from ...model.trace import TraceRef
from ...storage.run_paths import extract_run_id
from ...utils.trace_data import collect_event_counts

MAX_RANDOM_TRACE_ATTEMPTS = 1024


def match_review_label(
    family: str,
    stored_label: str,
    requested_label: str | None,
) -> bool:
    if requested_label is None:
        return True
    if family == "normal" and requested_label == "4+":
        return stored_label in {"4", "5", "6", "7", "8", "9"}
    return stored_label == requested_label


def sort_trace_refs(refs: list[TraceRef]) -> list[TraceRef]:
    return sorted(refs)


def trace_refs_from_filter_rows(rows: np.ndarray) -> list[TraceRef]:
    rows_array = np.asarray(rows, dtype=np.int64)
    if rows_array.ndim != 2 or rows_array.shape[1] != 3:
        raise ValueError(
            "filter rows must have shape (N, 3) with columns run,event_id,trace_id"
        )
    return [
        TraceRef(run=int(row[0]), event_id=int(row[1]), trace_id=int(row[2]))
        for row in rows_array.tolist()
    ]


def rebuild_review_refs(
    *,
    run: int,
    labels: Mapping[TraceRef, StoredLabel],
    family: str,
    label: str | None,
) -> list[TraceRef]:
    return sort_trace_refs(
        [
            ref
            for ref, stored_label in labels.items()
            if ref.run == run
            and stored_label.family == family
            and match_review_label(family, stored_label.label, label)
        ]
    )


def random_unlabeled_ref(
    *,
    run: int,
    event_counts: list[tuple[int, int]],
    labeled_refs: set[TraceRef],
    excluded_refs: set[TraceRef],
    max_attempts: int = MAX_RANDOM_TRACE_ATTEMPTS,
) -> TraceRef:
    if not event_counts:
        raise LookupError("no unlabeled trace was found after repeated random sampling")

    for _ in range(max_attempts):
        event_id, trace_count = random.choice(event_counts)
        trace_id = random.randrange(trace_count)
        ref = TraceRef(run=run, event_id=event_id, trace_id=trace_id)
        if ref in labeled_refs or ref in excluded_refs:
            continue
        return ref
    raise LookupError("no unlabeled trace was found after repeated random sampling")


class RandomUnlabeledSelector:
    clamp_at_end = False
    empty_message = "no unlabeled trace was found after repeated random sampling"

    def __init__(self, trace_file: Path) -> None:
        self.trace_file = trace_file
        self.run = extract_run_id(trace_file)
        with h5py.File(trace_file, "r") as handle:
            events = handle["events"]
            min_event = int(events.attrs["min_event"])
            max_event = int(events.attrs["max_event"])
            bad_events = {int(event_id) for event_id in events.attrs["bad_events"]}
            self._event_counts = collect_event_counts(
                events,
                min_event=min_event,
                max_event=max_event,
                bad_events=bad_events,
            )

    def initial_refs(self, labels: Mapping[TraceRef, StoredLabel]) -> list[TraceRef]:
        return []

    def ensure_forward_size(
        self,
        existing: list[TraceRef],
        pointer: int,
        target_size: int,
        labels: Mapping[TraceRef, StoredLabel],
    ) -> list[TraceRef]:
        additions: list[TraceRef] = []
        excluded_refs = set(existing)
        labeled_refs = {ref for ref in labels if ref.run == self.run}
        while len(existing) + len(additions) < target_size:
            try:
                ref = random_unlabeled_ref(
                    run=self.run,
                    event_counts=self._event_counts,
                    labeled_refs=labeled_refs,
                    excluded_refs=excluded_refs,
                )
            except LookupError:
                break
            additions.append(ref)
            excluded_refs.add(ref)
        return additions

    def on_label_updated(
        self,
        ref: TraceRef,
        family: str,
        label: str,
        existing: list[TraceRef],
        pointer: int,
        labels: Mapping[TraceRef, StoredLabel],
    ) -> list[TraceRef] | None:
        history_size = min(pointer + 1, len(existing))
        history = existing[:history_size]
        future = [candidate for candidate in existing[history_size:] if candidate not in labels]
        rebuilt = history + future
        return rebuilt if rebuilt != existing else None


class LabeledReviewSelector:
    clamp_at_end = True
    empty_message = "no traces match the selected review filter"

    def __init__(self, *, run: int, family: str, label: str | None) -> None:
        self.run = run
        self.family = family
        self.label = label

    def initial_refs(self, labels: Mapping[TraceRef, StoredLabel]) -> list[TraceRef]:
        return rebuild_review_refs(
            run=self.run,
            labels=labels,
            family=self.family,
            label=self.label,
        )

    def ensure_forward_size(
        self,
        existing: list[TraceRef],
        pointer: int,
        target_size: int,
        labels: Mapping[TraceRef, StoredLabel],
    ) -> list[TraceRef]:
        return []

    def on_label_updated(
        self,
        ref: TraceRef,
        family: str,
        label: str,
        existing: list[TraceRef],
        pointer: int,
        labels: Mapping[TraceRef, StoredLabel],
    ) -> list[TraceRef] | None:
        return rebuild_review_refs(
            run=self.run,
            labels=labels,
            family=self.family,
            label=self.label,
        )


class FilterRowsSelector:
    clamp_at_end = True
    empty_message = "no traces match the selected filter"

    def __init__(self, rows: np.ndarray) -> None:
        self._rows = np.asarray(rows, dtype=np.int64)

    def initial_refs(self, labels: Mapping[TraceRef, StoredLabel]) -> list[TraceRef]:
        return trace_refs_from_filter_rows(self._rows)

    def ensure_forward_size(
        self,
        existing: list[TraceRef],
        pointer: int,
        target_size: int,
        labels: Mapping[TraceRef, StoredLabel],
    ) -> list[TraceRef]:
        return []

    def on_label_updated(
        self,
        ref: TraceRef,
        family: str,
        label: str,
        existing: list[TraceRef],
        pointer: int,
        labels: Mapping[TraceRef, StoredLabel],
    ) -> list[TraceRef] | None:
        return None
