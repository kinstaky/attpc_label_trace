from __future__ import annotations

from typing import Any

from ...model.label import StoredLabel
from ...model.trace import TraceRecord


def serialize_trace_payload(
    record: TraceRecord,
    *,
    label: StoredLabel | None,
    review_progress: dict[str, int] | None,
    include_run: bool,
) -> dict[str, Any]:
    payload = {
        "eventId": record.event_id,
        "traceId": record.trace_id,
        "raw": record.raw.tolist(),
        "trace": record.trace.tolist(),
        "transformed": record.transformed.tolist(),
        "currentLabel": serialize_label(label),
        "reviewProgress": review_progress,
    }
    if include_run:
        payload["run"] = int(record.run)
    return payload


def serialize_label(label: StoredLabel | None) -> dict[str, Any] | None:
    if label is None:
        return None
    return {"family": label.family, "label": label.label}
