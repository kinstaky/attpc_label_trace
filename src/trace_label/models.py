from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
from typing import Any

NORMAL_BUCKETS = tuple(range(10))
RESERVED_SHORTCUTS = {
    "arrowleft",
    "arrowright",
    "arrowup",
    "arrowdown",
    "h",
    "j",
    "k",
    "l",
    "q",
    "escape",
    "space",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
}


@dataclass(slots=True)
class TraceRecord:
    run: str
    event_id: int
    trace_id: int
    detector: str
    hardware_id: np.ndarray
    trace: np.ndarray
    family: str | None
    label: str | None

@dataclass(slots=True)
class StoredLabel:
    family: str
    label: str


def trace_key(record: TraceRecord) -> tuple[str, int, int]:
    return (record.run, record.event_id, record.trace_id)


def bucket_title(bucket: int) -> str:
    if bucket == 0:
        return "0 peak"
    if bucket == 1:
        return "1 peak"
    if bucket == 9:
        return "9+ peaks"
    return f"{bucket} peaks"


def normalize_shortcut(value: str) -> str:
    lowered = value.strip().lower()
    if lowered == "space":
        return " "
    if lowered == "esc":
        return "escape"
    return lowered
