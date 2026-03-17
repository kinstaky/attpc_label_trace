from __future__ import annotations

import h5py
from pathlib import Path
import random

from .models import TraceRecord


class TraceSource:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.run = int(path.stem.split("_")[1])
        self.file = h5py.File(path, "r")
        self.min_event = self.file["events"].attrs["min_event"]
        self.max_event = self.file["events"].attrs["max_event"]
        self.bad_events = self.file["events"].attrs["bad_events"]
        self.event_stack: tuple[int, int] = []
        self.stack_pointer = 0
        self.labeled_traces: dict[tuple[int, int], tuple[str, str]] = {}

    def get_run(self) -> int:
        return self.run

    def get_trace(self, event_id: int, trace_id: int) -> TraceRecord | None:
        if (
            event_id < self.min_event
            or event_id > self.max_event
            or event_id in self.bad_events
        ):
            return None
        get_event = self.file["events"][f"event_{event_id}"]["get"]
        pad_event = get_event["pads"][:]
        if trace_id >= pad_event.shape[0]:
            return None
        if (event_id, trace_id) in self.labeled_traces:
            family, label = self.labeled_traces[(event_id, trace_id)]
        else:
            family = None
            label = None
        hardware = pad_event[trace_id][:5].copy()
        trace = pad_event[trace_id][5:].copy()
        trace[0] = trace[1]
        trace[-1] = trace[-2]
        return TraceRecord(
            run=self.run,
            event_id=event_id,
            trace_id=trace_id,
            detector="pad",
            hardware_id=hardware,
            trace=trace,
            family=family,
            label=label,
        )

    def _random_trace(self) -> tuple[int, int]:
        event_id = random.randint(self.min_event, self.max_event)
        while event_id in self.bad_events:
            event_id = random.randint(self.min_event, self.max_event)
        traces = self.file["events"][f"event_{event_id}"]["get"]["pads"][:]
        trace_id = random.randrange(0, traces.shape[0])
        while (event_id, trace_id) in self.labeled_traces:
            trace_id += 1
            if trace_id >= traces.shape[0]:
                event_id, trace_id = self._random_trace()
        return (event_id, trace_id)

    def next_trace(self) -> TraceRecord:
        if self.stack_pointer < len(self.event_stack):
            pointed = self.event_stack[self.stack_pointer]
            self.stack_pointer += 1
            return self.get_trace(pointed[0], pointed[1])
        event_id, trace_id = self._random_trace()
        self.event_stack.append((event_id, trace_id))
        self.stack_pointer += 1
        pad_event = self.file["events"][f"event_{event_id}"]["get"]["pads"][:]
        hardware = pad_event[trace_id][:5].copy()
        trace = pad_event[trace_id][5:].copy()
        trace[0] = trace[1]
        trace[-1] = trace[-2]
        return TraceRecord(
            run=self.run,
            event_id=event_id,
            trace_id=trace_id,
            detector="pad",
            hardware_id=hardware,
            trace=trace,
            family=None,
            label=None,
        )

    def previous_trace(self) -> TraceRecord:
        if self.stack_pointer > 1:
            self.stack_pointer -= 1
        pointed = self.event_stack[self.stack_pointer-1]
        return self.get_trace(pointed[0], pointed[1])

    def label_trace(self, event_id: int, trace_id: int, family: str, label: str) -> None:
        self.labeled_traces[(event_id, trace_id)] = (family, label)

    def set_labeled(self, labeled: dict[tuple[int, int], tuple[str, str]]) -> None:
        self.labeled_traces = labeled.copy()