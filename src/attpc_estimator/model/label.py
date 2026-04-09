from __future__ import annotations

from dataclasses import dataclass

NORMAL_BUCKETS = tuple(range(10))


@dataclass(slots=True)
class StoredLabel:
    family: str
    label: str
