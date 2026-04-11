from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    current: int
    total: int
    unit: str
    message: str = ""

    @property
    def percent(self) -> int:
        if self.total <= 0:
            return 100
        bounded = min(max(self.current, 0), self.total)
        return int((bounded * 100) / self.total)


ProgressReporter = Callable[[ProgressUpdate], None]


def emit_progress(
    reporter: ProgressReporter | None,
    *,
    current: int,
    total: int,
    unit: str,
    message: str = "",
) -> None:
    if reporter is None:
        return
    reporter(
        ProgressUpdate(
            current=int(current),
            total=int(total),
            unit=unit,
            message=message,
        )
    )
