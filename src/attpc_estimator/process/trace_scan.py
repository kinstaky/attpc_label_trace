from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import h5py
import numpy as np
from tqdm import tqdm

from ..utils.trace_data import PAD_TRACE_OFFSET, collect_event_counts, preprocess_traces


def scan_cleaned_trace_batches(
    trace_file_path: Path,
    *,
    baseline_window_scale: float,
    handler: Callable[[int, np.ndarray], None],
    progress_desc: str = "Processing pad traces",
) -> None:
    with h5py.File(trace_file_path, "r") as handle:
        events = handle["events"]
        min_event = int(events.attrs["min_event"])
        max_event = int(events.attrs["max_event"])
        bad_events = {int(event_id) for event_id in events.attrs["bad_events"]}
        event_counts = collect_event_counts(
            events=events,
            min_event=min_event,
            max_event=max_event,
            bad_events=bad_events,
        )
        total_traces = sum(trace_count for _, trace_count in event_counts)

        with tqdm(total=total_traces, desc=progress_desc, unit="trace") as progress:
            for event_id, trace_count in event_counts:
                pads = events[f"event_{event_id}"]["get"]["pads"]
                traces = np.asarray(pads[:, PAD_TRACE_OFFSET:], dtype=np.float32)
                cleaned = preprocess_traces(
                    traces, baseline_window_scale=baseline_window_scale
                )
                handler(event_id, cleaned)
                progress.update(trace_count)
                progress.set_postfix_str(f"event={event_id}")
