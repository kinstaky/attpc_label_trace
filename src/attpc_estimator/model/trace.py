from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True, order=True)
class TraceRef:
    run: int
    event_id: int
    trace_id: int


@dataclass(slots=True)
class TraceRecord:
    run: int
    event_id: int
    trace_id: int
    detector: str
    hardware_id: np.ndarray
    raw: np.ndarray
    trace: np.ndarray
    transformed: np.ndarray
    family: str | None
    label: str | None
