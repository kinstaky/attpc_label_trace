from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabeledTraceRow:
    run: int
    event_id: int
    trace_id: int
    label_key: str


def canonical_label_key(family: str, label: str) -> str:
    return f"{family}:{label}"


def sanitize_label_key(label_key: str) -> str:
    sanitized = "".join(char.lower() if char.isalnum() else "_" for char in label_key)
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized.strip("_")


def label_title_from_key(label_key: str) -> str:
    family, _, label = label_key.partition(":")
    if family != "normal":
        return label
    if label == "0":
        return "0 peak"
    if label == "4+":
        return "4+ peaks"
    if label == "9":
        return "9+ peaks"
    if label == "1":
        return "1 peak"
    return f"{label} peaks"
